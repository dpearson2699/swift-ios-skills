---
name: widgetkit
description: "Implement, review, or improve widgets, Live Activities, and controls using WidgetKit and ActivityKit. Use when building home screen, Lock Screen, or StandBy widgets with timeline providers; when creating interactive widgets with Button/Toggle and AppIntent actions; when adding Live Activities with Dynamic Island layouts (compact, minimal, expanded); when building Control Center widgets with ControlWidgetButton/ControlWidgetToggle; when configuring widget families, refresh budgets, deep links, push-based reloads, or Liquid Glass rendering; or when setting up widget extensions, App Groups, and entitlements."
---

# WidgetKit and ActivityKit

Build home screen widgets, Lock Screen widgets, Live Activities, Dynamic Island
presentations, Control Center controls, and StandBy surfaces for iOS 26+.

See `references/widgetkit-advanced.md` for timeline strategies, push-based
updates, Xcode setup, and advanced patterns.

## Workflow

### 1. Create a new widget

1. Add a Widget Extension target in Xcode (File > New > Target > Widget Extension).
2. Enable App Groups for shared data between the app and widget extension.
3. Define a `TimelineEntry` struct with a `date` property and display data.
4. Implement a `TimelineProvider` (static) or `AppIntentTimelineProvider` (configurable).
5. Build the widget view using SwiftUI, adapting layout per `WidgetFamily`.
6. Declare the `Widget` conforming struct with a configuration and supported families.
7. Register all widgets in a `WidgetBundle` annotated with `@main`.

### 2. Add a Live Activity

1. Define an `ActivityAttributes` struct with a nested `ContentState`.
2. Add `NSSupportsLiveActivities = YES` to the app's Info.plist.
3. Create an `ActivityConfiguration` in the widget bundle with Lock Screen content
   and Dynamic Island closures.
4. Start the activity with `Activity.request(attributes:content:pushType:)`.
5. Update with `activity.update(_:)` and end with `activity.end(_:dismissalPolicy:)`.

### 3. Add a Control Center control

1. Define an `AppIntent` for the action.
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
        DeliveryActivityWidget()   // Live Activity
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

### System Families (Home Screen)

| Family | Platform |
|---|---|
| `.systemSmall` | iOS, iPadOS, macOS, CarPlay (iOS 26+) |
| `.systemMedium` | iOS, iPadOS, macOS |
| `.systemLarge` | iOS, iPadOS, macOS |
| `.systemExtraLarge` | iPadOS only |

### Accessory Families (Lock Screen / watchOS)

| Family | Platform |
|---|---|
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

Use `Button` and `Toggle` with `AppIntent` conforming types to perform actions
directly from a widget without launching the app.

```swift
struct ToggleFavoriteIntent: AppIntent {
    static var title: LocalizedStringResource = "Toggle Favorite"
    @Parameter(title: "Item ID") var itemID: String

    func perform() async throws -> some IntentResult {
        await DataStore.shared.toggleFavorite(itemID)
        return .result()
    }
}

struct InteractiveWidgetView: View {
    let entry: FavoriteEntry
    var body: some View {
        HStack {
            Text(entry.itemName)
            Spacer()
            Button(intent: ToggleFavoriteIntent(itemID: entry.itemID)) {
                Image(systemName: entry.isFavorite ? "star.fill" : "star")
            }
        }
        .padding()
    }
}
```

## Live Activities and Dynamic Island

### ActivityAttributes

Define the static and dynamic data model.

```swift
struct DeliveryAttributes: ActivityAttributes {
    struct ContentState: Codable, Hashable {
        var driverName: String
        var estimatedDeliveryTime: ClosedRange<Date>
        var currentStep: DeliveryStep
    }

    var orderNumber: Int
    var restaurantName: String
}
```

### ActivityConfiguration

Provide Lock Screen content and Dynamic Island closures in the widget bundle.

