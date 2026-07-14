---
name: sensorkit
description: "Access research-grade sensor data using SensorKit for approved studies. Use when an app needs SensorKit entitlement setup, Research Sensor & Usage Data authorization, ambient light, recorded motion, device usage, keyboard metrics, visits, speech, face, wrist temperature, ECG, PPG, acoustic settings, or sleep-session data. Route ordinary motion to CoreMotion and health records/workouts to HealthKit."
---

# SensorKit

Collect research-grade sensor data from iOS and watchOS devices for approved research studies. Choose the exact `SRSensor` from the catalog below and verify its individual availability.

**SensorKit is restricted to Apple-approved research studies.** Apps must submit
a research proposal to Apple and receive the `com.apple.developer.sensorkit.reader.allow`
entitlement before any sensor data is accessible. This is not a general-purpose
sensor API -- use CoreMotion for ordinary accelerometer, gyroscope, pedometer,
or activity-recognition features, and HealthKit for health records and workouts.

## Contents

- [Overview and Requirements](#overview-and-requirements)
- [Entitlements](#entitlements)
- [Info.plist Configuration](#infoplist-configuration)
- [Authorization](#authorization)
- [Available Sensors](#available-sensors)
- [SRSensorReader](#srsensorreader)
- [Recording and Fetching Data](#recording-and-fetching-data)
- [SRDevice](#srdevice)
- [Common Mistakes](#common-mistakes)
- [Review Checklist](#review-checklist)
- [References](#references)

## Overview and Requirements

SensorKit enables research apps to record and fetch sensor data across iPhone
and Apple Watch. The framework requires:

1. **Apple-approved research study** -- submit a proposal at
   [researchandcare.org](https://www.researchandcare.org/resources/accessing-sensorkit-data/).
2. **SensorKit entitlement** -- Apple grants `com.apple.developer.sensorkit.reader.allow`
   only for approved studies.
3. **Manual provisioning profile** -- Xcode requires an explicit App ID with the
   SensorKit capability enabled.
4. **User authorization** -- the system presents a Research Sensor & Usage Data
   sheet that users approve per-sensor.
5. **24-hour data hold** -- newly recorded data is inaccessible for 24 hours,
   giving users time to delete data they do not want to share.

An app can access up to 7 days of prior recorded data for an active sensor.

## Entitlements

Add the SensorKit reader entitlement to a `.entitlements` file. List only the
sensors Apple approved for the study. Common entitlement values include:

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

Verify newer or specialized sensors against their individual `SRSensor` pages.
For example, Apple's ECG and PPG sensor pages explicitly require `ecg` and
`ppg` entitlement values in addition to their `NSSensorKitUsageDetail` entries.

For manual signing, set Code Signing Entitlements to the entitlements file,
Code Signing Identity to `Apple Developer`, Code Signing Style to `Manual`,
and Provisioning Profile to the explicit profile with SensorKit capability.

## Info.plist Configuration

Three keys are required:

```xml
<!-- Study purpose shown in the authorization sheet -->
<key>NSSensorKitUsageDescription</key>
<string>This study monitors activity patterns for sleep research.</string>

<!-- Link to your study's privacy policy -->
<key>NSSensorKitPrivacyPolicyURL</key>
<string>https://example.com/privacy-policy</string>

<!-- Per-sensor usage explanations -->
<key>NSSensorKitUsageDetail</key>
<dict>
    <key>SRSensorUsageMotion</key>
    <dict>
        <key>Description</key>
        <string>Measures physical activity levels during the study.</string>
        <key>Required</key>
        <true/>
    </dict>
    <key>SRSensorUsageAmbientLightSensor</key>
    <dict>
        <key>Description</key>
        <string>Records ambient light to assess sleep environment.</string>
    </dict>
</dict>
```

If `Required` is `true` and the user denies that sensor, the system warns them
that the study needs it and offers a chance to reconsider.

Use the exact usage-detail dictionary for each requested sensor. Examples:
motion sensors use `SRSensorUsageMotion`, ambient pressure uses `SRSensorUsageElevation`,
ECG uses `SRSensorUsageECG`, PPG uses `SRSensorUsagePPG`, heart rate uses
`SRSensorUsageHeartRate`, and wrist temperature uses `SRSensorUsageWristTemperature`.

## Authorization

Request authorization for the sensors your study needs. The system shows the
Research Sensor & Usage Data sheet on first request.

```swift
import SensorKit

let reader = SRSensorReader(sensor: .ambientLightSensor)

// Request authorization for multiple sensors at once
SRSensorReader.requestAuthorization(
    sensors: [.ambientLightSensor, .accelerometer, .keyboardMetrics]
) { error in
    if let error {
        print("Authorization request failed: \(error)")
    }
}
```

Check a reader's current status before recording:

```swift
switch reader.authorizationStatus {
case .authorized:
    reader.startRecording()
case .denied:
    // User declined -- direct to Settings > Privacy > Research Sensor & Usage Data
    break
case .notDetermined:
    // Request authorization first
    break
@unknown default:
    break
}
```

Monitor status changes through the delegate:

```swift
func sensorReader(_ reader: SRSensorReader, didChange authorizationStatus: SRAuthorizationStatus) {
    switch authorizationStatus {
    case .authorized:
        reader.startRecording()
    case .denied:
        reader.stopRecording()
    default:
        break
    }
}
```

## Available Sensors

### Device Sensors

| Sensor | Type | Sample Type |
|---|---|---|
| `.deviceUsageReport` | Device usage | `SRDeviceUsageReport` |
| `.keyboardMetrics` | Keyboard activity | `SRKeyboardMetrics` |
| `.onWristState` | Watch wrist state | `SRWristDetection` |
| `.acousticSettings` | Acoustic/accessibility settings | `SRAcousticSettings` |

### App Activity Sensors

| Sensor | Type | Sample Type |
|---|---|---|
| `.messagesUsageReport` | Messages app usage | `SRMessagesUsageReport` |
| `.phoneUsageReport` | Phone call usage | `SRPhoneUsageReport` |

### User Activity Sensors

| Sensor | Type | Sample Type |
|---|---|---|
| `.accelerometer` | Acceleration data | `[CMRecordedAccelerometerData]` |
| `.rotationRate` | Rotation rate | `[CMRecordedRotationRateData]` |
| `.pedometerData` | Step/distance data | `CMPedometerData` |
| `.visits` | Visited locations | `SRVisit` |
| `.mediaEvents` | Media interactions | `SRMediaEvent` |
| `.faceMetrics` | Face expressions | `SRFaceMetrics` |
| `.heartRate` | Heart rate | `CMHighFrequencyHeartRateData` |
| `.odometer` | Speed/slope | `CMOdometerData` |
| `.siriSpeechMetrics` | Siri speech | `SRSpeechMetrics` |
| `.telephonySpeechMetrics` | Phone speech | `SRSpeechMetrics` |
| `.wristTemperature` | Wrist temp (sleep) | `SRWristTemperatureSession` |
| `.sleepSessions` | Sleep session summaries | `SRSleepSession` |
| `.photoplethysmogram` | PPG stream | `[SRPhotoplethysmogramSample]` |
| `.electrocardiogram` | ECG stream | `[SRElectrocardiogramSample]` |

### Environment Sensors

| Sensor | Type | Sample Type |
|---|---|---|
| `.ambientLightSensor` | Ambient light | `SRAmbientLightSample` |
| `.ambientPressure` | Pressure/temp | `[CMRecordedPressureData]` |

## SRSensorReader

`SRSensorReader` is the central class for accessing sensor data. Each instance
reads from a single sensor.

```swift
import SensorKit

// Create a reader for one sensor
let lightReader = SRSensorReader(sensor: .ambientLightSensor)
let keyboardReader = SRSensorReader(sensor: .keyboardMetrics)

// Assign delegate to receive callbacks
lightReader.delegate = self
keyboardReader.delegate = self
```

The reader communicates entirely through `SRSensorReaderDelegate`:

| Delegate Method | Purpose |
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

## Recording and Fetching Data

### Start and Stop Recording

```swift
// Begin recording -- sensor stays active as long as any app has a stake
reader.startRecording()

// Stop recording -- framework deactivates the sensor when
// no app or system process is using it
reader.stopRecording()
```

### Fetch Data

Build an `SRFetchRequest` with a time range and target device, then pass it to
the reader:

```swift
let request = SRFetchRequest()
request.device = SRDevice.current
request.from = SRAbsoluteTime(CFAbsoluteTimeGetCurrent() - 86400 * 2)  // 2 days ago
request.to = SRAbsoluteTime.current()

reader.fetch(request)
```

Receive results through the delegate:

```swift
func sensorReader(
    _ reader: SRSensorReader,
    fetching request: SRFetchRequest,
    didFetchResult result: SRFetchResult<AnyObject>
) -> Bool {
    let timestamp = result.timestamp

    switch reader.sensor {
    case .ambientLightSensor:
        if let sample = result.sample as? SRAmbientLightSample {
            let lux = sample.lux
            let chromaticity = sample.chromaticity
            let placement = sample.placement
            processSample(lux: lux, chromaticity: chromaticity, at: timestamp)
        }
    case .keyboardMetrics:
        if let sample = result.sample as? SRKeyboardMetrics {
            let words = sample.totalWords
            let speed = sample.typingSpeed
            processKeyboard(words: words, speed: speed, at: timestamp)
        }
    case .deviceUsageReport:
        if let sample = result.sample as? SRDeviceUsageReport {
            let wakes = sample.totalScreenWakes
            let unlocks = sample.totalUnlocks
            processUsage(wakes: wakes, unlocks: unlocks, at: timestamp)
        }
    default:
        break
    }

    return true  // Return true to continue receiving results
}

func sensorReader(_ reader: SRSensorReader, didCompleteFetch request: SRFetchRequest) {
    print("Fetch complete for \(reader.sensor)")
}

func sensorReader(
    _ reader: SRSensorReader,
    fetching request: SRFetchRequest,
    failedWithError error: any Error
) {
    print("Fetch failed: \(error)")
}
```

Cast `result.sample` to the sample shape for the reader's sensor. Some streams
return one object per result, while recorded motion, ECG, PPG, and ambient
pressure streams can return arrays of recorded samples.

### Data Holding Period

SensorKit imposes a **24-hour holding period** on newly recorded data. Fetch
requests whose time range overlaps this period return no results. Design data
collection workflows around this delay.

## SRDevice

`SRDevice` identifies the hardware source for sensor samples. Use it to
distinguish data from iPhone versus Apple Watch.

```swift
// Get the current device
let currentDevice = SRDevice.current
print("Model: \(currentDevice.model)")
print("System: \(currentDevice.systemName) \(currentDevice.systemVersion)")

// Fetch all available devices for a sensor
reader.fetchDevices()
```

Handle fetched devices through the delegate:

```swift
func sensorReader(_ reader: SRSensorReader, didFetch devices: [SRDevice]) {
    for device in devices {
        let request = SRFetchRequest()
        request.device = device
        request.from = SRAbsoluteTime(CFAbsoluteTimeGetCurrent() - 86400)
        request.to = SRAbsoluteTime.current()
        reader.fetch(request)
    }
}

func sensorReader(_ reader: SRSensorReader, fetchDevicesDidFailWithError error: any Error) {
    print("Failed to fetch devices: \(error)")
}
```

### SRDevice Properties

| Property | Type | Description |
|---|---|---|
| `model` | `String` | User-defined device name |
| `name` | `String` | Framework-defined device name |
| `systemName` | `String` | OS name (iOS, watchOS) |
| `systemVersion` | `String` | OS version |
| `productType` | `String` | Hardware identifier |
| `current` | `SRDevice` | Class property for the running device |

## Common Mistakes

### DON'T: Attempt to use SensorKit without the entitlement

```swift
// WRONG -- fails at runtime with SRError.invalidEntitlement
let reader = SRSensorReader(sensor: .ambientLightSensor)
reader.startRecording()

// CORRECT -- obtain entitlement from Apple first, configure manual
// provisioning profile, then use SensorKit
```

### DON'T: Expect immediate data access

```swift
// WRONG -- fetching data recorded moments ago returns nothing
reader.startRecording()
// ... record for a few minutes ...
let request = SRFetchRequest()
request.from = SRAbsoluteTime(CFAbsoluteTimeGetCurrent() - 300)
request.to = SRAbsoluteTime.current()
reader.fetch(request)  // Empty results due to 24-hour hold

// CORRECT -- fetch data that is at least 24 hours old
request.from = SRAbsoluteTime(CFAbsoluteTimeGetCurrent() - 86400 * 3)
request.to = SRAbsoluteTime(CFAbsoluteTimeGetCurrent() - 86400)
reader.fetch(request)
```

### DON'T: Forget to set the delegate before fetching

```swift
// WRONG -- no delegate means no callbacks, results are silently lost
let reader = SRSensorReader(sensor: .accelerometer)
reader.startRecording()
reader.fetch(request)

// CORRECT -- assign delegate first
reader.delegate = self
reader.startRecording()
reader.fetch(request)
```

### DON'T: Skip per-sensor Info.plist usage detail

```swift
// WRONG -- missing NSSensorKitUsageDetail for the sensor
// Authorization sheet shows no explanation, user is less likely to approve

// CORRECT -- add usage detail for every sensor you request
// See Info.plist Configuration section above
```

### DON'T: Ignore SRError codes

```swift
// WRONG -- generic error handling
func sensorReader(_ reader: SRSensorReader, fetching: SRFetchRequest, failedWithError error: any Error) {
    print("Error")
}

// CORRECT -- handle specific error codes
func sensorReader(_ reader: SRSensorReader, fetching: SRFetchRequest, failedWithError error: any Error) {
    if let srError = error as? SRError {
        switch srError.code {
        case .invalidEntitlement:
            // Entitlement missing or sensor not in entitlement array
            break
        case .noAuthorization:
            // User has not authorized this sensor
            break
        case .dataInaccessible:
            // Data in 24-hour holding period or otherwise unavailable
            break
        case .fetchRequestInvalid:
            // Invalid time range or device
            break
        case .promptDeclined:
            // User declined the authorization prompt
            break
        @unknown default:
            break
        }
    }
}
```

## Review Checklist

- [ ] Apple-approved research study in place before development
- [ ] `com.apple.developer.sensorkit.reader.allow` entitlement lists only needed sensors
- [ ] Manual provisioning profile with explicit App ID and SensorKit capability
- [ ] `NSSensorKitUsageDescription` in Info.plist with clear study purpose
- [ ] `NSSensorKitPrivacyPolicyURL` in Info.plist with valid privacy policy URL
- [ ] `NSSensorKitUsageDetail` entries for every requested sensor
- [ ] `Required` key set appropriately for essential vs. optional sensors
- [ ] Authorization requested before recording, status checked before fetching
- [ ] Delegate assigned before calling `startRecording()` or `fetch(_:)`
- [ ] Fetch request time ranges account for 24-hour data holding period
- [ ] `SRError` codes handled in all failure delegate methods
- [ ] `fetchDevices()` used to discover available devices before fetching
- [ ] `stopRecording()` called when data collection is complete
- [ ] `sensorReader(_:fetching:didFetchResult:)` returns `true` to continue or `false` to stop

## References

- Extended patterns (delegate wiring, multi-sensor manager, sample type details): [references/sensorkit-patterns.md](references/sensorkit-patterns.md)
- [SensorKit framework](https://sosumi.ai/documentation/sensorkit)
- [SRSensorReader](https://sosumi.ai/documentation/sensorkit/srsensorreader)
- [SRSensor](https://sosumi.ai/documentation/sensorkit/srsensor)
- [SRDevice](https://sosumi.ai/documentation/sensorkit/srdevice)
- [SRFetchRequest](https://sosumi.ai/documentation/sensorkit/srfetchrequest)
- [Configuring your project for sensor reading](https://sosumi.ai/documentation/sensorkit/configuring-your-project-for-sensor-reading)
- [com.apple.developer.sensorkit.reader.allow](https://sosumi.ai/documentation/bundleresources/entitlements/com.apple.developer.sensorkit.reader.allow)
