---
name: audioaccessorykit
description: "Support automatic audio switching for paired third-party Bluetooth headphones or earbuds with AudioAccessoryKit. Use when a companion app registers an audio accessory, an app extension reports worn/removed placement or connected source-device changes, or AccessoryControlDevice capabilities and errors need handling. Do not use for general AVAudioSession routing, Bluetooth transport, or initial accessory pairing."
---

# AudioAccessoryKit

Automatic audio switching support and intelligent audio routing inputs for
third-party audio accessories. Enables companion apps to register audio
accessory configuration with the system, and app extensions to report placement
and connected source changes that help the system switch audio output.
Available iOS 26.4+ / iPadOS 26.4+.

> **Beta-sensitive.** AudioAccessoryKit is new in iOS 26.4. Re-check current
> Apple documentation before relying on specific API details.

AudioAccessoryKit builds on top of AccessorySetupKit. The accessory must first
be paired via AccessorySetupKit before it can be registered for audio features.
The central type is `AccessoryControlDevice`, which registers a
`Configuration` from the container app and applies ongoing configuration updates
from the app extension.

## Contents

- [Setup](#setup)
- [Session Management](#session-management)
- [Audio Switching](#audio-switching)
- [Device Placement](#device-placement)
- [Connected Audio Sources](#connected-audio-sources)
- [Feature Discovery](#feature-discovery)
- [Error Handling](#error-handling)
- [Common Mistakes](#common-mistakes)
- [Review Checklist](#review-checklist)
- [References](#references)

## Setup

### Prerequisites

1. Pair the accessory over Bluetooth using AccessorySetupKit. This yields an
   `ASAccessory` object.
2. Import the frameworks where needed in the container app and extension:

```swift
import AccessorySetupKit
import AudioAccessoryKit
```

### Framework Availability

| Platform | Minimum Version |
|---|---|
| iOS | 26.4+ |
| iPadOS | 26.4+ |

In the current Xcode 26.6 toolchain, AudioAccessoryKit is present in the device
SDK but not the iPhone Simulator 26.5 SDK. Use a physical-device destination
for this target. If the rest of the app must build for Simulator, isolate target
membership or guard the import and implementation with
`#if canImport(AudioAccessoryKit)` and provide a simulator stub.

## Session Management

### Registering an Accessory

After pairing via AccessorySetupKit, register the accessory from the container
app by passing an `AccessoryControlDevice.Configuration` that describes the
capabilities and any initial state the accessory supports:

```swift
let accessory: ASAccessory  // Obtained from AccessorySetupKit pairing

let configuration = AccessoryControlDevice.Configuration(
    devicePlacement: .offHead,
    deviceCapabilities: [.audioSwitching, .placement]
)

try await AccessoryControlDevice.register(accessory, configuration)
```

Registration activates the specified capabilities and gives the system the
configuration it needs to participate in audio routing decisions.

### Retrieving the Current Configuration

In the app extension, access the device's current configuration using the
static `current(for:)` method:

```swift
let device = try AccessoryControlDevice.current(for: accessory)
let currentConfig = device.configuration
```

This returns the `AccessoryControlDevice` instance associated with the paired
`ASAccessory`. The device exposes both the `accessory` reference and the
current `configuration`. Apple marks `current(for:)` as app-extension-only.

### Updating Configuration

In the app extension, push configuration changes to the system with
`update(_:)`. Only update fields for capabilities that were declared during
registration:

```swift
let device = try AccessoryControlDevice.current(for: accessory)
var config = device.configuration

config.devicePlacement = .onHead
try await device.update(config)
```

Treat this as a gated write workflow: confirm registration declared the
capability, copy and mutate `device.configuration`, then `try await update(_:)`.
The method returns no configuration value; update an app-side mirror only after
the call succeeds. On failure, use the disposition in
[Error Handling](#error-handling). Apple marks `update(_:)` as
app-extension-only.

## Audio Switching

Automatic audio switching lets the system intelligently route audio output to
the correct device based on placement and connected sources.

### Enabling Audio Switching

Declare `.audioSwitching` during the canonical registration flow above. Include
`.placement` and an initial placement only when the accessory can report ongoing
placement changes.

### Capabilities

Automatic switching commonly uses these `AccessoryControlDevice.Capabilities`:

| Capability | Purpose |
|---|---|
| `.audioSwitching` | Device supports automatic audio switching |
| `.placement` | Device can report its physical placement |

Combine capabilities as needed. Do not declare `.placement` unless the
accessory can keep the system updated with real placement state.

## Device Placement

Report the physical position of the accessory from the app extension to help the
system make routing decisions. Update placement whenever the accessory detects a
position change.

### Placement Values

`AccessoryControlDevice.Placement` defines four cases:

| Placement | Meaning |
|---|---|
| `.inEar` | Accessory is seated in the ear (e.g., earbuds) |
| `.onHead` | Accessory is on the head (e.g., headband headphones) |
| `.overTheEar` | Accessory is over the ear (e.g., over-ear headphones) |
| `.offHead` | Accessory is not being worn |

### Updating Placement

```swift
config.devicePlacement = .inEar
```

Apply this mutation within the canonical current→copy→update sequence above.

Common transitions:

- `.offHead` to `.onHead` or `.inEar` when the user puts on the accessory
- `.onHead` or `.inEar` to `.offHead` when removed
- Update promptly on every detected change for responsive audio routing

## Connected Audio Sources

For accessories that connect to multiple Bluetooth devices simultaneously,
inform the system from the app extension which devices are connected. This lets
the system route audio from the appropriate source.

### Setting Audio Source Identifiers

Provide the Bluetooth address of connected devices as `Data`:

```swift
let primaryBTAddress = Data([0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC])
config.primaryAudioSourceDeviceIdentifier = primaryBTAddress

let secondaryBTAddress = Data([0xAB, 0xCD, 0xEF, 0x01, 0x23, 0x45])
config.secondaryAudioSourceDeviceIdentifier = secondaryBTAddress
```

Update these identifiers when the Bluetooth connection state changes (new
device connects, existing device disconnects), then call the canonical
`update(_:)` sequence.

### Configuration Properties

Automatic switching uses these configuration fields:

| Property | Type | Purpose |
|---|---|---|
| `deviceCapabilities` | `Capabilities` | Declared device capabilities |
| `devicePlacement` | `Placement?` | Current physical placement |
| `primaryAudioSourceDeviceIdentifier` | `Data?` | Primary connected Bluetooth device address |
| `secondaryAudioSourceDeviceIdentifier` | `Data?` | Secondary connected Bluetooth device address |

## Feature Discovery

### Querying Capabilities

In the app extension, inspect the device's declared capabilities through its
configuration:

```swift
let device = try AccessoryControlDevice.current(for: accessory)
let caps = device.configuration.deviceCapabilities

if caps.contains(.audioSwitching) {
    // Device supports automatic audio switching
}

if caps.contains(.placement) {
    // Device reports physical placement
}
```

### Checking Placement

Read the current placement to determine if the accessory is being worn:

```swift
let device = try AccessoryControlDevice.current(for: accessory)

if let placement = device.configuration.devicePlacement {
    switch placement {
    case .inEar, .onHead, .overTheEar:
        // Accessory is being worn
        break
    case .offHead:
        // Accessory is not being worn
        break
    @unknown default:
        break
    }
}
```

## Error Handling

`AccessoryControlDevice.Error` covers failure cases during registration and
updates:

| Error | Cause |
|---|---|
| `.accessoryNotCapable` | Accessory does not support the requested capability |
| `.invalidRequest` | Request parameters are invalid |
| `.invalidated` | Device registration has been invalidated |
| `.unknown` | An unspecified error occurred |

Handle errors from registration and update calls:

```swift
let configuration = AccessoryControlDevice.Configuration(
    devicePlacement: .offHead,
    deviceCapabilities: [.audioSwitching, .placement]
)

do {
    try await AccessoryControlDevice.register(accessory, configuration)
} catch let error as AccessoryControlDevice.Error {
    switch error {
    case .accessoryNotCapable:
        // Accessory hardware does not support requested capabilities
        break
    case .invalidRequest:
        // Check registration parameters
        break
    case .invalidated:
        // Coordinate container-app registration again
        break
    case .unknown:
        // Log, surface, or propagate; Apple does not classify this as transient
        throw error
    @unknown default:
        throw error
    }
}
```

Do not infer that `.invalidated` or `.unknown` is transient. Correct invalid
capabilities or request parameters, discard an invalidated handle and notify
the container app to re-evaluate registration where appropriate, and surface unspecified errors. Load
[Error Recovery Patterns](references/audioaccessorykit-patterns.md#error-recovery-patterns)
for the complete disposition and invalidation handoff.

## Common Mistakes

### DON'T: Register before pairing with AccessorySetupKit

Register only the `ASAccessory` returned by a completed AccessorySetupKit pairing.

### DON'T: Declare placement capability without updating placement

If registration declares `.placement`, the extension must update placement on
every detected transition using the canonical update sequence.

### DON'T: Ignore connection state changes for multi-device accessories

Clear or replace primary and secondary source identifiers whenever Bluetooth
connections change; stale identifiers reduce switching accuracy.

### DON'T: Forget to handle the invalidated error

```swift
// WRONG -- ignores invalidation, keeps using stale device reference
try await device.update(config)  // Throws .invalidated, unhandled

// CORRECT -- discard the handle and let the container re-evaluate registration
do {
    try await device.update(config)
} catch AccessoryControlDevice.Error.invalidated {
    await notifyContainerAppToReevaluateRegistration(accessory)
}
```

## Review Checklist

- [ ] Accessory paired via AccessorySetupKit before AudioAccessoryKit registration
- [ ] Both `AccessorySetupKit` and `AudioAccessoryKit` imported
- [ ] Container app calls `register(_: _:)` with `AccessoryControlDevice.Configuration`
- [ ] App extension calls `current(for:)` and `update(_:)`
- [ ] Capabilities in the registration configuration match actual hardware support
- [ ] Updates only touch fields for capabilities declared during registration
- [ ] `.placement` capability accompanied by ongoing placement updates
- [ ] Placement transitions (on/off head) reported promptly
- [ ] Audio source device identifiers updated on Bluetooth connection changes
- [ ] All `AccessoryControlDevice.Error` cases handled, including `@unknown default`
- [ ] `update(_:)` calls use `try await` and handle errors
- [ ] Invalidated device references trigger container-app registration recovery
- [ ] Deployment target set to iOS 26.4+ or iPadOS 26.4+

## References

- Extended patterns (registration flow, placement monitoring, multi-device coordination): [references/audioaccessorykit-patterns.md](references/audioaccessorykit-patterns.md)
- [AudioAccessoryKit framework](https://sosumi.ai/documentation/audioaccessorykit)
- [Supporting automatic audio switching](https://sosumi.ai/documentation/audioaccessorykit/supporting-automatic-audio-switching)
- [AccessoryControlDevice](https://sosumi.ai/documentation/audioaccessorykit/accessorycontroldevice)
- [AccessoryControlDevice registration](https://sosumi.ai/documentation/audioaccessorykit/accessorycontroldevice/register%28_%3A_%3A%29)
- [AccessoryControlDevice lookup](https://sosumi.ai/documentation/audioaccessorykit/accessorycontroldevice/current%28for%3A%29)
- [AccessoryControlDevice update](https://sosumi.ai/documentation/audioaccessorykit/accessorycontroldevice/update%28_%3A%29)
- [AccessoryControlDevice.Configuration](https://sosumi.ai/documentation/audioaccessorykit/accessorycontroldevice/configuration-swift.struct)
- [AccessoryControlDevice.Capabilities](https://sosumi.ai/documentation/audioaccessorykit/accessorycontroldevice/capabilities)
- [AccessoryControlDevice.Placement](https://sosumi.ai/documentation/audioaccessorykit/accessorycontroldevice/placement)
- [AccessorySetupKit framework](https://sosumi.ai/documentation/accessorysetupkit) (prerequisite for pairing)