```swift
struct DeliveryActivityWidget: Widget {
    var body: some WidgetConfiguration {
        ActivityConfiguration(for: DeliveryAttributes.self) { context in
            VStack(alignment: .leading) {
                Text(context.attributes.restaurantName).font(.headline)
                HStack {
                    Text("Driver: \(context.state.driverName)")
                    Spacer()
                    Text(timerInterval: context.state.estimatedDeliveryTime, countsDown: true)
                }
            }
            .padding()
        } dynamicIsland: { context in
            DynamicIsland {
                DynamicIslandExpandedRegion(.leading) {
                    Image(systemName: "box.truck.fill").font(.title2)
                }
                DynamicIslandExpandedRegion(.trailing) {
                    Text(timerInterval: context.state.estimatedDeliveryTime, countsDown: true)
                        .font(.caption)
                }
                DynamicIslandExpandedRegion(.center) {
                    Text(context.attributes.restaurantName).font(.headline)
                }
                DynamicIslandExpandedRegion(.bottom) {
                    HStack {
                        ForEach(DeliveryStep.allCases, id: \.self) { step in
                            Image(systemName: step.icon)
                                .foregroundStyle(step <= context.state.currentStep ? .primary : .tertiary)
                        }
                    }
                }
            } compactLeading: {
                Image(systemName: "box.truck.fill")
            } compactTrailing: {
                Text(timerInterval: context.state.estimatedDeliveryTime, countsDown: true)
                    .frame(width: 40).monospacedDigit()
            } minimal: {
                Image(systemName: "box.truck.fill")
            }
        }
    }
}
```

### Dynamic Island Regions

| Region | Position |
|---|---|
| `.leading` | Left of the TrueDepth camera; wraps below |
| `.trailing` | Right of the TrueDepth camera; wraps below |
| `.center` | Directly below the camera |
| `.bottom` | Below all other regions |

### Starting, Updating, and Ending

```swift
// Start
let attributes = DeliveryAttributes(orderNumber: 123, restaurantName: "Pizza Place")
let state = DeliveryAttributes.ContentState(
    driverName: "Alex",
    estimatedDeliveryTime: Date()...Date().addingTimeInterval(1800),
    currentStep: .preparing
)
let content = ActivityContent(state: state, staleDate: nil, relevanceScore: 75)
let activity = try Activity.request(attributes: attributes, content: content, pushType: .token)

// Update (optionally with alert)
let updated = ActivityContent(state: newState, staleDate: nil, relevanceScore: 90)
await activity.update(updated)
await activity.update(updated, alertConfiguration: AlertConfiguration(
    title: "Order Update", body: "Your driver is nearby!", sound: .default
))

// End
let final = ActivityContent(state: finalState, staleDate: nil, relevanceScore: 0)
await activity.end(final, dismissalPolicy: .after(.now.addingTimeInterval(3600)))
```

## Control Center Widgets (iOS 18+)

