# SwiftData Advanced Reference

Deep reference for custom data stores, history tracking, CloudKit integration,
Core Data coexistence, batch operations, complex predicates, composite
attributes, model inheritance, multiple containers, undo/redo, and preview
patterns.

---

## Custom Data Stores (iOS 18+)

### DataStore Protocol

Implement the `DataStore` protocol to replace the default SQLite-backed store
with a custom persistence backend (JSON files, in-memory caches, REST APIs,
etc.).

```swift
final class JSONStore: DataStore {
    typealias Configuration = JSONStoreConfiguration
    typealias Snapshot = DefaultSnapshot

    let configuration: JSONStoreConfiguration
    let identifier: String
    let schema: Schema

    init(_ configuration: JSONStoreConfiguration,
         migrationPlan: (any SchemaMigrationPlan.Type)?) throws {
        self.configuration = configuration
        self.identifier = configuration.name
        self.schema = configuration.schema ?? Schema()
    }

    func fetch<T: PersistentModel>(
        _ request: DataStoreFetchRequest<T>
    ) throws -> DataStoreFetchResult<T, DefaultSnapshot> {
        // Load data from JSON file, apply predicate/sort from request.descriptor
        let snapshots: [DefaultSnapshot] = []  // Populate from file
        return DataStoreFetchResult(
            descriptor: request.descriptor,
            fetchedSnapshots: snapshots,
            relatedSnapshots: [:]
        )
    }

    func fetchCount<T: PersistentModel>(
        _ request: DataStoreFetchRequest<T>
    ) throws -> Int {
        try fetch(request).fetchedSnapshots.count
    }

    func fetchIdentifiers<T: PersistentModel>(
        _ request: DataStoreFetchRequest<T>
    ) throws -> [PersistentIdentifier] {
        try fetch(request).fetchedSnapshots.map(\.persistentIdentifier)
    }

    func save(
        _ request: DataStoreSaveChangesRequest<DefaultSnapshot>
    ) throws -> DataStoreSaveChangesResult<DefaultSnapshot> {
        // Persist inserted, updated; remove deleted
        return DataStoreSaveChangesResult(
            for: identifier,
            remappedIdentifiers: [:],
            snapshotsToReregister: [:]
        )
    }

    func erase() throws {
        // Remove all persisted data
    }

    func initializeState(for editingState: EditingState) {}
    func invalidateState(for editingState: EditingState) {}

    func cachedSnapshots(
        for identifiers: [PersistentIdentifier],
        editingState: EditingState
    ) throws -> [PersistentIdentifier: DefaultSnapshot] {
        [:]
    }
}
```

### DataStoreConfiguration

```swift
struct JSONStoreConfiguration: DataStoreConfiguration {
    typealias Store = JSONStore

    let name: String
    var schema: Schema?
    let fileURL: URL

    init(name: String, fileURL: URL) {
        self.name = name
        self.fileURL = fileURL
    }

    func validate() throws {
        // Validate file URL is accessible
    }
}
```

### Using a Custom Store

```swift
let config = JSONStoreConfiguration(
    name: "JSONStore",
    fileURL: URL.documentsDirectory.appending(path: "data.json")
)
let container = try ModelContainer(
    for: Trip.self,
    configurations: config
)
```

### Optional Conformances

- **`DataStoreBatching`**: Implement `delete(_:)` for batch delete support.
- **`HistoryProviding`**: Implement `fetchHistory(_:)` and `deleteHistory(_:)`
  for change tracking.

### DataStoreError Cases

Handle these when implementing custom stores:

| Case | Meaning |
|------|---------|
| `.invalidPredicate` | Predicate cannot be evaluated by the store |
| `.preferInMemoryFilter` | Store cannot filter; framework filters in memory |
| `.preferInMemorySort` | Store cannot sort; framework sorts in memory |
| `.unsupportedFeature` | Store does not support the requested operation |

---

## History Tracking and Change Detection (iOS 18+)

### Enable History Tracking

Set the `author` property on `ModelContext` to tag changes with an identifier.
Mark attributes with `.preserveValueOnDeletion` to retain values in tombstones
after deletion.

