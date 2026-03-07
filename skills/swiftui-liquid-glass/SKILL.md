---
name: swiftui-liquid-glass
description: Implement, review, or improve SwiftUI Liquid Glass effects for iOS 26+. Covers glassEffect modifier, GlassEffectContainer, glass button styles, glass toolbar, glass tab bar, morphing transitions, translucent material, vibrancy, tinting, interactive glass, ToolbarSpacer, scrollEdgeEffectStyle, backgroundExtensionEffect, and availability gating. Use when asked about Liquid Glass, glass buttons, glassEffect, GlassEffectContainer, GlassEffectTransition, glassEffectID, glassEffectUnion, scroll edge effects, or adopting iOS 26 design.
---

# SwiftUI Liquid Glass

## Overview

Liquid Glass is the dynamic translucent material introduced in iOS 26 (and iPadOS 26,
macOS 26, tvOS 26, watchOS 26). It blurs content behind it, reflects surrounding color
and light, and reacts to touch and pointer interactions. Standard SwiftUI components
(tab bars, toolbars, navigation bars, sheets) adopt Liquid Glass automatically when
built with the iOS 26 SDK. Use the APIs below for custom views and controls.

See `references/liquid-glass.md` for the full API reference with additional examples.

## Workflow

Choose the path that matches the request:

### 1. Implement a new feature with Liquid Glass

1. Identify target surfaces (cards, chips, floating controls, custom bars).
2. Decide shape, prominence, and whether each element needs interactivity.
3. Wrap grouped glass elements in a `GlassEffectContainer`.
4. Apply `.glassEffect()` **after** layout and appearance modifiers.
5. Add `.interactive()` only to tappable/focusable elements.
6. Add morphing transitions with `glassEffectID(_:in:)` where the view hierarchy
   changes with animation.
7. Gate with `if #available(iOS 26, *)` and provide a fallback for earlier versions.

### 2. Improve an existing feature with Liquid Glass

1. Find custom blur/material backgrounds that can be replaced with `.glassEffect()`.
2. Wrap sibling glass elements in `GlassEffectContainer` for blending and performance.
3. Replace custom glass-like buttons with `.buttonStyle(.glass)` or `.buttonStyle(.glassProminent)`.
4. Add morphing transitions where animated insertion/removal occurs.

### 3. Review existing Liquid Glass usage

Run through the Review Checklist below and verify each item.

## Core API Summary

### glassEffect(_:in:)

Applies Liquid Glass behind a view. Default: `.regular` variant in a `Capsule` shape.

```swift
func glassEffect(
    _ glass: Glass = .regular,
    in shape: some Shape = DefaultGlassEffectShape()
) -> some View
```

### Glass struct

| Property / Method | Purpose |
|---|---|
| `.regular` | Standard glass material |
| `.clear` | Clear variant (minimal tint) |
| `.identity` | No visual effect (pass-through) |
| `.tint(_:)` | Add a color tint for prominence |
| `.interactive(_:)` | React to touch and pointer interactions |

Chain them: `.regular.tint(.blue).interactive()`

### GlassEffectContainer

Wraps multiple glass views for shared rendering, blending, and morphing.

```swift
GlassEffectContainer(spacing: 24) {
    // child views with .glassEffect()
}
```

The `spacing` controls when nearby glass shapes begin to blend. Match or exceed
the interior layout spacing so shapes merge during animated transitions but remain
separate at rest.

### Morphing & Transitions

| Modifier | Purpose |
|---|---|
| `glassEffectID(_:in:)` | Stable identity for morphing during view hierarchy changes |
| `glassEffectUnion(id:namespace:)` | Merge multiple views into one glass shape |
| `glassEffectTransition(_:)` | Control how glass appears/disappears |

Transition types: `.matchedGeometry` (default when within spacing), `.materialize`
(fade content + animate glass in/out), `.identity` (no transition).

### Button Styles

```swift
Button("Action") { }
    .buttonStyle(.glass)           // standard glass button

Button("Primary") { }
    .buttonStyle(.glassProminent)  // prominent glass button
```

### Scroll Edge Effects and Background Extension (iOS 26+)

These complement Liquid Glass when building custom toolbars and scroll views:

```swift
ScrollView {
    content
}
.scrollEdgeEffectStyle(.soft, for: .top)  // Fading edge effect at scroll boundaries

// Mirror and blur content at safe area edges (behind glass toolbars)
content
    .backgroundExtensionEffect()
```

### ToolbarSpacer (iOS 26+)

Creates a visual break between items in toolbars containing Liquid Glass:

```swift
.toolbar {
    ToolbarItem { Button("Edit") { } }
    ToolbarItem { ToolbarSpacer() }
    ToolbarItem { Button("Share") { } }
}
```

## Code Examples

### Basic glass effect with availability gate

```swift
if #available(iOS 26, *) {
    Text("Status")
        .padding()
        .glassEffect(.regular.interactive(), in: .rect(cornerRadius: 16))
} else {
    Text("Status")
        .padding()
        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 16))
}
```

### Grouped glass elements in a container

```swift
GlassEffectContainer(spacing: 24) {
    HStack(spacing: 24) {
        ForEach(tools) { tool in
            Image(systemName: tool.icon)
                .frame(width: 56, height: 56)
                .glassEffect(.regular.interactive())
        }
    }
}
```

### Morphing transition

```swift
@State private var isExpanded = false
@Namespace private var ns

var body: some View {
    GlassEffectContainer(spacing: 40) {
        HStack(spacing: 40) {
            Image(systemName: "pencil")
                .frame(width: 80, height: 80)
                .glassEffect()
                .glassEffectID("pencil", in: ns)

            if isExpanded {
                Image(systemName: "eraser.fill")
                    .frame(width: 80, height: 80)
                    .glassEffect()
                    .glassEffectID("eraser", in: ns)
            }
        }
    }

    Button("Toggle") {
        withAnimation { isExpanded.toggle() }
    }
    .buttonStyle(.glass)
}
```

### Unioning views into a single glass shape

```swift
@Namespace private var ns

GlassEffectContainer(spacing: 20) {
    HStack(spacing: 20) {
        ForEach(items.indices, id: \.self) { i in
            Image(systemName: items[i])
                .frame(width: 80, height: 80)
                .glassEffect()
                .glassEffectUnion(id: i < 2 ? "group1" : "group2", namespace: ns)
        }
    }
}
```

### Tinted glass badge

```swift
struct GlassBadge: View {
    let icon: String
    let tint: Color

    var body: some View {
        Image(systemName: icon)
            .font(.title2)
            .padding()
            .glassEffect(.regular.tint(tint), in: .rect(cornerRadius: 12))
    }
}
```

## Do's and Don'ts

**Do:**

- Use `GlassEffectContainer` whenever multiple glass views coexist.
- Apply `.glassEffect()` after layout and appearance modifiers (padding, frame, font).
- Use `.interactive()` only on tappable or focusable elements.
- Match `GlassEffectContainer` spacing with the interior layout spacing.
- Prefer `.buttonStyle(.glass)` / `.buttonStyle(.glassProminent)` over manual glass on buttons.
- Gate with `if #available(iOS 26, *)` and provide a non-glass fallback.
- Use `withAnimation` when toggling views that have `glassEffectID` for morphing.

**Don't:**

- Apply Liquid Glass to every surface -- overuse distracts from content.
- Nest `GlassEffectContainer` inside another `GlassEffectContainer`.
- Add `.interactive()` to non-interactive decorative glass.
- Use custom blur/material overlays when `.glassEffect()` can replace them.
- Hard-code layout metrics that conflict with glass container spacing.
- Forget to test with Reduce Transparency and Reduce Motion accessibility settings.

## Review Checklist

- [ ] **Availability**: `if #available(iOS 26, *)` present with fallback UI.
- [ ] **Container**: Multiple glass views wrapped in `GlassEffectContainer`.
- [ ] **Modifier order**: `.glassEffect()` applied after layout/appearance modifiers.
- [ ] **Interactivity**: `.interactive()` used only where user interaction exists.
- [ ] **Transitions**: `glassEffectID` used with `@Namespace` for morphing animations.
- [ ] **Transition type**: `.matchedGeometry` for nearby effects; `.materialize` for distant ones.
- [ ] **Consistency**: Shapes, tints, and spacing are uniform across related elements.
- [ ] **Performance**: Glass effects are limited in number; container used for grouping.
- [ ] **Accessibility**: Tested with Reduce Transparency and Reduce Motion enabled.
- [ ] **Button styles**: Standard `.glass` / `.glassProminent` used for buttons.
- [ ] Ensure types driving Liquid Glass effects are Sendable; apply glass effects on @MainActor context

## Available MCP Tools

- **xcodebuildmcp**: If available, use to build and test your project directly.

## References

- Full API guide: `references/liquid-glass.md`
- Apple docs: [Applying Liquid Glass to custom views](https://sosumi.ai/documentation/SwiftUI/Applying-Liquid-Glass-to-custom-views)
- Apple docs: [Adopting Liquid Glass](https://sosumi.ai/documentation/technologyoverviews/adopting-liquid-glass)
