# MapKit Patterns Reference

Extended patterns for MapKit on iOS 17+ with SwiftUI. Import `MapKit` and
`SwiftUI` in every file that uses these APIs.

```swift
import MapKit
import SwiftUI
```

---

## Complete Map View Setup

A production-ready map view with markers, user location, and controls.

```swift
struct StoreLocatorMap: View {
    let stores: [Store]
    @State private var position: MapCameraPosition = .automatic
    @State private var selectedStore: Store?

    var body: some View {
        Map(position: $position, selection: $selectedStore) {
            UserAnnotation()

            ForEach(stores) { store in
                Marker(store.name, systemImage: "storefront",
                       coordinate: store.coordinate)
                    .tint(store.isOpen ? .green : .gray)
                    .tag(store)
            }
        }
        .mapStyle(.standard(pointsOfInterest: .excludingAll))
        .mapControls {
            MapUserLocationButton()
            MapCompass()
            MapScaleView()
            MapPitchToggle()
        }
        .safeAreaInset(edge: .bottom) {
            if let store = selectedStore {
                StoreDetailCard(store: store)
                    .padding()
            }
        }
    }
}
```

Conform the data model to `Hashable` for use with map selection:

```swift
struct Store: Identifiable, Hashable {
    let id: UUID
    let name: String
    let coordinate: CLLocationCoordinate2D
    let isOpen: Bool

    static func == (lhs: Store, rhs: Store) -> Bool { lhs.id == rhs.id }
    func hash(into hasher: inout Hasher) { hasher.combine(id) }
}
```

---

## Custom Annotation Views

Use `Annotation` for fully custom SwiftUI content at a coordinate. Prefer
`Marker` for standard pins because it handles clustering and accessibility
automatically.

```swift
Map {
    ForEach(friends) { friend in
        Annotation(friend.name, coordinate: friend.coordinate, anchor: .bottom) {
            VStack(spacing: 0) {
                AsyncImage(url: friend.avatarURL) { image in
                    image.resizable().scaledToFill()
                } placeholder: {
                    Color.gray
                }
                .frame(width: 40, height: 40)
                .clipShape(.circle)
                .overlay(Circle().stroke(.white, lineWidth: 2))

                Image(systemName: "triangle.fill")
                    .font(.caption2)
                    .foregroundStyle(.white)
                    .rotationEffect(.degrees(180))
                    .offset(y: -3)
            }
        }
    }
}
```

### Annotation with anchorOffset for callout-style layout

```swift
Annotation(place.name, coordinate: place.coordinate, anchor: .bottom) {
    VStack(spacing: 2) {
        Text(place.name)
            .font(.caption)
            .fontWeight(.semibold)
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .background(.ultraThinMaterial, in: .capsule)

        Image(systemName: "mappin.circle.fill")
            .font(.title)
            .foregroundStyle(.red)
    }
}
```

---

## Camera Control (MapCameraPosition)

### Animate camera changes

Wrap position updates in `withAnimation` for smooth transitions:

```swift
func flyTo(_ coordinate: CLLocationCoordinate2D) {
    withAnimation(.easeInOut(duration: 1.0)) {
        position = .camera(
            MapCamera(centerCoordinate: coordinate, distance: 2000,
                      heading: 0, pitch: 45)
        )
    }
}
```

### Frame multiple annotations

```swift
func frameAllStores() {
    withAnimation {
        position = .automatic  // Frames all map content
    }
}

// Or frame a specific rect
func frameRegion(_ region: MKCoordinateRegion) {
    withAnimation {
        position = .region(region)
    }
}
```

### Read current camera position

Use `onMapCameraChange` to observe what the user is looking at:

```swift
@State private var visibleRegion: MKCoordinateRegion?

Map(position: $position) { ... }
    .onMapCameraChange(frequency: .onEnd) { context in
        visibleRegion = context.region
    }
```

`frequency: .onEnd` fires after the user finishes scrolling. Use
`.continuous` only when you need live tracking (costs more CPU).

---

## Map Selection Handling

### Select markers by MKMapItem

Use `MKMapItem` as the selection type when you want to look up place details:

```swift
@State private var selectedItem: MKMapItem?

Map(selection: $selectedItem) {
    ForEach(searchResults) { result in
        Marker(item: result)
    }
}
.onChange(of: selectedItem) { _, newItem in
    guard let item = newItem else { return }
    Task { await fetchLookAround(for: item) }
}
```

### Select by custom Identifiable tag

```swift
@State private var selectedPlaceID: Place.ID?

Map(selection: $selectedPlaceID) {
    ForEach(places) { place in
        Marker(place.name, coordinate: place.coordinate)
            .tag(place.id)
    }
}
```

---

## Search with Autocomplete

