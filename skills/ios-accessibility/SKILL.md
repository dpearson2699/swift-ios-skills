---
name: ios-accessibility
description: "Implement, review, or improve accessibility in iOS/macOS apps with SwiftUI and UIKit. Use when adding VoiceOver support with accessibility labels, hints, values, and traits; when grouping or reordering accessibility elements; when managing focus with @AccessibilityFocusState; when supporting Dynamic Type with @ScaledMetric; when building custom rotors or accessibility actions; when auditing a11y compliance; or when adapting UI for assistive technologies and system accessibility preferences."
---

# iOS Accessibility — SwiftUI and UIKit

Every user-facing view must be usable with VoiceOver, Switch Control, Voice Control, Full Keyboard Access, and other assistive technologies. This skill covers the patterns and APIs required to build accessible iOS apps.

## Core Principles

1. Every interactive element MUST have an accessible label. If no visible text exists, add `.accessibilityLabel`.
2. Every custom control MUST have correct traits via `.accessibilityAddTraits` (never direct assignment).
3. Decorative images MUST be hidden from assistive technologies.
4. Sheet and dialog dismissals MUST return VoiceOver focus to the trigger element.
5. All tap targets MUST be at least 44x44 points.
6. Dynamic Type MUST be supported everywhere (system fonts, `@ScaledMetric`, adaptive layouts).
7. No information conveyed by color alone -- always provide text or icon alternatives.
8. System accessibility preferences MUST be respected: Reduce Motion, Reduce Transparency, Bold Text, Increase Contrast.

## How VoiceOver Reads Elements

VoiceOver reads element properties in a fixed, non-configurable order:

**Label -> Value -> Trait -> Hint**

Design your labels, values, and hints with this reading order in mind.

## SwiftUI Accessibility Modifiers

### Labels, Values, and Hints

```swift
// Label: the primary description VoiceOver reads
Button(action: { }) {
    Image(systemName: "heart.fill")
}
.accessibilityLabel("Favorite")

// Hint: describes the result of activation (read after a pause)
Button("Submit")
    .accessibilityHint("Submits the form and sends your feedback")

// Value: the current state for sliders, toggles, progress indicators
Slider(value: $volume, in: 0...100)
    .accessibilityValue("\(Int(volume)) percent")
```

- **Label**: Short, descriptive noun or noun phrase. Do not include the element type (VoiceOver announces the trait separately).
- **Value**: Current state. Update dynamically as the value changes.
- **Hint**: Starts with a verb, describes the result. Only add when the action is not obvious from the label and trait.

### Input Labels

Use `accessibilityInputLabels` to provide alternative labels for Voice Control:

```swift
Button("Go") { }
    .accessibilityInputLabels(["Go", "Start", "Begin"])
```

### Traits

Use `.accessibilityAddTraits` and `.accessibilityRemoveTraits` to modify traits. NEVER use direct trait assignment -- it overwrites the element's built-in traits.

| Trait | Use For |
|---|---|
| `.isButton` | Custom tappable views that are not `Button` |
| `.isHeader` | Section headers (enables rotor heading navigation) |
| `.isLink` | Elements that navigate to external content |
| `.isSelected` | Currently selected tab, segment, or radio button |
| `.isImage` | Meaningful images |
| `.isToggle` | Custom toggle controls |
| `.isModal` | Trap VoiceOver focus inside a custom overlay |
| `.updatesFrequently` | Timers, live counters, real-time displays |
| `.isSearchField` | Custom search inputs |
| `.startsMediaSession` | Elements that begin audio/video playback |

```swift
// WRONG: overwrites Button's built-in .isButton trait
Button("Go") { }
    .accessibilityTraits(.updatesFrequently)

// CORRECT: adds to existing traits
Button("Go") { }
    .accessibilityAddTraits(.updatesFrequently)

// Remove a trait when needed
Text("Not really a header anymore")
    .accessibilityRemoveTraits(.isHeader)
```

### Element Grouping

Reduce VoiceOver swipe count by grouping related elements into a single accessibility stop.

