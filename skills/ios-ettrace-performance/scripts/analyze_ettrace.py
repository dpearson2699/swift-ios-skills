#!/usr/bin/env python3
"""Validate and summarize ETTrace 1.1.1 processed flamegraph JSON."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


class InputError(ValueError):
    """An ETTrace artifact does not match the supported processed shape."""


def nonnegative_number(value: Any, field: str, source: Path) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InputError(f"{source}: {field} must be a number")
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise InputError(f"{source}: {field} must be finite and nonnegative")
    return number


def processed_address(value: Any, field: str, source: Path) -> int | None:
    """Validate ETTrace v1.1.1's optional unresolved-address marker."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise InputError(f"{source}: {field} must be a nonnegative integer or null")
    return value


def child_nodes(value: Any, field: str, source: Path) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        return [value]
    if isinstance(value, list) and all(isinstance(item, dict) for item in value):
        return value
    raise InputError(
        f"{source}: {field} must be an object or an array of objects "
        "(the ETTrace 1.1.1 processed shape)"
    )


def load_processed(path: Path) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise InputError(f"{path}: cannot read file: {error}") from error
    except json.JSONDecodeError as error:
        raise InputError(f"{path}: malformed JSON: {error}") from error

    if not isinstance(document, dict):
        raise InputError(f"{path}: top level must be an object")
    if "nodes" not in document:
        raise InputError(
            f"{path}: missing top-level 'nodes'; this may be ETTrace runner raw "
            "output.json rather than processed output_<threadId>.json"
        )
    if not isinstance(document["nodes"], dict):
        raise InputError(f"{path}: top-level 'nodes' must be an object")
    return document


def analyze_file(
    path: Path,
    pattern: re.Pattern[str] | None,
    totals: dict[tuple[str, str], dict[str, float | int]],
) -> tuple[dict[str, Any], list[str]]:
    document = load_processed(path)
    root = document["nodes"]
    root_duration = nonnegative_number(root.get("duration"), "nodes.duration", path)
    if not child_nodes(root.get("children"), "nodes.children", path):
        raise InputError(f"{path}: processed flamegraph contains no sampled nodes")
    warnings: list[str] = []
    unattributed = 0.0
    unresolved = 0.0
    unresolved_frames: dict[tuple[str, str, int | None], dict[str, Any]] = {}
    node_count = 0
    stack: list[tuple[dict[str, Any], str]] = [(root, "nodes")]

    while stack:
        node, location = stack.pop()
        node_count += 1
        name = node.get("name")
        library = node.get("library", "")
        if not isinstance(name, str):
            raise InputError(f"{path}: {location}.name must be a string")
        if not isinstance(library, str):
            raise InputError(f"{path}: {location}.library must be a string")

        start = nonnegative_number(node.get("start"), f"{location}.start", path)
        duration = nonnegative_number(
            node.get("duration"), f"{location}.duration", path
        )
        address = processed_address(node.get("address"), f"{location}.address", path)
        children = child_nodes(node.get("children"), f"{location}.children", path)
        child_duration = 0.0
        for index, child in enumerate(children):
            duration_value = nonnegative_number(
                child.get("duration"),
                f"{location}.children[{index}].duration",
                path,
            )
            is_separator = child.get("name") == "" and child.get("library", "") == ""
            if not is_separator:
                child_duration += duration_value
            stack.append((child, f"{location}.children[{index}]"))

        exclusive = duration - child_duration
        tolerance = max(1e-9, duration * 1e-9)
        if exclusive < -tolerance:
            warnings.append(
                f"{location} child durations exceed parent duration by "
                f"{-exclusive:.9f}s; exclusive time was clamped to zero"
            )
        exclusive = max(0.0, exclusive)

        if name == "<unattributed>":
            unattributed += exclusive
        is_unresolved = name == "<unknown>" or library == "<unknown>" or address is not None
        if is_unresolved:
            unresolved += exclusive
            key = (name, library, address)
            entry = unresolved_frames.setdefault(
                key,
                {
                    "symbol": name,
                    "library": library,
                    "address": address,
                    "occurrences": 0,
                    "inclusive_seconds": 0.0,
                    "exclusive_seconds": 0.0,
                },
            )
            entry["occurrences"] += 1
            entry["inclusive_seconds"] += duration
            entry["exclusive_seconds"] += exclusive
            if address is not None:
                warnings.append(
                    f"{location} carries address {address}; ETTrace 1.1.1 marks "
                    "this frame unresolved"
                )

        is_sentinel = name in {"", "<root>", "<unattributed>"}
        matches = pattern is None or pattern.search(f"{library} {name}") is not None
        if not is_sentinel and not is_unresolved and matches:
            entry = totals[(name, library)]
            entry["occurrences"] = int(entry["occurrences"]) + 1
            entry["inclusive_seconds"] = float(entry["inclusive_seconds"]) + duration
            entry["exclusive_seconds"] = float(entry["exclusive_seconds"]) + exclusive

        # Access validates that start is finite even though aggregation does not use it.
        _ = start

    metadata = {
        "path": str(path.resolve()),
        "root_duration_seconds": root_duration,
        "node_count": node_count,
        "unattributed_exclusive_seconds": unattributed,
        "unresolved_exclusive_seconds": unresolved,
        "unresolved_frames": sorted(
            unresolved_frames.values(),
            key=lambda item: (
                -float(item["exclusive_seconds"]),
                item["symbol"],
                item["library"],
                -1 if item["address"] is None else int(item["address"]),
            ),
        ),
        "os_build": document.get("osBuild"),
        "device": document.get("device"),
        "is_simulator": document.get("isSimulator"),
    }
    return metadata, warnings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  analyze_ettrace.py output_123.json --top 25 --pretty
  analyze_ettrace.py output_*.json --sort inclusive --match 'MyApp|FeatureKit'

