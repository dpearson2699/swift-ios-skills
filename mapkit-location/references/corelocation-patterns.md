# CoreLocation Patterns Reference

Extended patterns for CoreLocation on iOS 17+ with modern Swift concurrency.
Import `CoreLocation` in every file that uses these APIs.

```swift
import CoreLocation
```

---

## CLLocationUpdate.liveUpdates() (iOS 17+)

### Basic Usage

```swift
func startReceivingLocation() async {
    for try await update in CLLocationUpdate.liveUpdates() {
        guard let location = update.location else { continue }
        print("Lat: \(location.coordinate.latitude), Lon: \(location.coordinate.longitude)")
        print("Accuracy: \(location.horizontalAccuracy)m")
    }
}
```

### Full Implementation with Filtering

Filter out stale, inaccurate, or duplicate updates to avoid unnecessary UI
refreshes and reduce battery impact.

```swift
@Observable
final class LocationService: @unchecked Sendable {
    var currentLocation: CLLocation?
    var isTracking = false

    private var trackingTask: Task<Void, Never>?
    private var lastReportedLocation: CLLocation?

    /// Minimum distance in meters between reported locations.
    private let distanceFilter: CLLocationDistance = 10
    /// Maximum acceptable horizontal accuracy in meters.
    private let accuracyThreshold: CLLocationAccuracy = 100

    func startTracking() {
        guard !isTracking else { return }
        isTracking = true

        trackingTask = Task { [weak self] in
            guard let self else { return }
            let updates = CLLocationUpdate.liveUpdates(.default)

            for try await update in updates {
                if Task.isCancelled { break }

                // Skip updates without a location
                guard let location = update.location else { continue }

                // Skip inaccurate readings
                guard location.horizontalAccuracy >= 0,
                      location.horizontalAccuracy < self.accuracyThreshold else {
                    continue
                }

                // Skip if the user has not moved enough
                if let last = self.lastReportedLocation,
                   location.distance(from: last) < self.distanceFilter {
                    continue
                }

                self.lastReportedLocation = location

                await MainActor.run {
                    self.currentLocation = location
                }
            }

            await MainActor.run {
                self.isTracking = false
            }
        }
    }

    func stopTracking() {
        trackingTask?.cancel()
        trackingTask = nil
        isTracking = false
    }
}
```

### LiveConfiguration Options

`CLLocationUpdate.liveUpdates(_:)` accepts a `LiveConfiguration` parameter:

```swift
// Default: balanced power and accuracy
CLLocationUpdate.liveUpdates(.default)

// Best for navigation: highest accuracy, most frequent updates
CLLocationUpdate.liveUpdates(.automotiveNavigation)

// Fitness tracking
CLLocationUpdate.liveUpdates(.fitness)

// Other-navigation (non-automotive)
CLLocationUpdate.liveUpdates(.otherNavigation)

// Airborne: for drone or aviation apps
CLLocationUpdate.liveUpdates(.airborne)
```

### Handling Stationary and Error States (iOS 18+)

```swift
for try await update in CLLocationUpdate.liveUpdates() {
    // Check authorization status (iOS 18+)
    if update.authorizationDenied {
        // User denied location; prompt to open Settings
        break
    }

    if update.authorizationDeniedGlobally {
        // Location Services disabled system-wide
        break
    }

    if update.insufficientlyInUse {
        // App does not meet in-use requirements
        continue
    }

    if update.locationUnavailable {
        // Temporarily unable to determine location; keep iterating
        continue
    }

    if update.stationary {
        // Device stopped moving; updates will pause
        continue
    }

    guard let location = update.location else { continue }
    // Use location
}
```

Note: `authorizationDenied`, `authorizationDeniedGlobally`,
`insufficientlyInUse`, `locationUnavailable`, and `stationary` are only
available on iOS 18+. On iOS 17, check `update.location == nil` to detect
unavailable location.

---

## CLServiceSession (iOS 18+)

### Setup and Lifecycle

`CLServiceSession` declares your authorization requirements for a feature.
Hold a strong reference for the session's entire duration.

