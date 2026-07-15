# AudioAccessoryKit Patterns

Extended patterns and recipes for AudioAccessoryKit integration. This file
supplements the main `SKILL.md` with complete workflows and coordination
strategies.

## Contents

- [Complete Registration Flow](#complete-registration-flow)
- [Placement Monitoring](#placement-monitoring)
- [Multi-Device Audio Source Management](#multi-device-audio-source-management)
- [Error Recovery Patterns](#error-recovery-patterns)
- [AccessorySetupKit Integration](#accessorysetupkit-integration)
- [Architecture Patterns](#architecture-patterns)

## Complete Registration Flow

### Pairing Through Registration

The container app owns AccessorySetupKit pairing and AudioAccessoryKit
registration. Keep app-extension updates in separate types.

```swift
import AccessorySetupKit
import AudioAccessoryKit
import CoreBluetooth

final class AudioAccessoryRegistrar {
    private let session = ASAccessorySession()
    private var registeredAccessories = Set<ASAccessory>()

    func start() {
        session.activate(on: .main) { [weak self] event in
            self?.handleEvent(event)
        }
    }

    private func handleEvent(_ event: ASAccessoryEvent) {
        switch event.eventType {
        case .activated:
            // Check for previously paired accessories
            for accessory in session.accessories {
                Task { await registerIfNeeded(accessory) }
            }
        case .accessoryAdded:
            guard let accessory = event.accessory else { return }
            Task { await registerIfNeeded(accessory) }
        case .accessoryRemoved:
            if let accessory = event.accessory {
                registeredAccessories.remove(accessory)
            }
        default:
            break
        }
    }

    private func registerIfNeeded(_ accessory: ASAccessory) async {
        guard !registeredAccessories.contains(accessory) else { return }

        do {
            let configuration = AccessoryControlDevice.Configuration(
                devicePlacement: .offHead,
                deviceCapabilities: [.audioSwitching, .placement]
            )
            try await AccessoryControlDevice.register(accessory, configuration)
            registeredAccessories.insert(accessory)
        } catch {
            print("Registration failed: \(error)")
        }
    }
}
```

### Registration with Initial Configuration

Provide full initial state in the registration configuration:

```swift
func registerWithInitialState(
    _ accessory: ASAccessory,
    placement: AccessoryControlDevice.Placement,
    primarySource: Data?
) async throws {
    let configuration = AccessoryControlDevice.Configuration(
        devicePlacement: placement,
        deviceCapabilities: [.audioSwitching, .placement],
        primaryAudioSourceDeviceIdentifier: primarySource
    )
    try await AccessoryControlDevice.register(accessory, configuration)
}
```

## Placement Monitoring

Run placement updates from the app extension after the container app has
registered the `.placement` capability.

### Placement State Machine

Track and report placement transitions based on sensor data from the accessory:

```swift
final class PlacementMonitor {
    private let accessory: ASAccessory
    private var currentPlacement: AccessoryControlDevice.Placement = .offHead

    init(accessory: ASAccessory) {
        self.accessory = accessory
    }

    /// Call when the accessory firmware reports a new wear state.
    func reportPlacementChange(
        _ newPlacement: AccessoryControlDevice.Placement
    ) async {
        guard newPlacement != currentPlacement else { return }

        let previousPlacement = currentPlacement
        currentPlacement = newPlacement

        do {
            let device = try AccessoryControlDevice.current(for: accessory)
            var config = device.configuration
            config.devicePlacement = newPlacement
            try await device.update(config)
        } catch {
            // Revert local state on failure
            currentPlacement = previousPlacement
            print("Placement update failed: \(error)")
        }
    }
}
```

### Mapping Firmware Sensor Data to Placement

Translate raw sensor readings from the accessory into placement values:

```swift
extension PlacementMonitor {
    /// Map raw proximity/wear sensor data to an AudioAccessoryKit placement.
    func placementFromSensorData(
        isWorn: Bool,
        sensorType: AccessoryHardwareType
    ) -> AccessoryControlDevice.Placement {
        guard isWorn else { return .offHead }

        switch sensorType {
        case .inEarBud:
            return .inEar
        case .onEarHeadphone:
            return .onHead
        case .overEarHeadphone:
            return .overTheEar
        }
    }
}

enum AccessoryHardwareType {
    case inEarBud
    case onEarHeadphone
    case overEarHeadphone
}
```

### Debounced Placement Updates

Avoid rapid placement toggles from noisy sensor data:

```swift
final class DebouncedPlacementMonitor {
    private let accessory: ASAccessory
    private var pendingPlacement: AccessoryControlDevice.Placement?
    private var debounceTask: Task<Void, Never>?

    private let debounceInterval: Duration = .milliseconds(500)

    init(accessory: ASAccessory) {
        self.accessory = accessory
    }

    func reportRawPlacementChange(
        _ newPlacement: AccessoryControlDevice.Placement
    ) {
        pendingPlacement = newPlacement
        debounceTask?.cancel()

        debounceTask = Task { [weak self] in
            try? await Task.sleep(for: self?.debounceInterval ?? .milliseconds(500))
            guard !Task.isCancelled else { return }
            guard let placement = self?.pendingPlacement else { return }
            await self?.commitPlacement(placement)
        }
    }

    private func commitPlacement(
        _ placement: AccessoryControlDevice.Placement
    ) async {
        do {
            let device = try AccessoryControlDevice.current(for: accessory)
            var config = device.configuration
            config.devicePlacement = placement
            try await device.update(config)
        } catch {
            print("Debounced placement update failed: \(error)")
        }
    }
}
```

## Multi-Device Audio Source Management

Run connected-source updates from the app extension after registration.

### Tracking Connected Bluetooth Sources

Maintain a list of connected Bluetooth devices and update source identifiers
when connections change:

```swift
final class AudioSourceTracker {
    private let accessory: ASAccessory
    private var connectedDevices: [Data] = []

    init(accessory: ASAccessory) {
        self.accessory = accessory
    }

    func deviceConnected(bluetoothAddress: Data) async {
        connectedDevices.append(bluetoothAddress)
        await syncSourceIdentifiers()
    }

    func deviceDisconnected(bluetoothAddress: Data) async {
        connectedDevices.removeAll { $0 == bluetoothAddress }
        await syncSourceIdentifiers()
    }

    private func syncSourceIdentifiers() async {
        do {
            let device = try AccessoryControlDevice.current(for: accessory)
            var config = device.configuration

            config.primaryAudioSourceDeviceIdentifier = connectedDevices.first
            config.secondaryAudioSourceDeviceIdentifier = connectedDevices.count > 1
                ? connectedDevices[1]
                : nil

            try await device.update(config)
        } catch {
            print("Source identifier update failed: \(error)")
        }
    }
}
```

### Prioritizing Audio Sources

When multiple devices are connected, choose the primary source based on
application-specific logic:

```swift
extension AudioSourceTracker {
    func updatePrimarySource(
        to preferredAddress: Data
    ) async {
        // Move preferred device to front
        connectedDevices.removeAll { $0 == preferredAddress }
        connectedDevices.insert(preferredAddress, at: 0)
        await syncSourceIdentifiers()
    }
}
```

## Error Recovery Patterns

### Error Disposition

Classify the error before deciding whether another operation is safe:

| Error | Disposition |
|---|---|
| `.accessoryNotCapable` | Remove or correct the unsupported capability; repeating the request cannot add hardware support. |
| `.invalidRequest` | Correct the request parameters before constructing another request. |
| `.invalidated` | Discard the device handle and notify the container app to re-evaluate registration where appropriate. |
| `.unknown` | Log and surface or propagate the failure; do not assume it is transient. |
| `@unknown default` | Preserve the error and fail safely until its semantics are known. |

Only retry when independent evidence identifies a transient external condition;
the framework error cases themselves do not document one.

### Invalidation Recovery

When an app-extension update sees invalidation, discard that device handle and
notify the container app to re-evaluate whether registration is appropriate:

```swift
enum AudioAccessoryUpdateRecovery {
    case needsContainerRegistrationEvaluation(ASAccessory)
}

func updateOrRequestRegistration(
    accessory: ASAccessory,
    config: AccessoryControlDevice.Configuration
) async throws -> AudioAccessoryUpdateRecovery? {
    do {
        let device = try AccessoryControlDevice.current(for: accessory)
        try await device.update(config)
        return nil
    } catch AccessoryControlDevice.Error.invalidated {
        return .needsContainerRegistrationEvaluation(accessory)
    }
}
```

## AccessorySetupKit Integration

### Coordinating Pairing and Audio Registration

Show the AccessorySetupKit picker and register for audio features on
successful pairing:

```swift
import AccessorySetupKit
import AudioAccessoryKit
import CoreBluetooth

final class AccessorySetupCoordinator {
    private let session = ASAccessorySession()
    private var pendingAccessory: ASAccessory?

    func start() {
        session.activate(on: .main) { [weak self] event in
            self?.handleEvent(event)
        }
    }

    func showPicker(descriptor: ASDiscoveryDescriptor, image: UIImage) {
        let item = ASPickerDisplayItem(
            name: "Audio Accessory",
            productImage: image,
            descriptor: descriptor
        )

        session.showPicker(for: [item]) { error in
            if let error {
                print("Picker failed: \(error)")
            }
        }
    }

    private func handleEvent(_ event: ASAccessoryEvent) {
        switch event.eventType {
        case .accessoryAdded:
            guard let accessory = event.accessory else { return }
            pendingAccessory = accessory
        case .pickerDidDismiss:
            guard let accessory = pendingAccessory else { return }
            pendingAccessory = nil
            Task { await registerAudioFeatures(accessory) }
        default:
            break
        }
    }

    private func registerAudioFeatures(_ accessory: ASAccessory) async {
        let configuration = AccessoryControlDevice.Configuration(
            devicePlacement: .offHead,
            deviceCapabilities: [.audioSwitching, .placement]
        )

        do {
            try await AccessoryControlDevice.register(accessory, configuration)
        } catch {
            print("Audio registration failed: \(error)")
        }
    }
}
```

### Handling Previously Paired Accessories

On app launch, re-register previously paired accessories that are already
authorized:

```swift
extension AccessorySetupCoordinator {
    func restoreRegistrations() {
        for accessory in session.accessories {
            Task {
                await registerAudioFeatures(accessory)
            }
        }
    }
}
```

## Architecture Patterns

### Observable Audio Accessory State

Expose app-extension accessory state to SwiftUI views using Observation:

```swift
import AudioAccessoryKit
import AccessorySetupKit
import Observation

@Observable
final class AudioAccessoryExtensionState {
    private(set) var placement: AccessoryControlDevice.Placement?
    private(set) var hasPrimarySource = false
    private(set) var hasSecondarySource = false

    private var accessory: ASAccessory?

    func bind(to accessory: ASAccessory) {
        self.accessory = accessory
        refreshState()
    }

    func updatePlacement(
        _ newPlacement: AccessoryControlDevice.Placement
    ) async throws {
        guard let accessory else { return }
        let device = try AccessoryControlDevice.current(for: accessory)
        var config = device.configuration
        config.devicePlacement = newPlacement
        try await device.update(config)
        placement = newPlacement
    }

    private func refreshState() {
        guard let accessory,
              let device = try? AccessoryControlDevice.current(for: accessory)
        else { return }

        let config = device.configuration
        placement = config.devicePlacement
        hasPrimarySource = config.primaryAudioSourceDeviceIdentifier != nil
        hasSecondarySource = config.secondaryAudioSourceDeviceIdentifier != nil
    }
}
```

### SwiftUI Integration

Use the observable state in a SwiftUI view:

```swift
import SwiftUI

struct AudioAccessoryView: View {
    @State private var state = AudioAccessoryExtensionState()

    var body: some View {
        List {
            Section("Status") {
                if let placement = state.placement {
                    LabeledContent("Placement", value: placementLabel(placement))
                }
            }

            Section("Connected Sources") {
                LabeledContent("Primary", value: state.hasPrimarySource ? "Connected" : "None")
                LabeledContent("Secondary", value: state.hasSecondarySource ? "Connected" : "None")
            }
        }
    }

    private func placementLabel(
        _ placement: AccessoryControlDevice.Placement
    ) -> String {
        switch placement {
        case .inEar: "In Ear"
        case .onHead: "On Head"
        case .overTheEar: "Over the Ear"
        case .offHead: "Off Head"
        @unknown default: "Unknown"
        }
    }
}
```

### Separating Transport and Audio Concerns

Keep Bluetooth communication (CoreBluetooth) separate from audio configuration
(AudioAccessoryKit):

```swift
/// Handles Bluetooth communication with the accessory firmware.
final class AccessoryTransport {
    private var peripheral: CBPeripheral?

    func connect(bluetoothIdentifier: UUID, centralManager: CBCentralManager) {
        let peripherals = centralManager.retrievePeripherals(
            withIdentifiers: [bluetoothIdentifier]
        )
        guard let peripheral = peripherals.first else { return }
        self.peripheral = peripheral
        centralManager.connect(peripheral)
    }

    /// Called when firmware reports new sensor data.
    var onPlacementChanged: ((AccessoryControlDevice.Placement) -> Void)?
    var onConnectionStateChanged: ((Data, Bool) -> Void)?
}

/// Coordinates transport events with AudioAccessoryKit registration.
final class AudioAccessoryCoordinator {
    private let transport: AccessoryTransport
    private let placementMonitor: PlacementMonitor
    private let sourceTracker: AudioSourceTracker

    init(accessory: ASAccessory) {
        self.transport = AccessoryTransport()
        self.placementMonitor = PlacementMonitor(accessory: accessory)
        self.sourceTracker = AudioSourceTracker(accessory: accessory)

        transport.onPlacementChanged = { [weak self] placement in
            Task { await self?.placementMonitor.reportPlacementChange(placement) }
        }

        transport.onConnectionStateChanged = { [weak self] address, connected in
            Task {
                if connected {
                    await self?.sourceTracker.deviceConnected(bluetoothAddress: address)
                } else {
                    await self?.sourceTracker.deviceDisconnected(bluetoothAddress: address)
                }
            }
        }
    }
}
```
