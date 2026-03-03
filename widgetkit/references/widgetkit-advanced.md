# WidgetKit Advanced Reference

## Timeline Strategies

### TimelineReloadPolicy

Control when WidgetKit requests a new timeline after the current entries expire.

| Policy | Behavior | Use When |
|---|---|---|
| `.atEnd` | Requests a new timeline after the last entry's date. Default. | Data changes unpredictably. |
| `.after(Date)` | Requests a new timeline after a specific date. | Data updates on a known schedule (market hours, flights). |
| `.never` | No automatic refresh. App must trigger manually. | Data changes only from user action. |

### Multiple Timeline Entries

Pre-generate entries for known future states to reduce refresh requests and
conserve the daily budget.

```swift
func timeline(for configuration: Intent, in context: Context) async -> Timeline<StockEntry> {
    var entries: [StockEntry] = []
    let now = Date()

    // Generate hourly entries for the next 6 hours
    for hourOffset in 0..<6 {
        let entryDate = Calendar.current.date(byAdding: .hour, value: hourOffset, to: now)!
        let price = await StockService.shared.projectedPrice(at: entryDate, for: configuration.symbol)
        entries.append(StockEntry(date: entryDate, symbol: configuration.symbol.name, price: price))
    }

    let nextRefresh = Calendar.current.date(byAdding: .hour, value: 6, to: now)!
    return Timeline(entries: entries, policy: .after(nextRefresh))
}
```

### Triggering Manual Reloads

```swift
// Reload a specific widget kind
WidgetCenter.shared.reloadTimelines(ofKind: "OrderStatusWidget")

// Reload all widgets
WidgetCenter.shared.reloadAllTimelines()
```

Call `reloadTimelines(ofKind:)` only when displayed data actually changes. Each
call counts against the daily refresh budget.

### Refresh Budget

Each configured widget has a daily refresh limit. Exemptions apply for:
- Foreground app usage
- Active media sessions
- Standard location service usage

WidgetKit does not impose refresh limits when debugging in Xcode.

## Push-Based Timeline Reloads (iOS 26+)

### WidgetPushHandler

Use push notifications to trigger timeline reloads without scheduled polling.

```swift
struct MyWidgetPushHandler: WidgetPushHandler {
    func pushTokenDidChange(_ token: Data, widgets: [WidgetPushInfo]) {
        let tokenString = token.map { String(format: "%02x", $0) }.joined()
        Task {
            try await ServerAPI.shared.register(widgetPushToken: tokenString)
        }
    }
}
```

### Server-Side Integration

Send an APNs push with the widget's push token. The system calls your
`TimelineProvider.getTimeline` or `AppIntentTimelineProvider.timeline(for:in:)`
when the push arrives.

### ControlPushHandler

Equivalent handler for Control Center controls:

```swift
struct MyControlPushHandler: ControlPushHandler {
    func pushTokensDidChange(controls: [ControlPushInfo]) {
        for control in controls {
            let tokenString = control.token.map { String(format: "%02x", $0) }.joined()
            Task {
                try await ServerAPI.shared.register(controlPushToken: tokenString)
            }
        }
    }
}
```

## Widget URL Handling and Deep Links

### widgetURL(_:)

Set a single URL for the entire widget. Tapping anywhere opens the app with this URL.

```swift
struct SmallWidgetView: View {
    let entry: OrderEntry

    var body: some View {
        VStack {
            Text(entry.orderName)
            Text(entry.status)
        }
        .widgetURL(URL(string: "myapp://orders/\(entry.orderID)")!)
    }
}
```

### Link (Medium and Larger Widgets)

Use `Link` for multiple tap targets in `.systemMedium` and larger widgets.

```swift
struct MediumWidgetView: View {
    let entry: OrderListEntry

    var body: some View {
        VStack {
            ForEach(entry.orders) { order in
                Link(destination: URL(string: "myapp://orders/\(order.id)")!) {
                    HStack {
                        Text(order.name)
                        Spacer()
                        Text(order.status)
                    }
                }
            }
        }
    }
}
```

### Handling in the App

```swift
@main
struct MyApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
                .onOpenURL { url in
                    DeepLinkRouter.shared.handle(url)
                }
        }
    }
}
```

**Important:** `.systemSmall` widgets support only `widgetURL`, not `Link`.

## Intent-Driven Widget Configuration

### Defining a WidgetConfigurationIntent