```swift
@Observable
final class LocationFeature {
    private var serviceSession: CLServiceSession?
    private var locationTask: Task<Void, Never>?

    func activate() {
        // Declare that this feature needs when-in-use authorization
        serviceSession = CLServiceSession(authorization: .whenInUse)

        locationTask = Task {
            for try await update in CLLocationUpdate.liveUpdates() {
                guard let location = update.location else { continue }
                // process location
            }
        }
    }

    func deactivate() {
        locationTask?.cancel()
        locationTask = nil
        // Release the session to signal you no longer need location
        serviceSession = nil
    }
}
```

### Full Accuracy Request

Request full accuracy when the user has granted approximate-only permission:

```swift
// Requires Info.plist:
// NSLocationTemporaryUsageDescriptionDictionary
//   NearbySearchPurpose: "Show nearby stores within walking distance."

let session = CLServiceSession(
    authorization: .whenInUse,
    fullAccuracyPurposeKey: "NearbySearchPurpose"
)
```

### Always Authorization

Only use `.always` when you need the system to relaunch your app in the
background for significant location changes after termination.

```swift
let session = CLServiceSession(authorization: .always)
```

Requires `NSLocationAlwaysAndWhenInUseUsageDescription` in Info.plist.

### Implicit vs. Explicit Sessions

On iOS 18+, `CLLocationUpdate.liveUpdates()` and `CLMonitor` create an
implicit `CLServiceSession` behind the scenes if you do not create one. You
need an explicit session when:

- You require `.always` authorization
- You need full accuracy via `fullAccuracyPurposeKey`
- You want to enforce explicit session management (add
  `NSLocationRequireExplicitServiceSession` to Info.plist)

---

## CLMonitor for Geofencing (iOS 17+)

### Basic Setup

`CLMonitor` replaces `CLLocationManager` region monitoring. It is an `actor`,
so all its APIs require `await`.

```swift
@available(iOS 17, *)
actor GeofenceMonitor {
    private var monitor: CLMonitor?
    private var monitoringTask: Task<Void, any Error>?

    func startMonitoring(regions: [GeofenceRegion]) async {
        let monitor = await CLMonitor("myAppGeofences")
        self.monitor = monitor

        // Add circular geographic conditions
        for region in regions {
            let condition = CLMonitor.CircularGeographicCondition(
                center: region.center,
                radius: region.radius
            )
            await monitor.add(condition, identifier: region.id)
        }

        // Listen for events
        monitoringTask = Task {
            for try await event in await monitor.events {
                switch event.state {
                case .satisfied:
                    // Device entered the region
                    handleEntry(identifier: event.identifier)
                case .unsatisfied:
                    // Device exited the region
                    handleExit(identifier: event.identifier)
                case .unknown:
                    break
                default:
                    break
                }
            }
        }
    }

    func stopMonitoring() async {
        monitoringTask?.cancel()
        monitoringTask = nil

        if let monitor {
            for identifier in await monitor.identifiers {
                await monitor.remove(identifier)
            }
        }
        monitor = nil
    }

    private func handleEntry(identifier: String) {
        print("Entered region: \(identifier)")
    }

    private func handleExit(identifier: String) {
        print("Exited region: \(identifier)")
    }
}

struct GeofenceRegion: Identifiable {
    let id: String
    let center: CLLocationCoordinate2D
    let radius: CLLocationDistance
}
```

### Critical CLMonitor Rules

1. **Maximum 20 conditions per app.** Adding more causes excess conditions
   to report `unmonitored` state. This limit is per-app, not per-monitor.

2. **Do not recreate CLMonitor instances rapidly.** Creating a monitor with
   the same name while one is still alive crashes the app. Reuse the instance
   and call `add`/`remove` to change conditions.

3. **Subscribe to `events` exactly once per CLMonitor.** Cancelling and
   re-subscribing causes the new subscription to immediately cancel. Keep a
   single long-lived subscription.

4. **Use diffing for condition updates.** Instead of removing all conditions
   and re-adding them, calculate which to add and which to remove.

