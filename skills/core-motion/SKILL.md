---
name: core-motion
description: "Access Core Motion accelerometer, gyroscope, magnetometer, device-motion, pedometer, activity-recognition, altitude, headphone motion, batched high-frequency workout motion, and water-submersion/depth data. Use when reading device sensors, counting steps, detecting walking/running/driving/cycling, tracking altitude, building motion interactions, handling AirPods head tracking, or implementing watchOS dive/depth features."
---

# CoreMotion

Read device motion, pedometer/activity, altitude, headphone, batched-workout,
and submersion sensors with Core Motion. Scope: Swift 6.3, iOS 26+.

## Contents

- [Setup](#setup)
- [CMMotionManager: Sensor Data](#cmmotionmanager-sensor-data)
- [Processed Device Motion](#processed-device-motion)
- [CMPedometer: Step and Distance Data](#cmpedometer-step-and-distance-data)
- [CMMotionActivityManager: Activity Recognition](#cmmotionactivitymanager-activity-recognition)
- [CMAltimeter: Altitude Data](#cmaltimeter-altitude-data)
- [Update Intervals and Battery](#update-intervals-and-battery)
- [Common Mistakes](#common-mistakes)
- [Review Checklist](#review-checklist)
- [References](#references)

## Setup

### Info.plist

Add `NSMotionUsageDescription` to Info.plist with a user-facing string explaining
why your app needs motion data. Without this key, the app crashes on first access.

```xml
<key>NSMotionUsageDescription</key>
<string>This app uses motion data to track your activity.</string>
```

### Authorization

Use the matching manager's `authorizationStatus()` or `authorizationStatus`
property when an API exposes one (`CMPedometer`, `CMMotionActivityManager`,
`CMAltimeter`, headphone motion, batched sensors, and submersion). Raw
`CMMotionManager` accelerometer/gyro/device-motion streams have no explicit
authorization request API; still ship the usage string and handle errors from
start/update callbacks.

```swift
import CoreMotion

let status = CMMotionActivityManager.authorizationStatus()
switch status {
case .notDetermined:
    // Will prompt on first use
    break
case .authorized:
    break
case .restricted, .denied:
    // Direct user to Settings
    break
@unknown default:
    break
}
```

## CMMotionManager: Sensor Data

Create exactly **one** `CMMotionManager` per app. Multiple instances degrade
sensor update rates.

```swift
import CoreMotion

let motionManager = CMMotionManager()
```

### Accelerometer Updates

```swift
guard motionManager.isAccelerometerAvailable else { return }

motionManager.accelerometerUpdateInterval = 1.0 / 60.0  // 60 Hz

motionManager.startAccelerometerUpdates(to: .main) { data, error in
    guard let acceleration = data?.acceleration else { return }
    print("x: \(acceleration.x), y: \(acceleration.y), z: \(acceleration.z)")
}

// When done:
motionManager.stopAccelerometerUpdates()
```

### Gyroscope Updates

```swift
guard motionManager.isGyroAvailable else { return }

motionManager.gyroUpdateInterval = 1.0 / 60.0

motionManager.startGyroUpdates(to: .main) { data, error in
    guard let rotationRate = data?.rotationRate else { return }
    print("x: \(rotationRate.x), y: \(rotationRate.y), z: \(rotationRate.z)")
}

motionManager.stopGyroUpdates()
```

### Polling Pattern (Games)

For games, start updates without a handler and poll the latest sample each frame:

```swift
motionManager.startAccelerometerUpdates()

// In your game loop / display link:
if let data = motionManager.accelerometerData {
    let tilt = data.acceleration.x
    // Move player based on tilt
}
```

## Processed Device Motion

Device motion fuses accelerometer, gyroscope, and magnetometer into a single
`CMDeviceMotion` object with attitude, user acceleration (gravity removed),
rotation rate, and calibrated magnetic field.

When giving device-motion guidance, show the runtime frame check in the snippet
instead of hard-coding a corrected, magnetic-north, or true-north frame. Fall
back to `.xArbitraryZVertical` when the preferred frame is unavailable.

```swift
guard motionManager.isDeviceMotionAvailable else { return }

let availableFrames = CMMotionManager.availableAttitudeReferenceFrames()
let frame: CMAttitudeReferenceFrame = availableFrames.contains(.xArbitraryCorrectedZVertical)
    ? .xArbitraryCorrectedZVertical
    : .xArbitraryZVertical

motionManager.deviceMotionUpdateInterval = 1.0 / 60.0

motionManager.startDeviceMotionUpdates(
    using: frame,
    to: .main
) { motion, error in
    guard let motion else { return }

    let attitude = motion.attitude       // roll, pitch, yaw
    let userAccel = motion.userAcceleration
    let gravity = motion.gravity
    let heading = motion.heading         // degrees relative to the current frame

    print("Pitch: \(attitude.pitch), Roll: \(attitude.roll)")
}

motionManager.stopDeviceMotionUpdates()
```

### Attitude Reference Frames

For simple tilt controls, use `.xArbitraryZVertical` or
`.xArbitraryCorrectedZVertical`; they avoid magnetometer/location dependencies.
Before requesting corrected, magnetic-north, or true-north frames, call
`CMMotionManager.availableAttitudeReferenceFrames()` and fall back to an
available frame.

| Frame | Use Case |
|---|---|
| `.xArbitraryZVertical` | Default. Z is vertical, X arbitrary at start. Most games. |
| `.xArbitraryCorrectedZVertical` | Same as above, corrected for gyro drift over time. |
| `.xMagneticNorthZVertical` | X points to magnetic north. Requires magnetometer. |
| `.xTrueNorthZVertical` | X points to true north. Requires magnetometer + location. |

Check available frames before use:

```swift
let available = CMMotionManager.availableAttitudeReferenceFrames()
if available.contains(.xTrueNorthZVertical) {
    // Safe to use true north
}
```

## CMPedometer: Step and Distance Data

`CMPedometer` provides step counts, distance, pace, cadence, and floor counts.

```swift
let pedometer = CMPedometer()

guard CMPedometer.isStepCountingAvailable() else { return }

// Historical query
pedometer.queryPedometerData(
    from: Calendar.current.startOfDay(for: Date()),
    to: Date()
) { data, error in
    guard let data else { return }
    print("Steps today: \(data.numberOfSteps)")
    print("Distance: \(data.distance?.doubleValue ?? 0) meters")
    print("Floors up: \(data.floorsAscended?.intValue ?? 0)")
}

// Live updates
pedometer.startUpdates(from: Date()) { data, error in
    guard let data else { return }
    print("Steps: \(data.numberOfSteps)")
}

// Stop when done
pedometer.stopUpdates()
```

### Availability Checks

| Method | What It Checks |
|---|---|
| `isStepCountingAvailable()` | Step counter hardware |
| `isDistanceAvailable()` | Distance estimation |
| `isFloorCountingAvailable()` | Barometric altimeter for floors |
| `isPaceAvailable()` | Pace data |
| `isCadenceAvailable()` | Cadence data |

## CMMotionActivityManager: Activity Recognition

Detects whether the user is stationary, walking, running, cycling, or in a vehicle.

```swift
let activityManager = CMMotionActivityManager()

guard CMMotionActivityManager.isActivityAvailable() else { return }

// Live activity updates
activityManager.startActivityUpdates(to: .main) { activity in
    guard let activity else { return }

    if activity.walking {
        print("Walking (confidence: \(activity.confidence.rawValue))")
    } else if activity.running {
        print("Running")
    } else if activity.automotive {
        print("In vehicle")
    } else if activity.cycling {
        print("Cycling")
    } else if activity.stationary {
        print("Stationary")
    }
}

activityManager.stopActivityUpdates()
```

### Historical Activity Query

```swift
let yesterday = Calendar.current.date(byAdding: .day, value: -1, to: Date())!

activityManager.queryActivityStarting(
    from: yesterday,
    to: Date(),
    to: .main
) { activities, error in
    guard let activities else { return }
    for activity in activities {
        print("\(activity.startDate): walking=\(activity.walking)")
    }
}
```

## CMAltimeter: Altitude Data

Altimeter access is covered by `NSMotionUsageDescription`; handle denied motion
access through unavailable data and update-handler errors.

```swift
let altimeter = CMAltimeter()

guard CMAltimeter.isRelativeAltitudeAvailable() else { return }

altimeter.startRelativeAltitudeUpdates(to: .main) { data, error in
    guard let data else { return }
    print("Relative altitude: \(data.relativeAltitude) meters")
    print("Pressure: \(data.pressure) kPa")
}

altimeter.stopRelativeAltitudeUpdates()
```

Absolute altitude is altitude relative to sea level, not GPS-based altitude.
First check availability. Absolute altitude is available only on supported
hardware such as iPhone 12 or later and Apple Watch Series 6, Apple Watch SE, or
later.

```swift
guard CMAltimeter.isAbsoluteAltitudeAvailable() else { return }

altimeter.startAbsoluteAltitudeUpdates(to: .main) { data, error in
    guard let data else { return }
    print("Altitude: \(data.altitude)m, accuracy: \(data.accuracy)m")
}

altimeter.stopAbsoluteAltitudeUpdates()
```

## Update Intervals and Battery

| Interval | Hz | Use Case | Battery Impact |
|---|---|---|---|
| `1.0 / 10.0` | 10 | UI orientation | Low |
| `1.0 / 30.0` | 30 | Casual games | Moderate |
| `1.0 / 60.0` | 60 | Action games | High |
| `1.0 / 100.0` | 100 | Max rate (iPhone) | Very High |

Use the lowest frequency that meets your needs. Do not assume a fixed maximum
sample rate across devices. For high-frequency workout motion, use
`CMBatchedSensorManager` where supported and read its reported
`accelerometerDataFrequency` or `deviceMotionDataFrequency` instead of assigning
those read-only properties.

## Common Mistakes

### DON'T: Create multiple CMMotionManager instances

Retain one app-level `CMMotionManager`; competing instances can reduce update
rates.

### DON'T: Skip sensor availability checks

Apply the matching `is...Available` gate immediately before starting each
sensor stream.

### DON'T: Forget to stop updates

Pair every start with the matching stop in the counterpart lifecycle or task
cancellation path.

### DON'T: Use unnecessarily high update rates

Choose the lowest rate that meets the interaction and use the
[Update Intervals and Battery](#update-intervals-and-battery) table as a starting
point.

### DON'T: Assume all CMMotionActivity properties are mutually exclusive

```swift
// WRONG -- checking only one property
if activity.walking { handleWalking() }

// CORRECT -- multiple can be true simultaneously; check confidence
if activity.walking && activity.confidence == .high {
    handleWalking()
} else if activity.automotive && activity.confidence != .low {
    handleDriving()
}
```

## Review Checklist

- [ ] `NSMotionUsageDescription` present in Info.plist with a clear explanation
- [ ] Single `CMMotionManager` instance shared across the app
- [ ] Sensor availability checked before starting updates (`isAccelerometerAvailable`, etc.)
- [ ] Authorization status checked before pedometer/activity APIs
- [ ] Update interval set to the lowest acceptable frequency
- [ ] All `start*Updates` calls have matching `stop*Updates` in lifecycle counterparts
- [ ] Handlers dispatched to appropriate queues (not blocking main for heavy processing)
- [ ] `CMMotionActivity.confidence` checked before acting on activity type
- [ ] Error parameters checked in update handlers
- [ ] Device-motion snippets call `CMMotionManager.availableAttitudeReferenceFrames()` before requesting a specific attitude frame
- [ ] Attitude reference frame chosen based on actual need (not defaulting to true north unnecessarily)

## References

- Extended patterns (SwiftUI integration, batched sensor manager, headphone motion, water submersion): [references/motion-patterns.md](references/motion-patterns.md)
- [CoreMotion framework](https://sosumi.ai/documentation/coremotion)
- [CMMotionManager](https://sosumi.ai/documentation/coremotion/cmmotionmanager)
- [CMPedometer](https://sosumi.ai/documentation/coremotion/cmpedometer)
- [CMMotionActivityManager](https://sosumi.ai/documentation/coremotion/cmmotionactivitymanager)
- [CMDeviceMotion](https://sosumi.ai/documentation/coremotion/cmdevicemotion)
- [CMAltimeter](https://sosumi.ai/documentation/coremotion/cmaltimeter)
- [CMAbsoluteAltitudeData](https://sosumi.ai/documentation/coremotion/cmabsolutealtitudedata)
- [CMBatchedSensorManager](https://sosumi.ai/documentation/coremotion/cmbatchedsensormanager)
- [CMHeadphoneMotionManager](https://sosumi.ai/documentation/coremotion/cmheadphonemotionmanager)
- [CMWaterSubmersionManager](https://sosumi.ai/documentation/coremotion/cmwatersubmersionmanager)
- [Accessing submersion data](https://sosumi.ai/documentation/coremotion/accessing-submersion-data)
- [Getting processed device-motion data](https://sosumi.ai/documentation/coremotion/getting-processed-device-motion-data)