```swift
struct SelectCategoryIntent: WidgetConfigurationIntent {
    static var title: LocalizedStringResource = "Select Category"
    static var description: IntentDescription = "Choose a category to display."

    @Parameter(title: "Category")
    var category: CategoryEntity

    init() {}

    init(category: CategoryEntity) {
        self.category = category
    }
}
```

### Entity Query for Dynamic Options

```swift
struct CategoryEntity: AppEntity {
    static var typeDisplayRepresentation = TypeDisplayRepresentation(name: "Category")
    static var defaultQuery = CategoryQuery()

    var id: String
    var name: String

    var displayRepresentation: DisplayRepresentation {
        DisplayRepresentation(title: "\(name)")
    }
}

struct CategoryQuery: EntityQuery {
    func entities(for identifiers: [String]) async throws -> [CategoryEntity] {
        await DataStore.shared.categories(for: identifiers)
    }

    func suggestedEntities() async throws -> [CategoryEntity] {
        await DataStore.shared.allCategories()
    }

    func defaultResult() async -> CategoryEntity? {
        await DataStore.shared.defaultCategory()
    }
}
```

### Recommendations

Provide pre-configured suggestions for the widget gallery:

```swift
func recommendations() -> [AppIntentRecommendation<SelectCategoryIntent>] {
    let categories: [(String, CategoryEntity)] = [
        ("Groceries", .groceries),
        ("Work Tasks", .work),
    ]
    return categories.map { name, entity in
        let intent = SelectCategoryIntent(category: entity)
        return AppIntentRecommendation(intent: intent, description: name)
    }
}
```

## Multiple Widget Support in WidgetBundle

### Declaring Multiple Widgets

```swift
@main
struct MyAppWidgets: WidgetBundle {
    var body: some Widget {
        OrderStatusWidget()          // Home Screen widget
        FavoritesWidget()            // Configurable widget
        StepsAccessoryWidget()       // Lock Screen widget
        DeliveryActivityWidget()     // Live Activity
        QuickActionControl()         // Control Center
    }
}
```

### Conditional Widgets

Include widgets conditionally based on platform or availability:

```swift
@main
struct MyAppWidgets: WidgetBundle {
    var body: some Widget {
        CoreWidget()
        if #available(iOS 18, *) {
            QuickActionControl()
        }
    }
}
```

## Widget Previews and Snapshots

### Xcode Previews

```swift
#Preview("Small", as: .systemSmall) {
    OrderStatusWidget()
} timeline: {
    OrderEntry(date: .now, orderName: "Pizza", status: "Preparing")
    OrderEntry(date: .now.addingTimeInterval(600), orderName: "Pizza", status: "Delivering")
}

#Preview("Circular", as: .accessoryCircular) {
    StepsAccessoryWidget()
} timeline: {
    StepsEntry(date: .now, stepCount: 4200)
}
```

### Live Activity Previews

```swift
#Preview("Lock Screen", as: .content, using: DeliveryAttributes.preview) {
    DeliveryActivityWidget()
} contentStates: {
    DeliveryAttributes.ContentState(
        driverName: "Alex",
        estimatedDeliveryTime: Date()...Date().addingTimeInterval(900),
        currentStep: .delivering
    )
}

#Preview("Dynamic Island Compact", as: .dynamicIsland(.compact), using: DeliveryAttributes.preview) {
    DeliveryActivityWidget()
} contentStates: {
    DeliveryAttributes.ContentState(
        driverName: "Alex",
        estimatedDeliveryTime: Date()...Date().addingTimeInterval(900),
        currentStep: .delivering
    )
}
```

### Snapshot Best Practices

- Return sample data immediately in `placeholder(in:)` -- it must be synchronous.
- In `getSnapshot` / `snapshot(for:in:)`, check `context.isPreview`:
  - When `true`, return representative sample data quickly.
  - When `false`, return the current real state.

```swift
// WRONG: Performing a network call in placeholder
func placeholder(in context: Context) -> MyEntry {
    // Compilation error: placeholder must be synchronous
    let data = await fetchData()
    return MyEntry(date: .now, data: data)
}

// CORRECT: Return static sample data
func placeholder(in context: Context) -> MyEntry {
    MyEntry(date: .now, data: SampleData.placeholder)
}
```

## AccessoryWidgetBackground

Provide the standard translucent background for Lock Screen widgets.

```swift
struct CircularStepsView: View {
    let steps: Int

    var body: some View {
        ZStack {
            AccessoryWidgetBackground()
            VStack(spacing: 2) {
                Image(systemName: "figure.walk")
                    .font(.caption)
                Text("\(steps)")
                    .font(.headline)
                    .widgetAccentable()
            }
        }
    }
}
```

