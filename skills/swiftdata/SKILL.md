---
name: swiftdata
description: "Implement, review, or improve data persistence using SwiftData. Use when defining @Model classes with @Attribute, @Relationship, @Transient, @Unique, or @Index; when querying with @Query, #Predicate, FetchDescriptor, or SortDescriptor; when configuring ModelContainer and ModelContext for SwiftUI or background work with @ModelActor; when planning schema migrations with VersionedSchema and SchemaMigrationPlan; when setting up CloudKit sync with ModelConfiguration; or when coexisting with or migrating from Core Data."
---

# SwiftData

Persist, query, and manage structured data in iOS 26+ apps using SwiftData
with Swift 6.2.

## Model Definition

Apply `@Model` to a **class** (not struct). Generates `PersistentModel`, `Observable`, `Sendable`.

```swift
@Model
class Trip {
    var name: String
    var destination: String
    var startDate: Date
    var endDate: Date
    var isFavorite: Bool = false
    @Attribute(.externalStorage) var imageData: Data?
    @Relationship(deleteRule: .cascade, inverse: \LivingAccommodation.trip)
    var accommodation: LivingAccommodation?
    @Transient var isSelected: Bool = false  // Always provide default

    init(name: String, destination: String, startDate: Date, endDate: Date) {
        self.name = name; self.destination = destination
        self.startDate = startDate; self.endDate = endDate
    }
}
```

**@Attribute options**: `.externalStorage`, `.unique`, `.spotlight`, `.allowsCloudEncryption`, `.preserveValueOnDeletion` (iOS 18+), `.ephemeral`, `.transformable(by:)`. Rename: `@Attribute(originalName: "old_name")`.

**@Relationship**: `deleteRule:` `.cascade`/`.nullify`(default)/`.deny`/`.noAction`. Specify `inverse:` for reliable behavior. Unidirectional (iOS 18+): `inverse: nil`.

**#Unique (iOS 18+)**: `#Unique<Person>([\.firstName, \.lastName])` -- compound uniqueness.

**#Index (iOS 18+)**: `#Index<Trip>([\.name], [\.startDate, \.endDate])` -- query indexes.

**Inheritance (iOS 26+)**: `@Model class BusinessTrip: Trip { var company: String }`.

Supported types: `Bool`, `Int`/`UInt` variants, `Float`, `Double`, `String`, `Date`, `Data`, `URL`, `UUID`, `Decimal`, `Array`, `Dictionary`, `Set`, `Codable` enums, `Codable` structs (composite, iOS 18+), relationships to `@Model` classes.

## ModelContainer Setup

```swift
// Basic
let container = try ModelContainer(for: Trip.self, LivingAccommodation.self)

// Configured
let config = ModelConfiguration("Store", isStoredInMemoryOnly: false,
    groupContainer: .identifier("group.com.example.app"),
    cloudKitDatabase: .private("iCloud.com.example.app"))
let container = try ModelContainer(for: Trip.self, configurations: config)

// With migration plan
let container = try ModelContainer(for: SchemaV2.Trip.self,
    migrationPlan: TripMigrationPlan.self)

// In-memory (previews/tests)
let container = try ModelContainer(for: Trip.self,
    configurations: ModelConfiguration(isStoredInMemoryOnly: true))
```

## CRUD Operations

```swift
// CREATE
let trip = Trip(name: "Summer", destination: "Paris", startDate: .now, endDate: .now + 86400*7)
modelContext.insert(trip)
try modelContext.save()  // or rely on autosave

// READ
let trips = try modelContext.fetch(FetchDescriptor<Trip>(
    predicate: #Predicate { $0.destination == "Paris" },
    sortBy: [SortDescriptor(\.startDate)]))

// UPDATE -- modify properties directly; autosave handles persistence
trip.destination = "Rome"

// DELETE
modelContext.delete(trip)
try modelContext.delete(model: Trip.self, where: #Predicate { $0.isFavorite == false })

// TRANSACTION (atomic)
try modelContext.transaction {
    modelContext.insert(trip); trip.isFavorite = true
}
```

## @Query in SwiftUI