5. **Target iOS 18+ for best results.** Pair `CLMonitor` with
   `CLServiceSession` for reliable authorization management.

### Adding Conditions with Initial State

Specify an assumed initial state to avoid spurious events on first add:

```swift
await monitor.add(condition, identifier: "office", assuming: .unsatisfied)
```

Use `.unsatisfied` when you believe the device is outside the region. Use
`.satisfied` when you believe the device is inside.

### Updating Conditions Dynamically

```swift
func updateRegions(_ newRegions: [GeofenceRegion]) async {
    guard let monitor else { return }

    let existingIDs = Set(await monitor.identifiers)
    let newIDs = Set(newRegions.map(\.id))

    // Remove stale conditions
    for id in existingIDs.subtracting(newIDs) {
        await monitor.remove(id)
    }

    // Add new conditions
    for region in newRegions where !existingIDs.contains(region.id) {
        let condition = CLMonitor.CircularGeographicCondition(
            center: region.center,
            radius: region.radius
        )
        await monitor.add(condition, identifier: region.id, assuming: .unsatisfied)
    }
}
```

### Checking Last Known State

```swift
if let record = await monitor.record(for: "office") {
    let lastState = record.lastEvent.state
    let lastDate = record.lastEvent.date
    print("Region 'office' was \(lastState) at \(lastDate)")
}
```

---

## CLBackgroundActivitySession

Allow a when-in-use authorized app to receive location updates in the
background. Requires the `Location updates` background mode capability.

```swift
@available(iOS 17, *)
actor BackgroundLocationTracker {
    private var backgroundSession: CLBackgroundActivitySession?
    private var serviceSession: CLServiceSession?
    private var trackingTask: Task<Void, Never>?

    func startBackgroundTracking() {
        // Declare authorization intent (iOS 18+)
        serviceSession = CLServiceSession(authorization: .whenInUse)

        // Start background activity session -- shows blue location indicator
        backgroundSession = CLBackgroundActivitySession()

        trackingTask = Task {
            for try await update in CLLocationUpdate.liveUpdates(.fitness) {
                guard let location = update.location else { continue }
                // Record location for fitness tracking, navigation, etc.
                await recordLocation(location)
            }
        }
    }

    func stopBackgroundTracking() {
        trackingTask?.cancel()
        trackingTask = nil
        backgroundSession?.invalidate()
        backgroundSession = nil
        serviceSession = nil
    }

    private func recordLocation(_ location: CLLocation) async {
        // Persist to database, update Live Activity, etc.
    }
}
```

### Background Requirements Summary

To receive location in the background you need ALL of these:

1. `Background Modes > Location updates` capability enabled.
2. `NSLocationWhenInUseUsageDescription` in Info.plist.
3. `.whenInUse` or `.always` authorization granted.
4. Either a `CLBackgroundActivitySession` held or a Live Activity running.
5. An active `CLLocationUpdate` or `CLMonitor` subscription.

`.always` authorization is NOT required for background location. The
difference: with `.always`, the system can relaunch your terminated app for
significant location changes. With `.whenInUse` + background session, the
app must be running (foreground or suspended).

---

## Significant Location Change Monitoring

Use when you only need coarse location updates at ~500-meter intervals.
Extremely battery efficient because it piggybacks on cellular tower changes.

```swift
// Legacy CLLocationManager approach (still valid, no modern replacement)
let manager = CLLocationManager()
manager.startMonitoringSignificantLocationChanges()

// The delegate receives updates when the device moves ~500m+ from the
// last reported location. Updates arrive 1-5 minutes apart.
```

There is no `CLLocationUpdate` equivalent for significant location changes.
Use `CLLocationManager` for this specific use case.

---

## Visit Monitoring

Detect when the user arrives at or departs from a place. Useful for
journaling, check-in, and context-aware features.

