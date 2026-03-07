# SwiftData Queries Reference

Deep reference for all @Query initializer variants, FetchDescriptor options,
sort descriptors, sectioned queries, dynamic query switching, background fetch
patterns, and aggregate queries.

---

## @Query Initializer Variants

`@Query` is a SwiftUI property wrapper (`DynamicProperty`) that automatically
fetches and observes persistent model data. All variants are `@MainActor`.

### Basic (No Filter, No Sort)

```swift
// Fetch all, default order
@Query private var trips: [Trip]

// With animation
@Query(animation: .default) private var trips: [Trip]

// With transaction
@Query(transaction: Transaction(animation: .spring)) private var trips: [Trip]
```

### Filter + SortDescriptor Array

```swift
@Query(
    filter: #Predicate<Trip> { $0.isFavorite == true },
    sort: [SortDescriptor(\.startDate, order: .reverse)]
)
private var favoriteTrips: [Trip]

// With animation
@Query(
    filter: #Predicate<Trip> { $0.isFavorite == true },
    sort: [SortDescriptor(\.startDate, order: .reverse)],
    animation: .default
)
private var favoriteTrips: [Trip]
```

### Filter + KeyPath Sort

```swift
@Query(
    filter: #Predicate<Trip> { $0.destination != "" },
    sort: \.startDate,
    order: .forward
)
private var upcomingTrips: [Trip]

// With optional key path sort
@Query(
    sort: \.endDate,  // KeyPath<Trip, Date?> -- optional sort key
    order: .reverse
)
private var tripsByEndDate: [Trip]
```

### FetchDescriptor

```swift
static var recentDescriptor: FetchDescriptor<Trip> {
    var d = FetchDescriptor<Trip>(
        predicate: #Predicate { $0.startDate > Date.now },
        sortBy: [SortDescriptor(\.startDate)]
    )
    d.fetchLimit = 10
    return d
}

@Query(RecentTripsView.recentDescriptor) private var recentTrips: [Trip]

// With animation
@Query(RecentTripsView.recentDescriptor, animation: .default)
private var recentTrips: [Trip]
```

### Query Properties

| Property | Type | Description |
|----------|------|-------------|
| `wrappedValue` | `Result` (typically `[Element]`) | Most recent fetched results |
| `modelContext` | `ModelContext` | The context used for fetching |
| `fetchError` | `(any Error)?` | Error from most recent fetch, if any |

Access `fetchError` to detect query failures:

```swift
struct TripListView: View {
    @Query private var trips: [Trip]

    var body: some View {
        Group {
            if let error = $trips.fetchError {
                ContentUnavailableView("Fetch Error",
                    systemImage: "exclamationmark.triangle",
                    description: Text(error.localizedDescription))
            } else {
                List(trips) { trip in
                    Text(trip.name)
                }
            }
        }
    }
}
```

---

## FetchDescriptor Deep Dive

### Full Property Reference

```swift
var descriptor = FetchDescriptor<Trip>()
```

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `predicate` | `Predicate<T>?` | `nil` | Filter condition |
| `sortBy` | `[SortDescriptor<T>]` | `[]` | Sort order |
| `fetchLimit` | `Int?` | `nil` | Maximum results |
| `fetchOffset` | `Int?` | `nil` | Skip first N results |
| `includePendingChanges` | `Bool` | `true` | Include unsaved in-memory changes |
| `propertiesToFetch` | `[PartialKeyPath<T>]` | all | Specific properties to load |
| `relationshipKeyPathsForPrefetching` | `[PartialKeyPath<T>]` | `[]` | Related models to eagerly load |

### fetchLimit and fetchOffset (Pagination)

```swift
func fetchPage(page: Int, pageSize: Int) throws -> [Trip] {
    var descriptor = FetchDescriptor<Trip>(
        sortBy: [SortDescriptor(\.startDate)]
    )
    descriptor.fetchLimit = pageSize
    descriptor.fetchOffset = page * pageSize
    return try modelContext.fetch(descriptor)
}
```

### includePendingChanges

When `true` (default), the fetch includes objects inserted or modified in the
current context but not yet saved. Set to `false` for read-only queries against
the persisted store only.

```swift
var descriptor = FetchDescriptor<Trip>()
descriptor.includePendingChanges = false  // Only persisted data
```

Note: `includePendingChanges: true` cannot be used with batched fetches
(`fetch(_:batchSize:)`). This will throw
`SwiftDataError.includePendingChangesWithBatchSize`.