```swift
// .combine: merge children into one VoiceOver element
// VoiceOver concatenates child labels automatically
HStack {
    Image(systemName: "person.circle")
    VStack {
        Text("John Doe")
        Text("Engineer")
    }
}
.accessibilityElement(children: .combine)

// .ignore: replace children with a completely custom label
HStack {
    Image(systemName: "envelope")
    Text("inbox@example.com")
}
.accessibilityElement(children: .ignore)
.accessibilityLabel("Email: inbox@example.com")

// .contain: keep children individually navigable but logically grouped
VStack {
    Text("Order #1234")
    Button("Track") { }
}
.accessibilityElement(children: .contain)
```

**List rows should use `.accessibilityElement(children: .combine)` unless individual child elements require separate focus** (e.g., a row with multiple independently interactive controls).

### Custom Controls with accessibilityRepresentation

Use `.accessibilityRepresentation` (iOS 15+) for custom controls that map to standard SwiftUI equivalents. The framework generates correct accessibility elements from the representation automatically, including traits, adjustable actions, and values.

```swift
HStack {
    Text("Dark Mode")
    Circle()
        .fill(isDark ? .green : .gray)
        .onTapGesture { isDark.toggle() }
}
.accessibilityRepresentation {
    Toggle("Dark Mode", isOn: $isDark)
}
```

```swift
// Custom slider control
VStack {
    SliderTrack(value: value) // Custom visual implementation
}
.accessibilityRepresentation {
    Slider(value: $value, in: 0...100) {
        Text("Volume")
    }
}
```

### Adjustable Controls

For controls that support increment/decrement (star ratings, steppers):

```swift
HStack { /* custom star rating UI */ }
    .accessibilityElement()
    .accessibilityLabel("Rating")
    .accessibilityValue("\(rating) out of 5 stars")
    .accessibilityAdjustableAction { direction in
        switch direction {
        case .increment: if rating < 5 { rating += 1 }
        case .decrement: if rating > 1 { rating -= 1 }
        @unknown default: break
        }
    }
```

VoiceOver users swipe up/down to adjust. The `.accessibilityAdjustableAction` modifier automatically adds the `.adjustable` trait.

### Custom Actions

Replace hidden swipe actions, context menus, or long-press gestures with named accessibility actions so VoiceOver users can discover and invoke them:

```swift
MessageRow(message: message)
    .accessibilityAction(named: "Reply") { reply(to: message) }
    .accessibilityAction(named: "Delete") { delete(message) }
    .accessibilityAction(named: "Flag") { flag(message) }
```

System-level actions:

```swift
PlayerView()
    .accessibilityAction(.magicTap) { togglePlayPause() }
    .accessibilityAction(.escape) { dismiss() }
```

- **Magic Tap** (two-finger double-tap): Toggle the most relevant action (play/pause, answer/end call).
- **Escape** (two-finger Z-scrub): Dismiss the current modal or go back.

### Sort Priority

Control VoiceOver reading order among sibling elements. Higher values are read first:

```swift
ZStack {
    Image("photo").accessibilitySortPriority(0)     // Read third
    Text("Credit").accessibilitySortPriority(1)      // Read second
    Text("Breaking News").accessibilitySortPriority(2) // Read first
}
```

Only use when the default visual order produces a confusing reading sequence.

## Focus Management

Focus management is where most apps fail. When a sheet, alert, or popover is dismissed, VoiceOver focus MUST return to the element that triggered it.

### @AccessibilityFocusState (iOS 15+)

`@AccessibilityFocusState` is a property wrapper that reads and writes the current accessibility focus. It works with `Bool` for single-target focus or an optional `Hashable` enum for multi-target focus.

```swift
struct ContentView: View {
    @State private var showSheet = false
    @AccessibilityFocusState private var focusOnTrigger: Bool

    var body: some View {
        Button("Open Settings") { showSheet = true }
            .accessibilityFocused($focusOnTrigger)
            .sheet(isPresented: $showSheet) {
                SettingsSheet()
                    .onDisappear {
                        // Slight delay allows the transition to complete before moving focus
                        Task { @MainActor in
                            try? await Task.sleep(for: .milliseconds(100))
                            focusOnTrigger = true
                        }
                    }
            }
    }
}
```

### Multi-Target Focus with Enum