Full pattern: completer feeds suggestions, selecting a suggestion triggers a
full search that returns `MKMapItem` results.

```swift
@Observable
final class MapSearchService: NSObject, MKLocalSearchCompleterDelegate {
    var completions: [MKLocalSearchCompletion] = []
    var searchResults: [MKMapItem] = []
    var queryFragment: String = "" {
        didSet { completer.queryFragment = queryFragment }
    }

    private let completer: MKLocalSearchCompleter

    override init() {
        completer = MKLocalSearchCompleter()
        super.init()
        completer.delegate = self
        completer.resultTypes = [.address, .pointOfInterest]
    }

    // Restrict suggestions to the visible map region
    func updateRegion(_ region: MKCoordinateRegion) {
        completer.region = region
    }

    func completerDidUpdateResults(_ completer: MKLocalSearchCompleter) {
        completions = completer.results
    }

    func completer(_ completer: MKLocalSearchCompleter, didFailWithError error: Error) {
        completions = []
    }

    func select(_ completion: MKLocalSearchCompletion) async {
        let request = MKLocalSearch.Request(completion: completion)
        request.resultTypes = [.pointOfInterest, .address]
        do {
            let response = try await MKLocalSearch(request: request).start()
            searchResults = response.mapItems
        } catch {
            searchResults = []
        }
    }
}
```

### Search View Integration

```swift
struct MapSearchView: View {
    @State private var searchService = MapSearchService()
    @State private var searchText = ""
    @State private var position: MapCameraPosition = .automatic

    var body: some View {
        Map(position: $position) {
            ForEach(searchService.searchResults, id: \.self) { item in
                Marker(item: item)
            }
        }
        .searchable(text: $searchText, prompt: "Search places")
        .searchSuggestions {
            ForEach(searchService.completions, id: \.self) { completion in
                Button {
                    Task { await searchService.select(completion) }
                } label: {
                    VStack(alignment: .leading) {
                        Text(completion.title)
                        Text(completion.subtitle)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
            }
        }
        .task(id: searchText) {
            try? await Task.sleep(for: .milliseconds(300))
            guard !Task.isCancelled else { return }
            searchService.queryFragment = searchText
        }
        .onMapCameraChange(frequency: .onEnd) { context in
            searchService.updateRegion(context.region)
        }
    }
}
```

---

## Route Display

Calculate directions and draw the route polyline on the map.

```swift
struct DirectionsMapView: View {
    let source: MKMapItem
    let destination: MKMapItem
    @State private var route: MKRoute?
    @State private var position: MapCameraPosition = .automatic
    @State private var travelTime: String = ""

    var body: some View {
        Map(position: $position) {
            if let route {
                MapPolyline(route.polyline)
                    .stroke(.blue, lineWidth: 6)
            }
            Marker(item: source)
                .tint(.green)
            Marker(item: destination)
                .tint(.red)
        }
        .overlay(alignment: .top) {
            if !travelTime.isEmpty {
                Text(travelTime)
                    .font(.caption)
                    .padding(8)
                    .background(.ultraThinMaterial, in: .capsule)
                    .padding(.top, 8)
            }
        }
        .task { await calculateRoute() }
    }

    private func calculateRoute() async {
        let request = MKDirections.Request()
        request.source = source
        request.destination = destination
        request.transportType = .automobile

        do {
            let response = try await MKDirections(request: request).calculate()
            route = response.routes.first
            if let route {
                let formatter = DateComponentsFormatter()
                formatter.unitsStyle = .abbreviated
                formatter.allowedUnits = [.hour, .minute]
                travelTime = formatter.string(from: route.expectedTravelTime) ?? ""

                withAnimation {
                    position = .rect(route.polyline.boundingMapRect)
                }
            }
        } catch {
            print("Directions error: \(error.localizedDescription)")
        }
    }
}
```

### Multiple Route Options

```swift
request.requestsAlternateRoutes = true
let response = try await MKDirections(request: request).calculate()

// response.routes contains multiple route options
// Display all routes, highlight the selected one:
ForEach(Array(response.routes.enumerated()), id: \.offset) { index, route in
    MapPolyline(route.polyline)
        .stroke(index == 0 ? .blue : .gray.opacity(0.5), lineWidth: index == 0 ? 6 : 3)
}
```

---

## Look Around Preview

Show Apple's street-level imagery for a selected location. Availability
depends on region coverage.

```swift
struct LookAroundView: View {
    let mapItem: MKMapItem
    @State private var scene: MKLookAroundScene?

    var body: some View {
        Group {
            if let scene {
                LookAroundPreview(scene: .constant(scene))
                    .frame(height: 200)
                    .clipShape(.rect(cornerRadius: 12))
            } else {
                ContentUnavailableView("No Look Around",
                    systemImage: "eye.slash",
                    description: Text("Look Around is not available here."))
            }
        }
        .task(id: mapItem) {
            scene = nil
            let request = MKLookAroundSceneRequest(mapItem: mapItem)
            scene = try? await request.scene
        }
    }
}
```