### propertiesToFetch (Partial Loading)

Load only specific attributes to reduce memory footprint:

```swift
var descriptor = FetchDescriptor<Trip>()
descriptor.propertiesToFetch = [\.name, \.destination, \.startDate]
let trips = try modelContext.fetch(descriptor)
// Only name, destination, startDate are loaded; other properties fault on access
```

### relationshipKeyPathsForPrefetching

Eagerly load related objects to avoid N+1 query patterns:

```swift
var descriptor = FetchDescriptor<Trip>()
descriptor.relationshipKeyPathsForPrefetching = [
    \.accommodation,
    \.tags
]
let trips = try modelContext.fetch(descriptor)
// Accessing trip.accommodation does not trigger a separate fetch
```

### Fetch Variants on ModelContext

| Method | Returns | Use Case |
|--------|---------|----------|
| `fetch(_:)` | `[T]` | Standard fetch, all results in memory |
| `fetch(_:batchSize:)` | `FetchResultsCollection<T>` | Lazy batched loading |
| `fetchCount(_:)` | `Int` | Count only, no objects loaded |
| `fetchIdentifiers(_:)` | `[PersistentIdentifier]` | IDs only, lightweight |
| `fetchIdentifiers(_:batchSize:)` | `FetchResultsCollection<PersistentIdentifier>` | Batched ID loading |
| `enumerate(_:batchSize:...)` | `Void` | Process large sets in batches |

### FetchResultsCollection (Batched Fetch)

```swift
let results: FetchResultsCollection<Trip> = try modelContext.fetch(
    FetchDescriptor<Trip>(sortBy: [SortDescriptor(\.name)]),
    batchSize: 100
)

// Iterate lazily -- only 100 objects in memory at a time
for trip in results {
    print(trip.name)
}
```

Requirements for batched fetch:
- `includePendingChanges` must be `false` (or will throw).
- Results are read-only snapshots.

---

## Complex Sort Descriptors

### Single Sort

```swift
SortDescriptor(\.name, order: .forward)    // A-Z
SortDescriptor(\.name, order: .reverse)    // Z-A
SortDescriptor(\.startDate)                // Ascending (default)
```

### Multi-Level Sort

```swift
let descriptor = FetchDescriptor<Trip>(
    sortBy: [
        SortDescriptor(\.isFavorite, order: .reverse),  // Favorites first
        SortDescriptor(\.startDate, order: .forward),    // Then by date
        SortDescriptor(\.name, order: .forward)          // Then alphabetical
    ]
)
```

### Optional Key Path Sort

Sort on optional properties -- nil values sort to the end:

```swift
@Query(sort: \.endDate, order: .reverse) private var trips: [Trip]
// endDate is Date? -- trips without endDate appear last
```

### Dynamic Sort Switching

```swift
struct TripListView: View {
    @State private var sortOrder: SortOrder = .forward
    @State private var sortKey: TripSortKey = .name

    var body: some View {
        SortedTripList(sortKey: sortKey, sortOrder: sortOrder)
            .toolbar {
                Picker("Sort", selection: $sortKey) {
                    Text("Name").tag(TripSortKey.name)
                    Text("Date").tag(TripSortKey.date)
                    Text("Destination").tag(TripSortKey.destination)
                }
            }
    }
}

enum TripSortKey: String, CaseIterable {
    case name, date, destination
}

struct SortedTripList: View {
    @Query private var trips: [Trip]

    init(sortKey: TripSortKey, sortOrder: SortOrder) {
        let sortDescriptor: SortDescriptor<Trip> = switch sortKey {
        case .name: SortDescriptor(\.name, order: sortOrder)
        case .date: SortDescriptor(\.startDate, order: sortOrder)
        case .destination: SortDescriptor(\.destination, order: sortOrder)
        }
        _trips = Query(sort: [sortDescriptor])
    }

    var body: some View {
        List(trips) { trip in
            TripRow(trip: trip)
        }
    }
}
```

---

## Sectioned Queries Pattern

SwiftData does not provide a built-in sectioned query like Core Data's
`NSFetchedResultsController`. Build sectioned views manually:

### Using Dictionary Grouping