```swift
@Model
class Trip {
    @Attribute(.preserveValueOnDeletion) var name: String
    @Attribute(.preserveValueOnDeletion) var destination: String
    var startDate: Date

    init(name: String, destination: String, startDate: Date) {
        self.name = name
        self.destination = destination
        self.startDate = startDate
    }
}

// Tag context for history attribution
modelContext.author = "mainApp"
```

### Fetch History Transactions

```swift
var descriptor = HistoryDescriptor<DefaultHistoryTransaction>()

// Filter by token (only new changes since last check)
if let lastToken = savedToken {
    descriptor.predicate = #Predicate<DefaultHistoryTransaction> { transaction in
        transaction.token > lastToken
    }
}

// iOS 26+: Sort by timestamp
descriptor.sortBy = [SortDescriptor(\.timestamp, order: .reverse)]

let transactions = try modelContext.fetchHistory(descriptor)

for transaction in transactions {
    for change in transaction.changes {
        switch change {
        case .insert(let insert):
            let insertedID = insert.changedPersistentIdentifier
            // Process new record

        case .update(let update):
            let updatedID = update.changedPersistentIdentifier
            let changedAttributes = update.updatedAttributes
            // Process modification

        case .delete(let delete):
            let deletedID = delete.changedPersistentIdentifier
            let tombstone = delete.tombstone
            // Access preserved values
            if let name = tombstone[\.name] as? String {
                // Use preserved name for sync/audit
            }
        }
    }

    // Save token for next incremental fetch
    savedToken = transaction.token
}
```

### Delete Stale History

```swift
let cutoffDate = Calendar.current.date(byAdding: .month, value: -3, to: .now)!
var descriptor = HistoryDescriptor<DefaultHistoryTransaction>()
descriptor.predicate = #Predicate<DefaultHistoryTransaction> { transaction in
    transaction.timestamp < cutoffDate
}
try modelContext.deleteHistory(descriptor)
```

### DefaultHistoryTransaction Properties

| Property | Type | Description |
|----------|------|-------------|
| `author` | `String?` | The context author that made the change |
| `changes` | `[HistoryChange]` | Insert, update, delete changes |
| `storeIdentifier` | `String` | Store that owns the transaction |
| `timestamp` | `Date` | When the transaction occurred |
| `token` | `DefaultHistoryToken` | Opaque token for incremental queries |
| `transactionIdentifier` | ... | Unique transaction ID |
| `bundleIdentifier` | `String` | Bundle that made the change |
| `processIdentifier` | `String` | Process that made the change |

### Cross-Process Change Detection

Use `bundleIdentifier` and `processIdentifier` to differentiate changes from
widgets, extensions, or the main app.

```swift
for transaction in transactions {
    if transaction.author == "widget" {
        // Handle widget-originated changes
    }
}
```

---

## CloudKit Integration

### Configuration Options

```swift
// Automatic: uses CloudKit entitlement from the app
let autoConfig = ModelConfiguration(
    cloudKitDatabase: .automatic
)

// Explicit private database
let privateConfig = ModelConfiguration(
    cloudKitDatabase: .private("iCloud.com.example.myapp")
)

// No CloudKit sync
let localConfig = ModelConfiguration(
    cloudKitDatabase: .none
)
```

### Setup Requirements

1. Enable iCloud capability in Xcode.
2. Add CloudKit entitlement (`com.apple.developer.icloud-services`).
3. Configure a CloudKit container identifier.
4. Use the container identifier in `ModelConfiguration`.

### CloudKit-Compatible Model Design

```swift
@Model
class SyncedNote {
    // Use optional properties -- records may arrive partially from other devices
    var title: String?
    var body: String?

    // Encrypt sensitive fields in CloudKit
    @Attribute(.allowsCloudEncryption) var secretContent: String?

    // Store large data externally
    @Attribute(.externalStorage) var attachment: Data?

    // Avoid .unique with CloudKit -- CloudKit does not enforce server-side uniqueness
    // Use @Attribute(.unique) only for local-only stores

    init(title: String? = nil, body: String? = nil) {
        self.title = title
        self.body = body
    }
}
```

### CloudKit Limitations

