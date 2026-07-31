# Swift Synchronous Buffer Processing Review

## Problem/Feature Description

An image-processing library exposes a synchronous callback that reads one
pixel buffer and fills another. Profiling on supported devices shows that its
current `DispatchQueue.concurrentPerform` loop is materially faster than the
serial implementation. After enabling Swift 6.3 complete concurrency checking,
the closure's captures of `UnsafeBufferPointer<UInt16>` and
`UnsafeMutableBufferPointer<UInt16>` no longer compile.

The separate-output path returns a fresh `[UInt16]` built with
`Array(unsafeUninitializedCapacity:)`. A second entry point transforms an
already initialized buffer in place, so its input and output base address are
the same allocation.

The team is considering either replacing the loop with one task-group child per
pixel or marking the entire processing utility `nonisolated(unsafe)`. The
operation is sometimes called from a cancellable Swift task, and callers need a
defined result if cancellation occurs while processing is underway.

Review those proposals and recommend the smallest safe correction. Include a
compact corrected implementation for an element-wise transform and explain
what must be re-audited if the index calculation later changes to use
multi-element tiles. State which measurements and result comparisons must keep
passing before the parallel implementation remains justified.

## Output Specification

Create `parallel-buffer-review.md` containing the recommendation, corrected
Swift code, the safety argument for that code, and the cancellation contract.
Keep the public processing entry point synchronous.