```swift
// Button control
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

// Toggle control with value provider
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

`.systemSmall` widgets automatically appear in StandBy (iPhone on charger in
landscape). Use `@Environment(\.widgetLocation)` for conditional rendering:

```swift
@Environment(\.widgetLocation) var location
// location == .standBy, .homeScreen, .lockScreen, .carPlay, etc.
```

## iOS 26 Additions

### Liquid Glass Support

Adapt widgets to the Liquid Glass visual style using `WidgetAccentedRenderingMode`.

| Mode | Description |
|---|---|
| `.accented` | Accented rendering for Liquid Glass |
| `.accentedDesaturated` | Accented with desaturation |
| `.desaturated` | Fully desaturated |
| `.fullColor` | Full-color rendering |

### WidgetPushHandler

Enable push-based timeline reloads without scheduled polling.

```swift
struct MyWidgetPushHandler: WidgetPushHandler {
    func pushTokenDidChange(_ pushInfo: WidgetPushInfo, widgets: [WidgetInfo]) {
        let tokenString = pushInfo.token.map { String(format: "%02x", $0) }.joined()
        // Send tokenString to your server
    }
}
```

### CarPlay Widgets

`.systemSmall` widgets render in CarPlay on iOS 26+. Ensure small widget layouts
are legible at a glance for driver safety.

## Common Mistakes

1. **Using IntentTimelineProvider instead of AppIntentTimelineProvider.**
   `IntentTimelineProvider` is deprecated. Use `AppIntentTimelineProvider` with
   the App Intents framework.

2. **Exceeding the refresh budget.** Widgets have a daily refresh limit. Do not
   call `WidgetCenter.shared.reloadTimelines(ofKind:)` on every minor data change.
   Batch updates and use appropriate `TimelineReloadPolicy` values.

3. **Forgetting App Groups for shared data.** The widget extension runs in a
   separate process. Use `UserDefaults(suiteName:)` or a shared App Group
   container for data the widget reads.

4. **Performing network calls in placeholder().** `placeholder(in:)` must return
   synchronously with sample data. Use `getTimeline` or `timeline(for:in:)` for
   async work.

5. **Missing NSSupportsLiveActivities Info.plist key.** Live Activities will not
   start without `NSSupportsLiveActivities = YES` in the host app's Info.plist.

6. **Using the deprecated contentState API.** Use `ActivityContent` for all
   `Activity.request`, `update`, and `end` calls. The `contentState`-based
   methods are deprecated.

7. **Not handling the stale state.** Check `context.isStale` in Live Activity
   views and show a fallback (e.g., "Updating...") when content is outdated.

8. **Putting heavy logic in the widget view.** Widget views are rendered in a
   size-limited process. Pre-compute data in the timeline provider and pass
   display-ready values through the entry.

9. **Ignoring accessory rendering modes.** Lock Screen widgets render in
   `.vibrant` or `.accented` mode, not `.fullColor`. Test with
   `@Environment(\.widgetRenderingMode)` and avoid relying on color alone.

10. **Not testing on device.** Dynamic Island and StandBy behavior differ
    significantly from Simulator. Always verify on physical hardware.

## Review Checklist

- [ ] Widget extension target has App Groups entitlement matching the main app
- [ ] `@main` is on the `WidgetBundle`, not on individual widgets
- [ ] `placeholder(in:)` returns synchronously with sample data
- [ ] `getSnapshot` / `snapshot(for:in:)` returns quickly when `context.isPreview` is true
- [ ] Timeline reload policy matches data update frequency (`.atEnd`, `.after`, `.never`)
- [ ] `WidgetCenter.shared.reloadTimelines(ofKind:)` called only when data actually changes
- [ ] Layout adapts per `WidgetFamily` using `@Environment(\.widgetFamily)`
- [ ] Accessory widgets use `AccessoryWidgetBackground` and test in `.vibrant` mode
- [ ] Interactive widgets use `AppIntent` with `Button` or `Toggle` only
- [ ] Live Activity has `NSSupportsLiveActivities = YES` in Info.plist
- [ ] `ActivityContent` used (not deprecated `contentState` API)
- [ ] Dynamic Island provides all four closures (expanded, compactLeading, compactTrailing, minimal)
- [ ] `activity.end(_:dismissalPolicy:)` called to clean up Live Activities
- [ ] Control widgets use `StaticControlConfiguration` or `AppIntentControlConfiguration`
- [ ] Widget tested on device for StandBy, Dynamic Island, and Lock Screen
- [ ] iOS 26 Liquid Glass rendering tested with `WidgetAccentedRenderingMode`
- [ ] Ensure Timeline entries and Intent types are Sendable; widget configuration providers should be @MainActor-isolated if they access shared state

## API Verification

The apple-docs MCP server is available for verifying WidgetKit and ActivityKit API
names, signatures, and availability. Use `fetchAppleDocumentation` with paths like
`/documentation/widgetkit` or `/documentation/activitykit`.

## References

- Advanced guide: `references/widgetkit-advanced.md`
- Apple docs: [WidgetKit](https://sosumi.ai/documentation/widgetkit) |
  [ActivityKit](https://sosumi.ai/documentation/activitykit) |
  [Keeping a widget up to date](https://sosumi.ai/documentation/widgetkit/keeping-a-widget-up-to-date)