- **Unique constraints**: CloudKit does not enforce uniqueness server-side.
  Avoid `@Attribute(.unique)` and `#Unique` on CloudKit-synced models. Use
  `cloudKitDatabase: .none` for local-only stores that need uniqueness.
- **Optional properties**: Prefer optionals for all properties on synced models.
  Records from other devices may arrive with missing fields.
- **Delete rules**: `.cascade` may cause unexpected deletions when sync delivers
  partial data. Test thoroughly.
- **Schema changes**: CloudKit schemas are additive-only in production. New
  fields are fine; removing or renaming fields requires careful migration.

### Multiple Stores: Local + Synced

```swift
let localConfig = ModelConfiguration(
    "Local",
    schema: Schema([DraftNote.self]),
    cloudKitDatabase: .none
)

let syncedConfig = ModelConfiguration(
    "Synced",
    schema: Schema([PublishedNote.self]),
    cloudKitDatabase: .private("iCloud.com.example.app")
)

let container = try ModelContainer(
    for: Schema([DraftNote.self, PublishedNote.self]),
    configurations: [localConfig, syncedConfig]
)
```

---

## Core Data Coexistence and Migration

### Three Strategies

| Strategy | When to Use |
|----------|-------------|
| Pure Core Data | No migration needed; maintain existing stack |
| Full SwiftData | Greenfield app or complete rewrite |
| Coexistence | Gradual migration; both stacks share the same store |

### Coexistence Setup

Both stacks read/write the same SQLite file. Critical requirements:

1. **Enable persistent history tracking** on the Core Data side:
   ```swift
   let description = NSPersistentStoreDescription()
   description.setOption(
       true as NSNumber,
       forKey: NSPersistentHistoryTrackingKey
   )
   ```

2. **Match entity names** between Core Data `.xcdatamodeld` and SwiftData
   `@Model` classes.

3. **Use different class names** to avoid conflicts:
   ```swift
   // Core Data side
   class CDTrip: NSManagedObject { /* ... */ }

   // SwiftData side
   @Model
   class Trip { /* entity name "Trip" matches Core Data entity */ }
   ```

4. **Point both stacks at the same store URL**.

### Store File Locations

| Scenario | Location |
|----------|----------|
| Default | Application Support directory |
| App group entitlement | Root of app group container |
| Explicit URL | `ModelConfiguration(url: customURL)` |

### Migration from Core Data to SwiftData

Step-by-step:

1. Define `VersionedSchema` matching the current Core Data model.
2. Create `@Model` classes with matching entity/attribute names.
3. Set up `SchemaMigrationPlan` for future changes.
4. Enable persistent history tracking on Core Data side.
5. Point both stacks at the same store file.
6. Gradually move reads to `@Query` / `FetchDescriptor`.
7. Move writes to `ModelContext` operations.
8. Remove Core Data stack when migration is complete.

---

## Batch Operations and Performance

### Batch Enumeration

Process large result sets without loading all objects into memory:

```swift
try modelContext.enumerate(
    FetchDescriptor<Trip>(),
    batchSize: 5000,
    allowEscapingMutations: false
) { trip in
    trip.isProcessed = true
}
```

- `batchSize`: Number of objects loaded per batch (default 5000).
- `allowEscapingMutations`: Set to `true` only if mutations need to persist
  beyond the enumeration block.

### Batch Delete

```swift
try modelContext.delete(
    model: Trip.self,
    where: #Predicate { $0.isArchived == true },
    includeSubclasses: true  // iOS 26+ with inheritance
)
```

### Fetching Only Identifiers

When full objects are not needed (e.g., for counting or cross-actor references):

```swift
let ids = try modelContext.fetchIdentifiers(FetchDescriptor<Trip>())
```

### Fetch Count

```swift
let count = try modelContext.fetchCount(
    FetchDescriptor<Trip>(predicate: #Predicate { $0.isFavorite == true })
)
```

### Partial Property Fetch

Fetch only specific properties to reduce memory:

```swift
var descriptor = FetchDescriptor<Trip>()
descriptor.propertiesToFetch = [\.name, \.startDate]
let trips = try modelContext.fetch(descriptor)
```

### Relationship Prefetching

