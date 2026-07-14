---
name: cloudkit
description: "Implement, review, or improve CloudKit and iCloud sync in iOS/macOS apps. Use when working with CKContainer, CKRecord, CKQuery, CKSubscription, CKSyncEngine, CKShare, NSUbiquitousKeyValueStore, or iCloud Drive file coordination; when syncing SwiftData models via ModelConfiguration with cloudKitDatabase; when handling CKError codes for conflict resolution, network failures, or quota limits; or when checking iCloud account status before performing sync operations."
---

# CloudKit

Sync data across devices using CloudKit, iCloud key-value storage, and iCloud
Drive. Covers container setup, record CRUD, queries, subscriptions, CKSyncEngine,
SwiftData integration, conflict resolution, and error handling.

## Contents

- [Container and Database Setup](#container-and-database-setup)
- [Workflow](#workflow)
- [CKRecord CRUD](#ckrecord-crud)
- [CKQuery](#ckquery)
- [CKSubscription](#cksubscription)
- [CKSyncEngine (iOS 17+)](#cksyncengine-ios-17)
- [SwiftData + CloudKit](#swiftdata--cloudkit)
- [NSUbiquitousKeyValueStore](#nsubiquitouskeyvaluestore)
- [iCloud Drive File Sync](#icloud-drive-file-sync)
- [Account Status and Error Handling](#account-status-and-error-handling)
- [Conflict Resolution](#conflict-resolution)
- [Common Mistakes](#common-mistakes)
- [Review Checklist](#review-checklist)
- [References](#references)

## Workflow

1. Choose the database scope and sync owner; verify capability, container, account status, schema, and environment before writing records.
2. Make a local change durable, enqueue it, then let subscriptions or `CKSyncEngine` drive remote work rather than polling.
3. Persist change tokens or sync-engine state after successful application.
4. Test offline edits, partial failure, rate limiting, token expiry, conflict, account loss, zone deletion, and relaunch.
5. On failure, classify the `CKError`, restore the affected fixture or queue item, apply the documented retry/reset/merge action, and rerun the same scenario. Never restart a full sync blindly after partial success.

Load [references/cloudkit-patterns.md](references/cloudkit-patterns.md) for incremental zone changes, shares, assets, batch operations, and Dashboard procedures.

## Container and Database Setup

Enable iCloud + CloudKit in Signing & Capabilities. A container provides three databases:

| Database | Scope | Requires iCloud | Storage Quota |
|----------|-------|-----------------|---------------|
| Public   | All users | Read: No, Write: Yes | App quota |
| Private  | Current user | Yes | User quota |
| Shared   | Shared records | Yes | Owner quota |

```swift
import CloudKit

let container = CKContainer.default()
// Or named: CKContainer(identifier: "iCloud.com.example.app")

let publicDB  = container.publicCloudDatabase
let privateDB = container.privateCloudDatabase
let sharedDB  = container.sharedCloudDatabase
```

## CKRecord CRUD

Records are key-value pairs. Max 1 MB per record (excluding CKAsset data).

```swift
// CREATE
let record = CKRecord(recordType: "Note")
record["title"] = "Meeting Notes" as CKRecordValue
record["body"] = "Discussed Q3 roadmap" as CKRecordValue
record["createdAt"] = Date() as CKRecordValue
record["tags"] = ["work", "planning"] as CKRecordValue
let saved = try await privateDB.save(record)

// FETCH by ID
let recordID = CKRecord.ID(recordName: "unique-id-123")
let fetched = try await privateDB.record(for: recordID)

// UPDATE -- fetch first, modify, then save
fetched["title"] = "Updated Title" as CKRecordValue
let updated = try await privateDB.save(fetched)

// DELETE
try await privateDB.deleteRecord(withID: recordID)
```

### Custom Record Zones

Apps create custom zones in the private database. Shared databases expose zones
that other users share with the current user. Custom zones support atomic
commits, change tracking, and sharing; public databases do not support custom
zones.

```swift
let zoneID = CKRecordZone.ID(zoneName: "NotesZone")
let zone = CKRecordZone(zoneID: zoneID)
try await privateDB.save(zone)

let recordID = CKRecord.ID(recordName: UUID().uuidString, zoneID: zoneID)
let record = CKRecord(recordType: "Note", recordID: recordID)
```

## CKQuery

Query records with NSPredicate. Supported: `==`, `!=`, `<`, `>`, `<=`, `>=`,
`BEGINSWITH`, `CONTAINS`, `IN`, `AND`, `NOT`, `BETWEEN`,
`distanceToLocation:fromLocation:`.

`CONTAINS` tests list membership except for tokenized full-text search with
`self CONTAINS`. `BEGINSWITH` is the string-prefix operator; unsupported
operators, key paths, or field types fail when the query executes.
For every encryption review, explicitly call out field eligibility: encrypted
values cannot be queried or sorted; `CKAsset` is encrypted by default; and
`CKRecord.Reference` cannot be encrypted because CloudKit needs it server-side.

```swift
let predicate = NSPredicate(format: "title BEGINSWITH %@", "Meeting")
let query = CKQuery(recordType: "Note", predicate: predicate)
query.sortDescriptors = [NSSortDescriptor(key: "createdAt", ascending: false)]

let (results, _) = try await privateDB.records(matching: query)
for (_, result) in results {
    let record = try result.get()
    print(record["title"] as? String ?? "")
}

// Fetch all records of a type
let allQuery = CKQuery(recordType: "Note", predicate: NSPredicate(value: true))

// Full-text search across string fields
let searchQuery = CKQuery(
    recordType: "Note",
    predicate: NSPredicate(format: "self CONTAINS %@", "roadmap")
)

// Compound predicate
let compound = NSCompoundPredicate(andPredicateWithSubpredicates: [
    NSPredicate(format: "createdAt > %@", cutoffDate as NSDate),
    NSPredicate(format: "tags CONTAINS %@", "work")
])
```

## CKSubscription

Subscriptions trigger push notifications when records change server-side.
CloudKit/Xcode handles the APNs entitlement when CloudKit is enabled; no
separate explicit App ID push setup is needed. Silent/background processing
still needs Background Modes > Remote notifications.

```swift
// Query subscription -- fires when matching records change
let subscription = CKQuerySubscription(
    recordType: "Note",
    predicate: NSPredicate(format: "tags CONTAINS %@", "urgent"),
    subscriptionID: "urgent-notes",
    options: [.firesOnRecordCreation, .firesOnRecordUpdate]
)
let notifInfo = CKSubscription.NotificationInfo()
notifInfo.shouldSendContentAvailable = true  // silent push
subscription.notificationInfo = notifInfo
try await privateDB.save(subscription)

// Database subscription -- fires on any database change
let dbSub = CKDatabaseSubscription(subscriptionID: "private-db-changes")
dbSub.notificationInfo = notifInfo
try await privateDB.save(dbSub)

// Record zone subscription -- fires on changes within a zone
let zoneSub = CKRecordZoneSubscription(
    zoneID: CKRecordZone.ID(zoneName: "NotesZone"),
    subscriptionID: "notes-zone-changes"
)
zoneSub.notificationInfo = notifInfo
try await privateDB.save(zoneSub)
```

Handle in AppDelegate:

```swift
func application(
    _ application: UIApplication,
    didReceiveRemoteNotification userInfo: [AnyHashable: Any]
) async -> UIBackgroundFetchResult {
    let notification = CKNotification(fromRemoteNotificationDictionary: userInfo)
    guard notification?.subscriptionID == "private-db-changes" else { return .noData }
    // Fetch changes using CKSyncEngine or CKFetchRecordZoneChangesOperation
    return .newData
}
```

## CKSyncEngine (iOS 17+)

`CKSyncEngine` is the recommended sync approach for custom model data. It
handles scheduling, transient retries, change tokens, and database
subscriptions, but not app-specific save failures: `CKError.serverRecordChanged`
from `sentRecordZoneChanges.failedRecordSaves` still requires custom conflict
resolution and rescheduling. Automatic sync timing is indeterminate. Requires
CloudKit capability + Remote notifications; private/shared databases only.

```swift
import CloudKit

final class SyncManager: CKSyncEngineDelegate {
    let syncEngine: CKSyncEngine

    init(container: CKContainer = .default()) {
        let config = CKSyncEngine.Configuration(
            database: container.privateCloudDatabase,
            stateSerialization: Self.loadState(),
            delegate: self
        )
        self.syncEngine = CKSyncEngine(config)
    }

    func handleEvent(_ event: CKSyncEngine.Event, syncEngine: CKSyncEngine) async {
        switch event {
        case .stateUpdate(let update):
            Self.saveState(update.stateSerialization)
        case .accountChange(let change):
            handleAccountChange(change)
        case .fetchedRecordZoneChanges(let changes):
            for mod in changes.modifications { processRemoteRecord(mod.record) }
            for del in changes.deletions { processRemoteDeletion(del.recordID) }
        case .sentRecordZoneChanges(let sent):
            for saved in sent.savedRecords { markSynced(saved) }
            for fail in sent.failedRecordSaves { handleSaveFailure(fail) }
        default: break
        }
    }

    func nextRecordZoneChangeBatch(
        _ context: CKSyncEngine.SendChangesContext,
        syncEngine: CKSyncEngine
    ) async -> CKSyncEngine.RecordZoneChangeBatch? {
        let pending = syncEngine.state.pendingRecordZoneChanges
            .filter { context.options.zoneIDs.contains($0) }
        return await CKSyncEngine.RecordZoneChangeBatch(
            pendingChanges: pending
        ) { recordID in self.recordToSend(for: recordID) }
    }
}

// Schedule changes
let zoneID = CKRecordZone.ID(zoneName: "NotesZone")
let recordID = CKRecord.ID(recordName: noteID, zoneID: zoneID)
syncEngine.state.add(pendingRecordZoneChanges: [.saveRecord(recordID)])

// Trigger immediate sync (pull-to-refresh)
try await syncEngine.fetchChanges()
try await syncEngine.sendChanges()
```

**Key point**: persist `stateSerialization` across launches; the engine needs it
to resume from the correct change token.

## SwiftData + CloudKit

`ModelConfiguration` supports CloudKit sync. In every SwiftData CloudKit
implementation or review, always report two verdicts:

- **Model compatibility**: no `#Unique` or unique constraints, optional
  relationships, no `.deny`, and external storage for large `Data`.
- **Schema rollout**: initialize the development schema in nonproduction builds,
  verify it in CloudKit Dashboard, promote it before release, and after
  production promotion only add schema; don't delete model types or change
  existing attributes.

```swift
import SwiftData

@Model
class Note {
    var title: String
    var body: String?
    var createdAt: Date?
    @Attribute(.externalStorage) var imageData: Data?

    init(title: String, body: String? = nil) {
        self.title = title
        self.body = body
        self.createdAt = Date()
    }
}

let config = ModelConfiguration(
    "Notes",
    cloudKitDatabase: .private("iCloud.com.example.app")
)
let container = try ModelContainer(for: Note.self, configurations: config)
```

## NSUbiquitousKeyValueStore

Simple key-value sync. Max 1024 keys, 1 MB total, 1 MB per value. Stores
locally when iCloud is unavailable.

```swift
let kvStore = NSUbiquitousKeyValueStore.default

// Write
kvStore.set("dark", forKey: "theme")
kvStore.set(14.0, forKey: "fontSize")
kvStore.set(true, forKey: "notificationsEnabled")
kvStore.synchronize()

// Read
let theme = kvStore.string(forKey: "theme") ?? "system"

// Observe external changes
NotificationCenter.default.addObserver(
    forName: NSUbiquitousKeyValueStore.didChangeExternallyNotification,
    object: kvStore, queue: .main
) { notification in
    guard let userInfo = notification.userInfo,
          let reason = userInfo[NSUbiquitousKeyValueStoreChangeReasonKey] as? Int,
          let keys = userInfo[NSUbiquitousKeyValueStoreChangedKeysKey] as? [String]
    else { return }

    switch reason {
    case NSUbiquitousKeyValueStoreServerChange:
        for key in keys { applyRemoteChange(key: key) }
    case NSUbiquitousKeyValueStoreInitialSyncChange:
        reloadAllSettings()
    case NSUbiquitousKeyValueStoreQuotaViolationChange:
        handleQuotaExceeded()
    default: break
    }
}
```

## iCloud Drive File Sync

Use `FileManager` ubiquity APIs for document-level sync. Call
`url(forUbiquityContainerIdentifier:)` and `setUbiquitous` off the main thread;
`setUbiquitous` performs coordinated file work and can block. If the app is
presenting the file, configure an active file presenter before moving it.

```swift
Task.detached {
    guard let ubiquityURL = FileManager.default.url(
        forUbiquityContainerIdentifier: "iCloud.com.example.app"
    ) else { return }  // iCloud not available

    let docsURL = ubiquityURL.appendingPathComponent("Documents")
    try FileManager.default.createDirectory(at: docsURL, withIntermediateDirectories: true)
    let cloudURL = docsURL.appendingPathComponent("report.pdf")
    try FileManager.default.setUbiquitous(true, itemAt: localURL, destinationURL: cloudURL)
}
```

Monitor files with `NSMetadataQuery` scoped to
`NSMetadataQueryUbiquitousDocumentsScope` or
`NSMetadataQueryUbiquitousDataScope`.

## Account Status and Error Handling

Always check account status before sync. Listen for `.CKAccountChanged`.

```swift
func checkiCloudStatus() async throws -> CKAccountStatus {
    let status = try await CKContainer.default().accountStatus()
    switch status {
    case .available: return status
    case .noAccount: throw SyncError.noiCloudAccount
    case .restricted: throw SyncError.restricted
    case .temporarilyUnavailable: throw SyncError.temporarilyUnavailable
    case .couldNotDetermine: throw SyncError.unknown
    @unknown default: throw SyncError.unknown
    }
}
```

### CKError Handling

| Error Code | Strategy |
|-----------|----------|
| `.networkFailure`, `.networkUnavailable` | Queue for retry when network returns |
| `.serverRecordChanged` | Three-way merge (see Conflict Resolution) |
| `.requestRateLimited`, `.zoneBusy`, `.serviceUnavailable` | Retry after `retryAfterSeconds` |
| `.quotaExceeded` | Notify user; reduce data usage |
| `.notAuthenticated` | Prompt iCloud sign-in |
| `.partialFailure` | Inspect `partialErrorsByItemID` per item |
| `.changeTokenExpired` | Reset token, refetch all changes |
| `.userDeletedZone` | Recreate zone and re-upload data |

```swift
func handleCloudKitError(_ error: Error) {
    guard let ckError = error as? CKError else { return }
    switch ckError.code {
    case .networkFailure, .networkUnavailable:
        scheduleRetryWhenOnline()
    case .serverRecordChanged:
        resolveConflict(ckError)
    case .requestRateLimited, .zoneBusy, .serviceUnavailable:
        let delay = ckError.retryAfterSeconds ?? 3.0
        scheduleRetry(after: delay)
    case .quotaExceeded:
        notifyUserStorageFull()
    case .partialFailure:
        if let partial = ckError.partialErrorsByItemID {
            for (_, itemError) in partial { handleCloudKitError(itemError) }
        }
    case .changeTokenExpired:
        resetChangeToken()
    case .userDeletedZone:
        recreateZoneAndResync()
    default: logError(ckError)
    }
}
```

## Conflict Resolution

When saving a record that changed server-side, CloudKit returns
`.serverRecordChanged` with three record versions. Always merge into
`serverRecord` -- it has the correct change tag.

```swift
func resolveConflict(_ error: CKError) {
    guard error.code == .serverRecordChanged,
          let ancestor = error.ancestorRecord,
          let client = error.clientRecord,
          let server = error.serverRecord
    else { return }

    // Merge client changes into server record
    for key in client.changedKeys() {
        if server[key] == ancestor[key] {
            server[key] = client[key]           // Server unchanged, use client
        } else if client[key] == ancestor[key] {
            // Client unchanged, keep server (already there)
        } else {
            server[key] = mergeValues(          // Both changed, custom merge
                ancestor: ancestor[key], client: client[key], server: server[key])
        }
    }

    Task { try await CKContainer.default().privateCloudDatabase.save(server) }
}
```

## Common Mistakes

| Mistake | Fix |
|---|---|
| Syncing without an account gate | Check `accountStatus()` and model `.noAccount` as a user-visible state. |
| Personal data in the public database | Use private scope for user data; public scope is app-wide content. |
| Timer polling | Use database subscriptions or `CKSyncEngine`. |
| Immediate retry after throttling | Respect `retryAfterSeconds` and preserve pending work. |
| Assuming the engine resolves conflicts | Three-way merge `failedRecordSaves`, then reschedule the save. |
| Starting every fetch with a nil token | Persist tokens/state; reset only on the documented expiry path. |

## Review Checklist

- [ ] iCloud + CloudKit capability enabled in Signing & Capabilities
- [ ] Account status checked before sync; `.noAccount` handled gracefully
- [ ] Private database used for user data; public only for shared content
- [ ] Custom record zones created in private DB; shared DB zones discovered from shares
- [ ] `CKError.serverRecordChanged` handled with three-way merge into `serverRecord`
- [ ] Network failures queued for retry; `retryAfterSeconds` respected
- [ ] `CKDatabaseSubscription` or `CKSyncEngine` used for push-based sync; Remote notifications enabled for background delivery
- [ ] Change tokens persisted to disk; `changeTokenExpired` resets and refetches
- [ ] `.partialFailure` errors inspected per-item via `partialErrorsByItemID`
- [ ] `.userDeletedZone` handled by recreating zone and resyncing
- [ ] SwiftData CloudKit review reports model compatibility and schema rollout: initialized/verified development schema, promoted before release, and additive-only production changes
- [ ] `NSUbiquitousKeyValueStore.didChangeExternallyNotification` observed
- [ ] Encryption review says `CKRecord.Reference` cannot use `encryptedValues` because CloudKit needs it server-side; no query/sort on encrypted fields; `CKAsset` is encrypted by default
- [ ] `CKSyncEngine` state serialization persisted across launches (iOS 17+)

## References

- See [references/cloudkit-patterns.md](references/cloudkit-patterns.md) for incremental sync, CKShare, zones, CKAsset storage, batch operations, and Dashboard usage.
- [CloudKit Framework](https://sosumi.ai/documentation/cloudkit)
- [CKContainer](https://sosumi.ai/documentation/cloudkit/ckcontainer)
- [CKRecord](https://sosumi.ai/documentation/cloudkit/ckrecord)
- [CKQuery](https://sosumi.ai/documentation/cloudkit/ckquery)
- [CKSubscription](https://sosumi.ai/documentation/cloudkit/cksubscription)
- [CKSyncEngine](https://sosumi.ai/documentation/cloudkit/cksyncengine)
- [CKShare](https://sosumi.ai/documentation/cloudkit/ckshare)
- [CKError](https://sosumi.ai/documentation/cloudkit/ckerror)
- [NSUbiquitousKeyValueStore](https://sosumi.ai/documentation/foundation/nsubiquitouskeyvaluestore)
- [SwiftData CloudKit sync](https://sosumi.ai/documentation/swiftdata/syncing-model-data-across-a-persons-devices)
