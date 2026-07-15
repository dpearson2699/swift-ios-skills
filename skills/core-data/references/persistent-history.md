# Persistent History Across Targets

Use persistent history when an app, extension, widget, or other process writes
the same store and each consumer must merge transactions it has not processed.

## Enable History Tracking

Set the options before loading the persistent store:

```swift
let description = NSPersistentStoreDescription()
description.setOption(true as NSNumber, forKey: NSPersistentHistoryTrackingKey)
description.setOption(true as NSNumber,
    forKey: NSPersistentStoreRemoteChangeNotificationPostOptionKey)
container.persistentStoreDescriptions = [description]
```

## Observe, Fetch, Merge, and Purge

```swift
NotificationCenter.default.addObserver(
    self,
    selector: #selector(storeRemoteChange(_:)),
    name: .NSPersistentStoreRemoteChange,
    object: container.persistentStoreCoordinator
)

@objc func storeRemoteChange(_ notification: Notification) {
    let context = container.newBackgroundContext()
    context.perform {
        let request = NSPersistentHistoryChangeRequest.fetchHistory(
            after: self.lastToken
        )
        if let result = try? context.execute(request) as? NSPersistentHistoryResult,
           let transactions = result.result as? [NSPersistentHistoryTransaction] {
            for transaction in transactions {
                self.container.viewContext.mergeChanges(
                    fromContextDidSave: transaction.objectIDNotification()
                )
                self.lastToken = transaction.token
            }
        }
    }
}
```

Persist `lastToken` per target so processing resumes across launches. Purge only
after every relevant consumer has advanced beyond the cutoff; a single target's
latest token is not automatically safe for all targets.

```swift
let purge = NSPersistentHistoryChangeRequest.deleteHistory(before: safeCutoff)
try context.execute(purge)
```

## References

- [NSPersistentHistoryChangeRequest](https://sosumi.ai/documentation/coredata/nspersistenthistorychangerequest)
