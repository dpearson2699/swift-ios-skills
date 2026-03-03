---
name: live-activities
description: "Implement, review, or improve Live Activities and Dynamic Island experiences in iOS apps using ActivityKit. Use when building real-time updating widgets for the Lock Screen and Dynamic Island — delivery tracking, sports scores, ride-sharing status, workout timers, media playback, or any time-sensitive information that updates in real time. Trigger for any task involving ActivityKit, ActivityAttributes, Activity lifecycle (request/update/end), Dynamic Island layouts (compact/minimal/expanded), push-to-update Live Activities, or Lock Screen live widgets."
---

# Live Activities and Dynamic Island

Build real-time, glanceable experiences on the Lock Screen, Dynamic Island,
StandBy, CarPlay, and Mac menu bar using ActivityKit. Patterns target iOS 26+
with Swift 6.2, backward-compatible to iOS 16.1 unless noted.

See `references/live-activity-patterns.md` for complete code patterns including push payload formats, concurrent activities, state observation, and testing.

## Workflow

### 1. Create a new Live Activity

1. Add `NSSupportsLiveActivities = YES` to the host app's Info.plist.
2. Define an `ActivityAttributes` struct with a nested `ContentState`.
3. Create an `ActivityConfiguration` in the widget bundle with Lock Screen
   content and Dynamic Island closures.
4. Start the activity with `Activity.request(attributes:content:pushType:)`.
5. Update with `activity.update(_:)` and end with `activity.end(_:dismissalPolicy:)`.
6. Forward push tokens to your server for remote updates.

### 2. Review existing Live Activity code

Run through the Review Checklist at the end of this document.

## ActivityAttributes Definition

Define both static data (immutable for the activity lifetime) and dynamic
`ContentState` (changes with each update). Keep `ContentState` small because
the entire struct is serialized on every update and push payload.

```swift
import ActivityKit

struct DeliveryAttributes: ActivityAttributes {
    // Static -- set once at activity creation, never changes
    var orderNumber: Int
    var restaurantName: String

    // Dynamic -- updated throughout the activity lifetime
    struct ContentState: Codable, Hashable {
        var driverName: String
        var estimatedDeliveryTime: ClosedRange<Date>
        var currentStep: DeliveryStep
    }
}

enum DeliveryStep: String, Codable, Hashable, CaseIterable {
    case confirmed, preparing, pickedUp, delivering, delivered

    var icon: String {
        switch self {
        case .confirmed: "checkmark.circle"
        case .preparing: "frying.pan"
        case .pickedUp: "bag.fill"
        case .delivering: "box.truck.fill"
        case .delivered: "house.fill"
        }
    }
}
```

### Stale Date

Set `staleDate` on `ActivityContent` to tell the system when content becomes outdated. The system sets `context.isStale` to `true` after this date; show fallback UI (e.g., "Updating...") in your views.

```swift
let content = ActivityContent(
    state: state,
    staleDate: Date().addingTimeInterval(300), // stale after 5 minutes
    relevanceScore: 75
)
```

## Activity Lifecycle

### Starting

Use `Activity.request` to create and display a Live Activity. Pass `.token` as
the `pushType` to enable remote updates via APNs.

```swift
let attributes = DeliveryAttributes(orderNumber: 42, restaurantName: "Pizza Place")
let state = DeliveryAttributes.ContentState(
    driverName: "Alex",
    estimatedDeliveryTime: Date()...Date().addingTimeInterval(1800),
    currentStep: .preparing
)
let content = ActivityContent(state: state, staleDate: nil, relevanceScore: 75)

do {
    let activity = try Activity.request(
        attributes: attributes,
        content: content,
        pushType: .token
    )
    print("Started activity: \(activity.id)")
} catch {
    print("Failed to start activity: \(error)")
}
```

### Updating

Update the dynamic content state from the app. Use `AlertConfiguration` to
trigger a visible banner and sound alongside the update.

