#!/usr/bin/env python3
"""Collect dSYM bundles whose architecture UUIDs match an exact .app build."""

from __future__ import annotations

import argparse
import hashlib
import json
import plistlib
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


UUID_RE = re.compile(r"^UUID:\s+([0-9A-Fa-f-]+)\s+\(([^)]+)\)")


class CollectionError(RuntimeError):
    """The requested build or symbol search cannot be evaluated safely."""


def run_dwarfdump(path: Path) -> tuple[set[tuple[str, str]], str | None]:
    try:
        result = subprocess.run(
            ["xcrun", "dwarfdump", "--uuid", str(path)],
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError as error:
        return set(), f"could not run xcrun dwarfdump: {error}"
    if result.returncode != 0:
        diagnostic = result.stderr.strip() or result.stdout.strip() or "no diagnostic"
        return set(), f"dwarfdump exited {result.returncode}: {diagnostic}"
    values: set[tuple[str, str]] = set()
    for line in result.stdout.splitlines():
        match = UUID_RE.match(line.strip())
        if match:
            values.add((match.group(1).upper(), match.group(2).strip()))
    if not values:
        return set(), "dwarfdump returned no UUID records"
    return values, None


def executable_for_bundle(bundle: Path) -> Path | None:
    plist_candidates = [bundle / "Info.plist", bundle / "Resources" / "Info.plist"]
    for plist_path in plist_candidates:
        try:
            with plist_path.open("rb") as handle:
                executable = plistlib.load(handle).get("CFBundleExecutable")
        except (OSError, plistlib.InvalidFileException):
            continue
        if isinstance(executable, str):
            candidate = bundle / executable
            if candidate.is_file():
                return candidate
    fallback = bundle / bundle.stem
    return fallback if fallback.is_file() else None


def build_binaries(app: Path) -> list[Path]:
    candidates: set[Path] = set()
    main = executable_for_bundle(app)
    if main is None:
        raise CollectionError(f"could not locate CFBundleExecutable in {app}")
    candidates.add(main)
    for suffix in ("*.appex", "*.framework"):
        for bundle in app.rglob(suffix):
            executable = executable_for_bundle(bundle)
            if executable:
                candidates.add(executable)
    candidates.update(path for path in app.rglob("*.dylib") if path.is_file())
    return sorted(candidates)


def dsym_binaries(bundle: Path) -> list[Path]:
    dwarf = bundle / "Contents" / "Resources" / "DWARF"
    return sorted(path for path in dwarf.iterdir() if path.is_file()) if dwarf.is_dir() else []


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Example:
  collect_dsyms.py --app MyApp.app --search-root Build/Products \\
    --search-root Archives --output /tmp/myapp-dsyms --pretty

Exit status: 0 success; 2 invalid input/tool/build UUID failure;
3 ambiguous UUID match; 4 missing UUID match.
Structured JSON is written to stdout; diagnostics are written to stderr.""",
    )
    parser.add_argument("--app", required=True, type=Path, help="Exact .app build")
    parser.add_argument(
        "--search-root",
        required=True,
        action="append",
        type=Path,
        help="Explicit root to scan for .dSYM bundles; repeat as needed",
    )
    parser.add_argument(
        "--output", required=True, type=Path, help="Empty directory for copied matches"
    )
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        help="Copy matches but do not fail when a build UUID has no dSYM",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Report matches without copying dSYMs"
    )
    parser.add_argument("--pretty", action="store_true", help="Indent JSON output")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    app = args.app.resolve()
    output = args.output.resolve()
    if not app.is_dir() or app.suffix != ".app":
        print(f"--app must name an existing .app directory: {app}", file=sys.stderr)
        return 2
    if not shutil.which("xcrun"):
        print("xcrun is required to run dwarfdump; install Xcode command-line tools", file=sys.stderr)
        return 2

    roots = [root.resolve() for root in args.search_root]
    missing_roots = [str(root) for root in roots if not root.is_dir()]
    if missing_roots:
        print(f"search roots do not exist: {missing_roots}", file=sys.stderr)
        return 2
    if not args.dry_run and output.exists() and any(output.iterdir()):
        print(f"--output must be empty to prevent stale dSYMs: {output}", file=sys.stderr)
        return 2

    try:
        binaries = build_binaries(app)
    except CollectionError as error:
        print(error, file=sys.stderr)
        return 2

    target_uuids: dict[Path, set[tuple[str, str]]] = {}
    binary_errors: list[dict[str, str]] = []
    for binary in binaries:
        values, error = run_dwarfdump(binary)
        if error:
            binary_errors.append({"binary": str(binary), "error": error})
        else:
            target_uuids[binary] = values
    if binary_errors:
        json.dump(
            {
                "schema_version": 1,
                "app": str(app),
                "search_roots": [str(root) for root in roots],
                "output": str(output),
                "binary_errors": binary_errors,
            },
            sys.stdout,
            indent=2 if args.pretty else None,
            sort_keys=True,
        )
        sys.stdout.write("\n")
        print("one or more app binaries could not yield UUIDs", file=sys.stderr)
        return 2
    index: dict[tuple[str, str], set[Path]] = defaultdict(set)
    scanned: set[Path] = set()
    scan_errors: list[dict[str, str]] = []
    for root in roots:
        for bundle in root.rglob("*.dSYM"):
            resolved = bundle.resolve()
            if resolved in scanned or output == resolved or output in resolved.parents:
                continue
            scanned.add(resolved)
            for dwarf_binary in dsym_binaries(resolved):
                values, error = run_dwarfdump(dwarf_binary)
                if error:
                    scan_errors.append({"binary": str(dwarf_binary), "error": error})
                    continue
                for value in values:
                    index[value].add(resolved)

    matches: list[dict[str, Any]] = []
    missing: list[dict[str, str]] = []
    ambiguous: list[dict[str, Any]] = []
    selected: set[Path] = set()
    for binary, values in sorted(target_uuids.items()):
        for uuid, arch in sorted(values):
            candidates = sorted(index.get((uuid, arch), set()))
            record = {
                "binary": str(binary),
                "uuid": uuid,
                "architecture": arch,
            }
            if not candidates:
                missing.append(record)
            elif len(candidates) > 1:
                ambiguous.append({**record, "candidates": [str(path) for path in candidates]})
            else:
                selected.add(candidates[0])
                matches.append({**record, "dsym": str(candidates[0])})

    copied: list[dict[str, str]] = []
    if not args.dry_run and not ambiguous and (args.allow_missing or not missing):
        output.mkdir(parents=True, exist_ok=True)
        used_destinations: set[Path] = set()
        for source in sorted(selected):
            destination = output / source.name
            if destination in used_destinations or destination.exists():
                digest = hashlib.sha256(str(source).encode()).hexdigest()[:8]
                destination = output / f"{source.stem}-{digest}.dSYM"
            shutil.copytree(source, destination)
            used_destinations.add(destination)
            copied.append({"source": str(source), "destination": str(destination)})

    report = {
        "schema_version": 1,
        "app": str(app),
        "search_roots": [str(root) for root in roots],
        "output": str(output),
        "dry_run": args.dry_run,
        "scanned_dsym_bundles": len(scanned),
        "matches": matches,
        "missing": missing,
        "ambiguous": ambiguous,
        "scan_errors": scan_errors,
        "copied": copied,
    }
    json.dump(report, sys.stdout, indent=2 if args.pretty else None, sort_keys=True)
    sys.stdout.write("\n")

    if ambiguous:
        print("ambiguous dSYM UUID matches; narrow --search-root", file=sys.stderr)
        return 3
    if missing and not args.allow_missing:
        print("one or more build UUIDs have no matching dSYM", file=sys.stderr)
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