Avoid N+1 query problems by prefetching related objects:

```swift
var descriptor = FetchDescriptor<Trip>()
descriptor.relationshipKeyPathsForPrefetching = [\.accommodation, \.tags]
let trips = try modelContext.fetch(descriptor)
```

### Performance Tips

- Add `#Index` on frequently filtered/sorted properties.
- Use `fetchLimit` and `fetchOffset` for pagination.
- Use `enumerate` instead of `fetch` for processing large datasets.
- Use `fetchCount` when only the count is needed.
- Use `fetchIdentifiers` when only IDs are needed.
- Use `propertiesToFetch` to limit loaded data.
- Use `@Attribute(.externalStorage)` for `Data` properties over ~100KB.
- Disable `includePendingChanges` if unsaved data is not needed in results.
- Call `modelContext.save()` periodically during large imports to flush memory.

---

## Complex #Predicate Patterns

### Nested Collection Predicates

```swift
// Trips with at least one high-priority tag
#Predicate<Trip> { trip in
    trip.tags.contains { tag in
        tag.priority > 5
    }
}

// Trips where all items are packed
#Predicate<Trip> { trip in
    trip.packingList.allSatisfy { item in
        item.isPacked == true
    }
}
```

### Optional Chaining

```swift
// Trips with accommodation in a specific city
#Predicate<Trip> { trip in
    trip.accommodation?.city == "Paris"
}

// Nil coalescing
#Predicate<Trip> { trip in
    (trip.accommodation?.rating ?? 0) >= 4
}
```

### String Operations

```swift
// Case-insensitive search
#Predicate<Trip> { trip in
    trip.destination.localizedStandardContains(searchText)
}

// Prefix matching
#Predicate<Trip> { trip in
    trip.name.starts(with: "Summer")
}
```

### Date and Numeric Ranges

```swift
let startOfYear = Calendar.current.date(from: DateComponents(year: 2026, month: 1, day: 1))!
let endOfYear = Calendar.current.date(from: DateComponents(year: 2026, month: 12, day: 31))!

#Predicate<Trip> { trip in
    trip.startDate >= startOfYear && trip.startDate <= endOfYear
}

// Arithmetic
#Predicate<Trip> { trip in
    trip.budget - trip.spent > 100.0
}
```

### Ternary Expressions

```swift
#Predicate<Trip> { trip in
    (trip.isFavorite ? trip.name : trip.destination).localizedStandardContains(searchText)
}
```

### Combining Multiple Predicates

Build predicates incrementally using captured variables:

```swift
func buildPredicate(
    searchText: String,
    onlyFavorites: Bool,
    minDate: Date?
) -> Predicate<Trip> {
    #Predicate<Trip> { trip in
        (searchText.isEmpty || trip.name.localizedStandardContains(searchText))
        && (!onlyFavorites || trip.isFavorite == true)
        && (minDate == nil || trip.startDate >= (minDate ?? .distantPast))
    }
}
```

### Type Casting in Predicates (iOS 26+, with Inheritance)

```swift
// Filter for business trips only
#Predicate<Trip> { trip in
    trip is BusinessTrip
}
```

---

## Composite Attributes (iOS 18+)

Codable structs stored as composite (nested) attributes in the database.

```swift
struct Address: Codable {
    var street: String
    var city: String
    var state: String
    var zip: String
}

@Model
class Person {
    var name: String
    var homeAddress: Address   // Stored as composite attribute
    var workAddress: Address?

    init(name: String, homeAddress: Address) {
        self.name = name
        self.homeAddress = homeAddress
    }
}
```

Composite attributes appear as `Schema.CompositeAttribute` in the schema.
Sub-properties are stored inline in the same table. Query individual fields
via key-path navigation in `#Predicate`:

```swift
#Predicate<Person> { person in
    person.homeAddress.city == "San Francisco"
}
```

---

## Model Inheritance (iOS 26+)

### Base and Subclass Pattern

