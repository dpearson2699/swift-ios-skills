---
name: swiftui-animation
description: "Implement, review, or improve SwiftUI animations and transitions. Use when adding implicit or explicit animations with withAnimation, configuring spring animations (.smooth, .snappy, .bouncy), building phase or keyframe animations with PhaseAnimator/KeyframeAnimator, creating hero transitions with matchedGeometryEffect or matchedTransitionSource, adding SF Symbol effects (bounce, pulse, variableColor, breathe, rotate, wiggle), implementing custom Transition or CustomAnimation types, or ensuring animations respect accessibilityReduceMotion."
---

# SwiftUI Animation (iOS 26+)

Review, write, and fix SwiftUI animations. Apply modern animation APIs with
correct timing, transitions, and accessibility handling using Swift 6.2 patterns.

## Triage Workflow

### Step 1: Identify the animation category

| Category | API | When to use |
|---|---|---|
| State-driven | `withAnimation`, `.animation(_:value:)` | Simple property changes |
| Multi-phase | `PhaseAnimator` | Sequenced multi-step animations |
| Keyframe | `KeyframeAnimator` | Complex multi-property choreography |
| Shared element | `matchedGeometryEffect` | Layout-driven hero transitions |
| Navigation | `matchedTransitionSource` + `.navigationTransition(.zoom)` | NavigationStack push/pop zoom |
| View lifecycle | `.transition()` | Insertion and removal |
| Text content | `.contentTransition()` | In-place text/number changes |
| Symbol | `.symbolEffect()` | SF Symbol animations |
| Custom | `CustomAnimation` protocol | Novel timing curves |

### Step 2: Choose the animation curve

```swift
// Timing curves
.linear                              // constant speed
.easeIn(duration: 0.3)              // slow start
.easeOut(duration: 0.3)             // slow end
.easeInOut(duration: 0.3)           // slow start and end

// Spring presets (preferred for natural motion)
.smooth                              // no bounce, fluid
.smooth(duration: 0.5, extraBounce: 0.0)
.snappy                              // small bounce, responsive
.snappy(duration: 0.4, extraBounce: 0.1)
.bouncy                              // visible bounce, playful
.bouncy(duration: 0.5, extraBounce: 0.2)

// Custom spring
.spring(duration: 0.5, bounce: 0.3, blendDuration: 0.0)
.spring(Spring(duration: 0.6, bounce: 0.2), blendDuration: 0.0)
.interactiveSpring(response: 0.15, dampingFraction: 0.86)
```

### Step 3: Apply and verify

- Confirm animation triggers on the correct state change.
- Test with Accessibility > Reduce Motion enabled.
- Verify no expensive work runs inside animation content closures.

## withAnimation (Explicit Animation)

```swift
withAnimation(.spring) { isExpanded.toggle() }

// With completion (iOS 17+)
withAnimation(.smooth(duration: 0.35), completionCriteria: .logicallyComplete) {
    isExpanded = true
} completion: { loadContent() }
```

## .animation(_:value:) (Implicit Animation)

```swift
Circle()
    .scaleEffect(isActive ? 1.2 : 1.0)
    .opacity(isActive ? 1.0 : 0.6)
    .animation(.bouncy, value: isActive)
```

## Spring Type (iOS 17+)

Four initializer forms for different mental models.

```swift
// Perceptual (preferred)
Spring(duration: 0.5, bounce: 0.3)

// Physical
Spring(mass: 1.0, stiffness: 100.0, damping: 10.0)

// Response-based
Spring(response: 0.5, dampingRatio: 0.7)

// Settling-based
Spring(settlingDuration: 1.0, dampingRatio: 0.8)
```

Three presets mirror Animation presets: `.smooth`, `.snappy`, `.bouncy`.

## PhaseAnimator (iOS 17+)

Cycle through discrete phases with per-phase animation curves.

```swift
enum PulsePhase: CaseIterable {
    case idle, grow, shrink
}

struct PulsingDot: View {
    var body: some View {
        PhaseAnimator(PulsePhase.allCases) { phase in
            Circle()
                .frame(width: 40, height: 40)
                .scaleEffect(phase == .grow ? 1.4 : 1.0)
                .opacity(phase == .shrink ? 0.5 : 1.0)
        } animation: { phase in
            switch phase {
            case .idle: .easeIn(duration: 0.2)
            case .grow: .spring(duration: 0.4, bounce: 0.3)
            case .shrink: .easeOut(duration: 0.3)
            }
        }
    }
}
```

Trigger-based variant runs one cycle per trigger change:

```swift
PhaseAnimator(PulsePhase.allCases, trigger: tapCount) { phase in
    // ...
} animation: { _ in .spring(duration: 0.4) }
```

## KeyframeAnimator (iOS 17+)

Animate multiple properties along independent timelines.

