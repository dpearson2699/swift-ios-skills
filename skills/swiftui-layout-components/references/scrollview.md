# ScrollView and Lazy stacks

## Contents

- [Intent](#intent)
- [Core patterns](#core-patterns)
- [Example: vertical custom feed](#example-vertical-custom-feed)
- [ScrollPosition capabilities](#scrollposition-capabilities)
- [Paged primary and detail reveals](#paged-primary-and-detail-reveals)
- [Example: horizontal chips](#example-horizontal-chips)
- [Example: adaptive grid](#example-adaptive-grid)
- [Design choices to keep](#design-choices-to-keep)
- [iOS 26 Scroll Edge Effects](#ios-26-scroll-edge-effects)
- [Pitfalls](#pitfalls)

## Intent

Use `ScrollView` with `LazyVStack`, `LazyHStack`, or `LazyVGrid` when you need custom layout, mixed content, or horizontal/ grid-based scrolling.

## Core patterns

- Prefer `ScrollView` + `LazyVStack` for chat-like or custom feed layouts.
- Use `ScrollView(.horizontal)` + `LazyHStack` for chips, tags, avatars, and media strips.
- Use `LazyVGrid` for icon/media grids; prefer adaptive columns when possible.
- Use `ScrollPosition` for programmatic scrolling: scroll-to-id, scroll-to-edge, and point-based offsets.
- Use `safeAreaInset(edge:)` for input bars that should stick above the keyboard.

## Example: vertical custom feed

```swift
@MainActor
struct ConversationView: View {
  @State private var scrollPosition = ScrollPosition(edge: .bottom)

  var body: some View {
    ScrollView {
      LazyVStack {
        ForEach(messages) { message in
          MessageRow(message: message)
        }
      }
      .scrollTargetLayout()
      .padding(.horizontal, .layoutPadding)
    }
    .scrollPosition($scrollPosition)
    .safeAreaInset(edge: .bottom) {
      MessageInputBar()
    }
    .onChange(of: messages.last?.id) {
      withAnimation { scrollPosition.scrollTo(edge: .bottom) }
    }
  }
}
```

## ScrollPosition capabilities

`ScrollPosition` (iOS 18+) replaces `ScrollViewReader` for programmatic scrolling. It is declarative, supports bidirectional position tracking, and does not require a closure wrapper.

**Setup:** Declare state and attach to the scroll view. Apply `.scrollTargetLayout()` to the inner layout container so SwiftUI can track individual view identities.

```swift
@State private var scrollPosition = ScrollPosition(idType: Message.ID.self)

ScrollView {
    LazyVStack {
        ForEach(messages) { message in
            MessageRow(message: message)
        }
    }
    .scrollTargetLayout()
}
.scrollPosition($scrollPosition)
```

**Scroll to a specific item:**

```swift
scrollPosition.scrollTo(id: message.id, anchor: .top)
```

**Scroll to an edge:**

```swift
scrollPosition.scrollTo(edge: .bottom)
```

**Read the current position:**

```swift
if let currentID = scrollPosition.viewID(type: Message.ID.self) {
    // The view with this ID is currently at the scroll anchor
}
```

**Detect user-initiated scrolls:**

```swift
.onChange(of: scrollPosition.isPositionedByUser) { _, byUser in
    if byUser {
        // User scrolled manually -- show "scroll to bottom" button
    }
}
```

## Paged primary and detail reveals

For a primary surface that pages into secondary details, let the scroll view remain the interaction source of truth. Use `ScrollPosition` for semantic or programmatic positioning, then derive one normalized progress value from scroll offset for continuous presentation.

```swift
private enum RevealPage: Hashable {
    case primary
    case details
}

@MainActor
struct RevealPager: View {
    @State private var position = ScrollPosition(idType: RevealPage.self)
    @State private var progress: CGFloat = 0
    @State private var isZooming = false
    @State private var isCropping = false

    var body: some View {
        ScrollView(.vertical) {
            LazyVStack(spacing: 0) {
                PrimarySurface(progress: progress)
                    .containerRelativeFrame(.vertical)
                    .id(RevealPage.primary)

                DetailSurface(progress: progress)
                    .containerRelativeFrame(.vertical)
                    .id(RevealPage.details)
            }
            .scrollTargetLayout()
        }
        .scrollPosition($position)
        .scrollTargetBehavior(.paging)
        .onScrollGeometryChange(for: CGFloat.self) { geometry in
            let revealDistance = max(geometry.containerSize.height, 1)
            let offset = geometry.visibleRect.minY
            return min(max(offset / revealDistance, 0), 1)
        } action: { _, newProgress in
            progress = newProgress
        }
        .scrollDisabled(isZooming || isCropping)
    }
}
```

Use the same `progress` to derive opacity, offset, scale, blur, toolbar treatment, and reveal affordances. Keep these calculations in `RevealPager`'s small presentation subtree; do not publish pixel-by-pixel offsets into a shared store or invalidate an entire screen.

Avoid parallel state such as `isDetailsVisible`, `isToolbarVisible`, and a separate drag gesture that all describe the same transition. Derive thresholds from `progress` when a Boolean presentation choice is needed. Retain separate state only for a genuinely discrete event or interaction.

`onScrollGeometryChange` runs as the geometry changes frequently. Transform `ScrollGeometry` into the smallest useful `Equatable` value. A scalar is appropriate for smooth progress; use a threshold `Bool` or quantized value when per-pixel precision is unnecessary.

Use `onScrollVisibilityChange` or `onScrollTargetVisibilityChange` for discrete threshold-crossing effects such as deduplicated haptics, analytics, media activation, or accessibility announcements. Do not use visibility callbacks as continuous animation progress. A visibility threshold does not guarantee that paging has settled; when an effect must wait for rest, gate the discrete visibility result with an idle `onScrollPhaseChange`.

Disable scrolling while a conflicting interaction owns the same gesture, such as zoom, crop, or precision editing. Remember that `.scrollDisabled` propagates through the environment to nested scrollable views.

Prevent feedback loops: presentation derived from `progress` must not change the page height, content inset, or other geometry used to calculate that progress. Prefer render-only effects such as opacity, offset, scale, and blur; isolate unavoidable layout changes from the measured scroll content.

> **Docs:** [ScrollPosition](https://sosumi.ai/documentation/swiftui/scrollposition) · [onScrollGeometryChange](https://sosumi.ai/documentation/swiftui/view/onscrollgeometrychange(for:of:action:)) · [onScrollVisibilityChange](https://sosumi.ai/documentation/swiftui/view/onscrollvisibilitychange(threshold:_:)) · [scrollDisabled](https://sosumi.ai/documentation/swiftui/view/scrolldisabled(_:))

## Example: horizontal chips

```swift
ScrollView(.horizontal, showsIndicators: false) {
  LazyHStack {
    ForEach(chips) { chip in
      ChipView(chip: chip)
    }
  }
}
```

## Example: adaptive grid

```swift
let columns = [GridItem(.adaptive(minimum: 120))]

ScrollView {
  LazyVGrid(columns: columns) {
    ForEach(items) { item in
      GridItemView(item: item)
    }
  }
  .padding()
}
```

## Design choices to keep

- Use `Lazy*` stacks when item counts are large or unknown.
- Use non-lazy stacks for small, fixed-size content to avoid lazy overhead.
- Keep IDs stable for `ScrollPosition` tracking; changing IDs causes position jumps.
- Prefer explicit animations (`withAnimation`) when scrolling to an ID.

## iOS 26 Scroll Edge Effects

### scrollEdgeEffectStyle

Configure the visual treatment at scroll view edges (iOS 26+):

```swift
ScrollView {
    content
}
.scrollEdgeEffectStyle(.soft, for: .top)   // Soft fading edge at top
.scrollEdgeEffectStyle(.hard, for: .bottom) // Hard cutoff at bottom
```

`ScrollEdgeEffectStyle` values:
- `.automatic` -- platform default
- `.soft` -- soft fading edge effect
- `.hard` -- hard cutoff with dividing line

Use `scrollEdgeEffectHidden(_:for:)` to hide the edge effect entirely.

### backgroundExtensionEffect

Duplicates, mirrors, and blurs the view to extend behind safe area edges (iOS 26+):

```swift
NavigationSplitView {
    sidebar
} detail: {
    BannerView()
        .backgroundExtensionEffect()
}
```

Use sparingly -- Apple recommends only a single instance for visual clarity and performance. The modifier clips the view to prevent mirror overlap.

### safeAreaBar

Attach a bar view to the safe area edge, integrating with scroll edge effects (iOS 26+):

```swift
content
    .safeAreaBar(edge: .top) {
        FilterBar()
    }
```

## Pitfalls

- Avoid nesting scroll views of the same axis; it causes gesture conflicts.
- Don’t combine `List` and `ScrollView` in the same hierarchy without a clear reason.
- Overuse of `LazyVStack` for tiny content can add unnecessary complexity.
- Apply `scrollEdgeEffectStyle` on the ScrollView, not on inner content.
- Use `backgroundExtensionEffect()` on only one view per screen.
- Do not mirror one reveal transition into multiple booleans or a parallel drag state machine.
- Do not write raw per-frame scroll geometry into broad app state.
- Do not let progress-driven layout change the geometry used to calculate progress.
- Use visibility callbacks for discrete threshold effects, not continuous interpolation or an assumed settled state.