### Rendering Mode Awareness

Lock Screen widgets render in `.vibrant` or `.accented` mode. Adapt content:

```swift
@Environment(\.widgetRenderingMode) var renderingMode

var body: some View {
    switch renderingMode {
    case .fullColor:
        ColorfulView()
    case .vibrant, .accented:
        MonochromeView()
    @unknown default:
        MonochromeView()
    }
}
```

Use `.widgetAccentable()` to mark views that should receive the accent tint in
`.accented` rendering mode.

## Dynamic Island Expanded Layout Patterns

### Full Layout Example

```swift
DynamicIsland {
    DynamicIslandExpandedRegion(.leading) {
        VStack(alignment: .leading) {
            Image(systemName: "airplane")
                .font(.title2)
            Text("UA 1234")
                .font(.caption2)
        }
    }
    DynamicIslandExpandedRegion(.trailing) {
        VStack(alignment: .trailing) {
            Text("SFO")
                .font(.title3.bold())
            Text("On Time")
                .font(.caption2)
                .foregroundStyle(.green)
        }
    }
    DynamicIslandExpandedRegion(.center) {
        Text("San Francisco to New York")
            .font(.caption)
            .lineLimit(1)
    }
    DynamicIslandExpandedRegion(.bottom) {
        ProgressView(value: 0.45)
            .tint(.blue)
        HStack {
            Text("Departed 2:30 PM")
            Spacer()
            Text("Arrives 10:45 PM")
        }
        .font(.caption2)
        .foregroundStyle(.secondary)
    }
} compactLeading: {
    Image(systemName: "airplane")
} compactTrailing: {
    Text("2h 15m")
        .monospacedDigit()
} minimal: {
    Image(systemName: "airplane")
}
```

### Vertical Placement

Control vertical alignment within expanded regions:

```swift
DynamicIslandExpandedRegion(.leading) {
    Text("Top")
        .dynamicIsland(verticalPlacement: .belowIfTooWide)
}
```

### Content Margins

Override margins for specific Dynamic Island modes:

```swift
.contentMargins(.trailing, 20, for: .expanded)
.contentMargins(.bottom, 16, for: .expanded)
```

### Keyline Tint

Apply a subtle tint to the Dynamic Island border:

```swift
DynamicIsland { /* ... */ }
    .keylineTint(.blue)
```

## Alert Configuration for Live Activities

Trigger a visible and audible alert when updating a Live Activity:

```swift
let alert = AlertConfiguration(
    title: "Delivery Update",
    body: "Your order is out for delivery!",
    sound: .default
)
await activity.update(updatedContent, alertConfiguration: alert)
```

### Custom Alert Sound

```swift
let alert = AlertConfiguration(
    title: "Score Update",
    body: "Goal! The score is now 2-1.",
    sound: .named("goal-horn.aiff")
)
```

Place the sound file in the app bundle. Use `.default` when no custom sound is needed.

## Push Notification Support for Live Activities

### Registering for Push Updates

```swift
let activity = try Activity.request(
    attributes: attributes,
    content: content,
    pushType: .token  // Enable push updates
)

// Observe token changes
Task {
    for await token in activity.pushTokenUpdates {
        let tokenString = token.map { String(format: "%02x", $0) }.joined()
        try await ServerAPI.shared.registerActivityToken(tokenString, activityID: activity.id)
    }
}
```

### Push-to-Start (Remote Activity Creation)

```swift
// Observe the push-to-start token
Task {
    for await token in Activity<DeliveryAttributes>.pushToStartTokenUpdates {
        let tokenString = token.map { String(format: "%02x", $0) }.joined()
        try await ServerAPI.shared.registerPushToStartToken(tokenString)
    }
}
```

### Channel-Based Push (iOS 26+)

```swift
let activity = try Activity.request(
    attributes: attributes,
    content: content,
    pushType: .channel("delivery-updates")
)
```

### APNs Payload Format for Live Activity Updates

```json
{
    "aps": {
        "timestamp": 1234567890,
        "event": "update",
        "content-state": {
            "driverName": "Alex",
            "estimatedDeliveryTime": {
                "lowerBound": 1234567890,
                "upperBound": 1234568790
            },
            "currentStep": "delivering"
        },
        "alert": {
            "title": "Delivery Update",
            "body": "Your driver is nearby!"
        }
    }
}
```

The `content-state` must match the `ContentState` Codable structure exactly.

### Info.plist Keys