```swift
struct AnimValues {
    var scale: Double = 1.0
    var yOffset: Double = 0.0
    var opacity: Double = 1.0
}

struct BounceView: View {
    @State private var trigger = false

    var body: some View {
        Image(systemName: "star.fill")
            .font(.largeTitle)
            .keyframeAnimator(
                initialValue: AnimValues(),
                trigger: trigger
            ) { content, value in
                content
                    .scaleEffect(value.scale)
                    .offset(y: value.yOffset)
                    .opacity(value.opacity)
            } keyframes: { _ in
                KeyframeTrack(\.scale) {
                    SpringKeyframe(1.5, duration: 0.3)
                    CubicKeyframe(1.0, duration: 0.4)
                }
                KeyframeTrack(\.yOffset) {
                    CubicKeyframe(-30, duration: 0.2)
                    CubicKeyframe(0, duration: 0.4)
                }
                KeyframeTrack(\.opacity) {
                    LinearKeyframe(0.6, duration: 0.15)
                    LinearKeyframe(1.0, duration: 0.25)
                }
            }
            .onTapGesture { trigger.toggle() }
    }
}
```

Keyframe types: `LinearKeyframe` (linear), `CubicKeyframe` (smooth curve),
`SpringKeyframe` (spring physics), `MoveKeyframe` (instant jump).

Use `repeating: true` for looping keyframe animations.

## @Animatable Macro

Replaces manual `AnimatableData` boilerplate. Attach to any type with
animatable stored properties.

```swift
// WRONG: Manual AnimatableData (verbose, error-prone)
struct WaveShape: Shape, Animatable {
    var frequency: Double
    var amplitude: Double
    var phase: Double

    var animatableData: AnimatablePair<Double, AnimatablePair<Double, Double>> {
        get { AnimatablePair(frequency, AnimatablePair(amplitude, phase)) }
        set {
            frequency = newValue.first
            amplitude = newValue.second.first
            phase = newValue.second.second
        }
    }
    // ...
}

// CORRECT: @Animatable macro synthesizes animatableData
@Animatable
struct WaveShape: Shape {
    var frequency: Double
    var amplitude: Double
    var phase: Double
    @AnimatableIgnored var lineWidth: CGFloat

    func path(in rect: CGRect) -> Path {
        // draw wave using frequency, amplitude, phase
    }
}
```

Rules:
- Stored properties must conform to `VectorArithmetic`.
- Use `@AnimatableIgnored` to exclude non-animatable properties.
- Computed properties are never included.

## matchedGeometryEffect (iOS 14+)

Synchronize geometry between views for shared-element animations.

```swift
struct HeroView: View {
    @Namespace private var heroSpace
    @State private var isExpanded = false

    var body: some View {
        if isExpanded {
            DetailCard()
                .matchedGeometryEffect(id: "card", in: heroSpace)
                .onTapGesture {
                    withAnimation(.spring(duration: 0.4, bounce: 0.2)) {
                        isExpanded = false
                    }
                }
        } else {
            ThumbnailCard()
                .matchedGeometryEffect(id: "card", in: heroSpace)
                .onTapGesture {
                    withAnimation(.spring(duration: 0.4, bounce: 0.2)) {
                        isExpanded = true
                    }
                }
        }
    }
}
```

Exactly one view per ID must be visible at a time for the interpolation to work.

## Navigation Zoom Transition (iOS 18+)

Pair `matchedTransitionSource` on the source view with
`.navigationTransition(.zoom(...))` on the destination.

```swift
struct GalleryView: View {
    @Namespace private var zoomSpace
    let items: [GalleryItem]

    var body: some View {
        NavigationStack {
            ScrollView {
                LazyVGrid(columns: [GridItem(.adaptive(minimum: 100))]) {
                    ForEach(items) { item in
                        NavigationLink {
                            GalleryDetail(item: item)
                                .navigationTransition(
                                    .zoom(sourceID: item.id, in: zoomSpace)
                                )
                        } label: {
                            ItemThumbnail(item: item)
                                .matchedTransitionSource(
                                    id: item.id, in: zoomSpace
                                )
                        }
                    }
                }
            }
        }
    }
}
```

Apply `.navigationTransition` on the destination view, not on inner containers.

## Transitions (iOS 17+)

Control how views animate on insertion and removal.

```swift
if showBanner {
    BannerView()
        .transition(.move(edge: .top).combined(with: .opacity))
}
```

Built-in types: `.opacity`, `.slide`, `.scale`, `.scale(_:anchor:)`,
`.move(edge:)`, `.push(from:)`, `.offset(x:y:)`, `.identity`,
`.blurReplace`, `.blurReplace(_:)`, `.symbolEffect`,
`.symbolEffect(_:options:)`.

Asymmetric transitions:

```swift
.transition(.asymmetric(
    insertion: .push(from: .bottom),
    removal: .opacity
))
```

## ContentTransition (iOS 16+)

Animate in-place content changes without insertion/removal.

```swift
Text("\(score)")
    .contentTransition(.numericText(countsDown: false))
    .animation(.snappy, value: score)

// For SF Symbols
Image(systemName: isMuted ? "speaker.slash" : "speaker.wave.3")
    .contentTransition(.symbolEffect(.replace.downUp))
```

Types: `.identity`, `.interpolate`, `.opacity`,
`.numericText(countsDown:)`, `.numericText(value:)`, `.symbolEffect`.

## Symbol Effects (iOS 17+)

Animate SF Symbols with semantic effects.

