# SensorKit Extended Patterns

Overflow reference for the `sensorkit` skill. Contains delegate wiring,
multi-sensor management, and detailed sample type usage that exceed the main
skill file's scope.

## Contents

- [Entitlement and Usage-Detail Catalog](#entitlement-and-usage-detail-catalog)
- [Sensor Catalog](#sensor-catalog)
- [Delegate Method Catalog](#delegate-method-catalog)
- [Full Delegate Implementation](#full-delegate-implementation)
- [Multi-Sensor Manager](#multi-sensor-manager)
- [Ambient Light Samples](#ambient-light-samples)
- [Keyboard Metrics Deep Dive](#keyboard-metrics-deep-dive)
- [Device Usage Reports](#device-usage-reports)
- [Phone and Messages Usage](#phone-and-messages-usage)
- [Visit Tracking](#visit-tracking)
- [Media Events](#media-events)
- [Wrist Detection](#wrist-detection)
- [Speech Metrics](#speech-metrics)
- [Face Metrics](#face-metrics)
- [Wrist Temperature](#wrist-temperature)
- [Electrocardiogram and PPG](#electrocardiogram-and-ppg)
- [SRAbsoluteTime Utilities](#srabsolutetime-utilities)
- [Deletion Records](#deletion-records)
- [Testing Considerations](#testing-considerations)

## Entitlement and Usage-Detail Catalog

Use only values Apple approved for the study. The expanded value array covered
by this skill is:

```xml
<key>com.apple.developer.sensorkit.reader.allow</key>
<array>
    <string>ambient-light-sensor</string>
    <string>motion-accelerometer</string>
    <string>motion-rotation-rate</string>
    <string>device-usage</string>
    <string>keyboard-metrics</string>
    <string>messages-usage</string>
    <string>phone-usage</string>
    <string>visits</string>
    <string>pedometer</string>
    <string>on-wrist</string>
    <string>speech-metrics-siri</string>
    <string>speech-metrics-telephony</string>
    <string>ambient-pressure</string>
    <string>ecg</string>
    <string>ppg</string>
</array>
```

Map each requested sensor to its exact `NSSensorKitUsageDetail` key:

| Sensor family | Usage-detail key |
|---|---|
| Motion sensors | `SRSensorUsageMotion` |
| Ambient light | `SRSensorUsageAmbientLightSensor` |
| Ambient pressure | `SRSensorUsageElevation` |
| Electrocardiogram | `SRSensorUsageECG` |
| Photoplethysmogram | `SRSensorUsagePPG` |
| Heart rate | `SRSensorUsageHeartRate` |
| Wrist temperature | `SRSensorUsageWristTemperature` |

Verify newer or specialized sensors against their individual `SRSensor` pages.
ECG and PPG require both the `ecg` or `ppg` entitlement value and the matching
usage-detail entry.

## Sensor Catalog

| Category | Sensor | Sample Type |
|---|---|---|
| Device | `.deviceUsageReport` | `SRDeviceUsageReport` |
| Device | `.keyboardMetrics` | `SRKeyboardMetrics` |
| Device | `.onWristState` | `SRWristDetection` |
| Device | `.acousticSettings` | `SRAcousticSettings` |
| App activity | `.messagesUsageReport` | `SRMessagesUsageReport` |
| App activity | `.phoneUsageReport` | `SRPhoneUsageReport` |
| User activity | `.accelerometer` | `[CMRecordedAccelerometerData]` |
| User activity | `.rotationRate` | `[CMRecordedRotationRateData]` |
| User activity | `.pedometerData` | `CMPedometerData` |
| User activity | `.visits` | `SRVisit` |
| User activity | `.mediaEvents` | `SRMediaEvent` |
| User activity | `.faceMetrics` | `SRFaceMetrics` |
| User activity | `.heartRate` | `CMHighFrequencyHeartRateData` |
| User activity | `.odometer` | `CMOdometerData` |
| User activity | `.siriSpeechMetrics` | `SRSpeechMetrics` |
| User activity | `.telephonySpeechMetrics` | `SRSpeechMetrics` |
| User activity | `.wristTemperature` | `SRWristTemperatureSession` |
| User activity | `.sleepSessions` | `SRSleepSession` |
| User activity | `.photoplethysmogram` | `[SRPhotoplethysmogramSample]` |
| User activity | `.electrocardiogram` | `[SRElectrocardiogramSample]` |
| Environment | `.ambientLightSensor` | `SRAmbientLightSample` |
| Environment | `.ambientPressure` | `[CMRecordedPressureData]` |

## Delegate Method Catalog

| Delegate method | Purpose |
|---|---|
| `sensorReader(_:didChange:)` | Authorization status changed |
| `sensorReaderWillStartRecording(_:)` | Recording is about to start |
| `sensorReader(_:startRecordingFailedWithError:)` | Recording failed to start |
| `sensorReaderDidStopRecording(_:)` | Recording stopped |
| `sensorReader(_:stopRecordingFailedWithError:)` | Recording failed to stop |
| `sensorReader(_:didFetch:)` | Devices fetched |
| `sensorReader(_:fetchDevicesDidFailWithError:)` | Device fetch failed |
| `sensorReader(_:fetching:didFetchResult:)` | Sample received |
| `sensorReader(_:didCompleteFetch:)` | Fetch completed |
| `sensorReader(_:fetching:failedWithError:)` | Fetch failed |

## Full Delegate Implementation

A complete `SRSensorReaderDelegate` implementation covering all callbacks:

```swift
import SensorKit

final class SensorReaderHandler: NSObject, SRSensorReaderDelegate {

    // MARK: - Authorization

    func sensorReader(_ reader: SRSensorReader, didChange authorizationStatus: SRAuthorizationStatus) {
        switch authorizationStatus {
        case .authorized:
            reader.startRecording()
        case .denied:
            handleDenied(sensor: reader.sensor)
        case .notDetermined:
            break
        @unknown default:
            break
        }
    }

    // MARK: - Recording

    func sensorReaderWillStartRecording(_ reader: SRSensorReader) {
        print("Recording will start for \(reader.sensor)")
    }

    func sensorReader(_ reader: SRSensorReader, startRecordingFailedWithError error: any Error) {
        print("Recording failed for \(reader.sensor): \(error)")
    }

    func sensorReaderDidStopRecording(_ reader: SRSensorReader) {
        print("Recording stopped for \(reader.sensor)")
    }

    func sensorReader(_ reader: SRSensorReader, stopRecordingFailedWithError error: any Error) {
        print("Stop recording failed for \(reader.sensor): \(error)")
    }

    // MARK: - Device Fetching

    func sensorReader(_ reader: SRSensorReader, didFetch devices: [SRDevice]) {
        for device in devices {
            fetchData(for: reader, from: device)
        }
    }

    func sensorReader(_ reader: SRSensorReader, fetchDevicesDidFailWithError error: any Error) {
        print("Device fetch failed: \(error)")
    }

    // MARK: - Data Fetching

    func sensorReader(
        _ reader: SRSensorReader,
        fetching request: SRFetchRequest,
        didFetchResult result: SRFetchResult<AnyObject>
    ) -> Bool {
        processSample(result, for: reader.sensor)
        return true  // true = continue fetching, false = stop
    }

    func sensorReader(_ reader: SRSensorReader, didCompleteFetch request: SRFetchRequest) {
        print("Fetch complete for \(reader.sensor)")
    }

    func sensorReader(
        _ reader: SRSensorReader,
        fetching request: SRFetchRequest,
        failedWithError error: any Error
    ) {
        handleFetchError(error, sensor: reader.sensor)
    }

    // MARK: - Private

    private func fetchData(for reader: SRSensorReader, from device: SRDevice) {
        let request = SRFetchRequest()
        request.device = device
        // Fetch data from 3 days ago to 1 day ago (avoids 24-hour hold)
        request.from = SRAbsoluteTime(CFAbsoluteTimeGetCurrent() - 86400 * 3)
        request.to = SRAbsoluteTime(CFAbsoluteTimeGetCurrent() - 86400)
        reader.fetch(request)
    }

    private func handleDenied(sensor: SRSensor) {
        // Log or notify that the user denied this sensor
    }

    private func processSample(_ result: SRFetchResult<AnyObject>, for sensor: SRSensor) {
        // Route to sensor-specific processing
    }

    private func handleFetchError(_ error: any Error, sensor: SRSensor) {
        if let srError = error as? SRError {
            switch srError.code {
            case .invalidEntitlement:
                print("Missing entitlement for \(sensor)")
            case .noAuthorization:
                print("No authorization for \(sensor)")
            case .dataInaccessible:
                print("Data inaccessible for \(sensor) -- may be in holding period")
            case .fetchRequestInvalid:
                print("Invalid fetch request for \(sensor)")
            case .promptDeclined:
                print("User declined prompt for \(sensor)")
            @unknown default:
                print("Unknown error for \(sensor): \(error)")
            }
        }
    }
}
```

## Multi-Sensor Manager

Manage multiple sensors through a single coordinator:

```swift
import SensorKit

final class SensorKitManager: NSObject, SRSensorReaderDelegate {

    private var readers: [SRSensor: SRSensorReader] = [:]
    private var collectedSamples: [SRSensor: [Any]] = [:]

    private let studySensors: Set<SRSensor> = [
        .ambientLightSensor,
        .accelerometer,
        .keyboardMetrics,
        .deviceUsageReport,
        .visits
    ]

    // MARK: - Setup

    func configure() {
        for sensor in studySensors {
            let reader = SRSensorReader(sensor: sensor)
            reader.delegate = self
            readers[sensor] = reader
        }
    }

    func requestAuthorization() {
        SRSensorReader.requestAuthorization(sensors: studySensors) { error in
            if let error {
                print("Authorization failed: \(error)")
            }
        }
    }

    // MARK: - Recording

    func startAllRecording() {
        for (sensor, reader) in readers {
            guard reader.authorizationStatus == .authorized else {
                print("Skipping \(sensor) -- not authorized")
                continue
            }
            reader.startRecording()
        }
    }

    func stopAllRecording() {
        for reader in readers.values {
            reader.stopRecording()
        }
    }

    // MARK: - Fetching

    func fetchAllData(daysBack: Int = 3) {
        for reader in readers.values {
            guard reader.authorizationStatus == .authorized else { continue }
            reader.fetchDevices()
        }
    }

    // MARK: - SRSensorReaderDelegate

    func sensorReader(_ reader: SRSensorReader, didChange authorizationStatus: SRAuthorizationStatus) {
        if authorizationStatus == .authorized {
            reader.startRecording()
        }
    }

    func sensorReader(_ reader: SRSensorReader, didFetch devices: [SRDevice]) {
        for device in devices {
            let request = SRFetchRequest()
            request.device = device
            request.from = SRAbsoluteTime(CFAbsoluteTimeGetCurrent() - 86400 * 3)
            request.to = SRAbsoluteTime(CFAbsoluteTimeGetCurrent() - 86400)
            reader.fetch(request)
        }
    }

    func sensorReader(
        _ reader: SRSensorReader,
        fetching request: SRFetchRequest,
        didFetchResult result: SRFetchResult<AnyObject>
    ) -> Bool {
        var samples = collectedSamples[reader.sensor] ?? []
        samples.append(result.sample)
        collectedSamples[reader.sensor] = samples
        return true
    }

    func sensorReader(_ reader: SRSensorReader, didCompleteFetch request: SRFetchRequest) {
        let count = collectedSamples[reader.sensor]?.count ?? 0
        print("Fetched \(count) samples for \(reader.sensor)")
    }

    func sensorReader(
        _ reader: SRSensorReader,
        fetching request: SRFetchRequest,
        failedWithError error: any Error
    ) {
        print("Fetch error for \(reader.sensor): \(error)")
    }

    func sensorReader(_ reader: SRSensorReader, fetchDevicesDidFailWithError error: any Error) {
        print("Device fetch error for \(reader.sensor): \(error)")
    }
}
```

## Ambient Light Samples

`SRAmbientLightSample` provides lux, chromaticity, and sensor placement:

```swift
func processAmbientLight(_ result: SRFetchResult<AnyObject>) {
    guard let sample = result.sample as? SRAmbientLightSample else { return }

    // Illuminance in lux
    let luxValue = sample.lux.value  // Double
    let luxUnit = sample.lux.unit    // UnitIlluminance

    // Chromaticity coordinates (CIE 1931 xy)
    let chromX = sample.chromaticity.x  // Float32
    let chromY = sample.chromaticity.y  // Float32

    // Sensor placement relative to light source
    switch sample.placement {
    case .frontTop:
        print("Light from above front")
    case .frontBottom:
        print("Light from below front")
    case .frontLeft, .frontRight:
        print("Light from side")
    case .frontTopLeft, .frontTopRight:
        print("Light from upper corner")
    case .frontBottomLeft, .frontBottomRight:
        print("Light from lower corner")
    case .unknown:
        print("Unknown placement")
    @unknown default:
        break
    }

    print("Ambient light: \(luxValue) lux, chromaticity: (\(chromX), \(chromY))")
}
```

## Keyboard Metrics Deep Dive

`SRKeyboardMetrics` provides extensive typing analytics:

### Basic Metrics

```swift
func processKeyboardMetrics(_ result: SRFetchResult<AnyObject>) {
    guard let metrics = result.sample as? SRKeyboardMetrics else { return }

    // Session info
    let duration = metrics.duration
    let keyboardID = metrics.keyboardIdentifier
    let inputModes = metrics.inputModes  // Active languages
    let sessions = metrics.sessionIdentifiers

    // Quantitative metrics
    let totalWords = metrics.totalWords
    let totalTaps = metrics.totalTaps
    let totalDeletes = metrics.totalDeletes
    let totalEmojis = metrics.totalEmojis
    let totalAutoCorrections = metrics.totalAutoCorrections
    let typingSpeed = metrics.typingSpeed  // Characters per second

    // Keyboard dimensions
    let width = metrics.width   // Measurement<UnitLength>
    let height = metrics.height // Measurement<UnitLength>

    print("Session: \(duration)s, \(totalWords) words at \(typingSpeed) chars/sec")
}
```

### Correction Metrics

```swift
func analyzeCorrections(_ metrics: SRKeyboardMetrics) {
    let corrections = [
        "Auto": metrics.totalAutoCorrections,
        "Space": metrics.totalSpaceCorrections,
        "Retro": metrics.totalRetroCorrections,
        "Transposition": metrics.totalTranspositionCorrections,
        "Insert key": metrics.totalInsertKeyCorrections,
        "Skip touch": metrics.totalSkipTouchCorrections,
        "Near key": metrics.totalNearKeyCorrections,
        "Substitution": metrics.totalSubstitutionCorrections,
        "Hit test": metrics.totalHitTestCorrections
    ]

    for (type, count) in corrections where count > 0 {
        print("\(type) corrections: \(count)")
    }
}
```

### Sentiment Analysis

```swift
func analyzeSentiment(_ metrics: SRKeyboardMetrics) {
    let categories: [SRKeyboardMetrics.SentimentCategory] = [
        .positive, .sad, .anger, .anxiety,
        .confused, .down, .lowEnergy, .health,
        .death, .absolutist
    ]

    for category in categories {
        let wordCount = metrics.wordCount(for: category)
        let emojiCount = metrics.emojiCount(for: category)
        if wordCount > 0 || emojiCount > 0 {
            print("\(category): \(wordCount) words, \(emojiCount) emojis")
        }
    }
}
```

### Timing Distributions

Timing metrics use `SRKeyboardMetrics.ProbabilityMetric`, which contains a
distribution of sample values:

```swift
func analyzeTimings(_ metrics: SRKeyboardMetrics) {
    // Touch down to touch up duration for any key
    let touchDuration = metrics.touchDownUp
    let samples = touchDuration.distributionSampleValues  // [Measurement<UnitDuration>]

    if !samples.isEmpty {
        let avgMs = samples.map { $0.converted(to: .milliseconds).value }
            .reduce(0, +) / Double(samples.count)
        print("Average key press: \(avgMs)ms")
    }

    // QuickType (swipe) typing speed
    let pathSpeed = metrics.pathTypingSpeed  // Words per minute
    print("Swipe speed: \(pathSpeed) WPM")
}
```

## Device Usage Reports

`SRDeviceUsageReport` provides screen time, unlock, and per-app usage data:

```swift
func processDeviceUsage(_ result: SRFetchResult<AnyObject>) {
    guard let report = result.sample as? SRDeviceUsageReport else { return }

    // Summary metrics
    let reportDuration = report.duration
    let screenWakes = report.totalScreenWakes
    let unlocks = report.totalUnlocks
    let unlockDuration = report.totalUnlockDuration

    print("Wakes: \(screenWakes), Unlocks: \(unlocks), Duration: \(unlockDuration)s")

    // Per-category app usage
    for (category, apps) in report.applicationUsageByCategory {
        print("Category: \(category.rawValue)")
        for app in apps {
            let bundleID = app.bundleIdentifier ?? "unknown"
            let usageTime = app.usageTime
            print("  \(bundleID): \(usageTime)s")

            // Text input sessions within this app
            for session in app.textInputSessions {
                let inputDuration = session.duration
                let inputType = session.sessionType
                switch inputType {
                case .keyboard:
                    print("    Keyboard input: \(inputDuration)s")
                case .dictation:
                    print("    Dictation input: \(inputDuration)s")
                case .pencil:
                    print("    Pencil input: \(inputDuration)s")
                case .thirdPartyKeyboard:
                    print("    Third-party keyboard: \(inputDuration)s")
                @unknown default:
                    break
                }
            }
        }
    }

    // Notification interactions
    for (category, notifications) in report.notificationUsageByCategory {
        for notification in notifications {
            let event = notification.event
            switch event {
            case .received:
                print("Notification received: \(notification.bundleIdentifier ?? "unknown")")
            case .appLaunch:
                print("Notification opened app")
            case .clear, .hide, .silence:
                print("Notification dismissed")
            default:
                break
            }
        }
    }
}
```

## Phone and Messages Usage

### Phone Usage

```swift
func processPhoneUsage(_ result: SRFetchResult<AnyObject>) {
    guard let report = result.sample as? SRPhoneUsageReport else { return }

    let duration = report.duration
    let incoming = report.totalIncomingCalls
    let outgoing = report.totalOutgoingCalls
    let callDuration = report.totalPhoneCallDuration
    let contacts = report.totalUniqueContacts

    print("Calls: \(incoming) in / \(outgoing) out, Duration: \(callDuration)s")
    print("Unique contacts: \(contacts)")
}
```

### Messages Usage

```swift
func processMessagesUsage(_ result: SRFetchResult<AnyObject>) {
    guard let report = result.sample as? SRMessagesUsageReport else { return }

    let duration = report.duration
    let incoming = report.totalIncomingMessages
    let outgoing = report.totalOutgoingMessages
    let contacts = report.totalUniqueContacts

    print("Messages: \(incoming) in / \(outgoing) out over \(duration)s")
    print("Unique contacts: \(contacts)")
}
```

## Visit Tracking

`SRVisit` provides categorized location visit data with distance from home:

```swift
func processVisit(_ result: SRFetchResult<AnyObject>) {
    guard let visit = result.sample as? SRVisit else { return }

    let visitID = visit.identifier
    let arrival = visit.arrivalDateInterval
    let departure = visit.departureDateInterval
    let distance = visit.distanceFromHome  // CLLocationDistance in meters

    switch visit.locationCategory {
    case .home:
        print("At home")
    case .work:
        print("At work, \(distance)m from home")
    case .school:
        print("At school")
    case .gym:
        print("At gym")
    case .unknown:
        print("Unknown location, \(distance)m from home")
    @unknown default:
        break
    }

    print("Visit \(visitID): arrived \(arrival), departed \(departure)")
}
```

## Media Events

`SRMediaEvent` tracks interactions with images and videos in messaging apps:

```swift
func processMediaEvent(_ result: SRFetchResult<AnyObject>) {
    guard let event = result.sample as? SRMediaEvent else { return }

    let mediaID = event.mediaIdentifier

    switch event.eventType {
    case .onScreen:
        print("Media \(mediaID) appeared on screen")
    case .offScreen:
        print("Media \(mediaID) went off screen")
    @unknown default:
        break
    }
}
```

## Wrist Detection

`SRWristDetection` reports Apple Watch wrist state and configuration:

```swift
func processWristDetection(_ result: SRFetchResult<AnyObject>) {
    guard let wrist = result.sample as? SRWristDetection else { return }

    let isOnWrist = wrist.onWrist
    let onDate = wrist.onWristDate
    let offDate = wrist.offWristDate

    // Watch configuration
    switch wrist.wristLocation {
    case .left:
        print("Watch on left wrist")
    case .right:
        print("Watch on right wrist")
    @unknown default:
        break
    }

    switch wrist.crownOrientation {
    case .left:
        print("Crown on left")
    case .right:
        print("Crown on right")
    @unknown default:
        break
    }

    print("On wrist: \(isOnWrist)")
}
```

## Speech Metrics

`SRSpeechMetrics` provides audio level, speech recognition, sound classification,
and speech expression data from Siri and phone calls:

```swift
func processSpeechMetrics(_ result: SRFetchResult<AnyObject>) {
    guard let metrics = result.sample as? SRSpeechMetrics else { return }

    let sessionID = metrics.sessionIdentifier
    let timestamp = metrics.timestamp
    let timeSinceStart = metrics.timeSinceAudioStart

    // Audio level
    if let audioLevel = metrics.audioLevel {
        let loudness = audioLevel.loudness
        let timeRange = audioLevel.timeRange
        print("Audio level: \(loudness) dB")
    }

    // Speech expression (mood/valence analysis)
    if let expression = metrics.speechExpression {
        let confidence = expression.confidence
        let mood = expression.mood
        let valence = expression.valence
        let activation = expression.activation
        let dominance = expression.dominance
        print("Expression -- mood: \(mood), valence: \(valence), confidence: \(confidence)")
    }

    // Speech recognition results
    if let recognition = metrics.speechRecognition {
        let text = recognition.bestTranscription.formattedString
        print("Recognized: \(text)")
    }

    // Sound classification
    if let classification = metrics.soundClassification {
        for result in classification.classifications {
            print("Sound: \(result.identifier) (\(result.confidence))")
        }
    }
}
```

## Face Metrics

`SRFaceMetrics` provides face anchor data and expression analysis. Requires
a device with a TrueDepth camera (Face ID).

```swift
func processFaceMetrics(_ result: SRFetchResult<AnyObject>) {
    guard let face = result.sample as? SRFaceMetrics else { return }

    let sessionID = face.sessionIdentifier
    let context = face.context

    // Context indicates what triggered the capture
    if context.contains(.deviceUnlock) {
        print("Face captured during device unlock")
    }
    if context.contains(.messagingAppUsage) {
        print("Face captured during messaging")
    }

    // Face expressions
    for expression in face.wholeFaceExpressions {
        print("Expression \(expression.identifier): \(expression.value)")
    }

    for expression in face.partialFaceExpressions {
        print("Partial \(expression.identifier): \(expression.value)")
    }

    // ARKit face anchor (full blend shapes)
    let anchor = face.faceAnchor
    let blendShapes = anchor.blendShapes
    if let smile = blendShapes[.mouthSmileLeft] {
        print("Left smile: \(smile)")
    }
}
```

## Wrist Temperature

The `.wristTemperature` stream returns `SRWristTemperatureSession` samples.
Each session contains `SRWristTemperature` readings.

```swift
func processWristTemperature(_ result: SRFetchResult<AnyObject>) {
    guard let session = result.sample as? SRWristTemperatureSession else { return }

    print("Temperature session: \(session.startDate), duration: \(session.duration)s")

    for temp in session.temperatures {
        let timestamp = temp.timestamp
        let value = temp.value         // Measurement<UnitTemperature>, in Celsius
        let error = temp.errorEstimate // Measurement<UnitTemperature>

        // Check conditions that affect accuracy
        let condition = temp.condition
        if condition.contains(.offWrist) {
            print("Off wrist -- skip reading")
            continue
        }
        if condition.contains(.onCharger) {
            print("On charger -- reduced accuracy")
        }
        if condition.contains(.inMotion) {
            print("In motion -- reduced accuracy")
        }

        let celsius = value.converted(to: .celsius).value
        let errorC = error.converted(to: .celsius).value
        print("Temp at \(timestamp): \(celsius)C +/- \(errorC)C")
    }
}
```

## Electrocardiogram and PPG

### ECG Data

```swift
func processECG(_ result: SRFetchResult<AnyObject>) {
    guard let samples = result.sample as? [SRElectrocardiogramSample] else { return }

    for sample in samples {
        let frequency = sample.frequency
        let session = sample.session
        let isGuided = session.sessionGuidance == .guided

        // ECG voltage data points -- skip invalid readings
        for dataPoint in sample.data {
            guard !dataPoint.flags.contains(.signalInvalid) else { continue }
            let microvolts = dataPoint.value.converted(to: .microvolts).value
            print("ECG: \(microvolts) uV, guided: \(isGuided), crown: \(dataPoint.flags.contains(.crownTouched))")
        }
    }
}
```

### PPG Data

```swift
func processPPG(_ result: SRFetchResult<AnyObject>) {
    guard let samples = result.sample as? [SRPhotoplethysmogramSample] else { return }

    for sample in samples {
        // Usage: .foregroundHeartRate, .foregroundBloodOxygen, .deepBreathing, .backgroundSystem
        for usage in sample.usage {
            print("PPG usage: \(usage)")
        }

        // Optical sensor data with signal quality checks
        for optical in sample.opticalSamples {
            let wavelength = optical.nominalWavelength
            let reflectance = optical.normalizedReflectance
            let hasIssues = optical.conditions.contains {
                $0 == .signalSaturation || $0 == .unreliableNoise
            }
            if !hasIssues, let reflectance {
                print("Reflectance: \(reflectance) at \(wavelength)")
            }
        }
    }
}
```

## SRAbsoluteTime Utilities

`SRAbsoluteTime` wraps `CFAbsoluteTime` for SensorKit time ranges:

```swift
let now = SRAbsoluteTime.current()
let twoDaysAgo = SRAbsoluteTime(CFAbsoluteTimeGetCurrent() - 86400 * 2)
let cfTime = now.toCFAbsoluteTime()
let date = Date(timeIntervalSinceReferenceDate: cfTime)

func buildWeekFetchRequest(for device: SRDevice) -> SRFetchRequest {
    let request = SRFetchRequest()
    request.device = device
    request.from = SRAbsoluteTime(CFAbsoluteTimeGetCurrent() - 86400 * 7)
    request.to = SRAbsoluteTime(CFAbsoluteTimeGetCurrent() - 86400)
    return request
}
```

## Deletion Records

The framework deletes sensor data for various reasons. Handle `SRDeletionRecord`
in the fetch results delegate:

```swift
func processDeletionRecord(_ result: SRFetchResult<AnyObject>) {
    guard let deletion = result.sample as? SRDeletionRecord else { return }
    // Reasons: .userInitiated, .systemInitiated, .lowDiskSpace, .ageLimit, .noInterestedClients
    print("Data deleted (\(deletion.reason)): \(deletion.startTime) to \(deletion.endTime)")
}
```

## Testing Considerations

SensorKit has significant constraints for testing:

- **No Simulator support.** SensorKit requires physical hardware. All testing
  must happen on device.
- **Entitlement required.** Without the Apple-granted entitlement, the framework
  returns `SRError.invalidEntitlement` for all operations.
- **24-hour data delay.** Newly recorded data is unavailable for 24 hours.
  Automated test flows must account for this holding period.
- **User interaction required.** Authorization requires the user to interact with
  the Research Sensor & Usage Data sheet. This cannot be automated.
- **Conditional sensor availability.** Some sensors (wrist temperature, ECG, PPG)
  require Apple Watch. Others (face metrics) require TrueDepth camera. Test on
  devices that have the sensors the study uses.
- **Data volume.** Keyboard metrics and device usage reports can be large. Profile
  memory usage when processing bulk fetches.
- **Background execution.** SensorKit recording continues in the background
  without special background mode configuration. The framework manages sensor
  activation independently of app lifecycle.
