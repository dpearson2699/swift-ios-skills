#!/usr/bin/env python3
"""Deterministic regressions for the bundled iOS diagnostics helpers."""

from __future__ import annotations

import argparse
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str, relative_path: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {relative_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ANALYZE = load_script(
    "ios_ettrace_analyze", "skills/ios-ettrace-performance/scripts/analyze_ettrace.py"
)
COLLECT = load_script(
    "ios_ettrace_collect", "skills/ios-ettrace-performance/scripts/collect_dsyms.py"
)
CAPTURE = load_script(
    "ios_memgraph_capture", "skills/ios-memgraph-analysis/scripts/capture_sim_memgraph.py"
)
SUMMARIZE = load_script(
    "ios_memgraph_summarize", "skills/ios-memgraph-analysis/scripts/summarize_memgraph.py"
)


def processed_document(*, device: str = "iPhone", address: int | None = None) -> dict:
    frame = {
        "name": "KnownLookingFrame",
        "library": "/private/MyApp.app/MyApp",
        "start": 0,
        "duration": 1,
        "children": [],
    }
    if address is not None:
        frame["address"] = address
    return {
        "osBuild": "23A1",
        "device": device,
        "isSimulator": True,
        "nodes": {
            "name": "<root>",
            "library": "",
            "start": 0,
            "duration": 1,
            "children": frame,
        },
    }


class AnalyzeETTraceTests(unittest.TestCase):
    def run_main(self, *arguments: str) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with mock.patch.object(sys, "argv", ["analyze_ettrace.py", *arguments]):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                status = ANALYZE.main()
        return status, stdout.getvalue(), stderr.getvalue()

    def test_address_bearing_upstream_node_is_explicitly_unresolved(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            capture = Path(directory) / "output_1.json"
            capture.write_text(json.dumps(processed_document(address=0x1234)), encoding="utf-8")

            status, output, _ = self.run_main(str(capture))

        self.assertEqual(status, 0)
        report = json.loads(output)
        self.assertEqual(report["hotspots"], [])
        self.assertEqual(report["totals"]["unresolved_exclusive_seconds"], 1.0)
        self.assertEqual(report["files"][0]["unresolved_frames"][0]["address"], 0x1234)

    def test_blank_terminal_separator_preserves_parent_exclusive_time(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            capture = Path(directory) / "output_1.json"
            document = processed_document()
            document["nodes"]["children"]["children"] = {
                "name": "",
                "library": "",
                "start": 0,
                "duration": 1,
                "children": [],
            }
            capture.write_text(json.dumps(document), encoding="utf-8")

            status, output, _ = self.run_main(str(capture))

        self.assertEqual(status, 0)
        report = json.loads(output)
        self.assertEqual(report["hotspots"][0]["symbol"], "KnownLookingFrame")
        self.assertEqual(report["hotspots"][0]["exclusive_seconds"], 1.0)
        self.assertEqual(report["totals"]["unattributed_exclusive_seconds"], 0.0)

    def test_duplicate_processed_capture_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            capture = Path(directory) / "output_1.json"
            capture.write_text(json.dumps(processed_document()), encoding="utf-8")
            status, _, error = self.run_main(str(capture), str(capture))

        self.assertEqual(status, 2)
        self.assertIn("duplicate processed capture", error)

    def test_mismatched_capture_metadata_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "output_1.json"
            second = Path(directory) / "output_2.json"
            first.write_text(json.dumps(processed_document(device="Device-A")), encoding="utf-8")
            second.write_text(json.dumps(processed_document(device="Device-B")), encoding="utf-8")
            status, _, error = self.run_main(str(first), str(second))

        self.assertEqual(status, 2)
        self.assertIn("capture metadata does not match", error)
        self.assertIn("device", error)


class CollectDSYMTests(unittest.TestCase):
    def test_in_app_non_framework_binaries_use_app_destination(self) -> None:
        dylib = Path("/Build/MyApp.app/Frameworks/Feature.dylib")
        extension = Path("/Build/MyApp.app/PlugIns/Widget.appex/Widget")

        self.assertEqual(COLLECT.ettrace_destination_name(dylib), ("Feature.dylib.app.dSYM", None))
        self.assertEqual(COLLECT.ettrace_destination_name(extension), ("Widget.app.dSYM", None))

    def test_ettrace_destination_collision_is_rejected_by_plan(self) -> None:
        matches = [
            {
                "binary": "/Build/A/Foo.framework/Foo",
                "dsym": "/Symbols/A/Foo.framework.dSYM",
            },
            {
                "binary": "/Build/B/Foo.framework/Foo",
                "dsym": "/Symbols/B/Foo.framework.dSYM",
            },
        ]

        copy_plan, collisions, incompatible = COLLECT.plan_destinations(matches)

        self.assertEqual(copy_plan, [])
        self.assertEqual(incompatible, [])
        self.assertEqual(collisions[0]["destination"], "Foo.framework.dSYM")
        self.assertEqual(len(collisions[0]["sources"]), 2)

    def test_collision_returns_structured_exit_without_copying(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = root / "MyApp.app"
            symbols = root / "Symbols"
            output = root / "Collected"
            app.mkdir()
            first_dsym = symbols / "A" / "Foo.framework.dSYM"
            second_dsym = symbols / "B" / "Foo.framework.dSYM"
            first_dwarf = first_dsym / "Contents" / "Resources" / "DWARF" / "FooA"
            second_dwarf = second_dsym / "Contents" / "Resources" / "DWARF" / "FooB"
            first_dwarf.parent.mkdir(parents=True)
            second_dwarf.parent.mkdir(parents=True)
            first_dwarf.touch()
            second_dwarf.touch()
            first_binary = Path("/Build/A/Foo.framework/Foo")
            second_binary = Path("/Build/B/Foo.framework/Foo")
            uuid_map = {
                first_binary: {("AAAA", "arm64")},
                second_binary: {("BBBB", "arm64")},
                first_dwarf.resolve(): {("AAAA", "arm64")},
                second_dwarf.resolve(): {("BBBB", "arm64")},
            }
            args = argparse.Namespace(
                app=app,
                search_root=[symbols],
                output=output,
                allow_missing=False,
                dry_run=False,
                pretty=False,
            )

            def fake_dwarfdump(path: Path):
                return uuid_map[path], None

            stdout = io.StringIO()
            with mock.patch.object(COLLECT, "parse_args", return_value=args):
                with mock.patch.object(COLLECT.shutil, "which", return_value="/usr/bin/xcrun"):
                    with mock.patch.object(
                        COLLECT, "build_binaries", return_value=[first_binary, second_binary]
                    ):
                        with mock.patch.object(COLLECT, "run_dwarfdump", side_effect=fake_dwarfdump):
                            with redirect_stdout(stdout), redirect_stderr(io.StringIO()):
                                status = COLLECT.main()

            report = json.loads(stdout.getvalue())
            self.assertEqual(status, 5)
            self.assertEqual(
                report["destination_collisions"][0]["destination"],
                "Foo.framework.dSYM",
            )
            self.assertFalse(output.exists())

    def test_existing_non_directory_output_returns_stable_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = root / "MyApp.app"
            search = root / "Symbols"
            output = root / "not-a-directory"
            app.mkdir()
            search.mkdir()
            output.write_text("occupied", encoding="utf-8")
            args = argparse.Namespace(
                app=app,
                search_root=[search],
                output=output,
                allow_missing=False,
                dry_run=False,
                pretty=False,
            )
            stderr = io.StringIO()
            with mock.patch.object(COLLECT, "parse_args", return_value=args):
                with mock.patch.object(COLLECT.shutil, "which", return_value="/usr/bin/xcrun"):
                    with redirect_stderr(stderr):
                        status = COLLECT.main()

        self.assertEqual(status, 2)
        self.assertIn("exists but is not a directory", stderr.getvalue())


class CaptureMemgraphTests(unittest.TestCase):
    def test_exact_label_accepts_optional_apple_uikit_prefix(self) -> None:
        bundle_id = "com.example.MyApp"

        self.assertTrue(CAPTURE.exact_label(f"UIKitApplication:{bundle_id}[abc]", bundle_id))
        self.assertTrue(
            CAPTURE.exact_label(f"com.apple.UIKitApplication:{bundle_id}[abc]", bundle_id)
        )
        self.assertFalse(
            CAPTURE.exact_label("com.apple.UIKitApplication:com.example.Other[abc]", bundle_id)
        )

    def test_booted_devices_ignores_non_ios_runtimes(self) -> None:
        document = {
            "devices": {
                "com.apple.CoreSimulator.SimRuntime.iOS-26-5": [
                    {"udid": "PHONE", "name": "iPhone", "state": "Booted", "isAvailable": True}
                ],
                "com.apple.CoreSimulator.SimRuntime.watchOS-26-5": [
                    {"udid": "WATCH", "name": "Watch", "state": "Booted", "isAvailable": True}
                ],
            }
        }
        result = subprocess.CompletedProcess(["xcrun"], 0, json.dumps(document), "")

        with mock.patch.object(CAPTURE, "run", return_value=result):
            devices = CAPTURE.booted_devices()

        self.assertEqual([device["udid"] for device in devices], ["PHONE"])

    def test_existing_nonempty_output_is_rejected_before_capture(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory) / "capture"
            output_dir.mkdir()
            (output_dir / "stale.memgraph").write_bytes(b"old")
            args = argparse.Namespace(
                bundle_id="com.example.MyApp", output_dir=output_dir, udid=None, pretty=False
            )
            stderr = io.StringIO()

            with mock.patch.object(CAPTURE, "parse_args", return_value=args):
                with mock.patch.object(CAPTURE.shutil, "which", return_value="/usr/bin/tool"):
                    with mock.patch.object(CAPTURE, "run") as run:
                        with redirect_stderr(stderr):
                            status = CAPTURE.main()

        self.assertEqual(status, 2)
        self.assertEqual(run.call_count, 0)
        self.assertIn("prevent stale captures", stderr.getvalue())

    def test_leaks_error_and_empty_graph_fail_but_preserve_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory) / "capture"
            args = argparse.Namespace(
                bundle_id="com.example.MyApp", output_dir=output_dir, udid=None, pretty=False
            )

            def fake_run(command: list[str]) -> subprocess.CompletedProcess[str]:
                graph_argument = next(value for value in command if value.startswith("--outputGraph="))
                Path(graph_argument.split("=", 1)[1]).touch()
                return subprocess.CompletedProcess(command, 9, "partial", "tool failed")

            stdout = io.StringIO()
            stderr = io.StringIO()
            with mock.patch.object(CAPTURE, "parse_args", return_value=args):
                with mock.patch.object(CAPTURE.shutil, "which", return_value="/usr/bin/tool"):
                    with mock.patch.object(
                        CAPTURE,
                        "booted_devices",
                        return_value=[{"udid": "SIM", "name": "Phone", "runtime": "iOS"}],
                    ):
                        with mock.patch.object(
                            CAPTURE,
                            "process_candidates",
                            return_value=[{"pid": 123, "label": "com.example.MyApp"}],
                        ):
                            with mock.patch.object(CAPTURE, "run", side_effect=fake_run):
                                with redirect_stdout(stdout), redirect_stderr(stderr):
                                    status = CAPTURE.main()

            report = json.loads(stdout.getvalue())
            self.assertEqual(status, 4)
            self.assertEqual(report["status"], "failed")
            self.assertEqual(report["leaks_exit_status"], 9)
            self.assertTrue(Path(report["manifest"]).is_file())
            self.assertTrue(Path(report["raw_stderr"]).is_file())
            self.assertIn("usable nonempty graph", stderr.getvalue())

    def test_leaks_status_one_with_nonempty_graph_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            graph = Path(directory) / "capture.memgraph"
            graph.write_bytes(b"graph")
            self.assertTrue(CAPTURE.capture_succeeded(1, graph))
            self.assertFalse(CAPTURE.capture_succeeded(2, graph))


class SummarizeMemgraphTests(unittest.TestCase):
    def live_args(self, graph: Path, artifacts: Path, **overrides) -> argparse.Namespace:
        values = {
            "memgraph": graph,
            "list_output": None,
            "artifact_dir": artifacts,
            "app_image": [],
            "top": 20,
            "trace_limit": 0,
            "trace_lines": 80,
            "group_by_type": False,
            "reference_tree": False,
            "pretty": False,
        }
        values.update(overrides)
        return argparse.Namespace(**values)

    def test_raw_artifacts_are_exclusive_and_never_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            artifacts = Path(directory)
            first = subprocess.CompletedProcess(["leaks"], 0, "FIRST", "")
            second = subprocess.CompletedProcess(["leaks"], 0, "SECOND", "")
            with mock.patch.object(SUMMARIZE.subprocess, "run", side_effect=[first, second]) as run:
                SUMMARIZE.run_and_preserve(["leaks"], artifacts, "leaks-list")
                with self.assertRaises(SUMMARIZE.ArtifactError):
                    SUMMARIZE.run_and_preserve(["leaks"], artifacts, "leaks-list")

            self.assertEqual(run.call_count, 1)
            self.assertEqual((artifacts / "leaks-list.stdout.txt").read_text(), "FIRST")

    def test_primary_leaks_error_is_tool_failed_with_preserved_raw_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            graph = Path(directory) / "capture.memgraph"
            artifacts = Path(directory) / "raw"
            graph.write_bytes(b"graph")
            args = self.live_args(graph, artifacts)
            result = subprocess.CompletedProcess(
                ["leaks"], 9, "Process App: 1 leak for 16 total leaked bytes", "failed"
            )
            stdout = io.StringIO()
            with mock.patch.object(SUMMARIZE, "parse_args", return_value=args):
                with mock.patch.object(SUMMARIZE.shutil, "which", return_value="/usr/bin/leaks"):
                    with mock.patch.object(SUMMARIZE.subprocess, "run", return_value=result):
                        with redirect_stdout(stdout), redirect_stderr(io.StringIO()):
                            status = SUMMARIZE.main()

            report = json.loads(stdout.getvalue())
            self.assertEqual(status, 3)
            self.assertEqual(report["status"], "tool_failed")
            self.assertTrue(Path(report["source"]["list_command"]["stdout"]).is_file())

    def test_grouped_reference_tree_uses_one_grouped_invocation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            graph = Path(directory) / "capture.memgraph"
            artifacts = Path(directory) / "raw"
            graph.write_bytes(b"graph")
            args = self.live_args(graph, artifacts, group_by_type=True, reference_tree=True)
            commands: list[list[str]] = []

            def fake_run(command: list[str], **_kwargs) -> subprocess.CompletedProcess[str]:
                commands.append(command)
                if "--list" in command:
                    return subprocess.CompletedProcess(
                        command, 0, "Process App: 0 leaks for 0 total leaked bytes", ""
                    )
                return subprocess.CompletedProcess(command, 9, "partial", "optional failed")

            stdout = io.StringIO()
            with mock.patch.object(SUMMARIZE, "parse_args", return_value=args):
                with mock.patch.object(SUMMARIZE.shutil, "which", return_value="/usr/bin/leaks"):
                    with mock.patch.object(SUMMARIZE.subprocess, "run", side_effect=fake_run):
                        with redirect_stdout(stdout), redirect_stderr(io.StringIO()):
                            status = SUMMARIZE.main()

            report = json.loads(stdout.getvalue())
            expected = ["leaks", "--referenceTree", "--groupByType", str(graph.resolve())]
            self.assertEqual(status, 0)
            self.assertIn(expected, commands)
            self.assertFalse(report["artifacts"]["grouped_reference_tree"]["usable"])
            self.assertTrue(any("unusable" in warning for warning in report["warnings"]))


if __name__ == "__main__":
    unittest.main()
