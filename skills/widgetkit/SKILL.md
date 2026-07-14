---
name: widgetkit
description: "Implement, review, or improve WidgetKit widgets and controls. Use when building Home Screen, Lock Screen, StandBy, or CarPlay widgets with timeline providers; configurable widgets with AppIntentTimelineProvider; interactive widgets or Control Center controls with Button/Toggle wiring; WidgetKit push reloads, refresh budgets, deep links, Smart Stack relevance, Liquid Glass/accented rendering, widget extension setup, WidgetBundle, App Groups, and entitlements."
---

# WidgetKit

Build home screen widgets, Lock Screen widgets, Control Center controls, and
StandBy or CarPlay widget surfaces for iOS 26+.

Keep adjacent-framework guidance scoped to WidgetKit integration. Include
ActivityKit and App Intents only where they connect directly to WidgetKit
surfaces; hand off full lifecycle, APNs content-state, Siri/Shortcuts/Spotlight,
or entity-modeling work to sibling `activitykit` or `app-intents` skills.

See [references/widgetkit-advanced.md](references/widgetkit-advanced.md) for timeline strategies, push-based
updates, Xcode setup, and advanced patterns.

## Contents

- [Workflow](#workflow)
- [Widget Protocol and WidgetBundle](#widget-protocol-and-widgetbundle)
- [Configuration Types](#configuration-types)
- [TimelineProvider](#timelineprovider)
- [AppIntentTimelineProvider](#appintenttimelineprovider)
- [Widget Families](#widget-families)
- [Interactive Widgets (iOS 17+)](#interactive-widgets-ios-17)
- [ActivityConfiguration Handoff](#activityconfiguration-handoff)
- [Control Center Widgets (iOS 18+)](#control-center-widgets-ios-18)
- [Lock Screen Widgets](#lock-screen-widgets)
- [StandBy Mode](#standby-mode)
- [Widget URL Handling and Deep Links](#widget-url-handling-and-deep-links)
- [Smart Stack Relevance](#smart-stack-relevance)
- [Design Patterns](#design-patterns)
- [iOS 26 Additions](#ios-26-additions)
- [Common Mistakes](#common-mistakes)
- [Review Checklist](#review-checklist)
- [References](#references)

## Workflow

### 1. Create a new widget

1. Add a Widget Extension target in Xcode (File > New > Target > Widget Extension).
2. Enable App Groups for shared data between the app and widget extension.
3. Define a `TimelineEntry` struct with a `date` property and display data.
4. Implement a `TimelineProvider` (static) or `AppIntentTimelineProvider` (configurable).
5. Build the widget view using SwiftUI, adapting layout per `WidgetFamily`.
6. Declare the `Widget` conforming struct with a configuration and supported families.
7. Register all widgets in a `WidgetBundle` annotated with `@main`.

### 2. Integrate adjacent surfaces

1. Register an `ActivityConfiguration` in the widget bundle when the app has a
   Live Activity, but keep `ActivityAttributes`, request/update/end, APNs
   `content-state`, and Dynamic Island layout depth in `activitykit`.
2. Place `Button`, `Toggle`, `ControlWidgetButton`, and `ControlWidgetToggle`
   in WidgetKit views or controls, but keep intent modeling, entities, queries,
   Siri, Shortcuts, and Spotlight in `app-intents`.

### 3. Add a Control Center control

1. Reuse an `AppIntent`/`OpenIntent` for a button, or a `SetValueIntent` for a toggle.
2. Create a `ControlWidgetButton` or `ControlWidgetToggle` in the widget bundle.
3. Use `StaticControlConfiguration` or `AppIntentControlConfiguration`.

### 4. Review existing widget code

Run through the Review Checklist at the end of this document.

## Widget Protocol and WidgetBundle

### Widget

Every widget conforms to the `Widget` protocol and returns a `WidgetConfiguration`
from its `body`.

```swift
struct OrderStatusWidget: Widget {
    let kind: String = "OrderStatusWidget"

    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: OrderProvider()) { entry in
            OrderWidgetView(entry: entry)
        }
        .configurationDisplayName("Order Status")
        .description("Track your current order.")
        .supportedFamilies([.systemSmall, .systemMedium])
    }
}
```

### WidgetBundle

Use `WidgetBundle` to expose multiple widgets from a single extension.

```swift
@main
struct MyAppWidgets: WidgetBundle {
    var body: some Widget {
        OrderStatusWidget()
        FavoritesWidget()
        DeliveryActivityWidget()   // ActivityConfiguration handoff
        QuickActionControl()       // Control Center
    }
}
```

## Configuration Types

Use `StaticConfiguration` for non-configurable widgets. Use `AppIntentConfiguration`
(recommended) for configurable widgets paired with `AppIntentTimelineProvider`.

```swift
// Static
StaticConfiguration(kind: "MyWidget", provider: MyProvider()) { entry in
    MyWidgetView(entry: entry)
}
// Configurable
AppIntentConfiguration(kind: "ConfigWidget", intent: SelectCategoryIntent.self,
                       provider: CategoryProvider()) { entry in
    CategoryWidgetView(entry: entry)
}
```

### Shared Modifiers

| Modifier | Purpose |
|---|---|
| `.configurationDisplayName(_:)` | Name shown in the widget gallery |
| `.description(_:)` | Description shown in the widget gallery |
| `.supportedFamilies(_:)` | Array of `WidgetFamily` values |
| `.supplementalActivityFamilies(_:)` | Live Activity sizes (`.small`, `.medium`) |

## TimelineProvider

For static (non-configurable) widgets. Uses completion handlers. Three required methods:

```swift
struct WeatherProvider: TimelineProvider {
    typealias Entry = WeatherEntry

    func placeholder(in context: Context) -> WeatherEntry {
        WeatherEntry(date: .now, temperature: 72, condition: "Sunny")
    }

    func getSnapshot(in context: Context, completion: @escaping (WeatherEntry) -> Void) {
        let entry = context.isPreview
            ? placeholder(in: context)
            : WeatherEntry(date: .now, temperature: currentTemp, condition: currentCondition)
        completion(entry)
    }

    func getTimeline(in context: Context, completion: @escaping (Timeline<WeatherEntry>) -> Void) {
        Task {
            let weather = await WeatherService.shared.fetch()
            let entry = WeatherEntry(date: .now, temperature: weather.temp, condition: weather.condition)
            let nextUpdate = Calendar.current.date(byAdding: .hour, value: 1, to: .now)!
            completion(Timeline(entries: [entry], policy: .after(nextUpdate)))
        }
    }
}
```

## AppIntentTimelineProvider

For configurable widgets. Uses async/await natively. Receives user intent configuration.

```swift
struct CategoryProvider: AppIntentTimelineProvider {
    typealias Entry = CategoryEntry
    typealias Intent = SelectCategoryIntent

    func placeholder(in context: Context) -> CategoryEntry {
        CategoryEntry(date: .now, categoryName: "Sample", items: [])
    }

    func snapshot(for config: SelectCategoryIntent, in context: Context) async -> CategoryEntry {
        let items = await DataStore.shared.items(for: config.category)
        return CategoryEntry(date: .now, categoryName: config.category.name, items: items)
    }

    func timeline(for config: SelectCategoryIntent, in context: Context) async -> Timeline<CategoryEntry> {
        let items = await DataStore.shared.items(for: config.category)
        let entry = CategoryEntry(date: .now, categoryName: config.category.name, items: items)
        return Timeline(entries: [entry], policy: .atEnd)
    }
}
```

## Widget Families

| Family | Platform |
|---|---|
| `.systemSmall` | iOS, iPadOS, macOS, CarPlay (iOS 26+) |
| `.systemMedium` | iOS, iPadOS, macOS |
| `.systemLarge` | iOS, iPadOS, macOS |
| `.systemExtraLarge` | iPadOS only |
| `.accessoryCircular` | iOS, watchOS |
| `.accessoryRectangular` | iOS, watchOS |
| `.accessoryInline` | iOS, watchOS |
| `.accessoryCorner` | watchOS only |

Adapt layout per family using `@Environment(\.widgetFamily)`:

```swift
@Environment(\.widgetFamily) var family

var body: some View {
    switch family {
    case .systemSmall: CompactView(entry: entry)
    case .systemMedium: DetailedView(entry: entry)
    case .accessoryCircular: CircularView(entry: entry)
    default: FullView(entry: entry)
    }
}
```

## Interactive Widgets (iOS 17+)

Use `Button` and `Toggle` with intent types available to the widget extension or
shared code. WidgetKit owns the view placement; `app-intents` owns intent
modeling and behavior.

```swift
struct InteractiveWidgetView: View {
    let entry: FavoriteEntry

    var body: some View {
        Button(intent: ToggleFavoriteIntent(itemID: entry.itemID)) {
            Image(systemName: entry.isFavorite ? "star.fill" : "star")
        }
    }
}
```

## ActivityConfiguration Handoff

WidgetKit registers Live Activity surfaces in the widget extension. Keep this
section to registration and rendering handoff; use `activitykit` for
`ActivityAttributes`, lifecycle, push updates, and full Dynamic Island patterns.

```swift
struct DeliveryActivityWidget: Widget {
    var body: some WidgetConfiguration {
        ActivityConfiguration(for: DeliveryAttributes.self) { context in
            DeliveryLiveActivityView(context: context)
        } dynamicIsland: { context in
            DeliveryDynamicIsland(context: context)
        }
    }
}
```

## Control Center Widgets (iOS 18+)

WidgetKit owns control configuration, placement, kind, display name, push
handler, and extension registration. Control actions and value intents belong in
`app-intents`.

```swift
struct OpenCameraControl: ControlWidget {
    var body: some ControlWidgetConfiguration {
        StaticControlConfiguration(kind: "OpenCamera") {
            ControlWidgetButton(action: OpenCameraIntent()) {
                Label("Camera", systemImage: "camera.fill")
            }
        }
        .displayName("Open Camera")
    }
}

struct FlashlightControl: ControlWidget {
    var body: some ControlWidgetConfiguration {
        StaticControlConfiguration(kind: "Flashlight", provider: FlashlightValueProvider()) { value in
            ControlWidgetToggle(isOn: value, action: ToggleFlashlightIntent()) {
                Label("Flashlight", systemImage: value ? "flashlight.on.fill" : "flashlight.off.fill")
            }
        }
        .displayName("Flashlight")
    }
}
```

## Lock Screen Widgets

Use accessory families and `AccessoryWidgetBackground`.

```swift
struct StepsWidget: Widget {
    let kind = "StepsWidget"
    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: StepsProvider()) { entry in
            ZStack {
                AccessoryWidgetBackground()
                VStack {
                    Image(systemName: "figure.walk")
                    Text("\(entry.stepCount)").font(.headline)
                }
            }
        }
        .supportedFamilies([.accessoryCircular, .accessoryRectangular, .accessoryInline])
    }
}
```

## StandBy Mode

Small system widgets can appear in StandBy and CarPlay. Use
`@Environment(\.widgetLocation)` for conditional rendering:

```swift
@Environment(\.widgetLocation) var location
// location == .standBy, .homeScreen, .lockScreen, .carPlay, etc.
```

## Widget URL Handling and Deep Links

Use one `.widgetURL(_:)` as the whole-widget fallback route. Use `Link` for
deliberate subtargets only where the family and layout support them, including
`.accessoryRectangular`, `.systemSmall`, and larger system widgets. For small
widgets, prefer one clear fallback; avoid multiple `Link` targets unless the
visual affordance and hit areas remain unambiguous.

Never attach multiple `widgetURL` modifiers in the hierarchy.

## Smart Stack Relevance

Use `TimelineEntryRelevance(score:duration:)` on timeline entries for timely
iPhone and iPad Smart Stack relevance. Keep scores on a consistent positive
scale; zero or lower means not relevant.

For configurable widgets, donate App Intents that correspond to user actions or
widget parameters from app-side code, such as with `intent.donate()` or
`IntentDonationManager`. Keep `AppEntity` and `EntityQuery` design in
`app-intents`.

On watchOS, contextual relevance uses
`WidgetRelevance([WidgetRelevanceAttribute(...)])` from the provider
`relevance()` callback. That path is not used by iPhone or iPad Smart Stacks.

## Design Patterns

- **Prefer `Gauge` over manual arcs.** Use `.gaugeStyle(.accessoryCircular)` for
  Lock Screen circular widgets and `.linearCapacity` for home screen capacity bars.
  The system handles styling, accessibility, and rendering-mode adaptation.
- **Use `.containerBackground(_:for: .widget)`** (iOS 17+) for widget backgrounds
  instead of padding and background modifiers.
- **Use `Canvas` for dense visualizations** like sparklines or mini bar charts.
  The lack of per-element accessibility is acceptable since the entire widget
  surface is a single tap target.
- **Match timeline refresh to data granularity.** The budget is dynamic and opportunistic; schedule useful future entries, avoid unnecessary reloads, and use `Text(timerInterval:countsDown:)` for live countdowns. Load the advanced reference for current budget guidance.

See [references/widgetkit-advanced.md](references/widgetkit-advanced.md) for
code examples and detailed guidance on each pattern.

## iOS 26 Additions

### Liquid Glass Support

Adapt widgets to Liquid Glass with `@Environment(\.widgetRenderingMode)`,
`.widgetAccentable()`, and `Image.widgetAccentedRenderingMode(_:)`. In
`.vibrant`, the system maps content into the material style, so avoid relying on
original colors alone.

### Push Reload Handlers

Widget push reloads:
- Add Push Notifications capability to the widget extension target.
- Keep the `WidgetPushHandler` type in the widget extension target or shared
  code linked into it, not only in the main app target.
- Register the handler with `.pushHandler(...)` on the widget configuration.
- Do not use User Notifications registration to obtain widget push tokens;
  WidgetKit supplies tokens through `pushTokenDidChange(_:widgets:)`.
- Use `apns-push-type: widgets`, topic suffix `.push-type.widgets`, and
  `aps.content-changed`.
- Treat push as a budgeted, opportunistic reload signal, not state delivery and
  not the only freshness model. Timelines, reload policies, shared storage or
  refetch, and app-triggered `WidgetCenter` reloads remain the fallback path.

Control push reloads:
- Register a `ControlPushHandler` with `.pushHandler(...)` on the
  `ControlWidgetConfiguration`.
- `pushTokensDidChange(controls:)` receives `[ControlInfo]`; read tokens from
  each control's `pushInfo`.
- Use `apns-push-type: controls`, topic suffix `.push-type.controls`, and
  `aps.content-changed`.

### CarPlay Widgets

Small system widgets can appear in CarPlay on iOS 26+. Ensure layouts are
legible at a glance; taps and controls depend on vehicle touch support and, for
opening the app, CarPlay integration.

## Common Mistakes

1. **Using IntentTimelineProvider instead of AppIntentTimelineProvider.**
   `IntentTimelineProvider` is the older SiriKit Intents-based provider. Prefer
   `AppIntentTimelineProvider` with the App Intents framework for new widgets.

2. **Exceeding the refresh budget.** Widgets have a daily refresh limit. Do not
   call `WidgetCenter.shared.reloadTimelines(ofKind:)` on every minor data change.
   Batch updates and use appropriate `TimelineReloadPolicy` values.

3. **Forgetting App Groups for shared data.** The widget extension runs in a
   separate process. Use `UserDefaults(suiteName:)` or a shared App Group
   container for data the widget reads.

4. **Performing network calls in placeholder().** `placeholder(in:)` must return
   synchronously with sample data. Use `getTimeline` or `timeline(for:in:)` for
   async work.

5. **Treating WidgetKit push payloads as state.** Widget and control pushes are
   reload signals. Persist state in shared storage or refetch it in the provider.

6. **Registering widget pushes through User Notifications.** Widget push tokens
   come from WidgetKit handlers, not `UNUserNotificationCenter`.

7. **Putting heavy logic in the widget view.** Widget views are rendered in a
   size-limited process. Pre-compute data in the timeline provider and pass
   display-ready values through the entry.

8. **Ignoring accessory rendering modes.** Lock Screen widgets render in
   `.vibrant` or `.accented` mode, not `.fullColor`. Test with
   `@Environment(\.widgetRenderingMode)` and avoid relying on color alone.

9. **Not testing on device.** StandBy, CarPlay, and accessory rendering differ
    significantly from Simulator. Always verify on physical hardware.

## Review Checklist

- [ ] Widget extension target has App Groups entitlement matching the main app
- [ ] `@main` is on the `WidgetBundle`, not on individual widgets
- [ ] `placeholder(in:)` returns synchronously; `getSnapshot`/`snapshot(for:in:)` fast when `isPreview`
- [ ] Timeline reload policy matches update frequency; `reloadTimelines(ofKind:)` only on data change
- [ ] Layout adapts per `WidgetFamily`; accessory widgets tested in `.vibrant` mode
- [ ] Interactive widgets use extension-available App Intents with `Button`/`Toggle` only
- [ ] One `.widgetURL(_:)` fallback is used; `Link` subtargets are family-appropriate
- [ ] Widget push handlers live in the widget extension/shared code and do not use User Notifications token registration
- [ ] Widget/control pushes supplement timelines and shared-state/refetch fallbacks
- [ ] Smart Stack relevance uses timeline relevance and app-side intent donations where useful
- [ ] Live Activity lifecycle and App Intent modeling are handed off to sibling skills
- [ ] Controls use `StaticControlConfiguration`/`AppIntentControlConfiguration`
- [ ] Timeline entries and Intent types are Sendable; tested on device

## References

- Advanced guide: [references/widgetkit-advanced.md](references/widgetkit-advanced.md)
- Apple docs: [WidgetKit](https://sosumi.ai/documentation/widgetkit) | [Keeping a widget up to date](https://sosumi.ai/documentation/widgetkit/keeping-a-widget-up-to-date) | [Smart Stack visibility](https://sosumi.ai/documentation/widgetkit/widget-suggestions-in-smart-stacks)
