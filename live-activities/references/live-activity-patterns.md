# Live Activity Patterns

Complete implementation patterns for ActivityKit Live Activities, Dynamic
Island, push-to-update, and lifecycle management. All patterns use modern
Swift async/await and target iOS 16.1+ unless noted.

## Complete ActivityAttributes and ContentState

Define the data model for your Live Activity. Static properties go on the
outer struct; dynamic properties go in `ContentState`.

```swift
import ActivityKit

struct RideAttributes: ActivityAttributes {
    // Static -- set at creation, immutable for the activity lifetime
    var riderName: String
    var pickupLocation: String
    var dropoffLocation: String

    struct ContentState: Codable, Hashable {
        var driverName: String
        var driverPhoto: String        // SF Symbol name or asset name
        var vehicleDescription: String
        var eta: ClosedRange<Date>
        var status: RideStatus
        var distanceRemaining: Double   // miles
    }
}

enum RideStatus: String, Codable, Hashable {
    case driverAssigned
    case driverEnRoute
    case driverArrived
    case inProgress
    case arriving
    case completed
    case cancelled
}
```

Keep `ContentState` lightweight. Every update serializes the entire struct, and
push payloads have a 4 KB size limit. Avoid storing images, large strings, or
deeply nested objects.

## Starting a Live Activity with All Parameters

```swift
import ActivityKit

@MainActor
func startRideActivity(
    rider: String,
    pickup: String,
    dropoff: String,
    driver: String,
    vehicle: String
) async throws -> Activity<RideAttributes> {
    // Check authorization before attempting to start
    let authInfo = ActivityAuthorizationInfo()
    guard authInfo.areActivitiesEnabled else {
        throw RideError.liveActivitiesDisabled
    }

    let attributes = RideAttributes(
        riderName: rider,
        pickupLocation: pickup,
        dropoffLocation: dropoff
    )

    let initialState = RideAttributes.ContentState(
        driverName: driver,
        driverPhoto: "car.fill",
        vehicleDescription: vehicle,
        eta: Date()...Date().addingTimeInterval(600),
        status: .driverAssigned,
        distanceRemaining: 2.5
    )

    let content = ActivityContent(
        state: initialState,
        staleDate: Date().addingTimeInterval(120), // stale after 2 min
        relevanceScore: 80
    )

    let activity = try Activity.request(
        attributes: attributes,
        content: content,
        pushType: .token  // Enable push updates
    )

    // Forward push token to server for remote updates
    Task {
        for await token in activity.pushTokenUpdates {
            let tokenString = token.map { String(format: "%02x", $0) }.joined()
            try? await ServerAPI.shared.registerActivityToken(
                tokenString, rideID: activity.id
            )
        }
    }

    // Observe state changes for cleanup
    Task {
        for await state in activity.activityStateUpdates {
            if state == .dismissed {
                // Activity removed from UI -- clean up local resources
                RideStore.shared.removeActivity(id: activity.id)
            }
        }
    }

    return activity
}
```

### Starting with Scheduled Date (iOS 26+)

Schedule the activity to appear at a future time without the app in foreground:

```swift
let gameTime = Calendar.current.date(
    from: DateComponents(year: 2026, month: 3, day: 15, hour: 19, minute: 0)
)!

let activity = try Activity.request(
    attributes: attributes,
    content: content,
    pushType: .token,
    start: gameTime  // iOS 26+
)
```

### Starting with ActivityStyle (iOS 26+)

```swift
// Transient: system may auto-dismiss after a period
let activity = try Activity.request(
    attributes: attributes,
    content: content,
    pushType: .token,
    style: .transient  // iOS 26+
)
```

## Updating from the App

