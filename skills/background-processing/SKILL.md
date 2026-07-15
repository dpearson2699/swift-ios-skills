---
name: background-processing
description: "Schedule and execute background work on iOS using BGTaskScheduler. Use when registering BGAppRefreshTask for short background fetches, BGProcessingTask for long-running maintenance, BGContinuedProcessingTask (iOS 26+) for foreground-started work that continues in background, background URLSession downloads, or background push notifications. Covers Info.plist configuration, expiration handling, task completion, and debugging with simulated launches."
---

# Background Processing

Register, schedule, and execute background work on iOS using the BackgroundTasks
framework, background URLSession, and background push notifications.

## Contents

- [Info.plist Configuration](#infoplist-configuration)
- [BGTaskScheduler Registration](#bgtaskscheduler-registration)
- [BGAppRefreshTask Patterns](#bgapprefreshtask-patterns)
- [BGProcessingTask Patterns](#bgprocessingtask-patterns)
- [BGContinuedProcessingTask (iOS 26+)](#bgcontinuedprocessingtask-ios-26)
- [Background URLSession Downloads](#background-urlsession-downloads)
- [Background Push Triggers](#background-push-triggers)
- [Common Mistakes](#common-mistakes)
- [Review Checklist](#review-checklist)
- [References](#references)

## Info.plist Configuration

Every task identifier **must** be declared in `Info.plist` under
`BGTaskSchedulerPermittedIdentifiers`, or `submit(_:)` throws
`BGTaskScheduler.Error.Code.notPermitted`.

```xml
<key>BGTaskSchedulerPermittedIdentifiers</key>
<array>
    <string>com.example.app.refresh</string>
    <string>com.example.app.db-cleanup</string>
    <string>com.example.app.export.*</string>
</array>
```

Also enable the required `UIBackgroundModes`:

```xml
<key>UIBackgroundModes</key>
<array>
    <string>fetch</string>       <!-- Required for BGAppRefreshTask -->
    <string>processing</string>  <!-- Required for BGProcessingTask -->
</array>
```

In Xcode: target > Signing & Capabilities > Background Modes > enable "Background fetch" and "Background processing".

## BGTaskScheduler Registration

Register handlers **before** app launch completes. In UIKit, register in
`application(_:didFinishLaunchingWithOptions:)`; in SwiftUI, register in `App.init()`.

### UIKit Registration

```swift
import BackgroundTasks

@main
class AppDelegate: UIResponder, UIApplicationDelegate {
    func application(
        _ application: UIApplication,
        didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
    ) -> Bool {
        BGTaskScheduler.shared.register(
            forTaskWithIdentifier: "com.example.app.refresh",
            using: nil  // nil = default background queue
        ) { task in
            self.handleAppRefresh(task: task as! BGAppRefreshTask)
        }

        BGTaskScheduler.shared.register(
            forTaskWithIdentifier: "com.example.app.db-cleanup",
            using: nil
        ) { task in
            self.handleDatabaseCleanup(task: task as! BGProcessingTask)
        }

        return true
    }
}
```

### SwiftUI Registration

```swift
import SwiftUI
import BackgroundTasks

@main
struct MyApp: App {
    init() {
        BGTaskScheduler.shared.register(
            forTaskWithIdentifier: "com.example.app.refresh",
            using: nil
        ) { task in
            BackgroundTaskManager.shared.handleAppRefresh(
                task: task as! BGAppRefreshTask
            )
        }
    }

    var body: some Scene {
        WindowGroup { ContentView() }
    }
}
```

## BGAppRefreshTask Patterns

Short-lived tasks (~30 seconds) for fetching small data updates. The system
decides when to launch; `earliestBeginDate` is only a lower-bound hint.

```swift
func scheduleAppRefresh() {
    let request = BGAppRefreshTaskRequest(
        identifier: "com.example.app.refresh"
    )
    request.earliestBeginDate = Date(timeIntervalSinceNow: 15 * 60)
    do {
        try BGTaskScheduler.shared.submit(request)
    } catch {
        print("Could not schedule app refresh: \(error)")
    }
}

func handleAppRefresh(task: BGAppRefreshTask) {
    // Schedule the next refresh before doing work
    scheduleAppRefresh()

    let fetchTask = Task {
        do {
            let data = try await APIClient.shared.fetchLatestFeed()
            await FeedStore.shared.update(with: data)
            task.setTaskCompleted(success: true)
        } catch {
            task.setTaskCompleted(success: false)
        }
    }

    // CRITICAL: Handle expiration -- system can revoke time at any moment
    task.expirationHandler = {
        fetchTask.cancel()
        task.setTaskCompleted(success: false)
    }
}
```

## BGProcessingTask Patterns

Long-running tasks (minutes) for maintenance, data processing, or cleanup.
They run while the device is idle and can require external power; the same
`earliestBeginDate` lower-bound rule applies.

```swift
func scheduleProcessingTask() {
    let request = BGProcessingTaskRequest(
        identifier: "com.example.app.db-cleanup"
    )
    request.requiresNetworkConnectivity = false
    request.requiresExternalPower = true
    request.earliestBeginDate = Date(timeIntervalSinceNow: 60 * 60)
    do {
        try BGTaskScheduler.shared.submit(request)
    } catch {
        print("Could not schedule processing task: \(error)")
    }
}

func handleDatabaseCleanup(task: BGProcessingTask) {
    scheduleProcessingTask()

    let cleanupTask = Task {
        do {
            try await DatabaseManager.shared.purgeExpiredRecords()
            try await DatabaseManager.shared.rebuildIndexes()
            task.setTaskCompleted(success: true)
        } catch {
            task.setTaskCompleted(success: false)
        }
    }

    task.expirationHandler = {
        cleanupTask.cancel()
        task.setTaskCompleted(success: false)
    }
}
```

## BGContinuedProcessingTask (iOS 26+)

A task initiated in the foreground by a user action that continues running in the
background. The system displays progress via a Live Activity. Conforms to
`ProgressReporting`.

**Availability:** iOS 26.0+, iPadOS 26.0+

Unlike `BGAppRefreshTask` and `BGProcessingTask`, this task starts immediately
from the foreground. The system can terminate it under resource pressure,
prioritizing tasks that report minimal progress first. Set `expirationHandler` for user or system cancellation, cancel in-flight work, and clean up partial output before reporting completion.

```swift
import BackgroundTasks

func startExport() {
    // Register the task handler at app launch, not here.
    // BGTaskScheduler requires registration before app launch completes.
    let jobID = UUID().uuidString
    let request = BGContinuedProcessingTaskRequest(
        identifier: "com.example.app.export.\(jobID)",
        title: "Exporting Photos",
        subtitle: "Processing 247 items"
    )
    // Use a permitted base wildcard identifier: com.example.app.export.*
    // earliestBeginDate is ignored for continued processing requests.
    // .queue: begin as soon as possible if can't run immediately
    // .fail: fail submission if can't run immediately
    request.strategy = .queue

    do {
        try BGTaskScheduler.shared.submit(request)
    } catch {
        print("Could not submit continued processing task: \(error)")
    }
}

func performExport(task: BGContinuedProcessingTask) async {
    let items = await PhotoLibrary.shared.itemsToExport()
    let progress = task.progress
    progress.totalUnitCount = Int64(items.count)

    for (index, item) in items.enumerated() {
        if Task.isCancelled { break }

        await PhotoExporter.shared.export(item)
        progress.completedUnitCount = Int64(index + 1)

        // Update the user-facing title/subtitle
        task.updateTitle(
            "Exporting Photos",
            subtitle: "\(index + 1) of \(items.count) complete"
        )
    }

    task.setTaskCompleted(success: !Task.isCancelled)
}
```

For GPU work, check support and enable Background GPU Access (`com.apple.developer.background-tasks.continued-processing.gpu`):

```swift
let supported = BGTaskScheduler.supportedResources
if supported.contains(.gpu) {
    request.requiredResources = .gpu
}
```

## Background URLSession Downloads

Use `URLSessionConfiguration.background` for downloads that continue even after
the app is suspended or terminated. The system handles the transfer out of
process.

```swift
class DownloadManager: NSObject, URLSessionDownloadDelegate {
    static let shared = DownloadManager()

    private lazy var session: URLSession = {
        let config = URLSessionConfiguration.background(
            withIdentifier: "com.example.app.background-download"
        )
        config.isDiscretionary = true
        config.sessionSendsLaunchEvents = true
        return URLSession(configuration: config, delegate: self, delegateQueue: nil)
    }()

    func startDownload(from url: URL) {
        let task = session.downloadTask(with: url)
        task.earliestBeginDate = Date(timeIntervalSinceNow: 60)
        task.resume()
    }

    func urlSession(
        _ session: URLSession,
        downloadTask: URLSessionDownloadTask,
        didFinishDownloadingTo location: URL
    ) {
        // Move file from tmp before this method returns
        let dest = FileManager.default.urls(
            for: .documentDirectory, in: .userDomainMask
        )[0].appendingPathComponent("download.dat")
        try? FileManager.default.moveItem(at: location, to: dest)
    }

    func urlSession(
        _ session: URLSession,
        task: URLSessionTask,
        didCompleteWithError error: (any Error)?
    ) {
        if let error { print("Download failed: \(error)") }
    }
}
```

Handle app relaunch — store and invoke the system completion handler:

```swift
// In AppDelegate:
func application(
    _ application: UIApplication,
    handleEventsForBackgroundURLSession identifier: String,
    completionHandler: @escaping () -> Void
) {
    backgroundSessionCompletionHandler = completionHandler
}

// In URLSessionDelegate — call stored handler when events finish:
func urlSessionDidFinishEvents(forBackgroundURLSession session: URLSession) {
    Task { @MainActor in
        self.backgroundSessionCompletionHandler?()
        self.backgroundSessionCompletionHandler = nil
    }
}
```

## Background Push Triggers

Silent push notifications wake your app briefly to fetch new content. Set
`content-available: 1` in the push payload.

```json
{ "aps": { "content-available": 1 }, "custom-data": "new-messages" }
```

Send the APNs request with `apns-push-type: background` and
`apns-priority: 5`. Background push delivery is low priority and not
guaranteed; keep sends infrequent, generally no more than two or three per
hour.

Handle in AppDelegate:

```swift
func application(
    _ application: UIApplication,
    didReceiveRemoteNotification userInfo: [AnyHashable: Any],
    fetchCompletionHandler completionHandler:
        @escaping (UIBackgroundFetchResult) -> Void
) {
    Task {
        do {
            let hasNew = try await MessageStore.shared.fetchNewMessages()
            completionHandler(hasNew ? .newData : .noData)
        } catch {
            completionHandler(.failed)
        }
    }
}
```

Enable "Remote notifications" in Background Modes and register:

```swift
UIApplication.shared.registerForRemoteNotifications()
```

## Common Mistakes

### 1. Missing Info.plist identifiers

```swift
// DON'T: Submit a task whose identifier isn't in BGTaskSchedulerPermittedIdentifiers
let request = BGAppRefreshTaskRequest(identifier: "com.example.app.refresh")
try BGTaskScheduler.shared.submit(request)  // Throws .notPermitted

// DO: Add every identifier to Info.plist BGTaskSchedulerPermittedIdentifiers
// <string>com.example.app.refresh</string>
```

### 2. Not calling setTaskCompleted(success:)

Use the canonical app-refresh or processing handler above: every success,
failure, and cancellation path reports completion exactly once.

### 3. Ignoring the expiration handler

Use the same canonical handler to cancel in-flight work and report failure from
`expirationHandler`.

### 4. Scheduling too frequently

The scheduling sections own the lower-bound rule. Avoid minute-scale refresh
requests; the system still chooses actual launch time.

### 5. Over-relying on background time

```swift
// DON'T: Start a 10-minute operation assuming it will finish
func handleRefresh(task: BGAppRefreshTask) {
    Task { await tenMinuteSync() }
}

// DO: Design work to be incremental and cancellable
func handleRefresh(task: BGAppRefreshTask) {
    let work = Task {
        for batch in batches {
            try Task.checkCancellation()
            await processBatch(batch)
            await saveBatchProgress(batch)
        }
        task.setTaskCompleted(success: true)
    }
    task.expirationHandler = {
        work.cancel()
        task.setTaskCompleted(success: false)
    }
}
```

## Review Checklist

- [ ] All task identifiers listed in `BGTaskSchedulerPermittedIdentifiers`
- [ ] Required `UIBackgroundModes` enabled (`fetch`, `processing`)
- [ ] Tasks registered before app launch completes
- [ ] `setTaskCompleted(success:)` called on every code path
- [ ] `expirationHandler` set and cancels in-flight work
- [ ] Next task scheduled inside the handler (re-schedule pattern)
- [ ] `earliestBeginDate` uses reasonable intervals and is treated as a hint
- [ ] Background URLSession uses delegate (not async/closures)
- [ ] Background URLSession file moved in `didFinishDownloadingTo` before return
- [ ] `handleEventsForBackgroundURLSession` stores and calls completion handler
- [ ] Background push payload includes `content-available: 1`
- [ ] Background push APNs request uses `apns-push-type: background` and `apns-priority: 5`
- [ ] `fetchCompletionHandler` called promptly with correct result
- [ ] BGContinuedProcessingTask reports progress via `ProgressReporting`
- [ ] Work is incremental and cancellation-safe (`Task.checkCancellation()`)
- [ ] No blocking synchronous work in task handlers

## References

- See [references/background-task-patterns.md](references/background-task-patterns.md) for extended patterns, background
  URLSession edge cases, debugging with simulated launches, and background push
  best practices.
- [BGTaskScheduler](https://sosumi.ai/documentation/backgroundtasks/bgtaskscheduler)
- [BGAppRefreshTask](https://sosumi.ai/documentation/backgroundtasks/bgapprefreshtask)
- [BGProcessingTask](https://sosumi.ai/documentation/backgroundtasks/bgprocessingtask)
- [BGContinuedProcessingTask](https://sosumi.ai/documentation/backgroundtasks/bgcontinuedprocessingtask) (iOS 26+)
- [BGContinuedProcessingTaskRequest](https://sosumi.ai/documentation/backgroundtasks/bgcontinuedprocessingtaskrequest) (iOS 26+)
- [Using background tasks to update your app](https://sosumi.ai/documentation/uikit/using-background-tasks-to-update-your-app)
- [Performing long-running tasks on iOS and iPadOS](https://sosumi.ai/documentation/backgroundtasks/performing-long-running-tasks-on-ios-and-ipados)
