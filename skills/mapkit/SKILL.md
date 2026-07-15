---
name: mapkit
description: "Implement, review, or improve maps and location features in iOS/macOS apps using MapKit and CoreLocation. Use when working with Map views, annotations, markers, polylines, user location tracking, geocoding, reverse geocoding, search/autocomplete, directions and routes, geofencing, region monitoring, CLLocationUpdate async streams, or location authorization flows. Also use when working with maps, coordinates, addresses, places, directions, distance calculations, or location-based features in Swift apps."
---

# MapKit

Build map-based and location-aware features targeting iOS 17+ with SwiftUI
MapKit and modern CoreLocation async APIs. Use `Map` with `MapContentBuilder`
for views, `CLLocationUpdate.liveUpdates()` for streaming location, and
`CLMonitor` for geofencing.

Read [references/mapkit-patterns.md](references/mapkit-patterns.md) when you need full map setup, search,
routes, Look Around, snapshots, or iOS 26 place APIs. Read
[references/mapkit-corelocation-patterns.md](references/mapkit-corelocation-patterns.md) when the task involves
location update lifecycle, geofencing, background location, testing, or privacy keys.

## Contents

- [Workflow](#workflow)
- [SwiftUI Map View (iOS 17+)](#swiftui-map-view-ios-17)
- [CoreLocation Modern API](#corelocation-modern-api)
- [Geocoding](#geocoding)
- [Search](#search)
- [Directions](#directions)
- [PlaceDescriptor (iOS 26+)](#placedescriptor-ios-26)
- [Common Mistakes](#common-mistakes)
- [Review Checklist](#review-checklist)
- [References](#references)

## Workflow

### 1. Add a map with markers or annotations

1. Import `MapKit`.
2. Create a `Map` view with optional `MapCameraPosition` binding.
3. Add `Marker`, `Annotation`, `MapPolyline`, `MapPolygon`, or `MapCircle`
   inside the `MapContentBuilder` closure.
4. Configure map style with `.mapStyle()`.
5. Add map controls with `.mapControls { }`.
6. Handle selection with a `selection:` binding.

### 2. Track user location

1. Add `NSLocationWhenInUseUsageDescription` to Info.plist.
2. On iOS 18+, create a `CLServiceSession` to manage authorization.
3. Iterate `CLLocationUpdate.liveUpdates()` in a `Task`.
4. Filter updates by distance or accuracy before updating the UI.
5. Stop the task when location tracking is no longer needed.

### 3. Search for places

1. Configure `MKLocalSearchCompleter` for autocomplete suggestions.
2. Debounce user input (at least 300ms) before setting the query.
3. Convert selected completion to `MKLocalSearch.Request` for full results.
4. Display results as markers or in a list.

### 4. Get directions and display a route

1. Create an `MKDirections.Request` with source and destination `MKMapItem`.
2. Set `transportType` (`.automobile`, `.walking`, `.transit`, `.cycling`).
3. Await `MKDirections.calculate()`.
4. Draw the route with `MapPolyline(route.polyline)`.

### 5. Review existing map/location code

Run through the Review Checklist at the end of this file.

## SwiftUI Map View (iOS 17+)

```swift
import MapKit
import SwiftUI

struct PlaceMap: View {
    @State private var position: MapCameraPosition = .automatic

    var body: some View {
        Map(position: $position) {
            Marker("Apple Park", coordinate: applePark)
            Marker("Infinite Loop", systemImage: "building.2",
                   coordinate: infiniteLoop)
        }
        .mapStyle(.standard(elevation: .realistic))
        .mapControls {
            MapUserLocationButton()
            MapCompass()
            MapScaleView()
        }
    }
}
```

### Marker and Annotation

```swift
// Balloon marker -- simplest way to pin a location
Marker("Cafe", systemImage: "cup.and.saucer.fill", coordinate: cafeCoord)
    .tint(.brown)

// Annotation -- custom SwiftUI view at a coordinate
Annotation("You", coordinate: userCoord, anchor: .bottom) {
    Image(systemName: "figure.wave")
        .padding(6)
        .background(.blue.gradient, in: .circle)
        .foregroundStyle(.white)
}
```

### Overlays: Polyline, Polygon, Circle

```swift
Map {
    // Polyline from coordinates
    MapPolyline(coordinates: routeCoords)
        .stroke(.blue, lineWidth: 4)

    // Polygon (area highlight)
    MapPolygon(coordinates: parkBoundary)
        .foregroundStyle(.green.opacity(0.3))
        .stroke(.green, lineWidth: 2)

    // Circle (radius around a point)
    MapCircle(center: storeCoord, radius: 500)
        .foregroundStyle(.red.opacity(0.15))
        .stroke(.red, lineWidth: 1)
}
```

### Camera Position

`MapCameraPosition` controls what the map displays. Bind it to let the user
interact and to programmatically move the camera.

```swift
// Center on a region
@State private var position: MapCameraPosition = .region(
    MKCoordinateRegion(
        center: CLLocationCoordinate2D(latitude: 37.334, longitude: -122.009),
        span: MKCoordinateSpan(latitudeDelta: 0.05, longitudeDelta: 0.05)
    )
)

// Follow user location
@State private var position: MapCameraPosition = .userLocation(fallback: .automatic)

// Specific camera angle (3D perspective)
@State private var position: MapCameraPosition = .camera(
    MapCamera(centerCoordinate: applePark, distance: 1000, heading: 90, pitch: 60)
)

// Frame specific items
position = .item(MKMapItem.forCurrentLocation())
position = .rect(MKMapRect(...))
```

### Map Style

Default to `.standard`; select `.imagery` or `.hybrid`, realistic elevation,
traffic, and point-of-interest filtering only when the feature requires them.
See [Complete Map View Setup](references/mapkit-patterns.md#complete-map-view-setup).

### Map Interaction Modes

Keep `.all` for an interactive map. Restrict modes only for intentional gesture
coordination; use `[]` for a static embedded map. See
[Map in a List or ScrollView](references/mapkit-patterns.md#map-in-a-list-or-scrollview).

### Map Selection

```swift
@State private var selectedMarker: MKMapItem?

Map(selection: $selectedMarker) {
    ForEach(places) { place in
        Marker(place.name, coordinate: place.coordinate)
            .tag(place.mapItem)     // Tag must match selection type
    }
}
.onChange(of: selectedMarker) { _, newValue in
    guard let item = newValue else { return }
    // React to selection
}
```

## CoreLocation Modern API

### CLLocationUpdate.liveUpdates() (iOS 17+)

Replace `CLLocationManagerDelegate` callbacks with a single async sequence.
Each iteration yields a `CLLocationUpdate` containing an optional `CLLocation`.
On iOS 18+, handle diagnostic states such as denied authorization, globally
disabled Location Services, unavailable location, and insufficient in-use
conditions with a visible degraded path instead of silently waiting forever.
Store the task so the feature can cancel it, and reject invalid, inaccurate,
stale, or unusable movement data before driving map UI or background work.

```swift
import CoreLocation

@MainActor
@Observable
final class LocationTracker {
    var currentLocation: CLLocation?
    private var updateTask: Task<Void, Never>?

    func startTracking() {
        updateTask = Task {
            do {
                let updates = CLLocationUpdate.liveUpdates()
                for try await update in updates {
                    guard let location = update.location else { continue }
                    // Filter by horizontal accuracy
                    guard location.horizontalAccuracy >= 0,
                          location.horizontalAccuracy < 50 else { continue }
                    currentLocation = location
                }
            } catch is CancellationError {
                // Expected when tracking stops.
            } catch {
                currentLocation = nil
            }
        }
    }

    func stopTracking() {
        updateTask?.cancel()
        updateTask = nil
    }
}
```

### CLServiceSession (iOS 18+)

Declare authorization requirements for a feature's lifetime. Hold a reference
to the session for as long as you need location services.

```swift
// When-in-use authorization with full accuracy preference
let session = CLServiceSession(
    authorization: .whenInUse,
    fullAccuracyPurposeKey: "NearbySearchPurpose"
)
// Hold `session` as a stored property; release it when done.
```

On iOS 18+, `CLLocationUpdate.liveUpdates()` and `CLMonitor` take an implicit
`CLServiceSession` if you do not create one explicitly. Create one explicitly
when you need `.always` authorization or full accuracy.

### Authorization Flow

```swift
// Info.plist keys (required):
// NSLocationWhenInUseUsageDescription
// NSLocationAlwaysAndWhenInUseUsageDescription (only if .always needed)

// Check authorization and guide user to Settings when denied
struct LocationPermissionView: View {
    @Environment(\.openURL) private var openURL

    var body: some View {
        ContentUnavailableView {
            Label("Location Access Denied", systemImage: "location.slash")
        } description: {
            Text("Enable location access in Settings to use this feature.")
        } actions: {
            Button("Open Settings") {
                if let url = URL(string: UIApplication.openSettingsURLString) {
                    openURL(url)
                }
            }
        }
    }
}
```

## Geocoding

### CLGeocoder (iOS 8+)

```swift
let geocoder = CLGeocoder()

// Forward geocoding: address string -> coordinates
let placemarks = try await geocoder.geocodeAddressString("1 Apple Park Way, Cupertino")
if let location = placemarks.first?.location {
    print(location.coordinate) // CLLocationCoordinate2D
}

// Reverse geocoding: coordinates -> placemark
let location = CLLocation(latitude: 37.3349, longitude: -122.0090)
let placemarks = try await geocoder.reverseGeocodeLocation(location)
if let placemark = placemarks.first {
    let address = [placemark.name, placemark.locality, placemark.administrativeArea]
        .compactMap { $0 }
        .joined(separator: ", ")
}
```

### MKGeocodingRequest and MKReverseGeocodingRequest (iOS 26+)

New MapKit-native geocoding that returns `MKMapItem` with richer data and
`MKAddress` / `MKAddressRepresentations` for flexible address formatting.

```swift
@available(iOS 26, *)
func reverseGeocode(location: CLLocation) async throws -> MKMapItem? {
    guard let request = MKReverseGeocodingRequest(location: location) else {
        return nil
    }
    let mapItems = try await request.mapItems
    return mapItems.first
}

@available(iOS 26, *)
func forwardGeocode(address: String) async throws -> [MKMapItem] {
    guard let request = MKGeocodingRequest(addressString: address) else { return [] }
    return try await request.mapItems
}
```

## Search

### MKLocalSearchCompleter (Autocomplete)

```swift
@Observable
final class SearchCompleter: NSObject, MKLocalSearchCompleterDelegate {
    var results: [MKLocalSearchCompletion] = []
    var query: String = "" { didSet { completer.queryFragment = query } }

    private let completer = MKLocalSearchCompleter()

    override init() {
        super.init()
        completer.delegate = self
        completer.resultTypes = [.address, .pointOfInterest]
    }

    func completerDidUpdateResults(_ completer: MKLocalSearchCompleter) {
        results = completer.results
    }

    func completer(_ completer: MKLocalSearchCompleter, didFailWithError error: Error) {
        results = []
    }
}
```

### MKLocalSearch (Full Search)

```swift
func search(for completion: MKLocalSearchCompletion) async throws -> [MKMapItem] {
    let request = MKLocalSearch.Request(completion: completion)
    request.resultTypes = [.pointOfInterest, .address]
    let search = MKLocalSearch(request: request)
    let response = try await search.start()
    return response.mapItems
}

// Search by natural language query within a region
func searchNearby(query: String, region: MKCoordinateRegion) async throws -> [MKMapItem] {
    let request = MKLocalSearch.Request()
    request.naturalLanguageQuery = query
    request.region = region
    let search = MKLocalSearch(request: request)
    let response = try await search.start()
    return response.mapItems
}
```

## Directions

```swift
func getDirections(from source: MKMapItem, to destination: MKMapItem,
                   transport: MKDirectionsTransportType = .automobile) async throws -> MKRoute? {
    let request = MKDirections.Request()
    request.source = source
    request.destination = destination
    request.transportType = transport
    let directions = MKDirections(request: request)
    let response = try await directions.calculate()
    return response.routes.first
}
```

### Display Route on Map

```swift
@State private var route: MKRoute?

Map {
    if let route {
        MapPolyline(route.polyline)
            .stroke(.blue, lineWidth: 5)
    }
    Marker("Start", coordinate: startCoord)
    Marker("End", coordinate: endCoord)
}
.task {
    route = try? await getDirections(from: startItem, to: endItem)
}
```

### ETA Calculation

```swift
func getETA(from source: MKMapItem, to destination: MKMapItem) async throws -> TimeInterval {
    let request = MKDirections.Request()
    request.source = source
    request.destination = destination
    let directions = MKDirections(request: request)
    let response = try await directions.calculateETA()
    return response.expectedTravelTime
}
```

### Cycling Directions (iOS 14+)

Use `.cycling` as the request transport type; see the complete
[cycling route](references/mapkit-patterns.md#cycling-directions-ios-14) example.

## PlaceDescriptor (iOS 26+)

Create rich place references from coordinates or addresses without needing a
Place ID. Requires `import GeoToolbox`.

```swift
import GeoToolbox

@available(iOS 26, *)
func lookupPlace(name: String, coordinate: CLLocationCoordinate2D) async throws -> MKMapItem {
    let descriptor = PlaceDescriptor(
        representations: [.coordinate(coordinate)],
        commonName: name
    )
    let request = MKMapItemRequest(placeDescriptor: descriptor)
    return try await request.mapItem
}
```

## Common Mistakes

**DON'T:** Request always authorization upfront.
**DO:** Start with when-in-use authorization. On iOS 18+, hold a `CLServiceSession`
for the feature lifetime; request `.always` only for background features that
need system relaunch after termination.

**DON'T:** Use `CLLocationManagerDelegate` for simple location fetches on iOS 17+.
**DO:** Use `CLLocationUpdate.liveUpdates()` async stream for cleaner, more concise code.

**DON'T:** Ignore `CLLocationUpdate` diagnostics such as denied, globally denied, or unavailable location.
**DO:** Stop or degrade the feature, show recovery UI such as Settings guidance, and keep search/manual flows usable.

**DON'T:** Let `liveUpdates()` run from an unowned task after the map/view is gone.
**DO:** Store the `Task`, cancel it when the feature stops, and filter invalid, inaccurate, stale, or impossible movement fixes.

**DON'T:** Force-unwrap `CLPlacemark` properties — they are all optional.
**DO:** Use nil-coalescing: `placemark.locality ?? "Unknown"`.

**DON'T:** Fire `MKLocalSearchCompleter` queries on every keystroke.
**DO:** Debounce with `.task(id: searchText)` + `Task.sleep(for: .milliseconds(300))`.

**DON'T:** Silently fail when location authorization is denied.
**DO:** Detect `.denied` status and show an alert with a Settings deep link.

**DON'T:** Assume geocoding always succeeds — handle empty results and network errors.

## Review Checklist

- [ ] Info.plist has `NSLocationWhenInUseUsageDescription` with specific reason
- [ ] Authorization denial handled with Settings deep link
- [ ] `CLLocationUpdate` task cancelled when not needed (battery)
- [ ] Location accuracy appropriate for the use case
- [ ] Map annotations use `Identifiable` data with stable IDs
- [ ] Geocoding errors handled (network failure, no results)
- [ ] Search completer input debounced
- [ ] `CLMonitor` limited to 20 conditions, instance kept alive
- [ ] Background location uses `CLBackgroundActivitySession`
- [ ] Map tested with VoiceOver
- [ ] Map annotation view models and location UI updates are `@MainActor`-isolated

## References

- [references/mapkit-patterns.md](references/mapkit-patterns.md) — Map setup, annotations, search, routes, clustering, Look Around, snapshots.
- [references/mapkit-corelocation-patterns.md](references/mapkit-corelocation-patterns.md) — CLLocationUpdate, CLMonitor, CLServiceSession, background location, testing.