```swift
func updateRideActivity(
    _ activity: Activity<RideAttributes>,
    newStatus: RideStatus,
    eta: ClosedRange<Date>,
    distance: Double,
    showAlert: Bool = false
) async {
    let updatedState = RideAttributes.ContentState(
        driverName: activity.content.state.driverName,
        driverPhoto: activity.content.state.driverPhoto,
        vehicleDescription: activity.content.state.vehicleDescription,
        eta: eta,
        status: newStatus,
        distanceRemaining: distance
    )

    let content = ActivityContent(
        state: updatedState,
        staleDate: Date().addingTimeInterval(120),
        relevanceScore: newStatus == .driverArrived ? 100 : 80
    )

    if showAlert {
        await activity.update(content, alertConfiguration: AlertConfiguration(
            title: "Ride Update",
            body: alertMessage(for: newStatus),
            sound: .default
        ))
    } else {
        await activity.update(content)
    }
}

private func alertMessage(for status: RideStatus) -> String {
    switch status {
    case .driverArrived: "Your driver has arrived!"
    case .arriving: "You're almost there!"
    case .completed: "You've arrived at your destination."
    default: "Your ride status has changed."
    }
}
```

## Push-to-Update Server Payload Format

### Update Payload

```json
{
    "aps": {
        "timestamp": 1700000000,
        "event": "update",
        "content-state": {
            "driverName": "Maria",
            "driverPhoto": "car.fill",
            "vehicleDescription": "White Toyota Camry",
            "eta": {
                "lowerBound": 1700000000,
                "upperBound": 1700000300
            },
            "status": "driverArrived",
            "distanceRemaining": 0.0
        },
        "stale-date": 1700000300,
        "relevance-score": 100,
        "alert": {
            "title": "Ride Update",
            "body": "Your driver has arrived!",
            "sound": "default"
        }
    }
}
```

### End Payload

```json
{
    "aps": {
        "timestamp": 1700002000,
        "event": "end",
        "dismissal-date": 1700005600,
        "content-state": {
            "driverName": "Maria",
            "driverPhoto": "car.fill",
            "vehicleDescription": "White Toyota Camry",
            "eta": {
                "lowerBound": 1700002000,
                "upperBound": 1700002000
            },
            "status": "completed",
            "distanceRemaining": 0.0
        }
    }
}
```

### Push-to-Start Payload (iOS 17.2+)

Send to the push-to-start token to remotely create an activity:

```json
{
    "aps": {
        "timestamp": 1700000000,
        "event": "start",
        "attributes-type": "RideAttributes",
        "attributes": {
            "riderName": "Jordan",
            "pickupLocation": "123 Main St",
            "dropoffLocation": "456 Oak Ave"
        },
        "content-state": {
            "driverName": "Maria",
            "driverPhoto": "car.fill",
            "vehicleDescription": "White Toyota Camry",
            "eta": {
                "lowerBound": 1700000000,
                "upperBound": 1700000600
            },
            "status": "driverAssigned",
            "distanceRemaining": 3.2
        },
        "alert": {
            "title": "Ride Matched",
            "body": "Maria is on the way in a White Toyota Camry."
        }
    }
}
```

### Required APNs HTTP Headers

| Header | Value |
|---|---|
| `apns-push-type` | `liveactivity` |
| `apns-topic` | `<bundle-id>.push-type.liveactivity` |
| `apns-priority` | `5` (silent) or `10` (alert, updates with sound/banner) |
| `authorization` | `bearer <jwt>` (token auth) or use certificate auth |

The `content-state` JSON keys and value types must match the `ContentState`
Codable representation exactly. A type mismatch (e.g., sending a string where
a number is expected) causes the update to fail silently.

## Ending with Different Dismissal Policies

```swift
func endRideActivity(
    _ activity: Activity<RideAttributes>,
    finalStatus: RideStatus
) async {
    let finalState = RideAttributes.ContentState(
        driverName: activity.content.state.driverName,
        driverPhoto: activity.content.state.driverPhoto,
        vehicleDescription: activity.content.state.vehicleDescription,
        eta: Date()...Date(),
        status: finalStatus,
        distanceRemaining: 0
    )

    let content = ActivityContent(state: finalState, staleDate: nil, relevanceScore: 0)

    switch finalStatus {
    case .completed:
        // Keep on Lock Screen for 1 hour so user can review trip details
        await activity.end(content, dismissalPolicy: .after(
            Date().addingTimeInterval(3600)
        ))
    case .cancelled:
        // Remove immediately -- no useful info to show
        await activity.end(content, dismissalPolicy: .immediate)
    default:
        // Let the system decide
        await activity.end(content, dismissalPolicy: .default)
    }
}
```