```swift
let manager = CLLocationManager()
manager.startMonitoringVisits()

// Delegate callback:
func locationManager(_ manager: CLLocationManager, didVisit visit: CLVisit) {
    let coordinate = visit.coordinate
    let arrivalDate = visit.arrivalDate
    let departureDate = visit.departureDate
    // departureDate == .distantFuture means the user is still at the location
}
```

---

## Region Monitoring Migration (CLCircularRegion to CLMonitor)

### Legacy Approach (Deprecated)

```swift
// DEPRECATED
let region = CLCircularRegion(center: coordinate, radius: 200, identifier: "office")
region.notifyOnEntry = true
region.notifyOnExit = true
manager.startMonitoring(for: region)
```

### Modern Approach (iOS 17+)

```swift
// MODERN
let monitor = await CLMonitor("appMonitor")
let condition = CLMonitor.CircularGeographicCondition(center: coordinate, radius: 200)
await monitor.add(condition, identifier: "office")

for try await event in await monitor.events {
    if event.identifier == "office" {
        switch event.state {
        case .satisfied: handleEntry()
        case .unsatisfied: handleExit()
        default: break
        }
    }
}
```

Key differences:

| Aspect | CLCircularRegion | CLMonitor |
|--------|-----------------|-----------|
| API style | Delegate callbacks | Async sequence |
| Max regions | 20 per app | 20 per app |
| Entry/exit | Separate booleans | State enum (satisfied/unsatisfied) |
| Concurrency | @objc delegate | Actor-based |
| Min iOS | iOS 7 | iOS 17 |

---

## Location Accuracy Management

### Accuracy Levels for CLLocationManager

```swift
manager.desiredAccuracy = kCLLocationAccuracyBest             // GPS, ~5m, highest power
manager.desiredAccuracy = kCLLocationAccuracyNearestTenMeters // ~10m
manager.desiredAccuracy = kCLLocationAccuracyHundredMeters    // WiFi, ~100m
manager.desiredAccuracy = kCLLocationAccuracyKilometer        // Cell tower, ~1km
manager.desiredAccuracy = kCLLocationAccuracyThreeKilometers  // ~3km, lowest power
manager.desiredAccuracy = kCLLocationAccuracyReduced          // ~5km, privacy-safe
```

### Activity Type (Influences Power Management)

```swift
manager.activityType = .other                 // Default
manager.activityType = .automotiveNavigation  // Highway speeds, high accuracy
manager.activityType = .fitness               // Walking/running
manager.activityType = .otherNavigation       // Boats, trains
manager.activityType = .airborne              // Drones, aircraft (iOS 12+)
```

### CLLocationUpdate has no filtering

`CLLocationUpdate.liveUpdates()` does not support `desiredAccuracy` or
`distanceFilter`. Filter the stream yourself:

```swift
for try await update in CLLocationUpdate.liveUpdates() {
    guard let location = update.location,
          location.horizontalAccuracy < 50,
          location.horizontalAccuracy >= 0 else { continue }
    // Use filtered location
}
```

---

## Testing Location in Simulator

### Set a fixed simulated location

In Xcode: Debug > Simulate Location > choose a city or custom coordinate.

### GPX File for a Moving Route

Create a `.gpx` file and add it to your Xcode project:

```xml
<?xml version="1.0"?>
<gpx version="1.1" creator="Xcode">
    <wpt lat="37.3349" lon="-122.0090">
        <time>2025-01-01T00:00:00Z</time>
        <name>Apple Park</name>
    </wpt>
    <wpt lat="37.3318" lon="-122.0312">
        <time>2025-01-01T00:01:00Z</time>
        <name>Infinite Loop</name>
    </wpt>
    <wpt lat="37.3230" lon="-122.0322">
        <time>2025-01-01T00:02:00Z</time>
        <name>De Anza College</name>
    </wpt>
</gpx>
```

Set this file in the scheme: Edit Scheme > Run > Options > Default Location.

The simulator interpolates between waypoints using timestamps. Playback loops
automatically when it reaches the last waypoint.

### Programmatic Simulation in Tests

Use `CLLocationManager` with XCTest by injecting a location protocol:

```swift
protocol LocationProviding: Sendable {
    func updates() -> AsyncStream<CLLocation>
}

// Production
struct LiveLocationProvider: LocationProviding {
    func updates() -> AsyncStream<CLLocation> {
        AsyncStream { continuation in
            Task {
                for try await update in CLLocationUpdate.liveUpdates() {
                    if let location = update.location {
                        continuation.yield(location)
                    }
                }
                continuation.finish()
            }
        }
    }
}

// Test mock
struct MockLocationProvider: LocationProviding {
    let locations: [CLLocation]

    func updates() -> AsyncStream<CLLocation> {
        AsyncStream { continuation in
            for location in locations {
                continuation.yield(location)
            }
            continuation.finish()
        }
    }
}
```

---

## Privacy and Info.plist Keys

### Required Keys

| Key | When to add |
|-----|-------------|
| `NSLocationWhenInUseUsageDescription` | Always, for any location use |
| `NSLocationAlwaysAndWhenInUseUsageDescription` | Only if requesting `.always` |

### Optional Keys

| Key | Purpose |
|-----|---------|
| `NSLocationTemporaryUsageDescriptionDictionary` | Per-feature full-accuracy descriptions |
| `NSLocationRequireExplicitServiceSession` | Force explicit `CLServiceSession` usage (iOS 18+) |
| `NSLocationDefaultAccuracyReduced` | Default to approximate location |
| `UIBackgroundModes` (includes `location`) | Background location updates |

### Usage Description Best Practices

**Good:** "Shows nearby coffee shops within walking distance so you can find your next stop quickly."

**Bad:** "This app uses your location."

App Review rejects vague usage descriptions. Be specific about what the user
gains from sharing their location.

---

## Common Pitfalls

### CLMonitor crash on rapid recreation

```swift
// CRASH -- creating a monitor with a name already in use
let monitorA = await CLMonitor("myMonitor")
// ... immediately discard monitorA ...
let monitorB = await CLMonitor("myMonitor") // NSInternalInconsistencyException
```

Fix: reuse the existing monitor instance. Only create a new one after the
old one has been fully torn down (conditions removed, reference released,
NOT in the same run loop).

### CLLocationUpdate.liveUpdates() returns nothing on iOS 17 without full accuracy

On iOS 17 (not iOS 18+), `liveUpdates()` may return no updates when the user
has denied full accuracy. This is resolved in iOS 18. Target iOS 18+ or
fall back to `CLLocationManager` if you need to handle approximate-only
location on iOS 17.

### Forgetting to hold CLBackgroundActivitySession

```swift
// WRONG -- session is immediately deallocated
func startBackground() {
    let _ = CLBackgroundActivitySession()
    // ^ No strong reference; session ends immediately
}

// CORRECT -- hold as a stored property
private var bgSession: CLBackgroundActivitySession?

func startBackground() {
    bgSession = CLBackgroundActivitySession()
}
```

### Not checking horizontalAccuracy

```swift
// WRONG -- using location with negative accuracy (invalid)
guard let location = update.location else { continue }
updateMap(location) // May have accuracy of -1 (invalid)

// CORRECT
guard let location = update.location,
      location.horizontalAccuracy >= 0 else { continue }
updateMap(location)
```

A `horizontalAccuracy` of -1 means the coordinate is invalid.

---

## References

- Apple docs: [CLLocationUpdate](https://sosumi.ai/documentation/CoreLocation/CLLocationUpdate)
- Apple docs: [CLServiceSession](https://sosumi.ai/documentation/CoreLocation/CLServiceSession)
- Apple docs: [CLMonitor](https://sosumi.ai/documentation/CoreLocation/CLMonitor)
- Apple docs: [CLBackgroundActivitySession](https://sosumi.ai/documentation/CoreLocation/CLBackgroundActivitySession)
- Apple docs: [Requesting authorization](https://sosumi.ai/documentation/CoreLocation/requesting-authorization-to-use-location-services)
- Apple docs: [Handling background location](https://sosumi.ai/documentation/CoreLocation/handling-location-updates-in-the-background)