```swift
struct SectionedTripListView: View {
    @Query(sort: \.startDate) private var trips: [Trip]

    private var sections: [(String, [Trip])] {
        let formatter = DateFormatter()
        formatter.dateFormat = "MMMM yyyy"
        let grouped = Dictionary(grouping: trips) { trip in
            formatter.string(from: trip.startDate)
        }
        return grouped.sorted { $0.key < $1.key }
    }

    var body: some View {
        List {
            ForEach(sections, id: \.0) { section, trips in
                Section(section) {
                    ForEach(trips) { trip in
                        TripRow(trip: trip)
                    }
                }
            }
        }
    }
}
```

### Using Enum-Based Sections

```swift
enum TripStatus: String, CaseIterable {
    case upcoming = "Upcoming"
    case current = "Current"
    case past = "Past"
}

struct StatusSectionedView: View {
    @Query(sort: \.startDate) private var trips: [Trip]

    private func trips(for status: TripStatus) -> [Trip] {
        let now = Date.now
        return trips.filter { trip in
            switch status {
            case .upcoming: trip.startDate > now
            case .current: trip.startDate <= now && trip.endDate >= now
            case .past: trip.endDate < now
            }
        }
    }

    var body: some View {
        List {
            ForEach(TripStatus.allCases, id: \.self) { status in
                let sectionTrips = trips(for: status)
                if !sectionTrips.isEmpty {
                    Section(status.rawValue) {
                        ForEach(sectionTrips) { trip in
                            TripRow(trip: trip)
                        }
                    }
                }
            }
        }
    }
}
```

---

## Dynamic Query Switching

### Filter + Sort Controlled by Parent

```swift
struct TripBrowserView: View {
    @State private var searchText = ""
    @State private var showFavoritesOnly = false

    var body: some View {
        NavigationStack {
            FilteredTripList(
                searchText: searchText,
                favoritesOnly: showFavoritesOnly
            )
            .searchable(text: $searchText)
            .toolbar {
                Toggle("Favorites", isOn: $showFavoritesOnly)
            }
        }
    }
}

struct FilteredTripList: View {
    @Query private var trips: [Trip]

    init(searchText: String, favoritesOnly: Bool) {
        let predicate = #Predicate<Trip> { trip in
            (searchText.isEmpty || trip.name.localizedStandardContains(searchText))
            && (!favoritesOnly || trip.isFavorite == true)
        }
        _trips = Query(
            filter: predicate,
            sort: [SortDescriptor(\.startDate, order: .reverse)]
        )
    }

    var body: some View {
        List(trips) { trip in
            NavigationLink(trip.name) {
                TripDetailView(trip: trip)
            }
        }
    }
}
```

### Full Dynamic Descriptor

```swift
struct AdvancedTripList: View {
    @Query private var trips: [Trip]

    init(
        destination: String?,
        minDate: Date?,
        sortKey: KeyPath<Trip, some Comparable>,
        ascending: Bool,
        limit: Int?
    ) {
        var descriptor = FetchDescriptor<Trip>(
            sortBy: [SortDescriptor(\.startDate, order: ascending ? .forward : .reverse)]
        )

        if let destination {
            descriptor.predicate = #Predicate<Trip> { trip in
                trip.destination == destination
            }
        }

        if let limit {
            descriptor.fetchLimit = limit
        }

        _trips = Query(descriptor)
    }

    var body: some View {
        List(trips) { trip in
            TripRow(trip: trip)
        }
    }
}
```

---

## Background Fetch Patterns with @ModelActor

### Basic Background Fetch

```swift
@ModelActor
actor TripDataHandler {
    func fetchUpcomingTrips() throws -> [PersistentIdentifier] {
        let descriptor = FetchDescriptor<Trip>(
            predicate: #Predicate { $0.startDate > Date.now },
            sortBy: [SortDescriptor(\.startDate)]
        )
        return try modelContext.fetchIdentifiers(descriptor)
    }

    func fetchTripCount(destination: String) throws -> Int {
        let descriptor = FetchDescriptor<Trip>(
            predicate: #Predicate<Trip> { trip in
                trip.destination == destination
            }
        )
        return try modelContext.fetchCount(descriptor)
    }
}

// Usage from SwiftUI view
struct TripDashboardView: View {
    @Environment(\.modelContext) private var modelContext
    @State private var upcomingCount = 0

    var body: some View {
        Text("Upcoming: \(upcomingCount)")
            .task {
                let handler = TripDataHandler(
                    modelContainer: modelContext.container
                )
                upcomingCount = (try? await handler.fetchTripCount(
                    destination: "Paris"
                )) ?? 0
            }
    }
}
```

### Background Import with Progress

