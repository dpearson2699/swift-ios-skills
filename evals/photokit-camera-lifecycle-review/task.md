# Camera Session Concurrency Review

## Problem/Feature Description

A SwiftUI camera screen intermittently freezes during launch and sometimes
reports that its capture session is in an invalid configuration state. The
controller configures the session from UI-isolated code, starts it from an
unstructured background task, and stops it from a separate callback queue. One
configuration guard can also exit before the transaction is closed.

Review the lifecycle and propose a small controller design that removes the
races while keeping the preview responsive.

## Output Specification

Create `camera-lifecycle-review.md` containing:

- the corrected ownership and serialization model;
- pseudocode or Swift for configuration, start, and stop;
- the permission ordering and configuration failure path; and
- the responsibility of the SwiftUI preview wrapper.
