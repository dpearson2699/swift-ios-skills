---
name: sensorkit
description: "Access research-grade sensor data using SensorKit for approved studies. Use when an app needs SensorKit entitlement setup, Research Sensor & Usage Data authorization, ambient light, recorded motion, device usage, keyboard metrics, visits, speech, face, wrist temperature, ECG, PPG, acoustic settings, or sleep-session data. Route ordinary motion to CoreMotion and health records/workouts to HealthKit."
---

# SensorKit

Choose the exact `SRSensor` and verify its individual availability. Use
CoreMotion for ordinary motion/activity features and HealthKit for health
records and workouts.

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
5. **Delayed retrieval** -- design fetch timing around the canonical
   [Data Holding Period](#data-holding-period).

An app can access up to 7 days of prior recorded data for an active sensor.

## Entitlements

Add the SensorKit reader entitlement to a `.entitlements` file. List only the
sensors Apple approved for the study. Common entitlement values include:

```xml
<key>com.apple.developer.sensorkit.reader.allow</key>
<array>
    <string>ambient-light-sensor</string>
    <string>motion-accelerometer</string>
    <string>device-usage</string>
    <string>keyboard-metrics</string>
</array>
```

Load the [Entitlement and Usage-Detail Catalog](references/sensorkit-patterns.md#entitlement-and-usage-detail-catalog)
when selecting the exact entitlement string and `NSSensorKitUsageDetail` key
for each approved sensor. Recheck specialized sensors against their individual
`SRSensor` pages.

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

Use the exact usage-detail dictionary for each requested sensor. Load the
[Entitlement and Usage-Detail Catalog](references/sensorkit-patterns.md#entitlement-and-usage-detail-catalog)
when mapping sensors beyond the motion and ambient-light examples above.

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

Use one status handler both for the initial check and delegate changes:

```swift
private func applyAuthorizationStatus(
    _ status: SRAuthorizationStatus,
    to reader: SRSensorReader
) {
    switch status {
    case .authorized:
        reader.startRecording()
    case .denied:
        reader.stopRecording()
        // Direct the user to Settings > Privacy > Research Sensor & Usage Data.
    case .notDetermined:
        break // Request authorization first.
    @unknown default:
        break
    }
}

applyAuthorizationStatus(reader.authorizationStatus, to: reader)

func sensorReader(_ reader: SRSensorReader, didChange authorizationStatus: SRAuthorizationStatus) {
    applyAuthorizationStatus(authorizationStatus, to: reader)
}
```

## Available Sensors

Load the [Sensor Catalog](references/sensorkit-patterns.md#sensor-catalog) to map
each `SRSensor` to its sample type. Request only sensors approved for the study
and recheck the selected sensor's availability and usage-detail key.

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

The reader communicates through `SRSensorReaderDelegate`. Load the
[Delegate Method Catalog](references/sensorkit-patterns.md#delegate-method-catalog)
when wiring the complete authorization, recording, device-fetch, and
sample-fetch lifecycle.

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

Obtain Apple's study approval, the sensor-specific entitlement values, and a
matching manual provisioning profile before constructing production readers.

### DON'T: Expect immediate data access

Apply the [Data Holding Period](#data-holding-period); a fetch overlapping the
hold is not proof that recording failed.

### DON'T: Forget to set the delegate before fetching

Assign the delegate before `startRecording()` or `fetch(_:)`; results and
failures arrive through delegate callbacks.

### DON'T: Skip per-sensor Info.plist usage detail

Add the exact [Info.plist Configuration](#infoplist-configuration) usage-detail
entry for every requested sensor.

### DON'T: Ignore SRError codes

Distinguish at least `.invalidEntitlement`, `.noAuthorization`,
`.dataInaccessible`, `.fetchRequestInvalid`, `.promptDeclined`, and unknown
future codes. Load the [Full Delegate Implementation](references/sensorkit-patterns.md#full-delegate-implementation)
for the complete switch and callback wiring.

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