```swift
struct TripListView: View {
    @Query(filter: #Predicate<Trip> { $0.isFavorite == true },
           sort: \.startDate, order: .reverse)
    private var favorites: [Trip]

    var body: some View { List(favorites) { trip in Text(trip.name) } }
}

// Dynamic query via init
struct SearchView: View {
    @Query private var trips: [Trip]
    init(search: String) {
        _trips = Query(filter: #Predicate<Trip> { trip in
            search.isEmpty || trip.name.localizedStandardContains(search)
        }, sort: [SortDescriptor(\.name)])
    }
    var body: some View { List(trips) { trip in Text(trip.name) } }
}

// FetchDescriptor query
struct RecentView: View {
    static var desc: FetchDescriptor<Trip> {
        var d = FetchDescriptor<Trip>(sortBy: [SortDescriptor(\.startDate)])
        d.fetchLimit = 5; return d
    }
    @Query(RecentView.desc) private var recent: [Trip]
    var body: some View { List(recent) { trip in Text(trip.name) } }
}
```

## #Predicate

```swift
#Predicate<Trip> { $0.destination.localizedStandardContains("paris") }  // String
#Predicate<Trip> { $0.startDate > Date.now }                            // Date
#Predicate<Trip> { $0.isFavorite && $0.destination != "Unknown" }       // Compound
#Predicate<Trip> { $0.accommodation?.name != nil }                      // Optional
#Predicate<Trip> { $0.tags.contains { $0.name == "adventure" } }        // Collection
```

Supported: `==`, `!=`, `<`, `<=`, `>`, `>=`, `&&`, `||`, `!`, `contains()`, `allSatisfy()`, `filter()`, `starts(with:)`, `localizedStandardContains()`, `caseInsensitiveCompare()`, arithmetic, ternary, optional chaining, nil coalescing, type casting. **Not supported**: flow control, nested declarations, arbitrary method calls.

## FetchDescriptor

```swift
var d = FetchDescriptor<Trip>(predicate: ..., sortBy: [...])
d.fetchLimit = 20; d.fetchOffset = 0
d.includePendingChanges = true
d.propertiesToFetch = [\.name, \.startDate]
d.relationshipKeyPathsForPrefetching = [\.accommodation]
let trips = try modelContext.fetch(d)
let count = try modelContext.fetchCount(d)
let ids = try modelContext.fetchIdentifiers(d)
try modelContext.enumerate(d, batchSize: 1000) { trip in trip.isProcessed = true }
```

## Schema Versioning and Migration

```swift
enum SchemaV1: VersionedSchema {
    static var versionIdentifier = Schema.Version(1, 0, 0)
    static var models: [any PersistentModel.Type] { [Trip.self] }
    @Model class Trip { var name: String; init(name: String) { self.name = name } }
}

enum SchemaV2: VersionedSchema {
    static var versionIdentifier = Schema.Version(2, 0, 0)
    static var models: [any PersistentModel.Type] { [Trip.self] }
    @Model class Trip {
        var name: String; var startDate: Date?  // New property
        init(name: String) { self.name = name }
    }
}

enum TripMigrationPlan: SchemaMigrationPlan {
    static var schemas: [any VersionedSchema.Type] { [SchemaV1.self, SchemaV2.self] }
    static var stages: [MigrationStage] { [migrateV1toV2] }
    static let migrateV1toV2 = MigrationStage.lightweight(
        fromVersion: SchemaV1.self, toVersion: SchemaV2.self)
}

// Custom migration for data transformation
static let migrateV2toV3 = MigrationStage.custom(
    fromVersion: SchemaV2.self, toVersion: SchemaV3.self,
    willMigrate: nil,
    didMigrate: { context in
        let trips = try context.fetch(FetchDescriptor<SchemaV3.Trip>())
        for trip in trips { trip.displayName = trip.name.capitalized }
        try context.save()
    })
```

Lightweight handles: adding optional/defaulted properties, renaming (`originalName`), removing properties, adding model types.

## Concurrency (@ModelActor)

```swift
@ModelActor
actor DataHandler {
    func importTrips(_ records: [TripRecord]) throws {
        for r in records {
            modelContext.insert(Trip(name: r.name, destination: r.dest,
                                    startDate: r.start, endDate: r.end))
        }
        try modelContext.save()  // Always save explicitly in @ModelActor
    }

    func process(tripID: PersistentIdentifier) throws {
        guard let trip = self[tripID, as: Trip.self] else { return }
        trip.isProcessed = true; try modelContext.save()
    }
}

let handler = DataHandler(modelContainer: container)
try await handler.importTrips(records)
```

