# Photo Import Grid Review

## Problem/Feature Description

A travel-journal app imports several user-selected photos into a SwiftUI grid.
The current implementation asks for broad library access before opening the
picker, converts every selected original directly into a `UIImage`, and updates
the grid as each conversion finishes. Recent devices can supply very large
images, and the feature now shows memory spikes and confusing permission UI.

Review the design and provide a corrected implementation outline that preserves
user privacy and keeps thumbnail memory predictable.

## Output Specification

Create `photo-import-review.md` with:

- the recommended selection and loading flow;
- a compact Swift example for the important steps;
- permission behavior for picker-only and custom-library cases; and
- the memory handling required before images enter the grid.
