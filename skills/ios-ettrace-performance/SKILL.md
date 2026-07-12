---
name: ios-ettrace-performance
description: "Use when capturing or analyzing ETTrace profiles for a focused iOS launch or runtime flow, including exact-build dSYM UUID matching, Simulator or device capture, processed per-thread flamegraph JSON, sampled inclusive/exclusive time, unresolved symbols, and comparable verification. Use debugging-instruments or swiftui-performance for generic profiling instead."
---

# iOS ETTrace Performance

Use ETTrace for a bounded, symbolicated sampling experiment. Treat capture
conditions and symbolication as part of the evidence, not as setup trivia.

## Contents

- [Boundary](#boundary)
- [Capture Contract](#capture-contract)
- [Workflow](#workflow)
- [Interpret the Report](#interpret-the-report)
- [Common Mistakes](#common-mistakes)
- [Review Checklist](#review-checklist)
- [References](#references)

## Boundary

This skill owns ETTrace framework/CLI capture, exact-build dSYMs, processed
flamegraph JSON, and like-for-like verification. Use Instruments for broad CPU,
hitch, energy, or concurrency triage. Use SwiftUI performance guidance for view
identity, invalidation, and layout remediation.

ETTrace periodically samples thread stacks. Its durations reconstruct sampled
attribution from those intervals; do not present them as wall-clock production
timings or compare them directly with a differently configured profiler.

## Capture Contract

Write these down before capturing:

- one exact user flow and its start/stop boundary;
- launch capture or already-running runtime capture;
- app commit, build configuration, optimization settings, and architecture;
- ETTrace runner and framework versions, plus single-thread or multi-thread mode;
- simulator/device model and OS build;
- launch method, data state, cache state, and repetition count.

Reject a before/after claim when any of these materially differ. Rebuild and
repeat under one contract instead.

## Workflow

### 1. Triage before instrumenting

Confirm that ETTrace's sampled flamechart is the right next tool. Prefer
Instruments first when the slow interval is unknown, spans many subsystems, or
needs system-level blocking, I/O, hitch, or concurrency context.

Choose one flow small enough to repeat. Launch, first screen construction,
opening one document, or applying one edit are useful boundaries; "use the app"
is not.

### 2. Record and hold ETTrace versions fixed

Install the runner from the official tap and link the ETTrace package product
into the app target being measured. Record the runner version and the framework
revision or tag separately, then keep both fixed across compared captures. The
bundled analyzer supports the verified v1.1.1 processed output shape; re-check
upstream and the parser before using a different format.

```bash
brew install emergetools/homebrew-tap/ettrace
```

Run the instrumented app once and confirm the `Starting ETTrace` log. Absence of
that message means capture evidence is not trustworthy. Keep this wiring out of
shipping configurations unless the project deliberately owns that tradeoff.

### 3. Build first, then collect matching dSYMs

Use the final instrumented build for both capture and dSYM collection. Never
choose a dSYM by filename, modification time, or Derived Data proximity.

```bash
mkdir -p /tmp/myapp-ettrace
python3 scripts/collect_dsyms.py \
  --app /path/to/Build/Products/Release-iphonesimulator/MyApp.app \
  --search-root /path/to/Build/Products \
  --search-root /path/to/Archives \
  --output /tmp/myapp-ettrace/dsyms \
  --pretty > /tmp/myapp-ettrace/dsym-report.json
```

The helper compares `dwarfdump --uuid` output for the app executable and
embedded binaries. Missing or ambiguous UUID matches stop the run by default.
Read and preserve `dsym-report.json` rather than assuming every copied symbol
file is relevant. The helper fails when UUID matches cannot be copied to unique
flat destination names that ETTrace 1.1.1 can discover.

### 4. Capture from a clean artifact directory

Run ETTrace from an empty directory because processed files are written to the
current working directory. Use `--simulator` for Simulator and `--dsyms` for the
exact dSYM directory. Add `--launch` only for launch work, and follow the
runner's two-launch prompts exactly.

```bash
mkdir -p /tmp/myapp-ettrace
mkdir /tmp/myapp-ettrace/run-01
cd /tmp/myapp-ettrace/run-01
ettrace --simulator --dsyms /tmp/myapp-ettrace/dsyms
```

The second `mkdir` must fail if that per-run directory already exists. Choose a
new run name instead of mixing processed captures from retries.

Launch by tapping the app on the Home Screen when the runner asks. Launching
from Xcode can change the launch path and timing. For device capture, omit
`--simulator`; keep all other experiment fields stable.

Stop immediately after the bounded flow and preserve every fresh
`output_<threadId>.json` with the capture contract. ETTrace 1.1.1 creates these
processed files after symbolication. Its internal raw runner `output.json` is a
different artifact and is not accepted by the analyzer below.

### 5. Validate and summarize processed output

```bash
python3 scripts/analyze_ettrace.py \
  /tmp/myapp-ettrace/run-01/output_*.json \
  --top 25 --pretty > /tmp/myapp-ettrace/run-01/summary.json
```

The helper validates the v1.1.1 processed node shape, rejects duplicate inputs
or mixed `osBuild`/`device`/`isSimulator` metadata, handles the serializer's
object-or-array `children` field, and emits deterministic JSON. It does not
rewrite the capture files. Keep those originals beside the summary.

Stop and repair symbolication when important app frames are `<unknown>`, raw
addresses, or attributed to the wrong binary. An unsymbolicated hot address is
an evidence gap, not a code recommendation. ETTrace 1.1.1 address-bearing nodes
are listed under `unresolved_frames` and excluded from ordinary hotspots.

### 6. Change one cause and repeat

Make the smallest code or configuration change supported by a hot app-owned
path. Rebuild, recollect UUID-matched dSYMs, and capture the same flow at least
twice. Report variance and the full capture contract with the result.

## Interpret the Report

- **Exclusive seconds** approximate sampled time charged directly to a symbol
  after subtracting direct child durations. Start with high exclusive app-owned
  work.
- **Inclusive seconds** show the weight of an entire call subtree. Use them to
  find expensive entry paths, not to blame every parent frame.
- Aggregated inclusive time can exceed the root duration because recursive or
  nested appearances count each frame. Exclusive percentages use root duration.
- `<unattributed>` is reported separately. A large value weakens conclusions
  about what happened in the missing interval.
- A framework hotspot may still be caused by app call frequency, data shape, or
  configuration. Walk upward to the first controllable app-owned caller.
- Multi-thread files sum thread time, not wall-clock latency. Do not describe
  their combined root duration as elapsed time.

## Common Mistakes

- Profiling an unbounded session and then guessing which samples match the bug.
- Capturing one build while supplying dSYMs from another build or architecture.
- Treating ETTrace's raw runner JSON as a processed flamegraph.
- Comparing launch capture with runtime capture, or single-thread with
  multi-thread capture.
- Optimizing the top inclusive parent without inspecting exclusive work and
  child paths.
- Claiming improvement from one noisy run.
- Leaving ETTrace instrumentation in production by accident.

## Review Checklist

- [ ] One reproducible flow and start/stop boundary are recorded.
- [ ] Launch/runtime capture mode, single/multi-thread mode, runner version,
      and framework revision match.
- [ ] Build configuration, architecture, target/OS, launch method, and app
      data/cache state match.
- [ ] Every capture starts in a fresh, empty per-run artifact directory.
- [ ] App and embedded-binary UUIDs match the supplied dSYMs.
- [ ] The dSYM collection JSON report is preserved with source/destination and
      missing, ambiguous, collision, or incompatibility evidence.
- [ ] Processed `output_<threadId>.json` files are preserved unchanged.
- [ ] Important app frames are symbolicated.
- [ ] Exclusive, inclusive, unattributed, and multi-thread semantics are clear.
- [ ] The recommendation names an app-controlled path and supporting evidence.
- [ ] Verification repeats the same contract and reports more than one run.
- [ ] Temporary instrumentation is removed or intentionally scoped.

## References

- [ETTrace repository and runner workflow](https://github.com/EmergeTools/ETTrace)
- [ETTrace 1.1.1 release](https://github.com/EmergeTools/ETTrace/releases/tag/v1.1.1)