**Rules**: `ModelContainer` is `Sendable`. `ModelContext` is NOT -- use on its creating actor. Pass `PersistentIdentifier` (Sendable) across boundaries. Never pass `@Model` objects across actors.

## SwiftUI Integration

```swift
@main
struct MyApp: App {
    var body: some Scene {
        WindowGroup { ContentView() }
            .modelContainer(for: [Trip.self, LivingAccommodation.self])
    }
}

struct DetailView: View {
    @Environment(\.modelContext) private var modelContext
    let trip: Trip
    var body: some View {
        Text(trip.name)
        Button("Delete") { modelContext.delete(trip) }
    }
}

#Preview {
    let config = ModelConfiguration(isStoredInMemoryOnly: true)
    let container = try! ModelContainer(for: Trip.self, configurations: config)
    container.mainContext.insert(Trip(name: "Preview", destination: "London",
        startDate: .now, endDate: .now + 86400))
    return TripListView().modelContainer(container)
}
```

## Common Mistakes

**1. @Model on struct** -- Use class. `@Model` requires reference semantics.

**2. @Transient without default** -- Always provide default: `@Transient var x: Bool = false`.

**3. Missing .modelContainer** -- @Query returns empty without a container on the view hierarchy.

**4. Passing model objects across actors:**
```swift
// WRONG: await handler.process(trip: trip)
// CORRECT: await handler.process(tripID: trip.persistentModelID)
```

**5. ModelContext on wrong actor:**
```swift
// WRONG: Task.detached { context.fetch(...) }
// CORRECT: Use @ModelActor for background work
```

**6. Unsupported #Predicate expressions:**
```swift
// WRONG: #Predicate<Trip> { $0.name.uppercased() == "PARIS" }
// CORRECT: #Predicate<Trip> { $0.name.localizedStandardContains("paris") }
```

**7. Flow control in #Predicate:**
```swift
// WRONG: #Predicate<Trip> { for tag in $0.tags { ... } }
// CORRECT: #Predicate<Trip> { $0.tags.contains { $0.name == "x" } }
```

**8. No save in @ModelActor** -- Always call `try modelContext.save()` explicitly.

**9. ObservableObject with @Model** -- Never use `ObservableObject`/`@Published`. `@Model` generates `Observable`. Use `@Query` in views.

**10. Non-optional relationship without default:**
```swift
// WRONG: var accommodation: LivingAccommodation  // crashes on reconstitution
// CORRECT: var accommodation: LivingAccommodation?
```

**11. Cascade without inverse** -- Specify `inverse:` for reliable cascade delete behavior.

**12. DispatchQueue for background data work:**
```swift
// WRONG: DispatchQueue.global().async { ModelContext(container).fetch(...) }
// CORRECT: @ModelActor actor Handler { func fetch() throws { ... } }
```

## Review Checklist

- [ ] Every `@Model` is a class with a designated initializer
- [ ] All `@Transient` properties have default values
- [ ] Relationships specify `deleteRule` and `inverse`
- [ ] `.modelContainer` attached at scene/root view level
- [ ] `@Query` used for reactive data display in SwiftUI
- [ ] `#Predicate` uses only supported operators
- [ ] Background work uses `@ModelActor`
- [ ] `PersistentIdentifier` used across actor boundaries
- [ ] Schema changes have `VersionedSchema` + `SchemaMigrationPlan`
- [ ] Large data uses `@Attribute(.externalStorage)`
- [ ] CloudKit models use optionals and avoid unique constraints
- [ ] Explicit `save()` in `@ModelActor` methods
- [ ] `#Index` on frequently queried properties (iOS 18+)
- [ ] Previews use `ModelConfiguration(isStoredInMemoryOnly: true)`
- [ ] `@Model` classes accessed from SwiftUI views are on `@MainActor` via `@ModelActor` or MainActor isolation

## Reference Material

- See `references/swiftdata-advanced.md` for custom data stores, history
  tracking, CloudKit, Core Data coexistence, composite attributes,
  model inheritance, undo/redo, and performance patterns.
- See `references/swiftdata-queries.md` for @Query variants, FetchDescriptor
  deep dive, sectioned queries, dynamic queries, and background fetch patterns.

