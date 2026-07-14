---
name: core-bluetooth
description: "Build direct Bluetooth Low Energy workflows with Core Bluetooth. Use when implementing BLE central or peripheral GATT communication, scanning or connecting with CBCentralManager, discovering services and characteristics, reading/writing/subscribing with CBPeripheral, publishing local services with CBPeripheralManager, handling Bluetooth authorization, background BLE modes, state restoration, write flow control, or CBUUID-based workflows. For privacy-preserving accessory setup/picker flows, use accessorysetupkit first and return here for post-setup GATT communication."
---

# Core Bluetooth

Scan for, connect to, and exchange data with Bluetooth Low Energy (BLE) devices.
Covers the central role (scanning and connecting to peripherals), the peripheral
role (advertising services), background modes, and state restoration.
Use `accessorysetupkit` for privacy-preserving accessory discovery and setup;
use this skill for direct Core Bluetooth GATT communication.

## Contents

- [Setup](#setup)
- [Central Role: Scanning](#central-role-scanning)
- [Central Role: Connecting](#central-role-connecting)
- [Discovering Services and Characteristics](#discovering-services-and-characteristics)
- [Reading, Writing, and Notifications](#reading-writing-and-notifications)
- [Peripheral Role: Advertising](#peripheral-role-advertising)
- [Background BLE](#background-ble)
- [State Restoration](#state-restoration)
- [Common Mistakes](#common-mistakes)
- [Review Checklist](#review-checklist)
- [References](#references)

## Setup

### Info.plist Keys

| Key | Purpose |
|---|---|
| `NSBluetoothAlwaysUsageDescription` | Required. Explains why the app uses Bluetooth |
| `UIBackgroundModes` with `bluetooth-central` | Background scanning and connecting |
| `UIBackgroundModes` with `bluetooth-peripheral` | Background advertising |

### Bluetooth Authorization

Core Bluetooth has no explicit permission request API. Add
`NSBluetoothAlwaysUsageDescription`, create the manager when the app is ready for
Bluetooth access, then check `manager.authorization` and `manager.state`.
Treat `.denied` and `.restricted` as terminal until the user changes Settings;
wait for `.poweredOn` before scanning, connecting, advertising, or publishing
services.

## Central Role: Scanning

### Creating the Central Manager

Always wait for the `poweredOn` state before scanning.

```swift
import CoreBluetooth

final class BluetoothManager: NSObject, CBCentralManagerDelegate {
    private var centralManager: CBCentralManager!
    private var discoveredPeripheral: CBPeripheral?

    override init() {
        super.init()
        centralManager = CBCentralManager(delegate: self, queue: nil)
    }

    func centralManagerDidUpdateState(_ central: CBCentralManager) {
        guard central.state == .poweredOn else { return }
        startScanning()
    }
}
```

### Scanning for Peripherals

Scan for specific service UUIDs to save power. Pass `nil` to discover all
peripherals (not recommended in production).

```swift
let heartRateServiceUUID = CBUUID(string: "180D")

func startScanning() {
    centralManager.scanForPeripherals(
        withServices: [heartRateServiceUUID],
        options: [CBCentralManagerScanOptionAllowDuplicatesKey: false]
    )
}

func centralManager(
    _ central: CBCentralManager,
    didDiscover peripheral: CBPeripheral,
    advertisementData: [String: Any],
    rssi RSSI: NSNumber
) {
    guard RSSI.intValue > -70 else { return } // Filter weak signals

    // IMPORTANT: Retain the peripheral -- it will be deallocated otherwise
    discoveredPeripheral = peripheral
    centralManager.stopScan()
    centralManager.connect(peripheral, options: nil)
}
```

## Central Role: Connecting

```swift
func centralManager(
    _ central: CBCentralManager,
    didConnect peripheral: CBPeripheral
) {
    peripheral.delegate = self
    peripheral.discoverServices([heartRateServiceUUID])
}

func centralManager(
    _ central: CBCentralManager,
    didDisconnectPeripheral peripheral: CBPeripheral,
    timestamp: CFAbsoluteTime,
    isReconnecting: Bool,
    error: Error?
) {
    if isReconnecting {
        // System is automatically reconnecting
        return
    }
    // Handle disconnection -- optionally reconnect
    discoveredPeripheral = nil
}
```

## Discovering Services and Characteristics

Implement `CBPeripheralDelegate` to walk the service/characteristic tree.

```swift
extension BluetoothManager: CBPeripheralDelegate {
    func peripheral(
        _ peripheral: CBPeripheral,
        didDiscoverServices error: Error?
    ) {
        guard let services = peripheral.services else { return }
        for service in services {
            peripheral.discoverCharacteristics(nil, for: service)
        }
    }

    func peripheral(
        _ peripheral: CBPeripheral,
        didDiscoverCharacteristicsFor service: CBService,
        error: Error?
    ) {
        guard let characteristics = service.characteristics else { return }
        for characteristic in characteristics {
            if characteristic.properties.contains(.notify) {
                peripheral.setNotifyValue(true, for: characteristic)
            }
            if characteristic.properties.contains(.read) {
                peripheral.readValue(for: characteristic)
            }
        }
    }
}
```

## Reading, Writing, and Notifications

### Reading a Value

```swift
func peripheral(
    _ peripheral: CBPeripheral,
    didUpdateValueFor characteristic: CBCharacteristic,
    error: Error?
) {
    guard let data = characteristic.value else { return }

    switch characteristic.uuid {
    case CBUUID(string: "2A37"):
        if let heartRate = parseHeartRate(data) {
            print("Heart rate: \(heartRate) bpm")
        }
    case CBUUID(string: "2A19"):
        let batteryLevel = data.first.map { Int($0) } ?? 0
        print("Battery: \(batteryLevel)%")
    default:
        break
    }
}

private func parseHeartRate(_ data: Data) -> Int? {
    guard data.count >= 2 else { return nil }
    let flags = data[0]
    let is16Bit = (flags & 0x01) != 0
    if is16Bit {
        guard data.count >= 3 else { return nil }
        return Int(data[1]) | (Int(data[2]) << 8)
    } else {
        return Int(data[1])
    }
}
```

### Writing a Value

```swift
func writeValue(_ data: Data, to characteristic: CBCharacteristic,
                on peripheral: CBPeripheral,
                preferResponse: Bool = true) {
    let type: CBCharacteristicWriteType
    if preferResponse, characteristic.properties.contains(.write) {
        type = .withResponse
    } else if characteristic.properties.contains(.writeWithoutResponse),
              peripheral.canSendWriteWithoutResponse {
        type = .withoutResponse
    } else if characteristic.properties.contains(.write) {
        type = .withResponse
    } else {
        return
    }

    guard data.count <= peripheral.maximumWriteValueLength(for: type) else { return }
    peripheral.writeValue(data, for: characteristic, type: type)
}

// Confirmation callback for .withResponse writes.
func peripheral(
    _ peripheral: CBPeripheral,
    didWriteValueFor characteristic: CBCharacteristic,
    error: Error?
) {
    if let error {
        print("Write failed: \(error.localizedDescription)")
    }
}

// Resume queued .withoutResponse writes here.
func peripheralIsReady(toSendWriteWithoutResponse peripheral: CBPeripheral) {}
```

### Subscribing to Notifications

```swift
// Subscribe
peripheral.setNotifyValue(true, for: characteristic)

// Unsubscribe
peripheral.setNotifyValue(false, for: characteristic)

// Confirmation
func peripheral(
    _ peripheral: CBPeripheral,
    didUpdateNotificationStateFor characteristic: CBCharacteristic,
    error: Error?
) {
    if characteristic.isNotifying {
        print("Now receiving notifications for \(characteristic.uuid)")
    }
}
```

## Peripheral Role: Advertising

Publish services from the local device using `CBPeripheralManager`.

```swift
final class BLEPeripheralManager: NSObject, CBPeripheralManagerDelegate {
    private var peripheralManager: CBPeripheralManager!
    private let serviceUUID = CBUUID(string: "12345678-1234-1234-1234-123456789ABC")
    private let charUUID = CBUUID(string: "12345678-1234-1234-1234-123456789ABD")

    override init() {
        super.init()
        peripheralManager = CBPeripheralManager(delegate: self, queue: nil)
    }

    func peripheralManagerDidUpdateState(_ peripheral: CBPeripheralManager) {
        guard peripheral.state == .poweredOn else { return }
        setupService()
    }

    private func setupService() {
        let characteristic = CBMutableCharacteristic(
            type: charUUID,
            properties: [.read, .notify],
            value: nil,
            permissions: [.readable]
        )

        let service = CBMutableService(type: serviceUUID, primary: true)
        service.characteristics = [characteristic]
        peripheralManager.add(service)
    }

    func peripheralManager(
        _ peripheral: CBPeripheralManager,
        didAdd service: CBService,
        error: Error?
    ) {
        guard error == nil else { return }
        peripheralManager.startAdvertising([
            CBAdvertisementDataServiceUUIDsKey: [serviceUUID],
            CBAdvertisementDataLocalNameKey: "MyDevice"
        ])
    }
}
```

## Background BLE

### Background Central Mode

Add `bluetooth-central` to `UIBackgroundModes`. In the background:

- Scanning must specify one or more service UUIDs; `nil` scans are foreground-only
- Scan options, including `CBCentralManagerScanOptionAllowDuplicatesKey`, have no effect

### Background Peripheral Mode

Add `bluetooth-peripheral` to `UIBackgroundModes`. In the background:

- Without this mode, published service contents are disabled while suspended
- The local name is not advertised
- Service UUIDs move to the overflow area and require explicit service scans

## State Restoration

State restoration allows the system to re-create your central or peripheral
manager after your app is terminated and relaunched for a BLE event.

### Central Manager State Restoration

```swift
// 1. Create with a restoration identifier
centralManager = CBCentralManager(
    delegate: self,
    queue: nil,
    options: [CBCentralManagerOptionRestoreIdentifierKey: "myCentral"]
)

// 2. Implement the restoration delegate method
func centralManager(
    _ central: CBCentralManager,
    willRestoreState dict: [String: Any]
) {
    if let peripherals = dict[CBCentralManagerRestoredStatePeripheralsKey]
        as? [CBPeripheral] {
        for peripheral in peripherals {
            // Re-assign delegate and retain
            peripheral.delegate = self
            discoveredPeripheral = peripheral
        }
    }
    let restoredServices = dict[CBCentralManagerRestoredStateScanServicesKey]
        as? [CBUUID]
    let restoredOptions = dict[CBCentralManagerRestoredStateScanOptionsKey]
        as? [String: Any]
    // Resume scanning with restoredServices/restoredOptions if still needed.
}
```

### Peripheral Manager State Restoration

```swift
peripheralManager = CBPeripheralManager(
    delegate: self,
    queue: nil,
    options: [CBPeripheralManagerOptionRestoreIdentifierKey: "myPeripheral"]
)

func peripheralManager(
    _ peripheral: CBPeripheralManager,
    willRestoreState dict: [String: Any]
) {
    let services = dict[CBPeripheralManagerRestoredStateServicesKey]
        as? [CBMutableService]
    let advertisement = dict[CBPeripheralManagerRestoredStateAdvertisementDataKey]
        as? [String: Any]
    // Reconnect app state to restored services/advertisement as needed.
}
```

## Common Mistakes

| Mistake | Fix |
|---|---|
| Scan/connect before `.poweredOn` | Start BLE work from `centralManagerDidUpdateState`. |
| Discovered peripheral is not retained | Hold a strong reference through connection and discovery. |
| Production scan passes `nil` services | Filter by the service UUIDs the feature needs. |
| Service discovery begins before `didConnect` | Advance only from delegate callbacks and handle failure/disconnect paths. |
| Writes ignore characteristic properties or payload limits | Select the supported write type, respect `maximumWriteValueLength`, and gate `.withoutResponse` on `canSendWriteWithoutResponse`. |

## Review Checklist

- [ ] `NSBluetoothAlwaysUsageDescription` added to Info.plist
- [ ] All BLE operations gated on `centralManagerDidUpdateState` returning `.poweredOn`
- [ ] Discovered peripherals retained with a strong reference
- [ ] Scanning uses specific service UUIDs (not `nil`) in production
- [ ] `CBPeripheralDelegate` set before calling `discoverServices`
- [ ] Characteristic properties checked before read/write/notify
- [ ] Write payloads stay within `maximumWriteValueLength(for:)`
- [ ] `.withoutResponse` writes honor `canSendWriteWithoutResponse`
- [ ] Background mode (`bluetooth-central` or `bluetooth-peripheral`) added if needed
- [ ] State restoration identifier set if app needs relaunch-on-BLE-event support
- [ ] `willRestoreState` delegate method implemented when using state restoration
- [ ] Scanning stopped after discovering the target peripheral
- [ ] Disconnection handled with optional automatic reconnect logic
- [ ] Write type matches characteristic properties (`.withResponse` vs `.withoutResponse`)

## References

- Extended patterns (reconnection strategies, data parsing, SwiftUI integration): [references/ble-patterns.md](references/ble-patterns.md)
- [Core Bluetooth framework](https://sosumi.ai/documentation/corebluetooth)
- [CBCentralManager](https://sosumi.ai/documentation/corebluetooth/cbcentralmanager)
- [CBPeripheral](https://sosumi.ai/documentation/corebluetooth/cbperipheral)
- [CBPeripheralManager](https://sosumi.ai/documentation/corebluetooth/cbperipheralmanager)
- [CBService](https://sosumi.ai/documentation/corebluetooth/cbservice)
- [CBCharacteristic](https://sosumi.ai/documentation/corebluetooth/cbcharacteristic)
- [CBUUID](https://sosumi.ai/documentation/corebluetooth/cbuuid)
- [CBCentralManagerDelegate](https://sosumi.ai/documentation/corebluetooth/cbcentralmanagerdelegate)
- [CBPeripheralDelegate](https://sosumi.ai/documentation/corebluetooth/cbperipheraldelegate)
- [NSBluetoothAlwaysUsageDescription](https://sosumi.ai/documentation/bundleresources/information-property-list/nsbluetoothalwaysusagedescription)
- [CBManagerAuthorization](https://sosumi.ai/documentation/corebluetooth/cbmanagerauthorization)
- [scanForPeripherals(withServices:options:)](https://sosumi.ai/documentation/corebluetooth/cbcentralmanager/scanforperipherals(withservices:options:))
- [startAdvertising(_:)](https://sosumi.ai/documentation/corebluetooth/cbperipheralmanager/startadvertising(_:))
- [writeValue(_:for:type:)](https://sosumi.ai/documentation/corebluetooth/cbperipheral/writevalue(_:for:type:))
- [maximumWriteValueLength(for:)](https://sosumi.ai/documentation/corebluetooth/cbperipheral/maximumwritevaluelength(for:))
- [canSendWriteWithoutResponse](https://sosumi.ai/documentation/corebluetooth/cbperipheral/cansendwritewithoutresponse)
- [Configuring background execution modes](https://sosumi.ai/documentation/xcode/configuring-background-execution-modes)
