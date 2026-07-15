# Staged Core Data Migration

Use `NSStagedMigrationManager` on iOS 17+ to sequence lightweight and custom
schema migrations. Use compiled model-version checksums, not model names, when
constructing stages and model references.

## Define the Stages

```swift
import CoreData

let checksumV1 = "<ModelV1 version checksum>"
let checksumV2 = "<ModelV2 version checksum>"
let checksumV3 = "<ModelV3 version checksum>"

let stage1to2 = NSLightweightMigrationStage([checksumV1, checksumV2])
stage1to2.label = "Add isFavorite property"

let modelV2 = NSManagedObjectModelReference(
    name: "ModelV2", in: Bundle.main, versionChecksum: checksumV2
)
let modelV3 = NSManagedObjectModelReference(
    name: "ModelV3", in: Bundle.main, versionChecksum: checksumV3
)
let stage2to3 = NSCustomMigrationStage(migratingFrom: modelV2, to: modelV3)
stage2to3.label = "Split name into firstName/lastName"
stage2to3.willMigrateHandler = { migrationManager, currentStage in
    guard let container = migrationManager.container else { return }
    let context = container.newBackgroundContext()
    try context.performAndWait {
        let request = NSFetchRequest<NSManagedObject>(entityName: "Person")
        for person in try context.fetch(request) {
            let fullName = person.value(forKey: "name") as? String ?? ""
            let parts = fullName.split(separator: " ", maxSplits: 1)
            person.setValue(String(parts.first ?? ""), forKey: "firstName")
            person.setValue(
                parts.count > 1 ? String(parts.last!) : "",
                forKey: "lastName"
            )
        }
        try context.save()
    }
}
```

## Configure the Store

```swift
let manager = NSStagedMigrationManager([stage1to2, stage2to3])
let description = NSPersistentStoreDescription()
description.setOption(
    manager,
    forKey: NSPersistentStoreStagedMigrationManagerOptionKey
)
container.persistentStoreDescriptions = [description]
container.loadPersistentStores { _, error in
    if let error { fatalError("Migration failed: \(error)") }
}
```

For systems below iOS 17, use lightweight migration
(`NSInferMappingModelAutomaticallyOption`) or mapping models.

## References

- [NSStagedMigrationManager](https://sosumi.ai/documentation/coredata/nsstagedmigrationmanager)