Exit status: 0 success; 2 invalid arguments, unreadable JSON, or unsupported shape.
Structured JSON is written to stdout; diagnostics are written to stderr.""",
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        type=Path,
        help="One or more processed v1.1.1 output_<threadId>.json files",
    )
    parser.add_argument("--top", type=int, default=20, help="Maximum hotspots (1-200)")
    parser.add_argument(
        "--sort",
        choices=("exclusive", "inclusive"),
        default="exclusive",
        help="Hotspot ordering (default: exclusive)",
    )
    parser.add_argument(
        "--match", help="Only include symbols/libraries matching this regular expression"
    )
    parser.add_argument("--pretty", action="store_true", help="Indent JSON output")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not 1 <= args.top <= 200:
        print("--top must be between 1 and 200", file=sys.stderr)
        return 2

    try:
        pattern = re.compile(args.match) if args.match else None
    except re.error as error:
        print(f"invalid --match expression: {error}", file=sys.stderr)
        return 2

    totals: dict[tuple[str, str], dict[str, float | int]] = defaultdict(
        lambda: {"occurrences": 0, "inclusive_seconds": 0.0, "exclusive_seconds": 0.0}
    )
    files: list[dict[str, Any]] = []
    warnings: list[str] = []
    try:
        resolved_inputs: list[Path] = []
        seen_inputs: dict[Path, Path] = {}
        for supplied in args.inputs:
            path = supplied.resolve()
            if path in seen_inputs:
                raise InputError(
                    f"duplicate processed capture: {supplied} resolves to the same file as "
                    f"{seen_inputs[path]}"
                )
            seen_inputs[path] = supplied
            resolved_inputs.append(path)

        expected_capture: dict[str, Any] | None = None
        for path in resolved_inputs:
            metadata, file_warnings = analyze_file(path, pattern, totals)
            capture = {
                "os_build": metadata["os_build"],
                "device": metadata["device"],
                "is_simulator": metadata["is_simulator"],
            }
            if expected_capture is None:
                expected_capture = capture
            elif capture != expected_capture:
                mismatches = [
                    key for key in expected_capture if capture[key] != expected_capture[key]
                ]
                raise InputError(
                    f"{path}: capture metadata does not match the first input for "
                    f"{', '.join(mismatches)}"
                )
            files.append(metadata)
            warnings.extend(f"{path}: {warning}" for warning in file_warnings)
    except InputError as error:
        print(error, file=sys.stderr)
        return 2

    root_total = sum(item["root_duration_seconds"] for item in files)
    sort_key = f"{args.sort}_seconds"
    hotspots: list[dict[str, Any]] = []
    for (name, library), values in totals.items():
        entry: dict[str, Any] = {"symbol": name, "library": library, **values}
        exclusive = float(values["exclusive_seconds"])
        entry["exclusive_percent_of_summed_thread_time"] = (
            exclusive / root_total * 100.0 if root_total else 0.0
        )
        hotspots.append(entry)

    hotspots.sort(
        key=lambda item: (
            -float(item[sort_key]),
            -float(item["exclusive_seconds"]),
            -float(item["inclusive_seconds"]),
            item["symbol"],
            item["library"],
        )
    )

    report = {
        "schema_version": 1,
        "input_contract": "ETTrace 1.1.1 processed output_<threadId>.json",
        "files": files,
        "totals": {
            "summed_thread_time_seconds": root_total,
            "unattributed_exclusive_seconds": sum(
                item["unattributed_exclusive_seconds"] for item in files
            ),
            "unresolved_exclusive_seconds": sum(
                item["unresolved_exclusive_seconds"] for item in files
            ),
            "note": "Summed thread time is not wall-clock elapsed time.",
        },
        "sort": args.sort,
        "match": args.match,
        "hotspots": hotspots[: args.top],
        "warnings": warnings,
    }
    json.dump(report, sys.stdout, indent=2 if args.pretty else None, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