```swift
@Model
class Trip {
    var name: String
    var destination: String
    var startDate: Date
    var endDate: Date

    init(name: String, destination: String, startDate: Date, endDate: Date) {
        self.name = name
        self.destination = destination
        self.startDate = startDate
        self.endDate = endDate
    }
}

@Model
class PersonalTrip: Trip {
    var companion: String?
}

@Model
class BusinessTrip: Trip {
    var company: String
    var expenseReport: Data?

    init(name: String, destination: String, startDate: Date, endDate: Date,
         company: String) {
        self.company = company
        super.init(name: name, destination: destination,
                   startDate: startDate, endDate: endDate)
    }
}
```

### Querying with Inheritance

```swift
// Fetch all trips (includes PersonalTrip and BusinessTrip)
let allTrips = try modelContext.fetch(FetchDescriptor<Trip>())

// Fetch only business trips
let businessTrips = try modelContext.fetch(FetchDescriptor<BusinessTrip>())

// Delete with subclass inclusion
try modelContext.delete(
    model: Trip.self,
    where: #Predicate { $0.destination == "Cancelled" },
    includeSubclasses: true
)
```

### Container Registration

Register the base class; subclasses are included automatically:

```swift
let container = try ModelContainer(for: Trip.self)
// PersonalTrip and BusinessTrip are included via inheritance
```

---

## Multiple ModelContainer Configurations

### Separate Stores for Different Data

```swift
// Local-only data (no sync)
let localConfig = ModelConfiguration(
    "Local",
    schema: Schema([AppSettings.self, CacheEntry.self]),
    isStoredInMemoryOnly: false,
    cloudKitDatabase: .none
)

// Synced data
let syncConfig = ModelConfiguration(
    "Synced",
    schema: Schema([UserDocument.self, SharedNote.self]),
    cloudKitDatabase: .private("iCloud.com.example.app")
)

let container = try ModelContainer(
    for: Schema([AppSettings.self, CacheEntry.self, UserDocument.self, SharedNote.self]),
    configurations: [localConfig, syncConfig]
)
```

### Read-Only Bundled Database

```swift
let bundledURL = Bundle.main.url(forResource: "seed", withExtension: "store")!
let readOnlyConfig = ModelConfiguration(
    "SeedData",
    schema: Schema([ReferenceItem.self]),
    url: bundledURL,
    allowsSave: false
)
```

### App Group Sharing (Widget / Extension)

```swift
let sharedConfig = ModelConfiguration(
    groupContainer: .identifier("group.com.example.myapp")
)
let container = try ModelContainer(for: Trip.self, configurations: sharedConfig)
```

---

## Undo/Redo Support

### Setup

```swift
let context = ModelContext(container)
context.undoManager = UndoManager()
```

### SwiftUI Integration

```swift
@main
struct MyApp: App {
    let container: ModelContainer

    init() {
        container = try! ModelContainer(for: Trip.self)
        container.mainContext.undoManager = UndoManager()
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
        }
        .modelContainer(container)
    }
}
```

### Using Undo/Redo

```swift
struct TripEditorView: View {
    @Environment(\.modelContext) private var modelContext
    @Environment(\.undoManager) private var undoManager

    var body: some View {
        VStack {
            // ... editing UI ...
        }
        .toolbar {
            ToolbarItemGroup {
                Button("Undo") {
                    modelContext.undoManager?.undo()
                }
                .disabled(!(modelContext.undoManager?.canUndo ?? false))

                Button("Redo") {
                    modelContext.undoManager?.redo()
                }
                .disabled(!(modelContext.undoManager?.canRedo ?? false))
            }
        }
        .onAppear {
            modelContext.undoManager = undoManager
        }
    }
}
```

Process pending changes to register undo actions:

```swift
modelContext.insert(trip)
modelContext.processPendingChanges()
// Now undo is available for the insertion
```

---

## Preview Patterns with In-Memory Stores

### Basic Preview Container

```swift
@MainActor
let previewContainer: ModelContainer = {
    let config = ModelConfiguration(isStoredInMemoryOnly: true)
    let container = try! ModelContainer(for: Trip.self, configurations: config)

    // Seed sample data
    let sampleTrips = [
        Trip(name: "Summer in Paris", destination: "Paris",
             startDate: .now, endDate: .now.addingTimeInterval(86400 * 7)),
        Trip(name: "Tokyo Adventure", destination: "Tokyo",
             startDate: .now.addingTimeInterval(86400 * 30),
             endDate: .now.addingTimeInterval(86400 * 37)),
    ]
    for trip in sampleTrips {
        container.mainContext.insert(trip)
    }

    return container
}()

#Preview {
    TripListView()
        .modelContainer(previewContainer)
}
```