```swift
let updatedState = DeliveryAttributes.ContentState(
    driverName: "Alex",
    estimatedDeliveryTime: Date()...Date().addingTimeInterval(600),
    currentStep: .delivering
)
let updatedContent = ActivityContent(
    state: updatedState,
    staleDate: Date().addingTimeInterval(300),
    relevanceScore: 90
)

// Silent update
await activity.update(updatedContent)

// Update with an alert
await activity.update(updatedContent, alertConfiguration: AlertConfiguration(
    title: "Order Update",
    body: "Your driver is nearby!",
    sound: .default
))
```

### Ending

End the activity when the tracked event completes. Choose a dismissal policy
to control how long the ended activity lingers on the Lock Screen.

```swift
let finalState = DeliveryAttributes.ContentState(
    driverName: "Alex",
    estimatedDeliveryTime: Date()...Date(),
    currentStep: .delivered
)
let finalContent = ActivityContent(state: finalState, staleDate: nil, relevanceScore: 0)

// System decides when to remove (up to 4 hours)
await activity.end(finalContent, dismissalPolicy: .default)

// Remove immediately
await activity.end(finalContent, dismissalPolicy: .immediate)

// Remove after a specific time (max 4 hours from now)
await activity.end(finalContent, dismissalPolicy: .after(Date().addingTimeInterval(3600)))
```

Always end activities on all code paths -- success, error, and cancellation.
A leaked activity stays on the Lock Screen until the system kills it (up to
8 hours), which frustrates users.

## Lock Screen Presentation

The Lock Screen is the primary surface for Live Activities. Every device with
iOS 16.1+ displays Live Activities here. Design this layout first.

```swift
struct DeliveryActivityWidget: Widget {
    var body: some WidgetConfiguration {
        ActivityConfiguration(for: DeliveryAttributes.self) { context in
            // Lock Screen / StandBy / CarPlay / Mac menu bar content
            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Text(context.attributes.restaurantName)
                        .font(.headline)
                    Spacer()
                    Text("Order #\(context.attributes.orderNumber)")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }

                if context.isStale {
                    Label("Updating...", systemImage: "arrow.trianglehead.2.clockwise")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                } else {
                    HStack {
                        Label(context.state.driverName, systemImage: "person.fill")
                        Spacer()
                        Text(timerInterval: context.state.estimatedDeliveryTime,
                             countsDown: true)
                            .monospacedDigit()
                    }
                    .font(.subheadline)

                    // Progress steps
                    HStack(spacing: 12) {
                        ForEach(DeliveryStep.allCases, id: \.self) { step in
                            Image(systemName: step.icon)
                                .foregroundStyle(
                                    step <= context.state.currentStep ? .primary : .tertiary
                                )
                        }
                    }
                }
            }
            .padding()
        } dynamicIsland: { context in
            // Dynamic Island closures (see next section)
            DynamicIsland {
                // Expanded regions...
                DynamicIslandExpandedRegion(.leading) {
                    Image(systemName: "box.truck.fill").font(.title2)
                }
                DynamicIslandExpandedRegion(.trailing) {
                    Text(timerInterval: context.state.estimatedDeliveryTime,
                         countsDown: true)
                        .font(.caption).monospacedDigit()
                }
                DynamicIslandExpandedRegion(.center) {
                    Text(context.attributes.restaurantName).font(.headline)
                }
                DynamicIslandExpandedRegion(.bottom) {
                    HStack(spacing: 12) {
                        ForEach(DeliveryStep.allCases, id: \.self) { step in
                            Image(systemName: step.icon)
                                .foregroundStyle(
                                    step <= context.state.currentStep ? .primary : .tertiary
                                )
                        }
                    }
                }
            } compactLeading: {
                Image(systemName: "box.truck.fill")
            } compactTrailing: {
                Text(timerInterval: context.state.estimatedDeliveryTime,
                     countsDown: true)
                    .frame(width: 40).monospacedDigit()
            } minimal: {
                Image(systemName: "box.truck.fill")
            }
        }
    }
}
```

### Lock Screen Sizing

The Lock Screen presentation has limited vertical space. Avoid layouts taller
than roughly 160 points. Use `supplementalActivityFamilies` to opt into
`.small` (compact) or `.medium` (standard) sizing:

```swift
ActivityConfiguration(for: DeliveryAttributes.self) { context in
    // Lock Screen content
} dynamicIsland: { context in
    // Dynamic Island
}
.supplementalActivityFamilies([.small, .medium])
```

## Dynamic Island

The Dynamic Island is available on iPhone 14 Pro and later. It has three
presentation modes. Design all three, but treat the Lock Screen as the primary
surface since not all devices have a Dynamic Island.

### Compact (Leading + Trailing)

Always visible when a single Live Activity is active. Space is extremely
limited -- show only the most critical information.

| Region | Purpose |
|---|---|
| `compactLeading` | Icon or tiny label identifying the activity |
| `compactTrailing` | One key value (timer, score, status) |

### Minimal

Shown when multiple Live Activities compete for space. Only one activity gets
the minimal slot. Display a single icon or glyph.

### Expanded Regions

Shown when the user long-presses the Dynamic Island.

| Region | Position |
|---|---|
| `.leading` | Left of the TrueDepth camera; wraps below |
| `.trailing` | Right of the TrueDepth camera; wraps below |
| `.center` | Directly below the camera |
| `.bottom` | Below all other regions |

### Keyline Tint

Apply a subtle tint to the Dynamic Island border:

```swift
DynamicIsland { /* expanded */ }
    compactLeading: { /* ... */ }
    compactTrailing: { /* ... */ }
    minimal: { /* ... */ }
    .keylineTint(.blue)
```

## Push-to-Update

Push-to-update sends Live Activity updates through APNs, which is more
efficient than polling from the app and works when the app is suspended.

### Setup

Pass `.token` as the `pushType` when starting the activity, then forward the
push token to your server:

```swift
let activity = try Activity.request(
    attributes: attributes,
    content: content,
    pushType: .token
)

// Observe token changes -- tokens can rotate
Task {
    for await token in activity.pushTokenUpdates {
        let tokenString = token.map { String(format: "%02x", $0) }.joined()
        try await ServerAPI.shared.registerActivityToken(
            tokenString, activityID: activity.id
        )
    }
}
```

### APNs Payload Format

Send an HTTP/2 POST to APNs with these headers and JSON body:

**Required HTTP headers:**
- `apns-push-type: liveactivity`
- `apns-topic: <bundle-id>.push-type.liveactivity`
- `apns-priority: 5` (low) or `10` (high, triggers alert)

**Update payload:**

```json
{
    "aps": {
        "timestamp": 1700000000,
        "event": "update",
        "content-state": {
            "driverName": "Alex",
            "estimatedDeliveryTime": {
                "lowerBound": 1700000000,
                "upperBound": 1700001800
            },
            "currentStep": "delivering"
        },
        "stale-date": 1700000300,
        "alert": {
            "title": "Delivery Update",
            "body": "Your driver is nearby!"
        }
    }
}
```

**End payload:** Same structure with `"event": "end"` and optional `"dismissal-date"`.

The `content-state` JSON must match the `ContentState` Codable structure
exactly. Mismatched keys or types cause silent failures.

### Push-to-Start

Start a Live Activity remotely without the app running (iOS 17.2+):

```swift
Task {
    for await token in Activity<DeliveryAttributes>.pushToStartTokenUpdates {
        let tokenString = token.map { String(format: "%02x", $0) }.joined()
        try await ServerAPI.shared.registerPushToStartToken(tokenString)
    }
}
```

### Frequent Push Updates

Add `NSSupportsLiveActivitiesFrequentUpdates = YES` to Info.plist to increase
the push update budget. Use for activities that update more than once per
minute (sports scores, ride tracking).

## iOS 26 Additions

### Scheduled Live Activities (iOS 26+)

Schedule a Live Activity to start at a future time. The system starts the
activity automatically without the app being in the foreground. Use for events
with known start times (sports games, flights, scheduled deliveries).

```swift
let scheduledDate = Calendar.current.date(
    from: DateComponents(year: 2026, month: 3, day: 15, hour: 19, minute: 0)
)!

let activity = try Activity.request(
    attributes: attributes,
    content: content,
    pushType: .token,
    start: scheduledDate
)
```