### Ending All Activities (cleanup on sign-out)

```swift
func endAllRideActivities() async {
    for activity in Activity<RideAttributes>.activities {
        await activity.end(nil, dismissalPolicy: .immediate)
    }
}
```

## Complete Dynamic Island Layout (All Regions)

```swift
struct RideActivityWidget: Widget {
    var body: some WidgetConfiguration {
        ActivityConfiguration(for: RideAttributes.self) { context in
            // Lock Screen presentation
            RideLockScreenView(context: context)
        } dynamicIsland: { context in
            DynamicIsland {
                // EXPANDED: shown on long-press
                DynamicIslandExpandedRegion(.leading) {
                    VStack(alignment: .leading, spacing: 4) {
                        Image(systemName: context.state.driverPhoto)
                            .font(.title2)
                        Text(context.state.driverName)
                            .font(.caption2)
                            .lineLimit(1)
                    }
                }

                DynamicIslandExpandedRegion(.trailing) {
                    VStack(alignment: .trailing, spacing: 4) {
                        Text(timerInterval: context.state.eta, countsDown: true)
                            .font(.title3.monospacedDigit())
                        Text(String(format: "%.1f mi", context.state.distanceRemaining))
                            .font(.caption2)
                            .foregroundStyle(.secondary)
                    }
                }

                DynamicIslandExpandedRegion(.center) {
                    Text(context.state.status.displayName)
                        .font(.headline)
                        .lineLimit(1)
                }

                DynamicIslandExpandedRegion(.bottom) {
                    VStack(spacing: 8) {
                        ProgressView(
                            value: context.state.status.progress,
                            total: 1.0
                        )
                        .tint(.green)

                        HStack {
                            Label(context.attributes.pickupLocation,
                                  systemImage: "mappin.circle.fill")
                            Spacer()
                            Label(context.attributes.dropoffLocation,
                                  systemImage: "flag.checkered")
                        }
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                        .lineLimit(1)
                    }
                }
            } compactLeading: {
                // COMPACT LEADING: tiny icon identifying the activity
                Image(systemName: context.state.driverPhoto)
                    .foregroundStyle(.green)
            } compactTrailing: {
                // COMPACT TRAILING: one key value
                Text(timerInterval: context.state.eta, countsDown: true)
                    .frame(width: 44)
                    .monospacedDigit()
            } minimal: {
                // MINIMAL: shown when multiple activities compete
                Image(systemName: "car.fill")
                    .foregroundStyle(.green)
            }
            .keylineTint(.green)
        }
    }
}
```

## Lock Screen Layout with Timer and Progress

```swift
struct RideLockScreenView: View {
    let context: ActivityViewContext<RideAttributes>

    var body: some View {
        VStack(spacing: 12) {
            // Header
            HStack {
                VStack(alignment: .leading) {
                    Text(context.state.status.displayName)
                        .font(.headline)
                    Text(context.state.vehicleDescription)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                Spacer()
                // Live countdown timer (auto-updating, no code needed)
                Text(timerInterval: context.state.eta, countsDown: true)
                    .font(.title2.monospacedDigit().bold())
                    .foregroundStyle(.green)
            }

            if context.isStale {
                Label("Checking for updates...",
                      systemImage: "arrow.trianglehead.2.clockwise")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            // Progress bar
            ProgressView(value: context.state.status.progress, total: 1.0)
                .tint(.green)

            // Route
            HStack {
                VStack(alignment: .leading) {
                    Text("Pickup").font(.caption2).foregroundStyle(.secondary)
                    Text(context.attributes.pickupLocation).font(.caption).lineLimit(1)
                }
                Spacer()
                Image(systemName: "arrow.right")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                Spacer()
                VStack(alignment: .trailing) {
                    Text("Dropoff").font(.caption2).foregroundStyle(.secondary)
                    Text(context.attributes.dropoffLocation).font(.caption).lineLimit(1)
                }
            }
        }
        .padding()
    }
}
```