| Key | Value | Purpose |
|---|---|---|
| `NSSupportsLiveActivities` | `YES` | Enable Live Activities |
| `NSSupportsLiveActivitiesFrequentUpdates` | `YES` | Enable frequent push updates (budget increase) |

## ActivityAuthorizationInfo

Check whether Live Activities are permitted before attempting to start one.

```swift
let authInfo = ActivityAuthorizationInfo()

// Check permission synchronously
if authInfo.areActivitiesEnabled {
    try Activity.request(attributes: attributes, content: content, pushType: .token)
}

// Observe permission changes
Task {
    for await enabled in authInfo.activityEnablementUpdates {
        if enabled {
            // Activities became available
        }
    }
}

// Check frequent push support
if authInfo.frequentPushesEnabled {
    // Safe to use frequent push updates
}
```

### Error Handling

```swift
do {
    let activity = try Activity.request(attributes: attributes, content: content, pushType: .token)
} catch let error as ActivityAuthorizationError {
    switch error {
    case .denied:
        // User disabled Live Activities in Settings
        break
    case .globalMaximumExceeded:
        // Too many Live Activities across all apps
        break
    case .targetMaximumExceeded:
        // Too many Live Activities for this app
        break
    default:
        break
    }
}
```

## Widget Performance Best Practices

### Data Preparation

Pre-compute display values in the timeline provider. Pass display-ready data
through the entry.

```swift
// WRONG: Heavy computation in the widget view
struct MyWidgetView: View {
    let entry: RawDataEntry

    var body: some View {
        let processed = HeavyProcessor.process(entry.rawData)  // Slow
        Text(processed.summary)
    }
}

// CORRECT: Pre-compute in the provider
func timeline(for configuration: Intent, in context: Context) async -> Timeline<ProcessedEntry> {
    let raw = await DataStore.shared.fetch()
    let processed = HeavyProcessor.process(raw)
    let entry = ProcessedEntry(date: .now, summary: processed.summary, value: processed.value)
    return Timeline(entries: [entry], policy: .atEnd)
}
```

### Memory Constraints

Widget extensions run with strict memory limits. Avoid:
- Loading large images directly in the widget view
- Storing large data sets in the entry
- Creating complex view hierarchies

### Image Handling

```swift
// WRONG: Loading a full-resolution image
Image(uiImage: UIImage(contentsOfFile: fullResPath)!)

// CORRECT: Use a pre-resized thumbnail stored in the shared container
Image(uiImage: UIImage(contentsOfFile: thumbnailPath)!)
    .resizable()
    .aspectRatio(contentMode: .fill)
```

### Shared Data with App Groups

```swift
// In the main app: write data
let defaults = UserDefaults(suiteName: "group.com.example.myapp")
defaults?.set(encodedData, forKey: "widgetData")
WidgetCenter.shared.reloadTimelines(ofKind: "MyWidget")

// In the widget provider: read data
func timeline(for configuration: Intent, in context: Context) async -> Timeline<MyEntry> {
    let defaults = UserDefaults(suiteName: "group.com.example.myapp")
    let data = defaults?.data(forKey: "widgetData")
    // Decode and build entry
}
```

For larger datasets, use a shared SQLite database or Core Data store in the
App Group container.

## Xcode Setup

### Adding a Widget Extension Target

1. File > New > Target > Widget Extension.
2. Name the extension (e.g., "MyAppWidgets").
3. Select "Include Configuration App Intent" for configurable widgets.
4. Select "Include Live Activity" if building Live Activities.

### Entitlements

| Entitlement | Purpose |
|---|---|
| App Groups (`com.apple.security.application-groups`) | Share data between app and widget |
| Push Notifications (`aps-environment`) | Required for push-based Live Activity updates |

### App Groups Configuration

1. Enable "App Groups" capability on both the main app target and the widget
   extension target.
2. Create a shared group identifier (e.g., `group.com.example.myapp`).
3. Use `UserDefaults(suiteName:)` or `FileManager.containerURL(forSecurityApplicationGroupIdentifier:)`
   for shared storage.

### Build Schemes

- Use the widget extension scheme to debug widget rendering.
- Select "Widget" as the run destination to launch the widget directly.
- Use "Preview" in Xcode canvas for rapid iteration.

### Common Xcode Issues

```
// ERROR: "Widget extension must include at least one widget"
// FIX: Ensure @main is on the WidgetBundle, not a widget struct.

// ERROR: "No such module 'WidgetKit'"
// FIX: Ensure the widget extension target links WidgetKit and SwiftUI frameworks.

// ERROR: "The operation couldn't be completed. (ActivityKit.ActivityAuthorizationError error 3.)"
// FIX: Add NSSupportsLiveActivities = YES to the HOST APP's Info.plist (not the extension).
```