### Look Around overlay on a Map

```swift
Map(selection: $selectedItem) { ... }
    .overlay(alignment: .bottomTrailing) {
        if lookAroundScene != nil {
            LookAroundPreview(scene: $lookAroundScene)
                .frame(width: 200, height: 130)
                .clipShape(.rect(cornerRadius: 10))
                .padding()
        }
    }
    .onChange(of: selectedItem) { _, newItem in
        guard let item = newItem else {
            lookAroundScene = nil
            return
        }
        Task {
            let request = MKLookAroundSceneRequest(mapItem: item)
            lookAroundScene = try? await request.scene
        }
    }
```

---

## Map Snapshots (MKMapSnapshotter)

Generate a static image of a map region. Useful for share sheets, widgets,
notifications, or thumbnails.

```swift
func generateMapSnapshot(center: CLLocationCoordinate2D,
                         size: CGSize = CGSize(width: 300, height: 200)) async throws -> UIImage {
    let options = MKMapSnapshotter.Options()
    options.region = MKCoordinateRegion(
        center: center,
        span: MKCoordinateSpan(latitudeDelta: 0.01, longitudeDelta: 0.01)
    )
    options.size = size
    options.mapType = .standard
    options.showsBuildings = true

    let snapshotter = MKMapSnapshotter(options: options)
    let snapshot = try await snapshotter.start()

    // Draw a pin at the center
    let image = UIGraphicsImageRenderer(size: size).image { context in
        snapshot.image.draw(at: .zero)
        let point = snapshot.point(for: center)
        let pin = UIImage(systemName: "mappin.circle.fill")?
            .withTintColor(.red, renderingMode: .alwaysOriginal)
        pin?.draw(at: CGPoint(x: point.x - 15, y: point.y - 30),
                  blendMode: .normal, alpha: 1.0)
    }
    return image
}
```

---

## Clustering Annotations

MapKit clusters `Marker` views automatically when they overlap. Control the
clustering priority and displayed count.

```swift
Map {
    ForEach(allStores) { store in
        Marker(store.name, systemImage: "cart", coordinate: store.coordinate)
            .annotationTitles(.hidden)  // Hide titles at low zoom
    }
}
.mapStyle(.standard(pointsOfInterest: .excludingAll))
```

For custom clustering behavior with `MKMapView` (UIKit interop), set
`clusteringIdentifier` on `MKMarkerAnnotationView`. The SwiftUI `Map`
handles basic clustering automatically.

---

## MapKit with MKMapItem Utilities

### Open in Apple Maps

```swift
let item = MKMapItem(placemark: MKPlacemark(coordinate: coordinate))
item.name = "Destination"
item.openInMaps(launchOptions: [
    MKLaunchOptionsDirectionsModeKey: MKLaunchOptionsDirectionsModeDriving
])
```

### Distance Calculation

```swift
func distanceBetween(_ a: CLLocationCoordinate2D,
                     _ b: CLLocationCoordinate2D) -> CLLocationDistance {
    let locA = CLLocation(latitude: a.latitude, longitude: a.longitude)
    let locB = CLLocation(latitude: b.latitude, longitude: b.longitude)
    return locA.distance(from: locB) // meters
}
```

### Format Distance for Display

```swift
let formatter = MKDistanceFormatter()
formatter.unitStyle = .abbreviated
let text = formatter.string(fromDistance: 1500) // "0.9 mi" or "1.5 km"
```

---

## iOS 26 New APIs

### MKGeocodingRequest

Convert an address string to map items with richer data than `CLGeocoder`:

```swift
@available(iOS 26, *)
func geocodeAddresses(_ addresses: [String]) async -> [MKMapItem] {
    var items: [MKMapItem] = []
    for address in addresses {
        let request = MKGeocodingRequest(address: address)
        if let mapItems = try? await request.mapItems {
            items.append(contentsOf: mapItems)
        }
    }
    return items
}
```

### MKReverseGeocodingRequest

Convert coordinates to map items with `MKAddress`:

```swift
@available(iOS 26, *)
func reverseGeocode(_ coordinate: CLLocationCoordinate2D) async -> MKAddress? {
    let location = CLLocation(latitude: coordinate.latitude,
                              longitude: coordinate.longitude)
    guard let request = MKReverseGeocodingRequest(location: location) else {
        return nil
    }
    let mapItems = try? await request.mapItems
    return mapItems?.first?.address
}
```

### MKAddress and MKAddressRepresentations

