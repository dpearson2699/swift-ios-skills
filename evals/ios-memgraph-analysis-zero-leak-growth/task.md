# Diagnose Eight Megabytes per Open-Close Cycle

## Problem/Feature Description

A document viewer adds roughly 8 MB each time a large document is opened and
closed. The increase persists after background work has settled and is visible
across five repetitions, yet the team's leak scan reports zero entries. A
baseline memory graph and a graph taken after the fifth close can be captured
from the same build. The team wants an investigation plan that can distinguish
abandoned objects, an intentional cache, allocation growth, and fragmentation
before anyone edits ownership code.

Develop a command-line diagnostic playbook that turns those two captures into
an app-owned, source-actionable hypothesis. Account for both runs where
allocation logging is enabled and runs where it is disabled.

## Output Specification

Create `persistent-growth-playbook.md` containing:

- an ordered decision tree from region-level comparison through a specific
  suspicious allocation and ownership or allocation evidence;
- concrete command templates using `baseline.memgraph` and `post.memgraph`;
- an artifact-retention layout for all raw outputs; and
- a verification protocol that can distinguish a real correction from normal
  run-to-run footprint variation.

No graph files will be supplied. The deliverable is a ready-to-run playbook,
not a claimed diagnosis of this app.