```swift
enum A11yFocus: Hashable {
    case nameField
    case emailField
    case submitButton
}

struct FormView: View {
    @AccessibilityFocusState private var focus: A11yFocus?

    var body: some View {
        Form {
            TextField("Name", text: $name)
                .accessibilityFocused($focus, equals: .nameField)
            TextField("Email", text: $email)
                .accessibilityFocused($focus, equals: .emailField)
            Button("Submit") { validate() }
                .accessibilityFocused($focus, equals: .submitButton)
        }
    }

    func validate() {
        if name.isEmpty {
            focus = .nameField // Move VoiceOver to the invalid field
        }
    }
}
```

### Custom Modals

Custom overlay views need the `.isModal` trait to trap VoiceOver focus and an escape action for dismissal:

```swift
CustomDialog()
    .accessibilityAddTraits(.isModal)
    .accessibilityAction(.escape) { dismiss() }
```

### Accessibility Notifications (UIKit)

When you need to announce changes or move focus imperatively in UIKit contexts:

```swift
// Announce a status change (e.g., "Item deleted", "Upload complete")
UIAccessibility.post(notification: .announcement, argument: "Upload complete")

// Partial screen update -- move focus to a specific element
UIAccessibility.post(notification: .layoutChanged, argument: targetView)

// Full screen transition -- move focus to the new screen
UIAccessibility.post(notification: .screenChanged, argument: newScreenView)
```

## Dynamic Type

### @ScaledMetric (iOS 14+)

`@ScaledMetric` scales numeric values (spacing, icon sizes, padding) proportionally with the user's preferred text size. It takes a base value and optionally a text style to scale relative to.

```swift
@ScaledMetric(relativeTo: .title) private var iconSize: CGFloat = 24
@ScaledMetric private var spacing: CGFloat = 8

var body: some View {
    HStack(spacing: spacing) {
        Image(systemName: "star.fill")
            .frame(width: iconSize, height: iconSize)
        Text("Favorite")
    }
}
```

### Adaptive Layouts

Switch from horizontal to vertical layout at large accessibility text sizes:

```swift
@Environment(\.dynamicTypeSize) var dynamicTypeSize

var body: some View {
    if dynamicTypeSize.isAccessibilitySize {
        VStack(alignment: .leading) { icon; textContent }
    } else {
        HStack { icon; textContent }
    }
}
```

Use `dynamicTypeSize.isAccessibilitySize` (iOS 15+) rather than comparing against specific cases -- it covers all five accessibility size categories.

### Minimum Tap Targets

Every tappable element must be at least 44x44 points:

```swift
Button(action: { }) {
    Image(systemName: "plus")
        .frame(minWidth: 44, minHeight: 44)
}
.contentShape(Rectangle())
```

## Custom Rotors

Rotors let VoiceOver users quickly navigate to specific content types. Add custom rotors for content-heavy screens:

```swift
List(items) { item in
    ItemRow(item: item)
}
.accessibilityRotor("Unread") {
    ForEach(items.filter { !$0.isRead }) { item in
        AccessibilityRotorEntry(item.title, id: item.id)
    }
}
.accessibilityRotor("Flagged") {
    ForEach(items.filter { $0.isFlagged }) { item in
        AccessibilityRotorEntry(item.title, id: item.id)
    }
}
```

Users access rotors by rotating two fingers on screen. The system provides built-in rotors for headings, links, and form controls. Custom rotors extend this with app-specific navigation.

## System Accessibility Preferences

Always respect these environment values:

```swift
@Environment(\.accessibilityReduceMotion) var reduceMotion
@Environment(\.accessibilityReduceTransparency) var reduceTransparency
@Environment(\.colorSchemeContrast) var contrast         // .standard or .increased
@Environment(\.legibilityWeight) var legibilityWeight    // .regular or .bold
```

### Reduce Motion

Replace movement-based animations with crossfades or no animation:

```swift
withAnimation(reduceMotion ? nil : .spring()) {
    showContent.toggle()
}
content.transition(reduceMotion ? .opacity : .slide)
```

### Reduce Transparency, Increase Contrast, Bold Text

```swift
// Solid backgrounds when transparency is reduced
.background(reduceTransparency ? Color(.systemBackground) : Color(.systemBackground).opacity(0.85))

// Stronger colors when contrast is increased
.foregroundStyle(contrast == .increased ? .primary : .secondary)

// Bold weight when system bold text is enabled
.fontWeight(legibilityWeight == .bold ? .bold : .regular)
```

## Decorative Content

