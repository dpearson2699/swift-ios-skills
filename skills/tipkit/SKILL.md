---
name: tipkit
description: "Implement, review, or improve in-app tips and onboarding using Apple's TipKit framework. Use when adding feature discovery tooltips, onboarding flows, contextual tips, first-run experiences, or coach marks to iOS/macOS/visionOS apps. Trigger when working with Tip protocol, TipView, popoverTip, tip rules, tip events, or feature education UI."
---

# TipKit

Add feature discovery tips, contextual hints, and onboarding coach marks to
iOS 17+ apps using Apple's TipKit framework. TipKit manages display frequency,
eligibility rules, and persistence so tips appear at the right time and
disappear once the user has learned the feature.

## Setup

Call `Tips.configure()` once in `App.init`, before any views render. This
initializes the tips datastore and begins rule evaluation. Calling it later
risks a race where tip views attempt to display before the datastore is ready.

```swift
import SwiftUI
import TipKit

@main
struct MyApp: App {
    init() {
        try? Tips.configure([
            .datastoreLocation(.applicationDefault)
        ])
    }

    var body: some Scene {
        WindowGroup { ContentView() }
    }
}
```

### DatastoreLocation Options

| Option | Use Case |
|---|---|
| `.applicationDefault` | Default location, app sandbox (most apps) |
| `.groupContainer(identifier:)` | Share tips state across app and extensions |
| `.url(_:)` | Custom file URL for full control over storage location |

### CloudKit Sync

Sync tip state across a user's devices so they do not see the same tip on
every device. Add the CloudKit container option alongside the datastore
location.

```swift
try? Tips.configure([
    .datastoreLocation(.applicationDefault),
    .cloudKitContainer(.named("iCloud.com.example.app"))
])
```

## Defining Tips

Conform a struct to the `Tip` protocol. Provide a `title` at minimum.
Add `message` for supporting detail and `image` for a leading icon. Keep
titles short and action-oriented because the tip appears as a compact callout.

```swift
import TipKit

struct FavoriteTip: Tip {
    var title: Text { Text("Pin Your Favorites") }
    var message: Text? { Text("Tap the heart icon to save items for quick access.") }
    var image: Image? { Image(systemName: "heart") }
}
```

**Properties**: `title` (required), `message` (optional detail), `image` (optional leading icon), `actions` (optional buttons), `rules` (optional eligibility conditions), `options` (display frequency, max count).

**Lifecycle**: Pending (rules unsatisfied) -> Eligible (all rules pass) -> Invalidated (dismissed, actioned, or programmatically removed). Once invalidated, a tip does not reappear unless the datastore is reset.

## Displaying Tips

### Inline Tips with TipView

Embed a `TipView` directly in your layout. It renders as a rounded card that
appears and disappears with animation. Use for tips within scrollable content.

```swift
let favoriteTip = FavoriteTip()
var body: some View {
    VStack {
        TipView(favoriteTip)
        ItemListView()
    }
}
```

### Popover Tips with .popoverTip()

Attach a tip as a popover anchored to any view. The framework draws an arrow
from the popover to the anchor. Use for tips pointing to a specific control.

```swift
Button { toggleFavorite() } label: { Image(systemName: "heart") }
    .popoverTip(favoriteTip)

// Control arrow direction (omit to let system choose)
.popoverTip(favoriteTip, arrowEdge: .bottom)
```

### Custom TipViewStyle

Create a custom style to control tip appearance across the app. Conform
to `TipViewStyle` and implement `makeBody(configuration:)`.

```swift
struct CustomTipStyle: TipViewStyle {
    func makeBody(configuration: Configuration) -> some View {
        HStack(spacing: 12) {
            configuration.image?
                .font(.title2)
                .foregroundStyle(.tint)

            VStack(alignment: .leading, spacing: 4) {
                configuration.title
                    .font(.headline)
                configuration.message?
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }
        }
        .padding()
    }
}

// Apply globally or per view
TipView(favoriteTip)
    .tipViewStyle(CustomTipStyle())
```

## Tip Rules

Rules control when a tip becomes eligible. All rules in the `rules` array
must pass before the tip displays. TipKit supports two rule types:
parameter-based and event-based.

### Parameter-Based Rules

Use `@Parameter` to track app state. The tip becomes eligible when the
parameter value satisfies the rule condition.

