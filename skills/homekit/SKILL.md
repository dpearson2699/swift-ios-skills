---
name: homekit
description: "Control smart-home accessories and commission Matter devices using HomeKit and MatterSupport. Use when managing homes/rooms/accessories, creating action sets or triggers, reading accessory characteristics, onboarding Matter devices, or building a third-party smart-home ecosystem app."
---

# HomeKit

Control home automation accessories and commission Matter devices. HomeKit manages
the home/room/accessory model, action sets, and triggers. MatterSupport handles device commissioning into your ecosystem.

## Contents

- [Setup](#setup)
- [HomeKit Data Model](#homekit-data-model)
- [Managing Accessories](#managing-accessories)
- [Reading and Writing Characteristics](#reading-and-writing-characteristics)
- [Action Sets and Triggers](#action-sets-and-triggers)
- [Matter Commissioning](#matter-commissioning)
- [MatterAddDeviceExtensionRequestHandler](#matteradddeviceextensionrequesthandler)
- [Common Mistakes](#common-mistakes)
- [Review Checklist](#review-checklist)
- [References](#references)

## Setup

### HomeKit Configuration

1. Enable the **HomeKit** capability in Xcode (Signing & Capabilities)
2. Add `NSHomeKitUsageDescription` to Info.plist:

```xml
<key>NSHomeKitUsageDescription</key>
<string>This app controls your smart home accessories.</string>
```

### MatterSupport Configuration

For Matter commissioning into your own ecosystem:

1. Add a **MatterSupport Extension** target and set its principal class to a
   `MatterAddDeviceExtensionRequestHandler` subclass
2. Add `NSBonjourServices` entries for `_matter._tcp`, `_matterc._udp`, and
   `_matterd._udp`
3. Add `com.apple.developer.matter.allow-setup-payload` only if the caller
   supplies a Matter setup payload programmatically

### Framework Boundary

| Need | Framework |
|---|---|
| Homes, rooms, accessories, characteristics, actions, triggers | HomeKit |
| Commission Matter into the app ecosystem | MatterSupport |
| Select and authorize a nearby Bluetooth or Wi-Fi accessory | AccessorySetupKit |
| Exchange Bluetooth GATT data after selection | CoreBluetooth |
| Join or configure an accessory's Wi-Fi network after selection | NetworkExtension |

## HomeKit Data Model

HomeKit organizes home automation in a hierarchy:

```text
HMHomeManager
  -> HMHome (one or more)
       -> HMRoom (rooms in the home)
            -> HMAccessory (devices in a room)
                 -> HMService (functions: light, thermostat, etc.)
                      -> HMCharacteristic (readable/writable values)
       -> HMZone (groups of rooms)
       -> HMActionSet (grouped actions)
       -> HMTrigger (time or event-based triggers)
```

### Initializing the Home Manager

Create a single `HMHomeManager` and implement the delegate to know when
data is loaded. HomeKit loads asynchronously -- do not access `homes` until
the delegate fires.

```swift
import HomeKit

final class HomeStore: NSObject, HMHomeManagerDelegate {
    let homeManager = HMHomeManager()

    override init() {
        super.init()
        homeManager.delegate = self
    }

    func homeManagerDidUpdateHomes(_ manager: HMHomeManager) {
        // Safe to access manager.homes now
        let homes = manager.homes
        let primaryHome = manager.primaryHome
        print("Loaded \(homes.count) homes")
    }

    func homeManager(
        _ manager: HMHomeManager,
        didUpdate status: HMHomeManagerAuthorizationStatus
    ) {
        if status.contains(.authorized) {
            print("HomeKit access granted")
        }
    }
}
```

### Accessing Rooms

```swift
guard let home = homeManager.primaryHome else { return }

let rooms = home.rooms
let kitchen = rooms.first { $0.name == "Kitchen" }

// Room for accessories not assigned to a specific room
let defaultRoom = home.roomForEntireHome()
```

## Managing Accessories

### Discovering and Adding Accessories

Use the [Framework Boundary](#framework-boundary) table before adding an
accessory; only HomeKit/MatterSupport work continues in this skill.

```swift
// System UI for accessory discovery
home.addAndSetupAccessories { error in
    if let error {
        print("Setup failed: \(error)")
    }
}
```

### Listing Accessories and Services

```swift
for accessory in home.accessories {
    print("\(accessory.name) in \(accessory.room?.name ?? "unassigned")")

    for service in accessory.services {
        print("  Service: \(service.serviceType)")

        for characteristic in service.characteristics {
            print("    \(characteristic.characteristicType): \(characteristic.value ?? "nil")")
        }
    }
}
```

### Moving an Accessory to a Room

```swift
guard let accessory = home.accessories.first,
      let bedroom = home.rooms.first(where: { $0.name == "Bedroom" }) else { return }

home.assignAccessory(accessory, to: bedroom) { error in
    if let error {
        print("Failed to move accessory: \(error)")
    }
}
```

## Reading and Writing Characteristics

### Reading a Value

```swift
let characteristic: HMCharacteristic = // obtained from a service

characteristic.readValue { error in
    guard error == nil else { return }
    if let value = characteristic.value as? Bool {
        print("Power state: \(value)")
    }
}
```

### Writing a Value

```swift
// Turn on a light
characteristic.writeValue(true) { error in
    if let error {
        print("Write failed: \(error)")
    }
}
```

### Observing Changes

Enable notifications for real-time updates:

```swift
characteristic.enableNotification(true) { error in
    guard error == nil else { return }
}

// In HMAccessoryDelegate:
func accessory(
    _ accessory: HMAccessory,
    service: HMService,
    didUpdateValueFor characteristic: HMCharacteristic
) {
    print("Updated: \(characteristic.value ?? "nil")")
}
```

## Action Sets and Triggers

### Creating an Action Set

An `HMActionSet` groups characteristic writes that execute together:

```swift
home.addActionSet(withName: "Good Night") { actionSet, error in
    guard let actionSet, error == nil else { return }

    // Turn off living room light
    let lightChar = livingRoomLight.powerCharacteristic
    let action = HMCharacteristicWriteAction(
        characteristic: lightChar,
        targetValue: false as NSCopying
    )
    actionSet.addAction(action) { error in
        guard error == nil else { return }
        print("Action added to Good Night scene")
    }
}
```

### Executing an Action Set

```swift
home.executeActionSet(actionSet) { error in
    if let error {
        print("Execution failed: \(error)")
    }
}
```

### Creating a Timer Trigger

```swift
var timeOfDay = DateComponents()
timeOfDay.hour = 22
timeOfDay.minute = 30

let firstFireDate = Calendar.current.nextDate(
    after: Date(),
    matching: timeOfDay,
    matchingPolicy: .nextTime
)!

let trigger = HMTimerTrigger(
    name: "Nightly",
    fireDate: firstFireDate,
    recurrence: DateComponents(day: 1)  // Repeat every day after firstFireDate
)

home.addTrigger(trigger) { error in
    guard error == nil else { return }

    // Attach the action set to the trigger
    trigger.addActionSet(goodNightActionSet) { error in
        guard error == nil else { return }

        trigger.enable(true) { error in
            print("Trigger enabled: \(error == nil)")
        }
    }
}
```

### Creating an Event Trigger

```swift
let motionDetected = HMCharacteristicEvent(
    characteristic: motionSensorCharacteristic,
    triggerValue: true as NSCopying
)

let eventTrigger = HMEventTrigger(
    name: "Motion Lights",
    events: [motionDetected],
    predicate: nil
)

home.addTrigger(eventTrigger) { error in
    // Add action sets as above
}
```

## Matter Commissioning

Use `MatterAddDeviceRequest` to commission a Matter device into your ecosystem.
This is separate from the `HMHome` home-automation model; it handles the
Matter setup flow and calls into your MatterSupport extension.

### Basic Commissioning

```swift
import MatterSupport

func addMatterDevice() async throws {
    guard MatterAddDeviceRequest.isSupported else {
        print("Matter not supported on this device")
        return
    }

    let topology = MatterAddDeviceRequest.Topology(
        ecosystemName: "My Smart Home",
        homes: [
            MatterAddDeviceRequest.Home(displayName: "Main House")
        ]
    )

    let request = MatterAddDeviceRequest(
        topology: topology,
        setupPayload: nil,
        showing: .allDevices
    )

    // Presents system UI for device pairing
    try await request.perform()
}
```

When providing a setup code directly, import Matter and pass an
`MTRSetupPayload` as `setupPayload`; this is the case that requires the
setup-payload entitlement.

### Filtering Devices

```swift
// Only show devices from a specific vendor
let criteria = MatterAddDeviceRequest.DeviceCriteria.vendorID(0x1234)

let request = MatterAddDeviceRequest(
    topology: topology,
    setupPayload: nil,
    showing: criteria
)
```

Combine criteria with `.all([.vendorID(...), .not(.productID(...))])` or use
`.any(...)` when any one criterion is enough.

## MatterAddDeviceExtensionRequestHandler

For full ecosystem support, create a MatterSupport Extension. The extension
handles commissioning callbacks. Override the needed methods, but do not call
`super` from those overrides.
Load the complete [Advanced Matter Extension Handler](references/matter-commissioning.md#advanced-matter-extension-handler)
for credential validation, room selection, configuration, commissioning, and
network-association overrides.

## Common Mistakes

| Mistake | Fix |
|---|---|
| Reading homes before the delegate update | Create one manager, set its delegate, and wait for `homeManagerDidUpdateHomes`. |
| HomeKit setup is used for Matter ecosystem commissioning | Use `MatterAddDeviceRequest` plus the configured MatterSupport extension. |
| Matter configuration is incomplete | Verify principal handler, Bonjour services, and the setup-payload entitlement only when applicable. |
| Multiple `HMHomeManager` instances load the database | Share one retained manager/store. |
| Characteristic write ignores metadata | Check permissions, format, min/max/step, and allowed values before writing. |

## Review Checklist

- [ ] HomeKit capability enabled in Xcode
- [ ] `NSHomeKitUsageDescription` present in Info.plist
- [ ] Single `HMHomeManager` instance shared across the app
- [ ] `HMHomeManagerDelegate` implemented; homes not accessed before `homeManagerDidUpdateHomes`
- [ ] `HMHomeDelegate` set on homes to receive accessory and room changes
- [ ] `HMAccessoryDelegate` set on accessories to receive characteristic updates
- [ ] Characteristic metadata checked before writing values
- [ ] Error handling in all completion handlers
- [ ] MatterSupport extension target and principal handler configured
- [ ] Matter discovery `NSBonjourServices` entries added
- [ ] `com.apple.developer.matter.allow-setup-payload` used only when providing setup codes
- [ ] `MatterAddDeviceRequest.isSupported` checked before performing requests
- [ ] Matter extension handler implements `commissionDevice(in:onboardingPayload:commissioningID:)`
- [ ] Action sets tested with the HomeKit Accessory Simulator before shipping
- [ ] Triggers enabled after creation (`trigger.enable(true)`)

## References

- Extended patterns (Matter extension, delegate wiring, SwiftUI): [references/matter-commissioning.md](references/matter-commissioning.md)
- [HomeKit framework](https://sosumi.ai/documentation/homekit)
- [HMHomeManager](https://sosumi.ai/documentation/homekit/hmhomemanager)
- [HMHome](https://sosumi.ai/documentation/homekit/hmhome)
- [HMAccessory](https://sosumi.ai/documentation/homekit/hmaccessory)
- [HMRoom](https://sosumi.ai/documentation/homekit/hmroom)
- [HMActionSet](https://sosumi.ai/documentation/homekit/hmactionset)
- [HMTrigger](https://sosumi.ai/documentation/homekit/hmtrigger)
- [MatterSupport framework](https://sosumi.ai/documentation/mattersupport)
- [MatterAddDeviceRequest](https://sosumi.ai/documentation/mattersupport/matteradddevicerequest)
- [MatterAddDeviceExtensionRequestHandler](https://sosumi.ai/documentation/mattersupport/matteradddeviceextensionrequesthandler)
- [Enabling HomeKit in your app](https://sosumi.ai/documentation/homekit/enabling-homekit-in-your-app)
- [Adding Matter support to your ecosystem](https://sosumi.ai/documentation/mattersupport/adding-matter-support-to-your-ecosystem)
