---
name: core-data
description: "Build, review, or improve Core Data persistence in apps that have not adopted SwiftData. Use when working with NSManagedObject subclasses, NSFetchedResultsController for list-driven UI, NSBatchInsertRequest / NSBatchDeleteRequest / NSBatchUpdateRequest for bulk operations, NSPersistentHistoryChangeRequest for persistent history tracking and multi-target sync, NSStagedMigrationManager for staged schema migrations (iOS 17+), NSCompositeAttributeDescription for composite attributes (iOS 17+), or when integrating Core Data threading with Swift Concurrency. For Core Data + SwiftData coexistence or migration, see the swiftdata skill instead."
---

# Core Data

Build and maintain data persistence using Core Data for apps that have not
adopted SwiftData. Covers stack setup, concurrency, batch operations,
NSFetchedResultsController, persistent history tracking, staged migration,
and testing.

## Contents

- [Stack Setup](#stack-setup)
- [Concurrency and Threading](#concurrency-and-threading)
- [NSFetchedResultsController](#nsfetchedresultscontroller)
- [Batch Operations](#batch-operations)
- [Persistent History Tracking](#persistent-history-tracking)
- [Staged Migration](#staged-migration)
- [Composite Attributes](#composite-attributes)
- [SwiftData Boundary](#swiftdata-boundary)
- [Testing](#testing)
- [Common Mistakes](#common-mistakes)
- [Review Checklist](#review-checklist)
- [References](#references)

## Stack Setup

`NSPersistentContainer` encapsulates the Core Data stack.

Docs: [NSPersistentContainer](https://sosumi.ai/documentation/coredata/nspersistentcontainer)

```swift
import CoreData

final class CoreDataStack: @unchecked Sendable {
    static let shared = CoreDataStack()

    let container: NSPersistentContainer

    private init() {
        container = NSPersistentContainer(name: "MyAppModel")
        container.loadPersistentStores { _, error in
            if let error { fatalError("Core Data store failed: \(error)") }
        }
        container.viewContext.automaticallyMergesChangesFromParent = true
        container.viewContext.mergePolicy = NSMergeByPropertyObjectTrumpMergePolicy
    }

    var viewContext: NSManagedObjectContext { container.viewContext }

    func newBackgroundContext() -> NSManagedObjectContext {
        container.newBackgroundContext()
    }
}
```

For CloudKit sync, use `NSPersistentCloudKitContainer` instead.

## Concurrency and Threading

Core Data contexts are bound to queues. The `viewContext` is on the main queue;
background contexts operate on private queues.

Docs: [NSManagedObjectContext](https://sosumi.ai/documentation/coredata/nsmanagedobjectcontext)

**Rules:**
- Always use `perform(_:)` or `performAndWait(_:)` when accessing a context
  off its own queue.
- Never pass `NSManagedObject` instances across context or thread boundaries.
  Pass `NSManagedObjectID` instead and re-fetch.
- Set `automaticallyMergesChangesFromParent = true` on the `viewContext`.

```swift
// Writing on a background context
func updateTrip(id: NSManagedObjectID, newName: String) async throws {
    let context = CoreDataStack.shared.newBackgroundContext()
    try await context.perform {
        guard let trip = try context.existingObject(with: id) as? CDTrip else {
            throw PersistenceError.notFound
        }
        trip.name = newName
        try context.save()
    }
}
```

### Swift Concurrency Integration

`NSManagedObjectContext.perform(_:)` has an `async throws` overload
(iOS 15+). Avoid marking `NSManagedObject` subclasses as `Sendable`.

```swift
func importItems(_ records: [ItemRecord]) async throws {
    let context = CoreDataStack.shared.newBackgroundContext()
    try await context.perform {
        for record in records {
            let item = CDItem(context: context)
            item.id = record.id
            item.title = record.title
        }
        try context.save()
    }
    // After save completes, viewContext auto-merges if configured
}
```

**Do not use `@unchecked Sendable` on managed objects.** If you need
cross-boundary communication, pass the `objectID` (which is `Sendable`)
and re-fetch:

```swift
let objectID = trip.objectID  // Sendable
Task.detached {
    let bgContext = CoreDataStack.shared.newBackgroundContext()
    try await bgContext.perform {
        let trip = try bgContext.existingObject(with: objectID) as! CDTrip
        trip.isFavorite = true
        try bgContext.save()
    }
}
```

## NSFetchedResultsController

Efficiently drives `UITableView` / `UICollectionView` from a Core Data fetch
request, with built-in change tracking and optional caching.

Docs: [NSFetchedResultsController](https://sosumi.ai/documentation/coredata/nsfetchedresultscontroller)

```swift
import CoreData
import UIKit

class TripsViewController: UITableViewController, NSFetchedResultsControllerDelegate {

    private lazy var fetchedResultsController: NSFetchedResultsController<CDTrip> = {
        let request: NSFetchRequest<CDTrip> = CDTrip.fetchRequest()
        request.sortDescriptors = [
            NSSortDescriptor(keyPath: \CDTrip.startDate, ascending: false)
        ]
        request.fetchBatchSize = 20

        let controller = NSFetchedResultsController(
            fetchRequest: request,
            managedObjectContext: CoreDataStack.shared.viewContext,
            sectionNameKeyPath: nil,
            cacheName: "TripsCache"
        )
        controller.delegate = self
        return controller
    }()

    override func viewDidLoad() {
        super.viewDidLoad()
        try? fetchedResultsController.performFetch()
    }

    // MARK: - UITableViewDataSource

    override func numberOfSections(in tableView: UITableView) -> Int {
        fetchedResultsController.sections?.count ?? 0
    }

    override func tableView(_ tableView: UITableView, numberOfRowsInSection section: Int) -> Int {
        fetchedResultsController.sections?[section].numberOfObjects ?? 0
    }

    override func tableView(_ tableView: UITableView, cellForRowAt indexPath: IndexPath) -> UITableViewCell {
        let cell = tableView.dequeueReusableCell(withIdentifier: "TripCell", for: indexPath)
        let trip = fetchedResultsController.object(at: indexPath)
        cell.textLabel?.text = trip.name
        return cell
    }

    // MARK: - NSFetchedResultsControllerDelegate (diffable)

    func controller(
        _ controller: NSFetchedResultsController<any NSFetchRequestResult>,
        didChangeContentWith snapshot: NSDiffableDataSourceSnapshotReference
    ) {
        let snapshot = snapshot as NSDiffableDataSourceSnapshot<String, NSManagedObjectID>
        dataSource.apply(snapshot, animatingDifferences: true)
    }
}
```

**Key points:**
- The fetch request **must** have at least one sort descriptor.
- Call `deleteCache(withName:)` before changing the fetch request predicate or
  sort descriptors, or set `cacheName` to `nil`.
- The diffable snapshot delegate method (`didChangeContentWith:`) is available
  iOS 13+ and is preferred over the older per-change callbacks.
- After a context `reset()`, call `performFetch()` again.

## Batch Operations

Batch operations execute at the SQL level, bypassing the managed object
context. They are fast but don't trigger context notifications automatically.

### NSBatchInsertRequest (iOS 13+)

Docs: [NSBatchInsertRequest](https://sosumi.ai/documentation/coredata/nsbatchinsertrequest)

```swift
func batchImport(_ records: [[String: Any]]) async throws {
    let context = CoreDataStack.shared.newBackgroundContext()
    try await context.perform {
        let request = NSBatchInsertRequest(
            entity: CDTrip.entity(),
            objects: records
        )
        request.resultType = .objectIDs
        let result = try context.execute(request) as? NSBatchInsertResult
        if let ids = result?.result as? [NSManagedObjectID] {
            NSManagedObjectContext.mergeChanges(
                fromRemoteContextSave: [NSInsertedObjectsKey: ids],
                into: [CoreDataStack.shared.viewContext]
            )
        }
    }
}
```

### NSBatchDeleteRequest (iOS 9+)

Docs: [NSBatchDeleteRequest](https://sosumi.ai/documentation/coredata/nsbatchdeleterequest)

```swift
func deleteOldTrips(before cutoff: Date) async throws {
    let context = CoreDataStack.shared.newBackgroundContext()
    try await context.perform {
        let fetchRequest: NSFetchRequest<NSFetchRequestResult> = CDTrip.fetchRequest()
        fetchRequest.predicate = NSPredicate(format: "endDate < %@", cutoff as NSDate)
        let request = NSBatchDeleteRequest(fetchRequest: fetchRequest)
        request.resultType = .resultTypeObjectIDs
        let result = try context.execute(request) as? NSBatchDeleteResult
        if let ids = result?.result as? [NSManagedObjectID] {
            NSManagedObjectContext.mergeChanges(
                fromRemoteContextSave: [NSDeletedObjectsKey: ids],
                into: [CoreDataStack.shared.viewContext]
            )
        }
    }
}
```

### NSBatchUpdateRequest (iOS 8+)

```swift
func markAllTripsAsNotFavorite() async throws {
    let context = CoreDataStack.shared.newBackgroundContext()
    try await context.perform {
        let request = NSBatchUpdateRequest(entity: CDTrip.entity())
        request.propertiesToUpdate = ["isFavorite": false]
        request.resultType = .updatedObjectIDsResultType
        let result = try context.execute(request) as? NSBatchUpdateResult
        if let ids = result?.result as? [NSManagedObjectID] {
            NSManagedObjectContext.mergeChanges(
                fromRemoteContextSave: [NSUpdatedObjectsKey: ids],
                into: [CoreDataStack.shared.viewContext]
            )
        }
    }
}
```

**Always merge changes** back into relevant contexts after batch operations.
Batch delete does not enforce the Deny delete rule.

For destructive or retryable batch work, use a proof loop: preflight the predicate and expected count, execute with an object-ID result type, merge IDs into live contexts, refetch, and assert the postcondition. On failure, restore a pristine fixture or prove the operation is idempotent before retrying; never blindly rerun a partially completed batch.

## Persistent History Tracking

Track store-level changes across targets (app, extensions, widgets) and
processes. The core workflow is:

Docs: [NSPersistentHistoryChangeRequest](https://sosumi.ai/documentation/coredata/nspersistenthistorychangerequest)

1. Enable persistent history and remote-change notifications before loading the
   store.
2. Observe changes and fetch transactions after the target's durable token.
3. Merge transaction notifications into live contexts, then persist the new
   token.
4. Purge only history that every relevant consumer has processed.

Load [persistent-history.md](references/persistent-history.md) when implementing
the store options, observer, token persistence, merge loop, or purge policy.

## Staged Migration

`NSStagedMigrationManager` (iOS 17+) sequences schema migrations through
ordered lightweight or custom stages. Stage inputs use compiled model-version
checksums, not model names. Apps supporting systems below iOS 17 need the
lightweight migration or mapping-model path.

Docs: [NSStagedMigrationManager](https://sosumi.ai/documentation/coredata/nsstagedmigrationmanager)

Load [staged-migration.md](references/staged-migration.md) when building the
ordered stages, model references, custom handler, and persistent-store option.

## Composite Attributes

iOS 17+ supports composite attributes: groups of sub-attributes on an entity
that act as a single logical unit. Define them in the model editor by adding a
Composite type attribute and nesting sub-attributes beneath it.

Docs: [NSCompositeAttributeDescription](https://sosumi.ai/documentation/coredata/nscompositeattributedescription)

Composite attributes map to `Codable` structs in SwiftData coexistence
scenarios.

## SwiftData Boundary

Use the `swiftdata` skill for Core Data + SwiftData coexistence or migration
implementation. Before handing off, preserve these Core Data boundaries:

- SwiftData must point at the existing persistent store URL when it is meant to
  share or migrate Core Data data.
- Shared persisted data must keep entity names, property names, types, and
  schema compatible across the Core Data model and SwiftData `@Model` classes.
- Map renamed persisted properties with SwiftData `@Attribute(originalName:)`.

## Testing

### In-Memory Store for Tests

```swift
import CoreData
import Testing

struct CoreDataTests {
    func makeTestContainer() throws -> NSPersistentContainer {
        let container = NSPersistentContainer(name: "MyAppModel")
        let description = NSPersistentStoreDescription()
        description.type = NSInMemoryStoreType
        container.persistentStoreDescriptions = [description]

        var loadError: Error?
        container.loadPersistentStores { _, error in loadError = error }
        if let loadError { throw loadError }
        return container
    }

    @Test func createAndFetchTrip() throws {
        let container = try makeTestContainer()
        let context = container.viewContext

        let trip = CDTrip(context: context)
        trip.name = "Test Trip"
        trip.startDate = .now
        try context.save()

        let request: NSFetchRequest<CDTrip> = CDTrip.fetchRequest()
        let trips = try context.fetch(request)
        #expect(trips.count == 1)
        #expect(trips.first?.name == "Test Trip")
    }
}
```

**Tips:**
- Share the `NSManagedObjectModel` instance across tests to avoid "duplicate
  entity" warnings.
- Use a single shared model loaded once:

```swift
private let sharedModel: NSManagedObjectModel = {
    let url = Bundle.main.url(forResource: "MyAppModel", withExtension: "momd")!
    return NSManagedObjectModel(contentsOf: url)!
}()

func makeTestContainer() throws -> NSPersistentContainer {
    let container = NSPersistentContainer(name: "MyAppModel",
                                          managedObjectModel: sharedModel)
    // ... configure in-memory store
}
```

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Passing `NSManagedObject` across threads | Pass `objectID` and re-fetch in the target context |
| Forgetting to merge batch operation results | Call `mergeChanges(fromRemoteContextSave:into:)` |
| Calling `save()` without checking `hasChanges` | Guard with `context.hasChanges` first |
| Using deprecated `init(concurrencyType:)` confinement type | Use `.privateQueueConcurrencyType` or `.mainQueueConcurrencyType` |
| Not setting `mergePolicy` on `viewContext` | Set `NSMergeByPropertyObjectTrumpMergePolicy` to avoid conflict crashes |
| Modifying fetch request on live `NSFetchedResultsController` without deleting cache | Call `deleteCache(withName:)` first or use `cacheName: nil` |
| Batch delete ignoring Deny delete rule | Batch delete bypasses delete rules; validate manually |
| Marking `NSManagedObject` as `@unchecked Sendable` | Do not. Pass `objectID` instead |
| Pointing SwiftData at a fresh store during coexistence | Use the existing store URL and compatible schema when SwiftData should share or migrate Core Data data |

## Review Checklist

- [ ] `NSPersistentContainer` is initialized once and shared
- [ ] `viewContext` used only on main queue; background contexts for writes
- [ ] `perform(_:)` or `performAndWait(_:)` wraps all off-queue context access
- [ ] `automaticallyMergesChangesFromParent` set on `viewContext`
- [ ] `mergePolicy` set on `viewContext` to prevent conflict crashes
- [ ] Batch operation results merged into relevant contexts
- [ ] `NSFetchedResultsController` fetch requests have sort descriptors
- [ ] Persistent history tracking enabled for multi-target apps
- [ ] Core Data + SwiftData handoff preserves store URL, schema compatibility, entity/property names, and rename mappings
- [ ] Tests use in-memory stores with shared `NSManagedObjectModel`
- [ ] No `NSManagedObject` instances cross thread boundaries

## References

- [Persistent history across targets and processes](references/persistent-history.md)
- [Staged lightweight and custom migration](references/staged-migration.md)
- Apple docs: [Core Data](https://sosumi.ai/documentation/coredata) | [NSPersistentContainer](https://sosumi.ai/documentation/coredata/nspersistentcontainer) | [NSFetchedResultsController](https://sosumi.ai/documentation/coredata/nsfetchedresultscontroller) | [NSStagedMigrationManager](https://sosumi.ai/documentation/coredata/nsstagedmigrationmanager)