### Preview with Relationships

```swift
#Preview {
    let config = ModelConfiguration(isStoredInMemoryOnly: true)
    let container = try! ModelContainer(
        for: Trip.self, LivingAccommodation.self,
        configurations: config
    )

    let trip = Trip(name: "Beach Trip", destination: "Malibu",
                    startDate: .now, endDate: .now.addingTimeInterval(86400 * 3))
    let hotel = LivingAccommodation(name: "Beach Resort")
    trip.accommodation = hotel

    container.mainContext.insert(trip)

    return TripDetailView(trip: trip)
        .modelContainer(container)
}
```

### Preview Trait (iOS 18+)

Use `PreviewModifier` for reusable preview configurations:

```swift
struct SampleDataPreview: PreviewModifier {
    static func makeSharedContext() async throws -> ModelContainer {
        let config = ModelConfiguration(isStoredInMemoryOnly: true)
        let container = try ModelContainer(for: Trip.self, configurations: config)
        // Insert sample data
        return container
    }

    func body(content: Content, context: ModelContainer) -> some View {
        content.modelContainer(context)
    }
}

extension PreviewTrait where T == Preview.ViewTraits {
    static var sampleData: Self = .modifier(SampleDataPreview())
}

#Preview(traits: .sampleData) {
    TripListView()
}
```

---

## Notification Observation

### Observing Save Events

```swift
NotificationCenter.default.publisher(for: ModelContext.didSave, object: modelContext)
    .sink { notification in
        if let insertedIDs = notification.userInfo?[
            ModelContext.NotificationKey.insertedIdentifiers
        ] as? Set<PersistentIdentifier> {
            // Handle new insertions
        }

        if let updatedIDs = notification.userInfo?[
            ModelContext.NotificationKey.updatedIdentifiers
        ] as? Set<PersistentIdentifier> {
            // Handle updates
        }

        if let deletedIDs = notification.userInfo?[
            ModelContext.NotificationKey.deletedIdentifiers
        ] as? Set<PersistentIdentifier> {
            // Handle deletions
        }
    }
```

### Available Notification Keys

| Key | Description |
|-----|-------------|
| `.insertedIdentifiers` | IDs of newly inserted models |
| `.updatedIdentifiers` | IDs of updated models |
| `.deletedIdentifiers` | IDs of deleted models |
| `.invalidatedAllIdentifiers` | All data invalidated (e.g., store reset) |
| `.queryGeneration` | Query generation token |

---

## Error Handling

### SwiftDataError Cases

```swift
do {
    let trips = try modelContext.fetch(descriptor)
} catch let error as SwiftDataError {
    switch error {
    case SwiftDataError.unsupportedPredicate:
        // Predicate uses unsupported operations
    case SwiftDataError.unsupportedSortDescriptor:
        // Sort descriptor cannot be processed
    case SwiftDataError.modelValidationFailure:
        // Model fails validation (e.g., unique constraint)
    case SwiftDataError.loadIssueModelContainer:
        // Container could not load the store
    default:
        // Handle other SwiftData errors
    }
} catch {
    // Handle non-SwiftData errors
}
```

### Common Error Categories

| Category | Errors |
|----------|--------|
| Fetch | `.unsupportedPredicate`, `.unsupportedSortDescriptor`, `.unsupportedKeyPath`, `.includePendingChangesWithBatchSize` |
| Configuration | `.duplicateConfiguration`, `.configurationFileNameContainsInvalidCharacters`, `.configurationSchemaNotFoundInContainerSchema` |
| Container | `.loadIssueModelContainer` |
| Context | `.modelValidationFailure`, `.missingModelContext` |
| Migration | `.backwardMigration`, `.unknownSchema` |
| History (iOS 18+) | `.historyTokenExpired`, `.invalidTransactionFetchRequest` |