## Widget Relevance and Smart Stacks

### TimelineEntryRelevance

Score entries to surface widgets in Smart Stacks when relevant:

```swift
struct GameEntry: TimelineEntry {
    var date: Date
    var score: String
    var isLive: Bool

    var relevance: TimelineEntryRelevance? {
        isLive ? TimelineEntryRelevance(score: 100, duration: 3600) : nil
    }
}
```

Higher scores make the widget more likely to surface. The `duration` specifies
how long the relevance lasts.

### WidgetRelevance (AppIntentTimelineProvider)

```swift
func relevance() async -> WidgetRelevance<SelectCategoryIntent> {
    let topCategory = await DataStore.shared.mostActiveCategory()
    let intent = SelectCategoryIntent(category: topCategory)
    return WidgetRelevance(intent, score: 80)
}
```

## ActivityState Lifecycle

Track the full lifecycle of a Live Activity:

```swift
Task {
    for await state in activity.activityStateUpdates {
        switch state {
        case .active:
            // Activity is running and visible
            break
        case .pending:
            // Requested but not yet displayed (iOS 26+)
            break
        case .stale:
            // Content is outdated; update or end
            break
        case .ended:
            // Ended but may still be visible on Lock Screen
            break
        case .dismissed:
            // Fully removed from UI; clean up resources
            break
        @unknown default:
            break
        }
    }
}
```

## ActivityStyle

Control Live Activity persistence behavior (iOS 26+):

```swift
// Standard: persists until explicitly ended
let activity = try Activity.request(
    attributes: attributes,
    content: content,
    pushType: .token,
    style: .standard
)

// Transient: automatically dismissed after a period
let activity = try Activity.request(
    attributes: attributes,
    content: content,
    pushType: .token,
    style: .transient
)
```

Use `.transient` for short-lived notifications like sports scores or transit
arrivals that do not need persistent display.

## Dismissal Policies

Control when an ended Live Activity disappears from the Lock Screen:

```swift
// System-determined timing (default)
await activity.end(finalContent, dismissalPolicy: .default)

// Remove immediately
await activity.end(finalContent, dismissalPolicy: .immediate)

// Remove after a specific date (max 4 hours)
let removalDate = Date().addingTimeInterval(3600)
await activity.end(finalContent, dismissalPolicy: .after(removalDate))
```

## Querying Active Widgets and Activities

### Current Widget Configurations

```swift
let widgets = try await WidgetCenter.shared.currentConfigurations()
for widget in widgets {
    print("Kind: \(widget.kind), Family: \(widget.family)")
}
```

### Current Live Activities

```swift
let activities = Activity<DeliveryAttributes>.activities
for activity in activities {
    print("ID: \(activity.id), State: \(activity.activityState)")
}
```

### Observing New Activities

```swift
Task {
    for await activity in Activity<DeliveryAttributes>.activityUpdates {
        print("New activity started: \(activity.id)")
    }
}
```

## Apple Documentation Links

- [WidgetKit](https://sosumi.ai/documentation/widgetkit)
- [ActivityKit](https://sosumi.ai/documentation/activitykit)
- [TimelineProvider](https://sosumi.ai/documentation/widgetkit/timelineprovider)
- [AppIntentTimelineProvider](https://sosumi.ai/documentation/widgetkit/appintenttimelineprovider)
- [ActivityAttributes](https://sosumi.ai/documentation/activitykit/activityattributes)
- [ActivityConfiguration](https://sosumi.ai/documentation/widgetkit/activityconfiguration)
- [DynamicIsland](https://sosumi.ai/documentation/widgetkit/dynamicisland)
- [ControlWidgetButton](https://sosumi.ai/documentation/widgetkit/controlwidgetbutton)
- [ControlWidgetToggle](https://sosumi.ai/documentation/widgetkit/controlwidgettoggle)
- [Keeping a widget up to date](https://sosumi.ai/documentation/widgetkit/keeping-a-widget-up-to-date)
- [Adding StandBy and CarPlay support](https://sosumi.ai/documentation/widgetkit/adding-standby-and-carplay-support-to-your-widget)
- [Optimizing for accented rendering and Liquid Glass](https://sosumi.ai/documentation/widgetkit/optimizing-your-widget-for-accented-rendering-mode-and-liquid-glass)