```swift
struct FavoriteTip: Tip {
    @Parameter
    static var hasSeenList: Bool = false

    var title: Text { Text("Pin Your Favorites") }

    var rules: [Rule] {
        #Rule(Self.$hasSeenList) { $0 == true }
    }
}

// Set the parameter when the user reaches the list
FavoriteTip.hasSeenList = true
```

### Event-Based Rules

Use `Tips.Event` to track user actions. Donate to the event each time the
action occurs. The rule fires when the donation count or timing condition
is met. This is ideal for tips that should appear after the user has
performed an action several times without discovering a related feature.

```swift
struct ShortcutTip: Tip {
    static let appOpenedEvent = Tips.Event(id: "appOpened")

    var title: Text { Text("Try the Quick Action") }

    var rules: [Rule] {
        #Rule(Self.appOpenedEvent) { $0.donations.count >= 3 }
    }
}

// Donate each time the app opens
ShortcutTip.appOpenedEvent.donate()
```

### Combining Multiple Rules

Place multiple rules in the array. All must pass (logical AND).

```swift
struct AdvancedTip: Tip {
    @Parameter
    static var isLoggedIn: Bool = false

    static let featureUsedEvent = Tips.Event(id: "featureUsed")

    var title: Text { Text("Unlock Advanced Mode") }

    var rules: [Rule] {
        #Rule(Self.$isLoggedIn) { $0 == true }
        #Rule(Self.featureUsedEvent) { $0.donations.count >= 5 }
    }
}
```

### Display Frequency Options

Control how often tips appear using the `options` property.

```swift
struct DailyTip: Tip {
    var title: Text { Text("Daily Reminder") }

    var options: [TipOption] {
        MaxDisplayCount(3)                   // Show at most 3 times total
        IgnoresDisplayFrequency(true)        // Bypass global frequency limit
    }
}
```

Global display frequency is set at configuration time:

```swift
try? Tips.configure([
    .displayFrequency(.daily)  // .immediate, .hourly, .daily, .weekly, .monthly
])
```

With `.daily`, the system shows at most one tip per day across the entire
app, unless a specific tip sets `IgnoresDisplayFrequency(true)`.

## Tip Actions

Add action buttons to a tip for direct interaction. Each action has an `id`
and a label. Handle the action in the tip view's action handler.

```swift
struct FeatureTip: Tip {
    var title: Text { Text("Try the New Editor") }
    var message: Text? { Text("We added a powerful new editing mode.") }

    var actions: [Action] {
        Action(id: "open-editor", title: "Open Editor")
        Action(id: "learn-more", title: "Learn More")
    }
}
```

Handle actions in the view:

```swift
TipView(featureTip) { action in
    switch action.id {
    case "open-editor":
        navigateToEditor()
        featureTip.invalidate(reason: .actionPerformed)
    case "learn-more":
        showHelpSheet = true
    default:
        break
    }
}
```

## Tip Groups

Use `TipGroup` to coordinate multiple tips within a single view.
`TipGroup` ensures only one tip from the group displays at a time,
preventing tip overload. Tips display in priority order.

```swift
struct OnboardingView: View {
    let tipGroup = TipGroup(.ordered) {
        WelcomeTip()
        NavigationTip()
        ProfileTip()
    }

    var body: some View {
        VStack {
            TipView(tipGroup.currentTip!)

            Button("Next") {
                tipGroup.currentTip?.invalidate(reason: .actionPerformed)
            }
        }
    }
}
```

### Priority Options

| Initializer | Behavior |
|---|---|
| `.ordered` | Tips display in the order they are listed |

When the current tip is invalidated, the next eligible tip in the group
becomes `currentTip`.

## Programmatic Control

### Invalidating Tips

Call `invalidate(reason:)` when the user performs the discovered action or
when the tip is no longer relevant.

```swift
let tip = FavoriteTip()
tip.invalidate(reason: .actionPerformed)
```

| Reason | When to Use |
|---|---|
| `.actionPerformed` | User performed the action the tip describes |
| `.displayCountExceeded` | Tip hit its maximum display count |
| `.tipClosed` | User explicitly dismissed the tip |

### Testing Utilities

TipKit provides static methods to control tip visibility during development
and testing. Gate these behind `#if DEBUG` or `ProcessInfo` checks so they
never run in production builds.