```swift
// Discrete (triggers on value change)
Image(systemName: "bell.fill")
    .symbolEffect(.bounce, value: notificationCount)

Image(systemName: "arrow.clockwise")
    .symbolEffect(.wiggle.clockwise, value: refreshCount)

// Indefinite (active while condition holds)
Image(systemName: "wifi")
    .symbolEffect(.pulse, isActive: isSearching)

Image(systemName: "mic.fill")
    .symbolEffect(.breathe, isActive: isRecording)

// Variable color with chaining
Image(systemName: "speaker.wave.3.fill")
    .symbolEffect(
        .variableColor.iterative.reversing.dimInactiveLayers,
        options: .repeating,
        isActive: isPlaying
    )
```

All effects: `.bounce`, `.pulse`, `.variableColor`, `.scale`, `.appear`,
`.disappear`, `.replace`, `.breathe`, `.rotate`, `.wiggle`.

Scope: `.byLayer`, `.wholeSymbol`. Direction varies per effect.

## Common Mistakes

### 1. Animating without a value binding

```swift
// WRONG: .animation without value triggers on any state change
Text("Hello")
    .opacity(isVisible ? 1 : 0)
    .animation(.easeIn)

// CORRECT: Bind to the specific value
Text("Hello")
    .opacity(isVisible ? 1 : 0)
    .animation(.easeIn, value: isVisible)
```

### 2. Expensive work inside animation closures

```swift
// WRONG: Heavy computation every frame
.keyframeAnimator(initialValue: vals, trigger: t) { content, value in
    let filtered = applyExpensiveFilter(content)  // runs every frame
    return filtered.opacity(value.opacity)
} keyframes: { _ in /* ... */ }

// CORRECT: Precompute outside, animate only visual properties
.keyframeAnimator(initialValue: vals, trigger: t) { content, value in
    content.opacity(value.opacity)
} keyframes: { _ in /* ... */ }
```

### 3. Missing reduce motion support

```swift
// WRONG: Ignores accessibility setting
withAnimation(.bouncy) { showDetail = true }

// CORRECT: Respect reduce motion
@Environment(\.accessibilityReduceMotion) private var reduceMotion

withAnimation(reduceMotion ? .none : .bouncy) { showDetail = true }
```

### 4. Multiple matchedGeometryEffect sources

```swift
// WRONG: Both visible with same ID -- undefined behavior
HStack {
    Circle().matchedGeometryEffect(id: "dot", in: ns)
    Circle().matchedGeometryEffect(id: "dot", in: ns)
}

// CORRECT: Only one source visible at a time via conditional
if onLeft {
    Circle().matchedGeometryEffect(id: "dot", in: ns)
} else {
    Circle().matchedGeometryEffect(id: "dot", in: ns)
}
```

### 5. Using DispatchQueue or UIView.animate

```swift
// WRONG: UIKit patterns in SwiftUI
DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
    withAnimation { isVisible = true }
}
UIView.animate(withDuration: 0.3) { /* ... */ }

// CORRECT: SwiftUI animation with delay
withAnimation(.spring.delay(0.5)) { isVisible = true }
withAnimation(.easeInOut(duration: 0.3)) { /* state change */ }
```

### 6. Forgetting animation on ContentTransition

```swift
// WRONG: No animation -- content transition has no effect
Text("\(count)")
    .contentTransition(.numericText(countsDown: true))

// CORRECT: Pair with animation modifier
Text("\(count)")
    .contentTransition(.numericText(countsDown: true))
    .animation(.snappy, value: count)
```

### 7. navigationTransition on wrong view

```swift
// WRONG: Applied inside a container
NavigationLink {
    VStack {
        DetailView(item: item)
            .navigationTransition(.zoom(sourceID: item.id, in: ns))
    }
} label: { /* ... */ }

// CORRECT: Applied on the outermost destination view
NavigationLink {
    DetailView(item: item)
        .navigationTransition(.zoom(sourceID: item.id, in: ns))
} label: { /* ... */ }
```

## Review Checklist

- [ ] Animation curve matches intent (spring for natural, ease for mechanical)
- [ ] `withAnimation` wraps the state change, not the view
- [ ] `.animation(_:value:)` has an explicit `value` parameter
- [ ] `matchedGeometryEffect` has exactly one source per ID at a time
- [ ] Navigation zoom uses matching `id` and `namespace` on source and destination
- [ ] `@Animatable` macro used instead of manual `animatableData`
- [ ] `accessibilityReduceMotion` is checked and respected
- [ ] No heavy computation inside keyframe/phase content closures
- [ ] No `DispatchQueue` or `UIView.animate` for animation timing
- [ ] Transitions use `.transition()` on conditionally inserted views
- [ ] `contentTransition` is paired with `.animation(_:value:)`
- [ ] Symbol effects use correct category (discrete vs indefinite)
- [ ] Ensure animated state changes happen on @MainActor; types driving animations should be Sendable if passed across concurrency boundaries

## Reference Material

- See `references/animation-advanced.md` for CustomAnimation protocol,
  full Spring variants, all Transition types, symbol effect details, Transaction
  system, UnitCurve types, and performance guidance.

