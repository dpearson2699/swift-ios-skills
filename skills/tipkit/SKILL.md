---
name: tipkit
description: "Implement and review Apple TipKit feature-discovery UI for iOS 17+ apps. Use when adding or auditing in-app tips, contextual help, coach marks, Tip, TipView, popoverTip, rules, events, actions, display frequency, testing overrides, reusable tip identifiers, or iOS 18+ TipGroup and CloudKit tip sync; avoid for generic SwiftUI navigation or layout outside tip presentation."
---

# TipKit

Use TipKit for small, contextual feature-discovery moments: inline tips,
popover tips, rule-gated education, and lightweight coach marks. Keep generic
SwiftUI architecture, navigation, layout, and long first-run onboarding flows in
their sibling skills unless TipKit presentation is the core issue.

## Contents

- [Availability](#availability)
- [Configure TipKit](#configure-tipkit)
- [Design Good Tips](#design-good-tips)
- [Define Tips](#define-tips)
- [Present Tips](#present-tips)
- [Rules and Events](#rules-and-events)
- [Options and Invalidation](#options-and-invalidation)
- [Actions and Styles](#actions-and-styles)
- [Tip Groups](#tip-groups)
- [Testing](#testing)
- [Common Mistakes](#common-mistakes)
- [Review Checklist](#review-checklist)
- [References](#references)

## Availability

TipKit's core `Tip`, `TipView`, `popoverTip`, rules, events, options, and
testing overrides are available on iOS 17+, iPadOS 17+, macOS 14+, tvOS 17+,
watchOS 10+, and visionOS 1+.

Gate newer APIs explicitly:

| API | Availability | Use |
| --- | --- | --- |
| `TipGroup` | iOS 18+ | Group or sequence tips; apply the [Tip Groups](#tip-groups) decision. |
| `.cloudKitContainer(...)` | iOS 18+ | Sync tip state, parameters, events, and display counts across devices. |
| `MaxDisplayDuration` | iOS 18+ | Automatically invalidate after cumulative display time. |
| `resetEligibility()` | iOS 26+ | Make a previously invalidated tip eligible again without resetting the datastore. |

## Configure TipKit

Call `Tips.configure(_:)` once during app initialization, before any tip can
display. Do not configure TipKit from a view's `onAppear` or `.task`.

```swift
import SwiftUI
import TipKit

@main
struct MyApp: App {
    init() {
        do {
            try Tips.configure([
                .datastoreLocation(.applicationDefault),
                .displayFrequency(.daily)
            ])
        } catch {
            assertionFailure("TipKit configuration failed: \(error)")
        }
    }

    var body: some Scene {
        WindowGroup { ContentView() }
    }
}
```

Use `.datastoreLocation(.groupContainer(identifier:))` only when an app and
extension or app-group members intentionally share tip state. Keep option
settings consistent across app-group members because TipKit persists option
state with the tip record.

### CloudKit Sync

Use CloudKit sync only on iOS 18+ and later. Enable iCloud + CloudKit and
Background Modes > Remote notifications, then pass a container:

```swift
try Tips.configure([
    .cloudKitContainer(.named("iCloud.com.example.app.tips"))
])
```

Prefer a dedicated container with a `.tips` suffix. `.automatic` uses the first
entitled `.tips` container when present, then falls back to the primary
container.

## Design Good Tips

Tips are small, transient help. Use them for features people can understand and
try in a few simple steps. If the flow needs a long explanation, multiple
screens, or critical safety/error information, use a tutorial, alert, inline
warning, or onboarding flow instead.

Follow HIG-aligned defaults:

- Keep titles short, direct, and action-oriented.
- Use one or two sentences; avoid promotional or unrelated copy.
- Place tips near the feature they explain.
- Prefer inline tips when hiding nearby UI would interrupt the task.
- Prefer popover tips when preserving the current layout matters and the tip can
  point to a specific control.
- Use rules and display frequency so only the right audience sees each tip.
- Avoid repeating an icon in the tip when the popover already points to that icon.

## Define Tips

`Tip` conforms to `Identifiable` and `Sendable`. Provide `title` at minimum;
add `message`, `image`, `actions`, `rules`, `options`, and `id` only when they
improve the feature-discovery moment.

```swift
import TipKit

struct FavoriteTip: Tip {
    var title: Text { Text("Save to Favorites") }
    var message: Text? { Text("Tap the heart to keep items for quick access.") }
    var image: Image? { Image(systemName: "heart.fill") }
}
```

By default, TipKit uses the tip type name as `id`. Override `id` for reusable
tips whose persisted state should vary by content:

```swift
struct NewItemTip: Tip {
    let itemID: Item.ID

    var id: String { "NewItemTip-\(itemID)" }
    var title: Text { Text("New Item Available") }
}
```

Use stable, concrete identifiers. Do not derive IDs from transient copy or
unstable ordering.

## Present Tips

Use `TipView` for inline tips:

```swift
let favoriteTip = FavoriteTip()

VStack {
    TipView(favoriteTip, arrowEdge: .bottom)
    ItemListView()
}
```

Use `.popoverTip` when the tip should point to a control:

```swift
Button {
    toggleFavorite()
    favoriteTip.invalidate(reason: .actionPerformed)
} label: {
    Image(systemName: "heart")
}
.popoverTip(favoriteTip, arrowEdge: .top)
```

## Rules and Events

Rules are ANDed together. A tip becomes eligible only when every rule passes.

Use `@Parameter` for persisted app state:

```swift
struct FavoriteTip: Tip {
    @Parameter static var hasSeenList = false

    var title: Text { Text("Save to Favorites") }

    var rules: [Rule] {
        #Rule(Self.$hasSeenList) { $0 == true }
    }
}
```

Use `Tips.Event` for repeated user actions. TipKit queries the most recent 1000
donations by default, so keep event rules bounded and intentional.

```swift
struct ShortcutTip: Tip {
    static let manualSaveEvent = Tips.Event(id: "manualSave")

    var title: Text { Text("Save Faster") }

    var rules: [Rule] {
        #Rule(Self.manualSaveEvent) {
            $0.donations.donatedWithin(.week).count >= 3
        }
    }
}

ShortcutTip.manualSaveEvent.sendDonation()
```

For richer event rules, define `Tips.Event<DonationInfo>` where
`DonationInfo: Codable, Sendable`. Keep donation payloads small.

Group related event definitions in a shared namespace when several tips use the
same events; event IDs are the persistence boundary, so collisions can create
confusing eligibility.

## Options and Invalidation

Use options sparingly; frequency and invalidation rules are part of the tip's
persisted behavior.

```swift
struct DailyTip: Tip {
    var title: Text { Text("Try Filters") }

    var options: [any TipOption] {
        MaxDisplayCount(3)
        IgnoresDisplayFrequency(false)
    }
}
```

`MaxDisplayDuration` is iOS 18+. It counts cumulative display time and has a
minimum continuous display duration before automatic invalidation can occur.
Do not use it as a replacement for explicit `invalidate(reason:)` when the app
knows the taught action or ordered step is complete.

Call `invalidate(reason:)` when the user performs the discovered action or the
tip is no longer relevant. Invalidation is permanent until the datastore is
reset or, on iOS 26+, the specific tip calls `await resetEligibility()`.

```swift
favoriteTip.invalidate(reason: .actionPerformed)
```

Use `.tipClosed` for explicit dismissal and `.displayCountExceeded` or
`.displayDurationExceeded` only when describing automatic invalidation outcomes.

## Actions and Styles

Add `Action` buttons when the user needs a direct route to settings, more
information, or a setup flow.

```swift
struct FeatureTip: Tip {
    var title: Text { Text("Try the New Editor") }

    var actions: [Action] {
        Action(id: "open-editor", title: "Open Editor")
        Action(id: "learn-more", title: "Learn More")
    }
}

TipView(FeatureTip()) { action in
    switch action.id {
    case "open-editor":
        openEditor()
    case "learn-more":
        showHelp()
    default:
        break
    }
}
```

For custom appearance, prefer `TipViewStyle.Configuration` values over reading
directly from a concrete tip instance. That preserves labels, handlers, and
modifiers applied to the `TipView`.

```swift
struct CompactTipStyle: TipViewStyle {
    func makeBody(configuration: Configuration) -> some View {
        HStack(alignment: .top) {
            configuration.image?
            VStack(alignment: .leading) {
                configuration.title?
                configuration.message?
                ForEach(configuration.actions) { action in
                    Button(action: action.handler) {
                        action.label()
                    }
                }
            }
        }
        .padding()
    }
}
```

## Tip Groups

`TipGroup` is iOS 18+. Store groups in SwiftUI state so the observable group
object persists across view updates. In every review of a `TipGroup(.ordered)`
plan, explicitly distinguish the default priority from ordered sequences:
`TipGroup` defaults to `.firstAvailable`, and `TipGroup(.ordered)` is required
when each later tip must wait for all previous tips to be invalidated.

```swift
struct OnboardingView: View {
    @State private var tips = TipGroup(.ordered) {
        WelcomeTip()
        SearchTip()
        FilterTip()
    }

    var body: some View {
        VStack {
            TipView(tips.currentTip)
            ContentView()
        }
    }
}
```

`MaxDisplayDuration` can cap display time, but it is not the sequencing
mechanism for an ordered group. Cast `currentTip` when the same group spans
multiple controls:

```swift
Button("Search") { openSearch() }
    .popoverTip(tips.currentTip as? SearchTip)
```

## Testing

Use testing overrides only in debug/test code, and apply them before
`Tips.configure(_:)`.

```swift
#if DEBUG
if ProcessInfo.processInfo.arguments.contains("--reset-tips") {
    try? Tips.resetDatastore()
}
if ProcessInfo.processInfo.arguments.contains("--show-all-tips") {
    Tips.showAllTipsForTesting()
}
#endif

try Tips.configure()
```

Built-in launch arguments are also available:

- `-com.apple.TipKit.ResetDatastore 1`
- `-com.apple.TipKit.ShowAllTips 1`
- `-com.apple.TipKit.ShowTips TipTypeA,TipTypeB`
- `-com.apple.TipKit.HideAllTips 1`

Testing override precedence is specific show, specific hide, show all, then hide
all. `Tips.resetDatastore()` must run before `Tips.configure(_:)`.

## Common Mistakes

### DON'T: Configure TipKit from a view

Configure during app initialization. View-level configuration can race with tip
display and can also hit datastore-already-configured errors.

### DON'T: Present iOS 18+ APIs as iOS 17 guidance

Gate `TipGroup`, CloudKit sync, and `MaxDisplayDuration`. For group priority,
apply the canonical [Tip Groups](#tip-groups) decision.

### DON'T: Use tips for critical information

Tips are dismissible and educational. Use alerts, confirmations, inline
warnings, or blocking UI for safety, errors, data loss, and required steps.

### DON'T: Ship testing overrides

`showAllTipsForTesting()` and related overrides bypass rules and frequency
limits. Keep them behind `#if DEBUG`, test scheme arguments, or UI-test-only
launch arguments.

### DON'T: Use unstable reusable tip IDs

Tip IDs own persistence. If a reusable tip's ID changes unexpectedly, users can
see duplicate or stale education.

## Review Checklist

- [ ] `Tips.configure(_:)` runs once during app initialization before tips display.
- [ ] `Tips.resetDatastore()` runs only before configuration and only for tests/debug.
- [ ] iOS 18+ and iOS 26+ TipKit APIs have availability gates or fallback guidance.
- [ ] Tip copy is short, contextual, actionable, and not promotional.
- [ ] Inline vs popover presentation matches the surrounding UI flow.
- [ ] Rules target the intended audience and do not show every tip on first launch.
- [ ] Event IDs are stable, namespaced when shared, and donation payloads are small.
- [ ] Reusable tips override `id` with stable content-derived values.
- [ ] Tips invalidate when the user performs the taught action.
- [ ] `TipGroup` stays in `@State` and follows the Tip Groups priority decision.
- [ ] CloudKit sync uses iCloud + CloudKit, Remote notifications, and a dedicated container when appropriate.
- [ ] Custom styles use `configuration` values and call `action.label()`.
- [ ] Testing overrides are debug/test-only and never ship active in production.

## References

- Read [references/tipkit-patterns.md](references/tipkit-patterns.md) for complete implementation patterns: custom styles, event rules with donation values, TipGroup sequencing, CloudKit/app-group persistence, reusable IDs, previews, and test launch strategies.
- Apple TipKit docs: https://sosumi.ai/documentation/tipkit
- Apple `Tips.configure(_:)`: https://sosumi.ai/documentation/tipkit/tips/configure(_:)
- Apple `TipGroup`: https://sosumi.ai/documentation/tipkit/tipgroup
- Apple HIG "Offering help": https://sosumi.ai/design/human-interface-guidelines/offering-help
- WWDC24 "Customize feature discovery with TipKit": https://sosumi.ai/videos/play/wwdc2024/10070
- WWDC23 "Make features discoverable with TipKit": https://sosumi.ai/videos/play/wwdc2023/10229
