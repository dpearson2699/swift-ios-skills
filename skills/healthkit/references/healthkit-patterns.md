# HealthKit Extended Patterns

Overflow reference for the `healthkit` skill. Contains advanced patterns that exceed the main skill file's scope.

## Contents

- [Workout Session Lifecycle](#workout-session-lifecycle)
- [Platform and Authorization Edge Cases](#platform-and-authorization-edge-cases)
- [Background Delivery Details](#background-delivery-details)
- [Anchored Object Queries](#anchored-object-queries)
- [Predicate-Based Filtering](#predicate-based-filtering)
- [Statistics Collection for Charts](#statistics-collection-for-charts)
- [HealthKit + SwiftUI Integration](#healthkit--swiftui-integration)
- [Characteristic Types](#characteristic-types)

## Workout Session Lifecycle

`HKWorkoutSession` is available on iOS/iPadOS 17+, visionOS 1+, and watchOS
2+. `HKLiveWorkoutBuilder` is available on iOS/iPadOS 26+ and watchOS 5+.
When supporting iOS or iPadOS earlier than 26, gate live-builder code and use a
non-live workout save path where appropriate.

iPhone and iPad do not provide built-in live heart-rate samples. They require a
paired external heart-rate sensor for live heart-rate collection, while Apple
Watch workout sessions collect high-frequency heart-rate samples. iPhone also
often locks during workouts; if the app shows health metrics on the Lock
Screen, design around the system's workout-data access prompt and Live Activity
surface.

### Full Workout Manager

```swift
import HealthKit

@Observable
@MainActor
final class WorkoutManager: NSObject {
    let healthStore = HKHealthStore()

    private var session: HKWorkoutSession?
    private var builder: HKLiveWorkoutBuilder?

    var heartRate: Double = 0
    var activeCalories: Double = 0
    var distance: Double = 0
    var elapsedTime: TimeInterval = 0
    var isActive = false
    var finalizationError: Error?

    func startWorkout(activityType: HKWorkoutActivityType) async throws {
        let configuration = HKWorkoutConfiguration()
        configuration.activityType = activityType
        configuration.locationType = .outdoor

        let session = try HKWorkoutSession(
            healthStore: healthStore,
            configuration: configuration
        )
        let builder = session.associatedWorkoutBuilder()

        builder.dataSource = HKLiveWorkoutDataSource(
            healthStore: healthStore,
            workoutConfiguration: configuration
        )

        session.delegate = self
        builder.delegate = self

        self.session = session
        self.builder = builder

        session.startActivity(with: Date())
        try await builder.beginCollection(at: Date())
        isActive = true
    }

    func pause() {
        session?.pause()
    }

    func resume() {
        session?.resume()
    }

    func end() {
        guard let session else { return }
        session.stopActivity(with: Date())
    }

    private func finalizeStoppedWorkout(at date: Date) async {
        guard let builder else { return }

        do {
            try await builder.endCollection(at: date)
        } catch {
            finalizationError = error
            return
        }

        do {
            _ = try await builder.finishWorkout()
        } catch {
            finalizationError = error
            return
        }

        // A nil workout while locked is not a failed finish; the awaited return
        // is the success boundary.
        isActive = false
        self.session = nil
        self.builder = nil
    }
}

// MARK: - HKWorkoutSessionDelegate

extension WorkoutManager: HKWorkoutSessionDelegate {
    nonisolated func workoutSession(
        _ workoutSession: HKWorkoutSession,
        didChangeTo toState: HKWorkoutSessionState,
        from fromState: HKWorkoutSessionState,
        date: Date
    ) {
        Task { @MainActor in
            switch toState {
            case .running:
                isActive = true
            case .paused:
                isActive = false
            case .stopped:
                isActive = false
                await finalizeStoppedWorkout(at: date)
            case .ended:
                isActive = false
            default:
                break
            }
        }
    }

    nonisolated func workoutSession(
        _ workoutSession: HKWorkoutSession,
        didFailWithError error: Error
    ) {
        Task { @MainActor in
            print("Workout session failed: \(error)")
            isActive = false
        }
    }
}

// MARK: - HKLiveWorkoutBuilderDelegate

extension WorkoutManager: HKLiveWorkoutBuilderDelegate {
    nonisolated func workoutBuilderDidCollectEvent(
        _ workoutBuilder: HKLiveWorkoutBuilder
    ) {
        // Handle workout events (pause, resume, lap, etc.)
    }

    nonisolated func workoutBuilder(
        _ workoutBuilder: HKLiveWorkoutBuilder,
        didCollectDataOf collectedTypes: Set<HKSampleType>
    ) {
        Task { @MainActor in
            for type in collectedTypes {
                guard let quantityType = type as? HKQuantityType else { continue }

                let statistics = workoutBuilder.statistics(for: quantityType)

                switch quantityType {
                case HKQuantityType(.heartRate):
                    heartRate = statistics?.mostRecentQuantity()?
                        .doubleValue(for: HKUnit.count().unitDivided(by: .minute())) ?? 0

                case HKQuantityType(.activeEnergyBurned):
                    activeCalories = statistics?.sumQuantity()?
                        .doubleValue(for: .kilocalorie()) ?? 0

                case HKQuantityType(.distanceWalkingRunning):
                    distance = statistics?.sumQuantity()?
                        .doubleValue(for: .meter()) ?? 0

                default:
                    break
                }
            }

            elapsedTime = workoutBuilder.elapsedTime
        }
    }
}
```

### Multi-Device Mirroring (watchOS + iOS)

Start mirroring from the primary watchOS session. In the iOS companion app,
assign `workoutSessionMirroringStartHandler` as the app launches so it can
receive mirrored sessions even when launched in the background. The handler runs
on an arbitrary background queue and may be called more than once if the devices
disconnect and reconnect during a workout.

```swift
// On watchOS: start mirroring to companion iPhone
func startMirroring() async throws {
    try await session?.startMirroringToCompanionDevice()
}

// On iOS: receive the mirrored session
func setupMirroredSessionHandler() {
    healthStore.workoutSessionMirroringStartHandler = { mirroredSession in
        // mirroredSession is an HKWorkoutSession with type == .mirrored
        mirroredSession.delegate = self
        let builder = mirroredSession.associatedWorkoutBuilder()
        builder.delegate = self
    }
}

// Send data between devices
func sendDataToRemote(_ data: Data) async throws {
    try await session?.sendToRemoteWorkoutSession(data: data)
}
```

## Platform and Authorization Edge Cases

- Call `HKHealthStore.isHealthDataAvailable()` before any other HealthKit API.
  Current Apple docs say Health data is available on iOS, watchOS, visionOS,
  iPadOS 17+, and iOS apps running on Vision Pro. It is unavailable on iPadOS
  16 or earlier and may be restricted by managed device policy.
- Enabling the HealthKit capability for an iOS app can add `healthkit` to
  `UIRequiredDeviceCapabilities`, preventing installation on unsupported
  devices. Remove that entry only when HealthKit is optional and the app has a
  useful non-HealthKit mode.
- `authorizationStatus(for:)` is for write/share authorization. HealthKit does
  not reveal whether read access was granted or denied. If read access is
  denied, queries return samples your app saved successfully, which can look
  like partial or empty data.
- People can change HealthKit permissions later in Settings or the Health app.
  Refresh permission-sensitive UI and write paths instead of assuming the
  original authorization outcome still applies.
- In Vision Pro Guest User sessions, previously authorized data may be readable,
  but new authorization and writes can fail. Treat HealthKit writes as
  best-effort unless the user explicitly initiated a save action that needs an
  explanation.

## Background Delivery Details

Background delivery requires the HealthKit Background Delivery capability
(`com.apple.developer.healthkit.background-delivery` on current Apple docs) and
an executed `HKObserverQuery` for the same sample type. Set up observer queries
when the app launches, then call `enableBackgroundDelivery` once; the system
persists the registration.

```swift
func configureHealthKitBackgroundDelivery() async throws {
    let stepType = HKQuantityType(.stepCount)

    let query = HKObserverQuery(
        sampleType: stepType,
        predicate: nil
    ) { _, completionHandler, error in
        defer { completionHandler() }
        guard error == nil else { return }
        Task {
            // Run an anchored query or statistics refresh here.
        }
    }

    healthStore.execute(query)

    try await healthStore.enableBackgroundDelivery(
        for: stepType,
        frequency: .hourly
    )
}
```

Treat `HKUpdateFrequency` as a maximum delivery rate, not a guarantee. Some
types have tighter system caps; for example, iOS step-count background delivery
is capped at hourly even if `.immediate` is requested. Background server queries
are not supported on Simulator, so validate delivery on real hardware. If the
observer completion handler is not called, HealthKit backs off and can stop
sending background updates after repeated failures.

## Anchored Object Queries

Use `HKAnchoredObjectQuery` for incremental updates -- only fetches samples added or deleted since the last anchor.

```swift
@Observable
final class StepTracker {
    private let healthStore = HKHealthStore()
    private var anchor: HKQueryAnchor?
    private var observerQuery: HKObserverQuery?

    var totalSteps: Double = 0

    func startMonitoring() {
        let stepType = HKQuantityType(.stepCount)

        // Initial fetch + ongoing updates
        let anchoredQuery = HKAnchoredObjectQuery(
            type: stepType,
            predicate: nil,
            anchor: anchor,
            limit: HKObjectQueryNoLimit
        ) { [weak self] query, added, deleted, newAnchor, error in
            guard let self else { return }
            self.anchor = newAnchor
            self.processNewSamples(added ?? [])
        }

        // Enable updates handler for real-time monitoring
        anchoredQuery.updateHandler = { [weak self] query, added, deleted, newAnchor, error in
            guard let self else { return }
            self.anchor = newAnchor
            self.processNewSamples(added ?? [])
        }

        healthStore.execute(anchoredQuery)
    }

    private func processNewSamples(_ samples: [HKSample]) {
        for sample in samples {
            guard let quantitySample = sample as? HKQuantitySample else { continue }
            let steps = quantitySample.quantity.doubleValue(for: .count())
            totalSteps += steps
        }
    }
}
```

### Anchored Query with Async Descriptor

```swift
import HealthKit

let stepType = HKQuantityType(.stepCount)
let descriptor = HKAnchoredObjectQueryDescriptor(
    predicates: [.quantitySample(type: stepType)],
    anchor: savedAnchor
)

// One-shot
let result = try await descriptor.result(for: healthStore)
let newSamples = result.addedSamples
let deletedObjects = result.deletedObjects
let newAnchor = result.newAnchor

// Long-running with updates
for try await result in descriptor.results(for: healthStore) {
    // Process result.addedSamples and result.deletedObjects
}
```

## Predicate-Based Filtering

### Time-Based Predicates

```swift
// Samples from today
let today = Calendar.current.startOfDay(for: Date())
let tomorrow = Calendar.current.date(byAdding: .day, value: 1, to: today)!
let todayPredicate = HKQuery.predicateForSamples(
    withStart: today, end: tomorrow
)

// Samples from the last 7 days
let oneWeekAgo = Calendar.current.date(byAdding: .day, value: -7, to: Date())!
let weekPredicate = HKQuery.predicateForSamples(
    withStart: oneWeekAgo, end: Date()
)

// Strict: sample must be entirely within the range
let strictPredicate = HKQuery.predicateForSamples(
    withStart: today, end: tomorrow,
    options: .strictStartDate
)
```

### Source-Based Predicates

```swift
// Only samples from the current app
let sourcePredicate = HKQuery.predicateForObjects(
    from: HKSource.default()
)

// Only samples from Apple Watch
let devicePredicate = HKQuery.predicateForObjects(
    withDeviceProperty: HKDevicePropertyKeyModel,
    allowedValues: ["Watch"]
)
```

### Compound Predicates

```swift
let todayFromWatch = NSCompoundPredicate(
    andPredicateWithSubpredicates: [todayPredicate, devicePredicate]
)

let descriptor = HKSampleQueryDescriptor(
    predicates: [.quantitySample(type: stepType, predicate: todayFromWatch)],
    sortDescriptors: [SortDescriptor(\.endDate, order: .reverse)]
)
```

## Statistics Collection for Charts

### Weekly Step Count Chart Data

```swift
struct DailyStepData: Identifiable {
    let id = UUID()
    let date: Date
    let steps: Double
}

func fetchWeeklyStepData() async throws -> [DailyStepData] {
    let calendar = Calendar.current
    let today = calendar.startOfDay(for: Date())
    let endDate = calendar.date(byAdding: .day, value: 1, to: today)!
    let startDate = calendar.date(byAdding: .day, value: -7, to: endDate)!

    let stepType = HKQuantityType(.stepCount)
    let predicate = HKQuery.predicateForSamples(
        withStart: startDate, end: endDate
    )
    let samplePredicate = HKSamplePredicate.quantitySample(
        type: stepType, predicate: predicate
    )

    let query = HKStatisticsCollectionQueryDescriptor(
        predicate: samplePredicate,
        options: .cumulativeSum,
        anchorDate: endDate,
        intervalComponents: DateComponents(day: 1)
    )

    let collection = try await query.result(for: healthStore)

    var data: [DailyStepData] = []
    collection.statisticsCollection.enumerateStatistics(
        from: startDate, to: endDate
    ) { statistics, _ in
        let steps = statistics.sumQuantity()?
            .doubleValue(for: .count()) ?? 0
        data.append(DailyStepData(date: statistics.startDate, steps: steps))
    }

    return data
}
```

### Hourly Heart Rate Averages

```swift
func fetchHourlyHeartRate(for date: Date) async throws -> [(hour: Date, bpm: Double)] {
    let calendar = Calendar.current
    let startOfDay = calendar.startOfDay(for: date)
    let endOfDay = calendar.date(byAdding: .day, value: 1, to: startOfDay)!

    let heartRateType = HKQuantityType(.heartRate)
    let predicate = HKQuery.predicateForSamples(
        withStart: startOfDay, end: endOfDay
    )
    let samplePredicate = HKSamplePredicate.quantitySample(
        type: heartRateType, predicate: predicate
    )

    let query = HKStatisticsCollectionQueryDescriptor(
        predicate: samplePredicate,
        options: .discreteAverage,
        anchorDate: endOfDay,
        intervalComponents: DateComponents(hour: 1)
    )

    let collection = try await query.result(for: healthStore)
    let unit = HKUnit.count().unitDivided(by: .minute())

    var hourlyData: [(hour: Date, bpm: Double)] = []
    collection.statisticsCollection.enumerateStatistics(
        from: startOfDay, to: endOfDay
    ) { statistics, _ in
        if let avg = statistics.averageQuantity()?.doubleValue(for: unit) {
            hourlyData.append((hour: statistics.startDate, bpm: avg))
        }
    }

    return hourlyData
}
```

## HealthKit + SwiftUI Integration

### HealthKit Manager with `@Observable`

```swift
import HealthKit
import SwiftUI

@Observable
@MainActor
final class HealthManager {
    let healthStore = HKHealthStore()

    var isAuthorized = false
    var todaySteps: Double = 0
    var recentHeartRate: Double = 0

    var isAvailable: Bool {
        HKHealthStore.isHealthDataAvailable()
    }

    func requestAuthorization() async throws {
        let typesToRead: Set<HKObjectType> = [
            HKQuantityType(.stepCount),
            HKQuantityType(.heartRate)
        ]

        try await healthStore.requestAuthorization(
            toShare: [],
            read: typesToRead
        )
        isAuthorized = true
    }

    func refreshData() async {
        async let steps = fetchTodaySteps()
        async let heartRate = fetchLatestHeartRate()

        todaySteps = (try? await steps) ?? 0
        recentHeartRate = (try? await heartRate) ?? 0
    }

    private func fetchTodaySteps() async throws -> Double {
        let calendar = Calendar.current
        let startOfDay = calendar.startOfDay(for: Date())
        let predicate = HKQuery.predicateForSamples(
            withStart: startOfDay, end: Date()
        )
        let stepType = HKQuantityType(.stepCount)
        let samplePredicate = HKSamplePredicate.quantitySample(
            type: stepType, predicate: predicate
        )
        let query = HKStatisticsQueryDescriptor(
            predicate: samplePredicate, options: .cumulativeSum
        )
        return try await query.result(for: healthStore)?
            .sumQuantity()?.doubleValue(for: .count()) ?? 0
    }

    private func fetchLatestHeartRate() async throws -> Double {
        let heartRateType = HKQuantityType(.heartRate)
        let descriptor = HKSampleQueryDescriptor(
            predicates: [.quantitySample(type: heartRateType)],
            sortDescriptors: [SortDescriptor(\.endDate, order: .reverse)],
            limit: 1
        )
        let results = try await descriptor.result(for: healthStore)
        let unit = HKUnit.count().unitDivided(by: .minute())
        return results.first?.quantity.doubleValue(for: unit) ?? 0
    }
}
```

### SwiftUI View with HealthKit

```swift
struct HealthDashboardView: View {
    @Environment(HealthManager.self) private var healthManager

    var body: some View {
        NavigationStack {
            Group {
                if !healthManager.isAvailable {
                    ContentUnavailableView(
                        "HealthKit Unavailable",
                        systemImage: "heart.slash",
                        description: Text("This device does not support HealthKit.")
                    )
                } else if !healthManager.isAuthorized {
                    authorizationPrompt
                } else {
                    healthDataView
                }
            }
            .navigationTitle("Health")
        }
    }

    private var authorizationPrompt: some View {
        ContentUnavailableView {
            Label("Health Access", systemImage: "heart.text.square")
        } description: {
            Text("Grant access to view your health data.")
        } actions: {
            Button("Authorize") {
                Task {
                    try? await healthManager.requestAuthorization()
                }
            }
            .buttonStyle(.borderedProminent)
        }
    }

    private var healthDataView: some View {
        List {
            Section("Today") {
                LabeledContent("Steps") {
                    Text(healthManager.todaySteps, format: .number.precision(.fractionLength(0)))
                }
                LabeledContent("Heart Rate") {
                    Text("\(Int(healthManager.recentHeartRate)) bpm")
                }
            }
        }
        .task {
            await healthManager.refreshData()
        }
        .refreshable {
            await healthManager.refreshData()
        }
    }
}
```

### App Entry Point Wiring

```swift
@main
struct MyHealthApp: App {
    @State private var healthManager = HealthManager()

    var body: some Scene {
        WindowGroup {
            HealthDashboardView()
                .environment(healthManager)
        }
    }
}
```

## Characteristic Types

Characteristic types are read-only values set by the user in the Health app. They do not require sample queries.

```swift
func readCharacteristics() throws {
    // Date of birth
    let dobComponents = try healthStore.dateOfBirthComponents()
    let calendar = Calendar.current
    if let dob = calendar.date(from: dobComponents) {
        let age = calendar.dateComponents([.year], from: dob, to: Date()).year ?? 0
        print("Age: \(age)")
    }

    // Biological sex
    let biologicalSex = try healthStore.biologicalSex().biologicalSex
    switch biologicalSex {
    case .female: print("Female")
    case .male: print("Male")
    case .other: print("Other")
    case .notSet: print("Not set")
    @unknown default: break
    }

    // Blood type
    let bloodType = try healthStore.bloodType().bloodType
    switch bloodType {
    case .aPositive: print("A+")
    case .aNegative: print("A-")
    case .bPositive: print("B+")
    case .bNegative: print("B-")
    case .abPositive: print("AB+")
    case .abNegative: print("AB-")
    case .oPositive: print("O+")
    case .oNegative: print("O-")
    case .notSet: print("Not set")
    @unknown default: break
    }

    // Fitzpatrick skin type
    let skinType = try healthStore.fitzpatrickSkinType().skinType
    print("Skin type: \(skinType.rawValue)")

    // Wheelchair use
    let wheelchair = try healthStore.wheelchairUse().wheelchairUse
    print("Wheelchair: \(wheelchair == .yes)")
}
```

**Important:** These throw an error if the value is not set, so always use `try` and handle the `HKError.errorNoData` case.

```swift
do {
    let dob = try healthStore.dateOfBirthComponents()
    // Use dob
} catch let error as HKError where error.code == .errorNoData {
    // User hasn't set date of birth in Health app
} catch {
    // Other error
}
```
