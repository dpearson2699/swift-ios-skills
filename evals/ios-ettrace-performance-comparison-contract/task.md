# Evaluate a Claimed ETTrace Improvement

## Problem/Feature Description

The team reports that a search feature is 35% faster after a refactor. The before capture
used a Debug Simulator build, single-thread runtime mode, ETTrace runner 1.1.0, framework
revision A, a warm cache, and an Xcode launch. The after capture used a Release build,
multi-thread launch mode, ETTrace runner 1.1.1, framework revision B, a cold cache, and a
Home Screen launch. The 35% number is the decrease in the sum of root durations across
all after-capture thread files.

Review the claim and design the smallest valid rerun that could determine whether the
refactor improved the bounded search flow. Also state whether another profiler should be
used first if the location of the delay is still unknown.

## Output Specification

Create a file named `ettrace-comparison-review.md` containing:

- A verdict on the 35% claim and a discrete confound checklist.
- A normalized capture contract table with one controlled dimension per row.
- Symbolication, artifact, and repetition requirements.
- Correct interpretation of multi-thread and sampled durations.
- The boundary between ETTrace and broader Instruments triage.
