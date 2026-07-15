---
name: healthkit
description: "Read, write, and query Apple Health data using HealthKit. Covers HKHealthStore authorization, sample queries, statistics queries, statistics collection queries for charts, saving HKQuantitySample data, background delivery, workout sessions with HKWorkoutSession and HKLiveWorkoutBuilder, HKUnit, and HKQuantityTypeIdentifier values. Use when integrating with Apple Health, displaying health metrics, recording workouts, or enabling background health data delivery."
---

# HealthKit

Read and write health and fitness data from the Apple Health store. Covers authorization, queries, writing samples, background delivery, and workout sessions. Targets Swift 6.3 / iOS 26+.

## Contents

- [Setup and Availability](#setup-and-availability)
- [Authorization](#authorization)
- [Reading Data: Sample Queries](#reading-data-sample-queries)
- [Reading Data: Statistics Queries](#reading-data-statistics-queries)
- [Reading Data: Statistics Collection Queries](#reading-data-statistics-collection-queries)
- [Writing Data](#writing-data)
- [Background Delivery](#background-delivery)
- [Workout Sessions](#workout-sessions)
- [Common Data Types](#common-data-types)
- [HKUnit Reference](#hkunit-reference)
- [Common Mistakes](#common-mistakes)
- [Review Checklist](#review-checklist)
- [References](#references)

## Setup and Availability

### Project Configuration

1. Enable the HealthKit capability in Xcode (adds the entitlement)
2. Add `NSHealthShareUsageDescription` (read) and `NSHealthUpdateUsageDescription` (write) to Info.plist
3. For background delivery, enable the "Background Delivery" sub-capability

### Availability Check

Always check availability before calling other HealthKit APIs. Health data is
available on iOS, watchOS, visionOS, iPadOS 17+, and iOS apps running on
Vision Pro. It is unavailable on iPadOS 16 or earlier and may be restricted by
managed device policy.

```swift
import HealthKit

guard HKHealthStore.isHealthDataAvailable() else {
    // Health data is unavailable or restricted on this device.
    return
}

let healthStore = HKHealthStore()
```

Create a single `HKHealthStore` instance and reuse it throughout your app. It
is thread-safe. If HealthKit is optional, review Xcode's generated
`UIRequiredDeviceCapabilities` `healthkit` entry so unsupported devices are not
excluded unintentionally.

## Authorization

Request only the types your app genuinely needs. App Review rejects apps that over-request.

```swift
func requestAuthorization() async throws {
    let typesToShare: Set<HKSampleType> = [
        HKQuantityType(.stepCount),
        HKQuantityType(.activeEnergyBurned)
    ]

    let typesToRead: Set<HKObjectType> = [
        HKQuantityType(.stepCount),
        HKQuantityType(.heartRate),
        HKQuantityType(.activeEnergyBurned),
        HKCharacteristicType(.dateOfBirth)
    ]

    try await healthStore.requestAuthorization(
        toShare: typesToShare,
        read: typesToRead
    )
}
```

### Checking Authorization Status

`authorizationStatus(for:)` reports write/share authorization. HealthKit does
not reveal whether read permission was granted or denied. If the user denies
read access, queries return only samples your app successfully saved, which may
look like empty or partial data.

```swift
let status = healthStore.authorizationStatus(
    for: HKQuantityType(.stepCount)
)

switch status {
case .notDetermined:
    // Haven't requested yet -- safe to call requestAuthorization
    break
case .sharingAuthorized:
    // User granted write access
    break
case .sharingDenied:
    // User denied write access (read denial is indistinguishable from "no data")
    break
@unknown default:
    break
}
```

## Reading Data: Sample Queries

Use `HKSampleQueryDescriptor` (async/await) for one-shot reads. Prefer descriptors over the older callback-based `HKSampleQuery`.

```swift
func fetchRecentHeartRates() async throws -> [HKQuantitySample] {
    let heartRateType = HKQuantityType(.heartRate)

    let descriptor = HKSampleQueryDescriptor(
        predicates: [.quantitySample(type: heartRateType)],
        sortDescriptors: [SortDescriptor(\.endDate, order: .reverse)],
        limit: 20
    )

    let results = try await descriptor.result(for: healthStore)
    return results
}

// Extracting values from samples:
for sample in results {
    let bpm = sample.quantity.doubleValue(
        for: HKUnit.count().unitDivided(by: .minute())
    )
    print("\(bpm) bpm at \(sample.endDate)")
}
```

## Reading Data: Statistics Queries

Use `HKStatisticsQueryDescriptor` for aggregated single-value stats (sum, average, min, max).

```swift
func fetchTodayStepCount() async throws -> Double? {
    let calendar = Calendar.current
    let startOfDay = calendar.startOfDay(for: Date())
    let endOfDay = calendar.date(byAdding: .day, value: 1, to: startOfDay)!

    let predicate = HKQuery.predicateForSamples(
        withStart: startOfDay, end: endOfDay
    )
    let stepType = HKQuantityType(.stepCount)
    let samplePredicate = HKSamplePredicate.quantitySample(
        type: stepType, predicate: predicate
    )

    let query = HKStatisticsQueryDescriptor(
        predicate: samplePredicate,
        options: .cumulativeSum
    )

    let result = try await query.result(for: healthStore)
    return result?.sumQuantity()?.doubleValue(for: .count())
}
```

**Options by data type:**
- Cumulative types (steps, calories): `.cumulativeSum`
- Discrete types (heart rate, weight): `.discreteAverage`, `.discreteMin`, `.discreteMax`

## Reading Data: Statistics Collection Queries

Use `HKStatisticsCollectionQueryDescriptor` for time-series data grouped into intervals -- ideal for charts.

```swift
func fetchDailySteps(forLast days: Int) async throws -> [(date: Date, steps: Double)] {
    let calendar = Calendar.current
    let endDate = calendar.startOfDay(
        for: calendar.date(byAdding: .day, value: 1, to: Date())!
    )
    let startDate = calendar.date(byAdding: .day, value: -days, to: endDate)!

    let predicate = HKQuery.predicateForSamples(
        withStart: startDate, end: endDate
    )
    let stepType = HKQuantityType(.stepCount)
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
    var dailySteps: [(date: Date, steps: Double)] = []

    collection.statisticsCollection.enumerateStatistics(
        from: startDate, to: endDate
    ) { statistics, _ in
        let steps = statistics.sumQuantity()?
            .doubleValue(for: .count()) ?? 0
        dailySteps.append((date: statistics.startDate, steps: steps))
    }

    return dailySteps
}
```

### Long-Running Collection Query

Use `results(for:)` (plural) to get an `AsyncSequence` that emits updates as new data arrives:

```swift
let updateStream = query.results(for: healthStore)

Task {
    for try await result in updateStream {
        // result.statisticsCollection contains updated data
    }
}
```

## Writing Data

Create `HKQuantitySample` objects and save them to the store.

```swift
func saveSteps(count: Double, start: Date, end: Date) async throws {
    let stepType = HKQuantityType(.stepCount)
    let quantity = HKQuantity(unit: .count(), doubleValue: count)

    let sample = HKQuantitySample(
        type: stepType,
        quantity: quantity,
        start: start,
        end: end
    )

    try await healthStore.save(sample)
}
```

Treat `try await healthStore.save(sample)` returning as the save success gate;
only then report success or advance app state. On failure, surface the error and
correct the known authorization, type, unit, duration, or input problem before
constructing another sample. A bounded query or inspection in the Health app is
useful as an integration-test check when persistence evidence is required, but
is not a mandatory production read after every save.

Your app can only delete samples it created. Samples from other apps or Apple Watch are read-only.

## Background Delivery

Register for background updates so your app is launched when new data arrives. Requires the background delivery entitlement.

```swift
func enableStepCountBackgroundDelivery() async throws {
    let stepType = HKQuantityType(.stepCount)

    try await healthStore.enableBackgroundDelivery(
        for: stepType,
        frequency: .hourly
    )
}
```

**Pair with an `HKObserverQuery`** to handle notifications. Always call the completion handler:

```swift
let observerQuery = HKObserverQuery(
    sampleType: HKQuantityType(.stepCount),
    predicate: nil
) { query, completionHandler, error in
    defer { completionHandler() }  // Must call to signal done
    guard error == nil else { return }
    // Fetch new data, update UI, etc.
}
healthStore.execute(observerQuery)
```

**Frequencies:** `.immediate`, `.hourly`, `.daily`, `.weekly`

Set up observer queries as soon as the app launches, then call
`enableBackgroundDelivery` once for the same sample type. The system persists
the registration, wakes the app at most once per requested frequency, and
enforces tighter caps for some types such as hourly step-count delivery on iOS.
Background delivery is not supported on Simulator; test it on device.

## Workout Sessions

Use `HKWorkoutSession` and `HKLiveWorkoutBuilder` to track live workouts.
`HKWorkoutSession` is available on iOS/iPadOS 17+, visionOS 1+, and watchOS 2+.
`HKLiveWorkoutBuilder` is available on iOS/iPadOS 26+ and watchOS 5+, so gate
live-builder code if supporting older iOS/iPadOS releases.

On iPhone and iPad, live heart-rate collection requires a paired external heart
rate sensor. Apple Watch sessions can collect high-frequency heart-rate data.
For locked iPhone workouts, plan for the system's workout-data access flow
before showing health metrics on the Lock Screen.

```swift
func startWorkout() async throws {
    let configuration = HKWorkoutConfiguration()
    configuration.activityType = .running
    configuration.locationType = .outdoor

    let session = try HKWorkoutSession(
        healthStore: healthStore,
        configuration: configuration
    )
    session.delegate = self

    let builder = session.associatedWorkoutBuilder()
    builder.dataSource = HKLiveWorkoutDataSource(
        healthStore: healthStore,
        workoutConfiguration: configuration
    )

    session.startActivity(with: Date())
    try await builder.beginCollection(at: Date())
}

// Request teardown; finalize from the delegate's .stopped transition.
session.stopActivity(with: Date())
```

Do not call `endCollection` and `finishWorkout` immediately after requesting the
stop. Wait for the session delegate's `.stopped` transition, then await
`builder.endCollection(at:)` followed by `builder.finishWorkout()`. Report the
workout as saved and clear session state only after both operations return.
Handle each thrown error without blindly repeating teardown. A successful
`finishWorkout()` can return no workout object while the device is locked, so a
`nil` result alone is not failure.

For full workout lifecycle management including pause/resume, delegate handling, and multi-device mirroring, see [references/healthkit-patterns.md](references/healthkit-patterns.md).

## Common Data Types

### HKQuantityTypeIdentifier

| Identifier | Category | Unit |
|---|---|---|
| `.stepCount` | Fitness | `.count()` |
| `.distanceWalkingRunning` | Fitness | `.meter()` |
| `.activeEnergyBurned` | Fitness | `.kilocalorie()` |
| `.basalEnergyBurned` | Fitness | `.kilocalorie()` |
| `.heartRate` | Vitals | `.count()/.minute()` |
| `.restingHeartRate` | Vitals | `.count()/.minute()` |
| `.oxygenSaturation` | Vitals | `.percent()` |
| `.bodyMass` | Body | `.gramUnit(with: .kilo)` |
| `.bodyMassIndex` | Body | `.count()` |
| `.height` | Body | `.meter()` |
| `.bodyFatPercentage` | Body | `.percent()` |
| `.bloodGlucose` | Lab | `.gramUnit(with: .milli).unitDivided(by: .literUnit(with: .deci))` |

### HKCategoryTypeIdentifier

Common category types: `.sleepAnalysis`, `.mindfulSession`, `.appleStandHour`

### HKCharacteristicType

Read-only user characteristics include `.dateOfBirth`, `.biologicalSex`,
`.bloodType`, `.fitzpatrickSkinType`, `.wheelchairUse`, and `.activityMoveMode`.

## HKUnit Reference

```swift
// Basic units
HKUnit.count()                              // Steps, counts
HKUnit.meter()                              // Distance
HKUnit.mile()                               // Distance (imperial)
HKUnit.kilocalorie()                        // Energy
HKUnit.joule(with: .kilo)                   // Energy (SI)
HKUnit.gramUnit(with: .kilo)                // Mass (kg)
HKUnit.pound()                              // Mass (imperial)
HKUnit.percent()                            // Percentage

// Compound units
HKUnit.count().unitDivided(by: .minute())   // Heart rate (bpm)
HKUnit.meter().unitDivided(by: .second())   // Speed (m/s)

// Prefixed units
HKUnit.gramUnit(with: .milli)               // Milligrams
HKUnit.literUnit(with: .deci)               // Deciliters
```

## Common Mistakes

1. **Over-requesting data types.** Request only the read/write types the feature
   actually uses; broad HealthKit permission sheets are an App Review risk.
2. **Treating read authorization like write authorization.** You can check
   `.sharingAuthorized` before saving, but read denial is privacy-protected and
   looks like app-owned-only, empty, or partial results.
3. **Skipping `isHealthDataAvailable()`.** Check before HealthKit access and
   handle unavailable or restricted stores without crashing.
4. **Using callback queries for new async code.** Prefer async descriptors for
   one-shot reads and statistics, and keep broad queries off the main actor.
5. **Forgetting observer completion handlers.** Always call the handler; missed
   completions can delay or stop future background deliveries.
6. **Assuming `.immediate` means immediate.** Background delivery is capped by
   the system and must be tested on device.
7. **Using cumulative stats for discrete values.** Match statistics options to
   the data type: cumulative sums for steps/energy, discrete average/min/max for
   heart rate, weight, and similar samples.

## Review Checklist

- [ ] `HKHealthStore.isHealthDataAvailable()` checked before any HealthKit access
- [ ] Only necessary data types requested in authorization
- [ ] `Info.plist` includes `NSHealthShareUsageDescription` and/or `NSHealthUpdateUsageDescription`
- [ ] HealthKit capability enabled in Xcode project
- [ ] Write authorization checked before saving; read denial handled as partial
      or empty query results
- [ ] Single `HKHealthStore` instance reused (not created per query)
- [ ] Async query descriptors used instead of callback-based queries
- [ ] Heavy queries not blocking main thread
- [ ] Statistics options match data type (cumulative vs. discrete)
- [ ] Background delivery paired with app-launch `HKObserverQuery` setup and
      `completionHandler` called
- [ ] Background delivery entitlement enabled if using `enableBackgroundDelivery`
- [ ] Background delivery tested on device and frequency caps considered
- [ ] Workout stop waits for the delegate's `.stopped` transition before
      `endCollection` and `finishWorkout`; state clears only after successful
      finalization
- [ ] Workout API availability and live heart-rate sensor requirements handled
- [ ] Delete operations target only objects the app previously saved

## References

- Extended patterns (workouts, anchored queries, SwiftUI integration): [references/healthkit-patterns.md](references/healthkit-patterns.md)
- [HealthKit framework](https://sosumi.ai/documentation/healthkit)
- [HKHealthStore](https://sosumi.ai/documentation/healthkit/hkhealthstore)
- [HKSampleQueryDescriptor](https://sosumi.ai/documentation/healthkit/hksamplequerydescriptor)
- [HKStatisticsQueryDescriptor](https://sosumi.ai/documentation/healthkit/hkstatisticsquerydescriptor)
- [HKStatisticsCollectionQueryDescriptor](https://sosumi.ai/documentation/healthkit/hkstatisticscollectionquerydescriptor)
- [HKWorkoutSession](https://sosumi.ai/documentation/healthkit/hkworkoutsession)
- [HKLiveWorkoutBuilder](https://sosumi.ai/documentation/healthkit/hkliveworkoutbuilder)
- [Setting up HealthKit](https://sosumi.ai/documentation/healthkit/setting-up-healthkit)
- [Authorizing access to health data](https://sosumi.ai/documentation/healthkit/authorizing-access-to-health-data)
- [Configuring HealthKit access](https://sosumi.ai/documentation/xcode/configuring-healthkit-access)