`MKAddress` provides structured address components. Use
`MKAddressRepresentations` to format addresses for different contexts:

```swift
@available(iOS 26, *)
func formatAddress(_ address: MKAddress) -> String {
    // Use address representations for locale-aware formatting
    return address.representations.fullAddress()
}
```

### PlaceDescriptor (via GeoToolbox)

Create place references from coordinates when you do not have a Place ID:

```swift
@available(iOS 26, *)
import GeoToolbox

let descriptor = PlaceDescriptor(
    representations: [.coordinate(myCoordinate)],
    commonName: "My Favorite Cafe"
)

let request = MKMapItemRequest(placeDescriptor: descriptor)
let mapItem = try await request.mapItem

// Use mapItem with any MapKit API: Marker(item:), directions, place cards
```

### Cycling Directions

```swift
@available(iOS 26, *)
func cyclingRoute(to destination: MKMapItem) async throws -> MKRoute? {
    let request = MKDirections.Request()
    request.source = .forCurrentLocation()
    request.destination = destination
    request.transportType = .cycling
    let response = try await MKDirections(request: request).calculate()
    return response.routes.first
}
```

---

## User Location Display

Show the user's position with the built-in blue dot:

```swift
Map(position: $position) {
    UserAnnotation()       // Blue dot with accuracy ring
    // ... other content
}
.mapControls {
    MapUserLocationButton()  // Button to re-center on user
}
```

`UserAnnotation()` requires location authorization. If authorization is
denied, the annotation does not appear and no error is thrown.

---

## Map in a List or ScrollView

When embedding a `Map` inside a `ScrollView`, disable map gestures that
conflict with scrolling:

```swift
ScrollView {
    Map(position: $position, interactionModes: []) {
        Marker("Location", coordinate: coord)
    }
    .frame(height: 200)
    .clipShape(.rect(cornerRadius: 12))

    Text("Details below the map...")
}
```

Use `interactionModes: []` for a fully static map thumbnail or
`interactionModes: [.zoom]` to allow pinch-to-zoom without pan conflicts.

---

## Coordinate Utilities

### Region from an array of coordinates

```swift
func regionForCoordinates(_ coords: [CLLocationCoordinate2D]) -> MKCoordinateRegion {
    guard !coords.isEmpty else {
        return MKCoordinateRegion()
    }
    var minLat = coords[0].latitude
    var maxLat = coords[0].latitude
    var minLon = coords[0].longitude
    var maxLon = coords[0].longitude

    for coord in coords {
        minLat = min(minLat, coord.latitude)
        maxLat = max(maxLat, coord.latitude)
        minLon = min(minLon, coord.longitude)
        maxLon = max(maxLon, coord.longitude)
    }

    let center = CLLocationCoordinate2D(
        latitude: (minLat + maxLat) / 2,
        longitude: (minLon + maxLon) / 2
    )
    let span = MKCoordinateSpan(
        latitudeDelta: (maxLat - minLat) * 1.3,  // 30% padding
        longitudeDelta: (maxLon - minLon) * 1.3
    )
    return MKCoordinateRegion(center: center, span: span)
}
```

### CLLocationCoordinate2D Equatable conformance

`CLLocationCoordinate2D` does not conform to `Equatable` by default.
Extend it when needed for comparisons:

```swift
extension CLLocationCoordinate2D: @retroactive Equatable {
    public static func == (lhs: Self, rhs: Self) -> Bool {
        lhs.latitude == rhs.latitude && lhs.longitude == rhs.longitude
    }
}
```

Note: Use `@retroactive` (Swift 5.10+) to silence the warning about
conforming types from other modules.

---

## Accessibility

### Marker accessibility

`Marker` views include built-in VoiceOver support using the title string.
Add `.accessibilityLabel` for richer descriptions:

```swift
Marker(store.name, coordinate: store.coordinate)
    .accessibilityLabel("\(store.name), \(store.distanceText) away")
```

### Map accessibility

Add a concise description of the map purpose:

```swift
Map { ... }
    .accessibilityElement()
    .accessibilityLabel("Store locations map showing \(stores.count) stores")
```

---

## References

- Apple docs: [MapKit for SwiftUI](https://sosumi.ai/documentation/MapKit/MapKit-for-SwiftUI)
- Apple docs: [Map](https://sosumi.ai/documentation/MapKit/Map)
- Apple docs: [MapCameraPosition](https://sosumi.ai/documentation/MapKit/MapCameraPosition)
- Apple docs: [MKLocalSearch](https://sosumi.ai/documentation/MapKit/MKLocalSearch)
- Apple docs: [MKDirections](https://sosumi.ai/documentation/MapKit/MKDirections)
- Apple docs: [MKLookAroundScene](https://sosumi.ai/documentation/MapKit/MKLookAroundScene)