## Multiple Concurrent Activities

An app can run multiple Live Activities simultaneously (system limit applies).
Track them by storing references or querying `Activity<T>.activities`.

```swift
@Observable
@MainActor
final class ActivityManager {
    private(set) var activeDeliveries: [String: Activity<DeliveryAttributes>] = [:]

    func startDelivery(orderID: String, attributes: DeliveryAttributes,
                       state: DeliveryAttributes.ContentState) async throws {
        let content = ActivityContent(state: state, staleDate: nil, relevanceScore: 75)
        let activity = try Activity.request(
            attributes: attributes, content: content, pushType: .token
        )
        activeDeliveries[orderID] = activity

        // Token forwarding
        Task { [weak self] in
            for await token in activity.pushTokenUpdates {
                let tokenString = token.map { String(format: "%02x", $0) }.joined()
                try? await ServerAPI.shared.registerActivityToken(tokenString, orderID: orderID)
            }
            self?.activeDeliveries.removeValue(forKey: orderID)
        }
    }

    func updateDelivery(orderID: String, state: DeliveryAttributes.ContentState) async {
        guard let activity = activeDeliveries[orderID] else { return }
        let content = ActivityContent(state: state, staleDate: nil, relevanceScore: 80)
        await activity.update(content)
    }

    func endDelivery(orderID: String, finalState: DeliveryAttributes.ContentState) async {
        guard let activity = activeDeliveries[orderID] else { return }
        let content = ActivityContent(state: finalState, staleDate: nil, relevanceScore: 0)
        await activity.end(content, dismissalPolicy: .default)
        activeDeliveries.removeValue(forKey: orderID)
    }

    /// Reconcile in-memory state with system activities on app launch
    func reconcile() {
        let systemActivities = Activity<DeliveryAttributes>.activities
        for activity in systemActivities {
            let orderID = "\(activity.attributes.orderNumber)"
            if activeDeliveries[orderID] == nil {
                activeDeliveries[orderID] = activity
            }
        }
    }
}
```

## Observing Activity State Changes

```swift
func observeActivityState(_ activity: Activity<RideAttributes>) {
    // State updates: .active, .pending, .stale, .ended, .dismissed
    Task {
        for await state in activity.activityStateUpdates {
            switch state {
            case .active:
                print("Activity is visible and running")
            case .pending:
                // iOS 26+: scheduled but not yet displayed
                print("Activity is pending start")
            case .stale:
                // The staleDate passed without an update
                print("Content is stale -- update or end")
            case .ended:
                // Ended but may still be visible on Lock Screen
                print("Activity ended, may still linger on Lock Screen")
            case .dismissed:
                // Fully removed from UI -- safe to release resources
                print("Activity dismissed from Lock Screen")
                cleanupResources(for: activity.id)
            @unknown default:
                break
            }
        }
    }

    // Content updates (observe state changes from push or other processes)
    Task {
        for await content in activity.contentUpdates {
            print("New state: \(content.state)")
        }
    }
}
```

## Token Update Handling

Push tokens can change at any time. Always observe the async sequence and
re-register with your server.

```swift
func observePushToken(for activity: Activity<RideAttributes>) {
    Task {
        for await token in activity.pushTokenUpdates {
            let tokenString = token.map { String(format: "%02x", $0) }.joined()
            do {
                try await ServerAPI.shared.registerActivityToken(
                    tokenString, activityID: activity.id
                )
            } catch {
                // Retry with exponential backoff; token is critical for updates
                print("Failed to register token: \(error)")
            }
        }
    }
}

/// Observe the push-to-start token for remote activity creation (iOS 17.2+)
func observePushToStartToken() {
    Task {
        for await token in Activity<RideAttributes>.pushToStartTokenUpdates {
            let tokenString = token.map { String(format: "%02x", $0) }.joined()
            try? await ServerAPI.shared.registerPushToStartToken(tokenString)
        }
    }
}
```

## Authorization Check

Always check authorization before starting an activity. The user can disable
Live Activities in Settings at any time.

