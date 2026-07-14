---
name: activitykit
description: "Implement, review, or improve Live Activities and Dynamic Island experiences in iOS apps using ActivityKit. Use when building real-time updating widgets for the Lock Screen and Dynamic Island — delivery tracking, sports scores, ride-sharing status, workout timers, media playback, or any time-sensitive information that updates in real time. Also use when working with ActivityKit, ActivityAttributes, Activity lifecycle (request/update/end), Dynamic Island layouts (compact/minimal/expanded), push-to-update Live Activities, or Lock Screen live widgets."
---

# ActivityKit

ActivityKit owns real-time, glanceable Live Activities displayed on the Lock
Screen and Dynamic Island. Ordinary timeline widgets belong in `widgetkit`, and
generic APNs setup belongs in `push-notifications`; ActivityKit owns the Live
Activity lifecycle and payload contract. `aps.content-state` must decode into
the exact `ActivityAttributes.ContentState` shape, including any coordinated
custom date/range encoding. Modern `ActivityContent` lifecycle examples require
iOS 16.2+ unless noted.

See [references/activitykit-patterns.md](references/activitykit-patterns.md) for complete code patterns including push payload formats, concurrent activities, state observation, and testing.

## Contents

- [Workflow](#workflow)
- [ActivityAttributes Definition](#activityattributes-definition)
- [Activity Lifecycle](#activity-lifecycle)
- [Lock Screen Presentation](#lock-screen-presentation)
- [Dynamic Island](#dynamic-island)
- [Push-to-Update](#push-to-update)
- [Recent Additions](#recent-additions)
- [Common Mistakes](#common-mistakes)
- [Review Checklist](#review-checklist)
- [References](#references)

## Workflow

### 1. Create a new Live Activity

1. Verify the host app capability and `NSSupportsLiveActivities = YES`.
2. Define `ActivityAttributes.ContentState`; encode and decode a representative
   fixture that matches the server payload contract.
3. Create `ActivityConfiguration` and preview Lock Screen and Dynamic Island
   states, including stale and terminal content.
4. Check `ActivityAuthorizationInfo.areActivitiesEnabled`, then request and
   observe the activity lifecycle.
5. Exercise local update and every terminal end path.
6. For remote updates, validate a complete reference payload before registering
   rotating update or push-to-start tokens with the server.

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
the `pushType` to enable remote updates via APNs. The `ActivityContent` request
shown here requires iOS 16.2+.

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

Always end activities on all terminal code paths -- success, user/app
cancellation, sign-out/session stop, unrecoverable app error, and terminal server
failure. If the server says the tracked event can no longer continue or be
represented accurately, apply or send a final terminal state and end the activity
instead of leaving stale progress visible. When reviewing duration claims,
distinguish the active lifetime (up to 8 hours unless the app or user ends it
sooner), system-ended Lock Screen presence (up to 4 additional hours, for 12
hours total from start), and app-ended `.default` dismissal linger (up to 4 hours
after ending).

## Lock Screen Presentation

The Lock Screen is the primary Live Activity display surface. Every device with
iOS 16.1+ displays Live Activities here. Design this layout first, then adapt
for Dynamic Island where available.

```swift
struct DeliveryActivityWidget: Widget {
    var body: some WidgetConfiguration {
        ActivityConfiguration(for: DeliveryAttributes.self) { context in
            VStack(alignment: .leading) {
                Text(context.attributes.restaurantName).font(.headline)

                if context.isStale {
                    Label("Updating...", systemImage: "arrow.trianglehead.2.clockwise")
                        .foregroundStyle(.secondary)
                } else {
                    Text(timerInterval: context.state.estimatedDeliveryTime, countsDown: true)
                        .monospacedDigit()
                }
            }
            .padding()
        } dynamicIsland: { context in
            DynamicIsland {
                DynamicIslandExpandedRegion(.center) {
                    Text(context.attributes.restaurantName).font(.headline)
                }
                DynamicIslandExpandedRegion(.trailing) {
                    Text(timerInterval: context.state.estimatedDeliveryTime, countsDown: true)
                }
            } compactLeading: {
                Image(systemName: "box.truck.fill")
            } compactTrailing: {
                Text(timerInterval: context.state.estimatedDeliveryTime, countsDown: true)
            } minimal: {
                Image(systemName: "box.truck.fill")
            }
        }
    }
}
```

### Supplemental Activity Families

The Lock Screen presentation has limited vertical space. Avoid layouts taller
than roughly 160 points. On iOS 18+, use `supplementalActivityFamilies` when
you provide adaptive layouts beyond the default: `.medium` for iOS/macOS
Live Activity sizing and `.small` for watchOS Live Activity sizing.

```swift
ActivityConfiguration(for: DeliveryAttributes.self) { context in
    // Lock Screen content
} dynamicIsland: { context in
    // Dynamic Island
}
.supplementalActivityFamilies([.medium, .small])
```

## Dynamic Island

Dynamic Island presentations appear only on devices that include Dynamic Island.
Design all three modes, but treat the Lock Screen as the primary surface since
not all devices have a Dynamic Island.

### Compact (Leading + Trailing)

Used when one Live Activity occupies Dynamic Island compact space. Space is
extremely limited -- show only the most critical information.

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
efficient than polling from the app and works when the app is suspended, subject
to APNs delivery, priority, budget, and throttling.

### Setup

Pass `.token` as the `pushType` when starting the activity, then forward the
per-activity update token to your server. Update tokens can rotate, so observe
`activity.pushTokenUpdates` and re-register every emitted token:

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

**Required device-token HTTP headers:**
- `apns-push-type: liveactivity`
- `apns-topic: <bundle-id>.push-type.liveactivity`
- `apns-priority: 5` (lower priority) or `10` (immediate, counts against budget)

The `aps.alert` payload controls visible alert/banner/sound behavior; priority
alone does not create an alert.

Put `timestamp`, `event`, and the full `content-state` inside `aps`. Validate
update, end, and push-to-start bodies against the complete examples in
[Push-to-Update Payloads](references/activitykit-patterns.md#push-to-update-server-payload-format),
including the exact `Codable` date/range representation.

### Push-to-Start

Start a Live Activity remotely without the app running (iOS 17.2+). Push-to-start tokens are ActivityKit-specific tokens from `Activity<Attributes>.pushToStartTokenUpdates`; they are distinct from ordinary app/device APNs tokens and per-activity update tokens:

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
the system-managed push update budget. When cadence matters, check
`ActivityAuthorizationInfo.frequentPushesEnabled` and observe
`frequentPushEnablementUpdates`; Apple does not guarantee a fixed update rate.

## Recent Additions

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
    style: .standard,
    alertConfiguration: AlertConfiguration(
        title: "Game Starting",
        body: "The live score is ready.",
        sound: .default
    ),
    start: scheduledDate
)
```

### ActivityStyle (iOS 18+ request parameter)

Use the iOS 18+ `style:` request parameter to choose persistence behavior. Use
`.standard` for persistent Live Activities such as deliveries, rides, sports
scores, timers, and flight/status boards. Use `.transient` only for a
short-lived expanded Dynamic Island presentation; it can auto-end when the user
locks the device, collapses or shrinks the expanded presentation, leaves the
app, or does other work outside Dynamic Island.

```swift
let activity = try Activity.request(
    attributes: attributes,
    content: content,
    pushType: .token,
    style: .standard
)
```

### Paired Mac & CarPlay (iOS 26+)

Live Activities can appear on a paired Mac and on the CarPlay Home Screen. No additional ActivityKit API is required, but validate compact layouts; buttons and toggles in Live Activities do not perform actions in CarPlay.

### Channel-Based Push (iOS 18+)

Broadcast updates to many Live Activities at once with an APNs-created channel
ID. Enable the broadcast capability outside Xcode, create the channel on the
server, then subscribe with `.channel(channelID)`. Channel pushes update or end
Live Activities; they do not start them. Use `apns-channel-id` and expiration
for channel pushes instead of the device-token `apns-topic` example above.

```swift
let activity = try Activity.request(
    attributes: attributes, content: content,
    pushType: .channel(channelIDFromServer)
)
```

## Common Mistakes

**DON'T:** Put too much content in the compact presentation -- it is tiny.
**DO:** Show only the most critical info (icon + one value) in compact leading/trailing.

**DON'T:** Update Live Activities too frequently from the app (drains battery).
**DO:** Use push-to-update for server-driven updates. Limit app-side updates to user actions.

**DON'T:** Forget to end the activity when the event reaches any terminal state.
**DO:** End activities on success, cancellation, sign-out, unrecoverable errors, and terminal server failures. A leaked activity frustrates users.

**DON'T:** Assume every device has Dynamic Island.
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

**DON'T:** Fetch network data or location directly from Live Activity views.
**DO:** Pre-compute display values in the app or server and pass them through ActivityKit updates or pushes.

## Review Checklist

- [ ] `ActivityAttributes` defines static properties and `ContentState`
- [ ] `NSSupportsLiveActivities = YES` in host app Info.plist
- [ ] Activity uses `ActivityContent` (not deprecated contentState API)
- [ ] Activity ended in all terminal paths (success, error, cancellation, sign-out, terminal server failure)
- [ ] ActivityKit lifecycle and Lock Screen/Dynamic Island Live Activity surfaces are separated from ordinary Home Screen/timeline widget work
- [ ] Lock Screen layout, the primary Live Activity surface, handles `context.isStale`
- [ ] Dynamic Island compact, expanded, and minimal implemented with Lock Screen fallback
- [ ] Push update token forwarded to server via `activity.pushTokenUpdates`
- [ ] Push-to-start token collected via `Activity<Attributes>.pushToStartTokenUpdates`
- [ ] Push-to-start payload includes required `alert`
- [ ] `content-state` JSON matches the actual `ContentState` `Codable` shape, including coordinated date/range encoding
- [ ] Review distinguishes 8-hour active lifetime, 12-hour total system-ended Lock Screen presence, and 4-hour app-ended `.default` linger
- [ ] `ActivityAuthorizationInfo` checked before starting
- [ ] `frequentPushesEnabled` checked before assuming high-cadence pushes
- [ ] ContentState kept small (serialized on every update)
- [ ] iOS 18+ availability guarded for `style:`, `.channel`, and supplemental families
- [ ] iOS 18+ `style:` choices are justified: `.standard` for persistent Live Activities, `.transient` only for short-lived expanded Dynamic Island presentations
- [ ] ActivityKit push priority and `aps.alert` behavior are handled separately
- [ ] Live Activity views avoid direct network/location work
- [ ] Tested on device for push delivery and Dynamic Island behavior

## References

- See [references/activitykit-patterns.md](references/activitykit-patterns.md) for patterns and code examples