```swift
// Decorative images: hidden from VoiceOver
Image(decorative: "background-pattern")
Image("visual-divider").accessibilityHidden(true)

// Icon next to text: Label handles this automatically
Label("Settings", systemImage: "gear")

// Icon-only buttons: MUST have an accessibility label
Button(action: { }) {
    Image(systemName: "gear")
}
.accessibilityLabel("Settings")
```

## Assistive Access (iOS 26+)

iOS 26 introduces `AssistiveAccess` for supporting Assistive Access mode in scenes. Use the `AssistiveAccess` scene modifier to provide simplified versions of your app's UI for users with cognitive disabilities. Test your app with Assistive Access enabled in Settings > Accessibility > Assistive Access.

## UIKit Accessibility Patterns

When working with UIKit views:

- Set `isAccessibilityElement = true` on meaningful custom views.
- Set `accessibilityLabel` on all interactive elements without visible text.
- Use `.insert()` and `.remove()` for trait modification (not direct assignment).
- Set `accessibilityViewIsModal = true` on custom overlay views to trap focus.
- Post `.announcement` for transient status messages.
- Post `.layoutChanged` with a target view for partial screen updates.
- Post `.screenChanged` for full screen transitions.

```swift
// UIKit trait modification
customButton.accessibilityTraits.insert(.button)
customButton.accessibilityTraits.remove(.staticText)

// Modal overlay
overlayView.accessibilityViewIsModal = true
```

## Accessibility Custom Content

Use `accessibilityCustomContent` for supplementary details that should not clutter the primary label. VoiceOver users access custom content via the "More Content" rotor:

```swift
ProductRow(product: product)
    .accessibilityCustomContent("Price", product.formattedPrice)
    .accessibilityCustomContent("Rating", "\(product.rating) out of 5")
    .accessibilityCustomContent(
        "Availability",
        product.inStock ? "In stock" : "Out of stock",
        importance: .high  // .high reads automatically with the element
    )
```

## Common Mistakes

1. **Direct trait assignment**: `.accessibilityTraits(.isButton)` overwrites all existing traits. Use `.accessibilityAddTraits(.isButton)`.
2. **Missing focus restoration**: Dismissing sheets without returning VoiceOver focus to the trigger element.
3. **Ungrouped list rows**: Multiple text elements per row create excessive swipe stops. Use `.accessibilityElement(children: .combine)`.
4. **Redundant trait in labels**: `.accessibilityLabel("Settings button")` reads as "Settings button, button." Omit the type.
5. **Missing labels on icon-only buttons**: Every `Image`-only button MUST have `.accessibilityLabel`.
6. **Ignoring Reduce Motion**: Always check `accessibilityReduceMotion` before movement animations.
7. **Fixed font sizes**: `.font(.system(size: 16))` ignores Dynamic Type. Use `.font(.body)` or similar text styles.
8. **Small tap targets**: Icons without `frame(minWidth: 44, minHeight: 44)` and `.contentShape()`.
9. **Color as sole indicator**: Red/green for error/success without text or icon alternatives.
10. **Missing `.isModal` on overlays**: Custom modals without `.accessibilityAddTraits(.isModal)` let VoiceOver escape.

## Review Checklist

For every user-facing view, verify:

- [ ] Every interactive element has an accessible label
- [ ] Custom controls use correct traits via `.accessibilityAddTraits`
- [ ] Decorative images are hidden (`Image(decorative:)` or `.accessibilityHidden(true)`)
- [ ] List rows group content with `.accessibilityElement(children: .combine)`
- [ ] Sheets and dialogs return focus to the trigger on dismiss
- [ ] Custom overlays have `.isModal` trait and escape action
- [ ] All tap targets are at least 44x44 points
- [ ] Dynamic Type supported (`@ScaledMetric`, system fonts, adaptive layouts)
- [ ] Reduce Motion respected (no movement animations when enabled)
- [ ] Reduce Transparency respected (solid backgrounds when enabled)
- [ ] Increase Contrast respected (stronger foreground colors)
- [ ] No information conveyed by color alone
- [ ] Custom actions provided for swipe-to-reveal and context menu features
- [ ] Icon-only buttons have labels
- [ ] Heading traits set on section headers
- [ ] Custom accessibility types and notification payloads are `Sendable` when passed across concurrency boundaries

