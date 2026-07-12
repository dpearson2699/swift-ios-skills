# Stabilize a Paged Canvas-to-Details Editor

## Problem/Feature Description

An iOS 26 media editor pages vertically from a full-screen canvas into a secondary details surface. During the transition, the product wants the canvas, toolbar, and reveal affordance to change smoothly with the user's movement.

The prototype has become unstable: several stored flags disagree during interrupted drags, a second drag recognizer competes with paging, haptics repeat while the finger moves, toolbar appearance can shift the content mid-scroll, and zoom or crop gestures fight vertical navigation. The implementation also forwards raw geometry through the screen's shared model, causing unrelated controls to update continuously.

Produce a modern SwiftUI layout recommendation and compact code sketch that makes the transition coherent while leaving document, crop, zoom, and command-domain logic in their existing owners.

## Output Specification

Create `recommendation.md` describing the scroll structure, continuous transition state, discrete side-effect timing, interaction arbitration, and invalidation/layout safeguards.