```swift
func checkLiveActivityAuthorization() async -> Bool {
    let authInfo = ActivityAuthorizationInfo()

    // Synchronous check
    guard authInfo.areActivitiesEnabled else {
        return false
    }

    return true
}

/// Observe authorization changes to react when user toggles the setting
func observeAuthorization() {
    Task {
        let authInfo = ActivityAuthorizationInfo()
        for await enabled in authInfo.activityEnablementUpdates {
            if enabled {
                // Re-register push-to-start token
                observePushToStartToken()
            } else {
                // Inform server to stop sending push updates
                try? await ServerAPI.shared.disableActivityPush()
            }
        }
    }
}
```

## Error Handling

```swift
func startActivitySafely(
    attributes: DeliveryAttributes,
    state: DeliveryAttributes.ContentState
) async {
    let content = ActivityContent(state: state, staleDate: nil, relevanceScore: 75)

    do {
        let activity = try Activity.request(
            attributes: attributes, content: content, pushType: .token
        )
        print("Started: \(activity.id)")
    } catch let error as ActivityAuthorizationError {
        switch error {
        case .denied:
            // User disabled Live Activities in Settings
            print("Live Activities disabled by user")
        case .globalMaximumExceeded:
            // Too many Live Activities across all apps (system limit ~5)
            print("System-wide activity limit reached")
        case .targetMaximumExceeded:
            // Too many Live Activities for this app
            print("App activity limit reached -- end an existing one first")
        default:
            print("Authorization error: \(error)")
        }
    } catch {
        print("Unexpected error: \(error)")
    }
}
```

## Background Handling Considerations

Live Activities continue to display when the app is backgrounded or suspended.
Push-to-update is the primary mechanism for background updates. When the app
returns to foreground, reconcile local state with the activity's current
content.

```swift
@MainActor
func handleAppBecameActive() {
    // Reconcile local state with live activities on foregrounding
    let activities = Activity<DeliveryAttributes>.activities
    for activity in activities {
        switch activity.activityState {
        case .active:
            // Refresh from server in case pushes were missed
            Task {
                let serverState = try await ServerAPI.shared.fetchDeliveryState(
                    orderNumber: activity.attributes.orderNumber
                )
                let content = ActivityContent(
                    state: serverState,
                    staleDate: Date().addingTimeInterval(120),
                    relevanceScore: 80
                )
                await activity.update(content)
            }
        case .stale:
            // Content is outdated -- update immediately
            Task {
                let serverState = try await ServerAPI.shared.fetchDeliveryState(
                    orderNumber: activity.attributes.orderNumber
                )
                let content = ActivityContent(
                    state: serverState,
                    staleDate: Date().addingTimeInterval(120),
                    relevanceScore: 80
                )
                await activity.update(content)
            }
        case .ended, .dismissed:
            // Clean up local tracking
            break
        default:
            break
        }
    }
}
```

For truly background-driven updates, rely on push-to-update rather than
Background App Refresh. Push updates are delivered reliably even when the app
is suspended, while Background App Refresh has limited and unpredictable
scheduling.

## Testing in Simulator and on Device

### Simulator

The Simulator supports Live Activity rendering on the Lock Screen and displays
the Dynamic Island on iPhone 14 Pro+ simulator models. Use Xcode previews for
rapid iteration:

```swift
#Preview("Lock Screen", as: .content, using: RideAttributes.preview) {
    RideActivityWidget()
} contentStates: {
    RideAttributes.ContentState(
        driverName: "Alex",
        driverPhoto: "car.fill",
        vehicleDescription: "White Toyota Camry",
        eta: Date()...Date().addingTimeInterval(300),
        status: .driverEnRoute,
        distanceRemaining: 1.5
    )
    RideAttributes.ContentState(
        driverName: "Alex",
        driverPhoto: "car.fill",
        vehicleDescription: "White Toyota Camry",
        eta: Date()...Date().addingTimeInterval(60),
        status: .arriving,
        distanceRemaining: 0.1
    )
}

#Preview("Dynamic Island Compact", as: .dynamicIsland(.compact), using: RideAttributes.preview) {
    RideActivityWidget()
} contentStates: {
    RideAttributes.ContentState(
        driverName: "Alex",
        driverPhoto: "car.fill",
        vehicleDescription: "White Toyota Camry",
        eta: Date()...Date().addingTimeInterval(300),
        status: .driverEnRoute,
        distanceRemaining: 1.5
    )
}

#Preview("Dynamic Island Expanded", as: .dynamicIsland(.expanded), using: RideAttributes.preview) {
    RideActivityWidget()
} contentStates: {
    RideAttributes.ContentState(
        driverName: "Alex",
        driverPhoto: "car.fill",
        vehicleDescription: "White Toyota Camry",
        eta: Date()...Date().addingTimeInterval(300),
        status: .driverEnRoute,
        distanceRemaining: 1.5
    )
}

#Preview("Dynamic Island Minimal", as: .dynamicIsland(.minimal), using: RideAttributes.preview) {
    RideActivityWidget()
} contentStates: {
    RideAttributes.ContentState(
        driverName: "Alex",
        driverPhoto: "car.fill",
        vehicleDescription: "White Toyota Camry",
        eta: Date()...Date().addingTimeInterval(300),
        status: .driverEnRoute,
        distanceRemaining: 1.5
    )
}
```

### Preview Data Helper

```swift
extension RideAttributes {
    static var preview: RideAttributes {
        RideAttributes(
            riderName: "Jordan",
            pickupLocation: "123 Main St",
            dropoffLocation: "456 Oak Ave"
        )
    }
}
```

### On Device

Test push-to-update by sending payloads through APNs using a tool like `curl`
or a push notification testing app. The Simulator does not support APNs, so
push-to-update must be tested on a physical device.

```bash
# Example curl command for APNs push update (HTTP/2)
curl -v \
  --http2 \
  --header "apns-push-type: liveactivity" \
  --header "apns-topic: com.example.app.push-type.liveactivity" \
  --header "apns-priority: 10" \
  --header "authorization: bearer $JWT_TOKEN" \
  --data '{"aps":{"timestamp":1700000000,"event":"update","content-state":{"driverName":"Alex","driverPhoto":"car.fill","vehicleDescription":"White Toyota Camry","eta":{"lowerBound":1700000000,"upperBound":1700000300},"status":"driverArrived","distanceRemaining":0.0},"alert":{"title":"Driver Arrived","body":"Your driver is here!"}}}' \
  https://api.push.apple.com/3/device/$DEVICE_PUSH_TOKEN
```

### Debugging Tips

- Check Console.app for `ActivityKit` log messages when activities fail to start.
- Verify `content-state` JSON keys match `ContentState` property names exactly
  (including camelCase). Mismatches cause silent failures.
- Use `Activity<T>.activities` to inspect all running activities in the debugger.
- Set a breakpoint in `pushTokenUpdates` to verify tokens are being delivered.
- If activities do not appear, confirm `NSSupportsLiveActivities = YES` is in
  the host app's Info.plist (not the widget extension's).

## Info.plist Keys Reference

| Key | Value | Purpose |
|---|---|---|
| `NSSupportsLiveActivities` | `YES` | Enable Live Activities (required) |
| `NSSupportsLiveActivitiesFrequentUpdates` | `YES` | Increase push update budget |

Both keys belong in the host app's Info.plist, not the widget extension.

## Apple Documentation Links

- [ActivityKit](https://sosumi.ai/documentation/activitykit)
- [ActivityAttributes](https://sosumi.ai/documentation/activitykit/activityattributes)
- [Activity](https://sosumi.ai/documentation/activitykit/activity)
- [ActivityContent](https://sosumi.ai/documentation/activitykit/activitycontent)
- [ActivityAuthorizationInfo](https://sosumi.ai/documentation/activitykit/activityauthorizationinfo)
- [DynamicIsland](https://sosumi.ai/documentation/widgetkit/dynamicisland)
- [ActivityConfiguration](https://sosumi.ai/documentation/widgetkit/activityconfiguration)
- [Starting and updating with push notifications](https://sosumi.ai/documentation/activitykit/starting-and-updating-live-activities-with-activitykit-push-notifications)