```swift
#if DEBUG
// Show all tips regardless of rules (useful during development)
Tips.showAllTipsForTesting()

// Show only specific tips
Tips.showTipsForTesting([FavoriteTip.self, ShortcutTip.self])

// Hide all tips (useful for UI tests that do not involve tips)
Tips.hideAllTipsForTesting()

// Reset the datastore (clears all tip state, invalidations, and events)
try? Tips.resetDatastore()
#endif
```

### Using ProcessInfo for Test Schemes

```swift
if ProcessInfo.processInfo.arguments.contains("--show-all-tips") {
    Tips.showAllTipsForTesting()
}
```

Pass `--show-all-tips` as a launch argument in the Xcode scheme for
development builds.

## Common Mistakes

### DON'T: Call Tips.configure() anywhere except App.init

Calling `Tips.configure()` in a view's `onAppear` or `task` modifier
creates a race condition where tip views try to render before the
datastore is ready, causing missing or flickering tips.

```swift
// WRONG
struct ContentView: View {
    var body: some View {
        Text("Hello")
            .task { try? Tips.configure() }  // Too late, views already rendered
    }
}

// CORRECT
@main struct MyApp: App {
    init() { try? Tips.configure() }
    var body: some Scene { WindowGroup { ContentView() } }
}
```

### DON'T: Show too many tips at once

Displaying multiple tips simultaneously overwhelms users and dilutes the
impact of each tip. Users learn to ignore them.

```swift
// WRONG: Three tips visible at the same time
VStack {
    TipView(tipA)
    TipView(tipB)
    TipView(tipC)
}

// CORRECT: Use TipGroup to sequence them
let group = TipGroup(.ordered) { TipA(); TipB(); TipC() }
TipView(group.currentTip!)
```

### DON'T: Forget to invalidate tips after the user performs the action

If a tip says "Tap the star to favorite" and the user taps the star but
the tip remains, it erodes trust in the UI.

```swift
// WRONG: Tip stays visible after user acts
Button("Favorite") { toggleFavorite() }
    .popoverTip(favoriteTip)

// CORRECT: Invalidate on action
Button("Favorite") {
    toggleFavorite()
    favoriteTip.invalidate(reason: .actionPerformed)
}
.popoverTip(favoriteTip)
```

### DON'T: Leave testing tips enabled in production

`Tips.showAllTipsForTesting()` bypasses all rules and frequency limits.
Shipping this in production means every user sees every tip immediately.

```swift
// WRONG: Always active
Tips.showAllTipsForTesting()

// CORRECT: Gated behind DEBUG
#if DEBUG
Tips.showAllTipsForTesting()
#endif
```

### DON'T: Make tip titles too long

Long titles get truncated or wrap awkwardly in the compact tip callout.
Put the key action in the title and supporting context in the message.

```swift
// WRONG
var title: Text { Text("You can tap the heart button to save this item to your favorites list") }

// CORRECT
var title: Text { Text("Save to Favorites") }
var message: Text? { Text("Tap the heart icon to keep items for quick access.") }
```

### DON'T: Use tips for critical information

Users can dismiss tips at any time and they do not reappear. Never put
essential instructions or safety information in a tip.

```swift
// WRONG: Critical info in a dismissible tip
struct DataLossTip: Tip {
    var title: Text { Text("Unsaved changes will be lost") }
}

// CORRECT: Use an alert or inline warning for critical information
// Reserve tips for feature discovery and progressive disclosure
```

## Review Checklist

- [ ] `Tips.configure()` called in `App.init`, before any views render
- [ ] Each tip has a clear, concise title (action-oriented, under ~40 characters)
- [ ] Tips invalidated when the user performs the discovered action
- [ ] Rules set so tips appear at the right time (not immediately on first launch for all tips)
- [ ] `TipGroup` used when multiple tips exist in one view
- [ ] Testing utilities (`showAllTipsForTesting`, `resetDatastore`) gated behind `#if DEBUG`
- [ ] CloudKit sync configured if the app supports multiple devices
- [ ] Display frequency set appropriately (`.daily` or `.weekly` for most apps)
- [ ] Tips used for feature discovery only, not for critical information
- [ ] Custom `TipViewStyle` applied consistently if the default style does not match the app design
- [ ] Tip actions handled and tip invalidated in the action handler
- [ ] Event donations placed at the correct user action points
- [ ] Ensure custom Tip types are Sendable; configure Tips on @MainActor

## Reference Material

- See `references/tipkit-patterns.md` for complete implementation patterns
  including custom styles, event-based rules, tip groups, testing strategies,
  onboarding flows, and SwiftUI preview configuration.