```swift
@ModelActor
actor ImportHandler {
    func importTrips(
        _ records: [TripRecord],
        progress: @Sendable (Int) -> Void
    ) throws -> Int {
        var imported = 0
        for (index, record) in records.enumerated() {
            let trip = Trip(
                name: record.name,
                destination: record.destination,
                startDate: record.startDate,
                endDate: record.endDate
            )
            modelContext.insert(trip)
            imported += 1

            // Save periodically to flush memory
            if index % 500 == 0 {
                try modelContext.save()
                progress(imported)
            }
        }
        try modelContext.save()
        return imported
    }
}
```

### Resolving Identifiers on MainActor

```swift
@ModelActor
actor DataHandler {
    func findDuplicateIDs() throws -> [PersistentIdentifier] {
        // Complex logic to find duplicates
        let all = try modelContext.fetch(FetchDescriptor<Trip>())
        var seen = Set<String>()
        var duplicateIDs: [PersistentIdentifier] = []
        for trip in all {
            if seen.contains(trip.name) {
                duplicateIDs.append(trip.persistentModelID)
            }
            seen.insert(trip.name)
        }
        return duplicateIDs
    }
}

// On MainActor, resolve IDs to objects
struct DuplicateReviewView: View {
    @Environment(\.modelContext) private var modelContext
    @State private var duplicates: [Trip] = []

    var body: some View {
        List(duplicates) { trip in
            Text(trip.name)
        }
        .task {
            let handler = DataHandler(modelContainer: modelContext.container)
            let ids = (try? await handler.findDuplicateIDs()) ?? []
            duplicates = ids.compactMap { id in
                modelContext.registeredModel(for: id) as Trip?
                    ?? (try? modelContext.model(for: id) as? Trip)
            }
        }
    }
}
```

---

## Aggregate Queries

SwiftData does not provide built-in aggregate functions (SUM, AVG, etc.).
Compute aggregates using fetch + Swift computation.

### Count

```swift
let count = try modelContext.fetchCount(
    FetchDescriptor<Trip>(predicate: #Predicate { $0.isFavorite == true })
)
```

### Sum, Average, Min, Max

```swift
let trips = try modelContext.fetch(FetchDescriptor<Trip>())

let totalBudget = trips.reduce(0.0) { $0 + $1.budget }
let averageBudget = trips.isEmpty ? 0 : totalBudget / Double(trips.count)
let maxBudget = trips.map(\.budget).max() ?? 0
let minBudget = trips.map(\.budget).min() ?? 0
```

### Efficient Aggregates with Partial Fetch

Fetch only the property needed for aggregation:

```swift
var descriptor = FetchDescriptor<Trip>()
descriptor.propertiesToFetch = [\.budget]
let trips = try modelContext.fetch(descriptor)
let total = trips.reduce(0.0) { $0 + $1.budget }
```

### Background Aggregate Computation

```swift
@ModelActor
actor StatsHandler {
    struct TripStats: Sendable {
        let totalCount: Int
        let favoriteCount: Int
        let averageDuration: TimeInterval
    }

    func computeStats() throws -> TripStats {
        let allTrips = try modelContext.fetch(FetchDescriptor<Trip>())
        let favoriteCount = try modelContext.fetchCount(
            FetchDescriptor<Trip>(predicate: #Predicate { $0.isFavorite == true })
        )

        let totalDuration = allTrips.reduce(0.0) { sum, trip in
            sum + trip.endDate.timeIntervalSince(trip.startDate)
        }
        let avgDuration = allTrips.isEmpty ? 0 : totalDuration / Double(allTrips.count)

        return TripStats(
            totalCount: allTrips.count,
            favoriteCount: favoriteCount,
            averageDuration: avgDuration
        )
    }
}
```

---

## Enumerate for Large Datasets

Use `enumerate` instead of `fetch` when processing many records to keep memory
usage constant:

```swift
// Process all trips without loading all into memory
try modelContext.enumerate(
    FetchDescriptor<Trip>(sortBy: [SortDescriptor(\.startDate)]),
    batchSize: 1000,
    allowEscapingMutations: false
) { trip in
    // Process each trip
    trip.isProcessed = true
}
try modelContext.save()
```

Parameters:
- `batchSize`: Objects per batch (default 5000). Lower values use less memory.
- `allowEscapingMutations`: When `false`, objects are autoreleased after the
  block. Set to `true` only if mutations must persist beyond the block.