### ActivityStyle (iOS 26+)

Control persistence: `.standard` (persists until ended, default) or `.transient` (system may dismiss automatically). Use `.transient` for short-lived updates like transit arrivals.

```swift
let activity = try Activity.request(
    attributes: attributes, content: content,
    pushType: .token, style: .transient
)
```

### Mac Menu Bar & CarPlay (iOS 26+)

Live Activities automatically appear in macOS Tahoe menu bar (via iPhone Mirroring) and CarPlay Home Screen. No additional code needed — ensure Lock Screen layout is legible at smaller scales.

### Channel-Based Push (iOS 26+)

Broadcast updates to many Live Activities at once with `.channel`:

```swift
let activity = try Activity.request(
    attributes: attributes, content: content,
    pushType: .channel("delivery-updates")
)
```

## Common Mistakes

**DON'T:** Put too much content in the compact presentation -- it is tiny.
**DO:** Show only the most critical info (icon + one value) in compact leading/trailing.

**DON'T:** Update Live Activities too frequently from the app (drains battery).
**DO:** Use push-to-update for server-driven updates. Limit app-side updates to user actions.

**DON'T:** Forget to end the activity when the event completes.
**DO:** Always end activities on success, error, and cancellation paths. A leaked activity frustrates users.

**DON'T:** Assume the Dynamic Island is available (only iPhone 14 Pro+).
**DO:** Design for the Lock Screen as the primary surface; Dynamic Island is supplementary.

**DON'T:** Store sensitive information in ActivityAttributes (visible on Lock Screen).
**DO:** Keep sensitive data in the app and show only safe-to-display summaries.

**DON'T:** Forget to handle stale dates.
**DO:** Check `context.isStale` in views and show fallback UI ("Updating..." or similar).

**DON'T:** Ignore push token rotation. Tokens can change at any time.
**DO:** Use `activity.pushTokenUpdates` async sequence and re-register on every emission.

**DON'T:** Forget the `NSSupportsLiveActivities` Info.plist key.
**DO:** Add `NSSupportsLiveActivities = YES` to the host app's Info.plist (not the extension).

**DON'T:** Use the deprecated `contentState`-based API for request/update/end.
**DO:** Use `ActivityContent` for all lifecycle calls.

**DON'T:** Put heavy logic in Live Activity views. They render in a size-limited widget process.
**DO:** Pre-compute display values and pass them through `ContentState`.

## Review Checklist

- [ ] `ActivityAttributes` defines static properties and `ContentState`
- [ ] `NSSupportsLiveActivities = YES` in host app Info.plist
- [ ] Activity uses `ActivityContent` (not deprecated contentState API)
- [ ] Activity ended in all code paths (success, error, cancellation)
- [ ] Lock Screen layout handles `context.isStale`
- [ ] Dynamic Island compact, expanded, and minimal implemented
- [ ] Push token forwarded to server via `activity.pushTokenUpdates`
- [ ] `AlertConfiguration` used for important updates
- [ ] `ActivityAuthorizationInfo` checked before starting
- [ ] ContentState kept small (serialized on every update)
- [ ] Tested on device (Dynamic Island differs from Simulator)
- [ ] Ensure ActivityAttributes and ContentState types are Sendable; update Live Activity UI on @MainActor

## API Verification

The apple-docs MCP server can verify ActivityKit API names, signatures, and
availability. Use `fetchAppleDocumentation` with paths like
`/documentation/activitykit` or `/documentation/activitykit/activityattributes`.

## References

- Patterns and code: `references/live-activity-patterns.md`
- Apple docs: [ActivityKit](https://sosumi.ai/documentation/activitykit) |
  [ActivityAttributes](https://sosumi.ai/documentation/activitykit/activityattributes) |
  [DynamicIsland](https://sosumi.ai/documentation/widgetkit/dynamicisland) |
  [Push notifications](https://sosumi.ai/documentation/activitykit/starting-and-updating-live-activities-with-activitykit-push-notifications)
