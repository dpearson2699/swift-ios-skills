# Refactor an Account Dashboard for Independent Development

## Problem/Feature Description

An iOS 26 account dashboard has grown to roughly 420 lines. Its header is a short stateless fragment, while the activity area contains multiple loading and failure branches, launches asynchronous work, and reads a small part of a much larger observable store. The file has already been split into extensions with section markers, but engineers still struggle to follow the parent data flow or work on the activity UI independently.

The dashboard preview currently avoids missing-dependency failures by making several production dependencies optional. It signs in through the live service and opens the production SwiftData store, which makes preview behavior slow and inconsistent across developers.

Produce a focused review that establishes useful view boundaries and a safe preview construction approach without introducing a new architecture layer or weakening production dependency contracts.

## Output Specification

Create `recommendation.md` containing:

- the proposed view boundary and input/action interface;
- what should remain local to the parent;
- how preview states and dependencies should be constructed;
- the boundary between this SwiftUI composition guidance and deeper concurrency guidance.
