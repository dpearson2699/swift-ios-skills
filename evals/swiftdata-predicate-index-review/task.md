# Slow SwiftData Query Review

## Problem/Feature Description

A trip list filters by destination, excludes expired records using the current
time, and sorts by start date. Its predicate invokes a convenience method on
the model. The proposed performance fix is to index every property and assume
index changes never need migration testing.

Review the query and propose a measured predicate and indexing plan.

## Output Specification

Create `swiftdata-query-review.md` with a corrected predicate sketch, index
selection guidance, and a verification plan for performance and schema changes.
