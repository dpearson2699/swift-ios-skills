---
name: callkit
description: "Implement VoIP calling with CallKit and PushKit. Use when building incoming/outgoing call flows, registering for VoIP push notifications, configuring CXProvider and CXCallController, handling call actions, coordinating audio sessions, or creating Call Directory extensions for caller ID and call blocking."
---

# CallKit

Build VoIP calling features that integrate with the native iOS call UI using
CallKit and PushKit. Covers incoming/outgoing call flows, VoIP push
registration, audio session coordination, and call directory extensions.

## Contents

- [Setup](#setup)
- [Provider Configuration](#provider-configuration)
- [Incoming Call Flow](#incoming-call-flow)
- [Outgoing Call Flow](#outgoing-call-flow)
- [PushKit VoIP Registration](#pushkit-voip-registration)
- [Audio Session Coordination](#audio-session-coordination)
- [Call Directory Extension and Manager](#call-directory-extension-and-manager)
- [Common Mistakes](#common-mistakes)
- [Review Checklist](#review-checklist)
- [References](#references)

## Setup

### Project Configuration

1. Enable the **Voice over IP** background mode in Signing & Capabilities
2. Add the **Push Notifications** capability
3. For call directory extensions, add a **Call Directory Extension** target

### Key Types

| Type | Role |
|---|---|
| `CXProvider` | Reports calls to the system, receives call actions |
| `CXCallController` | Requests call actions (start, end, hold, mute) |
| `CXCallUpdate` | Describes call metadata (caller name, video, handle) |
| `CXProviderDelegate` | Handles system call actions and audio session events |
| `PKPushRegistry` | Registers for and receives VoIP push notifications |
| `PKVoIPPushMetadata` | iOS 26.4+ metadata that says whether a VoIP push must be reported |

## Provider Configuration

Create a single `CXProvider` at app launch and keep it alive for the app
lifetime. Configure it with a `CXProviderConfiguration` that describes your
calling capabilities.

```swift
import CallKit

/// CXProvider dispatches all delegate calls to the queue passed to `setDelegate(_:queue:)`.
/// The `let` properties are initialized once and never mutated, making this type
/// safe to share across concurrency domains despite @unchecked Sendable.
final class CallManager: NSObject, @unchecked Sendable {
    static let shared = CallManager()

    let provider: CXProvider
    let callController = CXCallController()

    private override init() {
        let config = CXProviderConfiguration()
        config.localizedName = "My VoIP App"
        config.supportsVideo = true
        config.maximumCallsPerCallGroup = 1
        config.maximumCallGroups = 2
        config.supportedHandleTypes = [.phoneNumber, .emailAddress]
        config.includesCallsInRecents = true

        provider = CXProvider(configuration: config)
        super.init()
        provider.setDelegate(self, queue: nil)
    }
}
```

## Incoming Call Flow

When a required VoIP call push arrives, report the incoming call to CallKit
immediately. The system displays the native call UI. You must report required
calls before the PushKit completion handler returns -- failure to do so causes
the system to terminate your app.

```swift
func reportIncomingCall(
    uuid: UUID,
    handle: String,
    hasVideo: Bool
) async throws {
    let update = CXCallUpdate()
    update.remoteHandle = CXHandle(type: .phoneNumber, value: handle)
    update.hasVideo = hasVideo
    update.localizedCallerName = "Jane Doe"

    try await withCheckedThrowingContinuation {
        (continuation: CheckedContinuation<Void, Error>) in
        provider.reportNewIncomingCall(
            with: uuid,
            update: update
        ) { error in
            if let error {
                continuation.resume(throwing: error)
            } else {
                continuation.resume()
            }
        }
    }
}
```

### Handling the Answer Action

Implement `CXProviderDelegate` to respond when the user answers:

```swift
extension CallManager: CXProviderDelegate {
    func providerDidReset(_ provider: CXProvider) {
        // End all calls, reset audio
    }

    func provider(_ provider: CXProvider, perform action: CXAnswerCallAction) {
        // Prepare audio, then fulfill only after the call is actually ready
        configureAudioSession()
        connectToCallServer(callUUID: action.callUUID) { success in
            if success {
                action.fulfill()
            } else {
                provider.reportCall(
                    with: action.callUUID,
                    endedAt: Date(),
                    reason: .failed
                )
                action.fail()
            }
        }
    }

    func provider(_ provider: CXProvider, perform action: CXEndCallAction) {
        disconnectFromCallServer(callUUID: action.callUUID)
        action.fulfill()
    }
}
```

## Outgoing Call Flow

Use `CXCallController` to request an outgoing call. The system routes the
request through your `CXProviderDelegate`.

```swift
func startOutgoingCall(handle: String, hasVideo: Bool) {
    let uuid = UUID()
    let handle = CXHandle(type: .phoneNumber, value: handle)
    let startAction = CXStartCallAction(call: uuid, handle: handle)
    startAction.isVideo = hasVideo

    let transaction = CXTransaction(action: startAction)
    callController.request(transaction) { error in
        if let error {
            print("Failed to start call: \(error)")
        }
    }
}
```

### Delegate Methods for Outgoing Calls

```swift
extension CallManager {
    func provider(_ provider: CXProvider, perform action: CXStartCallAction) {
        configureAudioSession()
        // Begin connecting to server
        provider.reportOutgoingCall(
            with: action.callUUID,
            startedConnectingAt: Date()
        )

        connectToServer(callUUID: action.callUUID) {
            provider.reportOutgoingCall(
                with: action.callUUID,
                connectedAt: Date()
            )
        }
        action.fulfill()
    }
}
```

## PushKit VoIP Registration

Register for VoIP pushes at every app launch and send token changes to your
server. For iOS 13 SDK+ apps, every report-required VoIP call push must be
reported before PushKit completion using CallKit, or LiveCommunicationKit for
apps built on that framework. On iOS 26.4+, `PKVoIPPushMetadata.mustReport` is
the gate: `true` means report before completion; `false` means no CallKit or
LiveCommunicationKit report is required. Missing a required report before
completion can terminate the app, and repeated failures may stop VoIP delivery.

| Path | Report decision | Completion timing |
|---|---|---|
| iOS 26.4+ `mustReport == true` | Report with CallKit or LiveCommunicationKit | After report callback |
| iOS 26.4+ `mustReport == false` | No CallKit/LiveCommunicationKit report required | After local handling |
| Older delegate | iOS 13 SDK+ treats VoIP call pushes as report-required | After report callback |

```swift
import PushKit

final class PushManager: NSObject, PKPushRegistryDelegate {
    let registry: PKPushRegistry

    override init() {
        registry = PKPushRegistry(queue: .main)
        super.init()
        registry.delegate = self
        registry.desiredPushTypes = [.voIP]
    }

    func pushRegistry(
        _ registry: PKPushRegistry,
        didUpdate pushCredentials: PKPushCredentials,
        for type: PKPushType
    ) {
        let token = pushCredentials.token
            .map { String(format: "%02x", $0) }
            .joined()
        // Send token to your server
        sendTokenToServer(token)
    }

    @available(iOS 26.4, *)
    func pushRegistry(
        _ registry: PKPushRegistry,
        didReceiveIncomingVoIPPushWith payload: PKPushPayload,
        metadata: PKVoIPPushMetadata,
        withCompletionHandler completion: @escaping @Sendable () -> Void
    ) {
        guard metadata.mustReport else {
            completion()
            return
        }
        handleIncomingVoIPPush(payload, completion: completion)
    }

    // Keep the older callback for iOS 26.0-26.3 and older deployment targets.
    func pushRegistry(
        _ registry: PKPushRegistry,
        didReceiveIncomingPushWith payload: PKPushPayload,
        for type: PKPushType,
        completion: @escaping () -> Void
    ) {
        guard type == .voIP else {
            completion()
            return
        }

        handleIncomingVoIPPush(payload, completion: completion)
    }

    private func handleIncomingVoIPPush(
        _ payload: PKPushPayload,
        completion: @escaping () -> Void
    ) {
        let callUUID = UUID()
        let handle = payload.dictionaryPayload["handle"] as? String ?? "Unknown"

        Task {
            do {
                try await CallManager.shared.reportIncomingCall(
                    uuid: callUUID,
                    handle: handle,
                    hasVideo: false
                )
            } catch {
                // Call was filtered by DND or block list
            }
            completion()
        }
    }
}
```

Server-side VoIP pushes should use a short lifetime: set `apns-expiration` to
`0` or only a few seconds. After the initial push wakes the app, send hangups
and call-detail changes over the app-server connection instead of sending more
VoIP pushes.

## Audio Session Coordination

CallKit owns the audio activation boundary: start media only in
`provider(_:didActivate:)`, and stop or tear it down in
`provider(_:didDeactivate:)` and reset paths.

```swift
extension CallManager {
    func provider(_ provider: CXProvider, didActivate audioSession: AVAudioSession) {
        // Audio session is now active -- start audio engine / WebRTC
        startAudioEngine()
    }

    func provider(_ provider: CXProvider, didDeactivate audioSession: AVAudioSession) {
        // Audio session deactivated -- stop audio engine
        stopAudioEngine()
    }

    func configureAudioSession() {
        let session = AVAudioSession.sharedInstance()
        do {
            try session.setCategory(
                .playAndRecord,
                mode: .voiceChat,
                options: [.allowBluetooth, .allowBluetoothA2DP]
            )
        } catch {
            print("Audio session configuration failed: \(error)")
        }
    }
}
```

## Call Directory Extension and Manager

Use Call Directory for preloaded caller ID/blocking, not per-call API lookup.
The extension loads sorted bulk data in `beginRequest(with:)`; the main app uses
`CXCallDirectoryManager` to check enabled status, open Call Blocking &
Identification settings when disabled, and reload after data changes. Store
`CXCallDirectoryPhoneNumber` as country code plus digits in ascending order
(for example `18005551234`), not a formatted string.

```swift
import CallKit

final class CallDirectoryHandler: CXCallDirectoryProvider {
    override func beginRequest(
        with context: CXCallDirectoryExtensionContext
    ) {
        if context.isIncremental {
            addOrRemoveIncrementalEntries(to: context)
        } else {
            addAllEntries(to: context)
        }
        context.completeRequest()
    }

    private func addAllEntries(
        to context: CXCallDirectoryExtensionContext
    ) {
        // Country code + digits, sorted in ascending order
        let blockedNumbers: [CXCallDirectoryPhoneNumber] = [
            18005551234, 18005555678
        ]
        for number in blockedNumbers {
            context.addBlockingEntry(
                withNextSequentialPhoneNumber: number
            )
        }

        let identifiedNumbers: [(CXCallDirectoryPhoneNumber, String)] = [
            (18005551111, "Local Pizza"),
            (18005552222, "Dentist Office")
        ]
        for (number, label) in identifiedNumbers {
            context.addIdentificationEntry(
                withNextSequentialPhoneNumber: number,
                label: label
            )
        }
    }
}
```

### Main-App Manager: Status, Settings, Reload

```swift
let manager = CXCallDirectoryManager.sharedInstance
manager.getEnabledStatusForExtension(withIdentifier: extensionID) { status, _ in
    guard status == .enabled else {
        manager.openSettings { _ in } // Call Blocking & Identification
        return
    }
    manager.reloadExtension(withIdentifier: extensionID) { _ in }
}
```

Check `getEnabledStatusForExtension(...)` before assuming the extension is
active, use `openSettings(...)` for Call Blocking & Identification when
disabled, and call `reloadExtension(...)` after data changes. Route APNs
auth-key rotation and normal remote-notification setup to push-notifications.

## Common Mistakes

| Mistake | Fix |
|---|---|
| Required VoIP push is treated as data-only | Apply the version-specific report rule, report before completion, then invoke the PushKit completion handler. |
| Answer action is fulfilled before media/server readiness | Keep it pending while connecting; fulfill on readiness or fail and report `.failed`. |
| Media starts before `provider(_:didActivate:)` | Prepare earlier if needed, but start only after activation and stop on deactivation/reset. |
| An action path never calls `fulfill()` or `fail()` | Give success, cancellation, timeout, and network-error paths one terminal action. |
| Token refresh is ignored | Send every `didUpdate pushCredentials` token to the server. |
| Call Directory performs per-call networking | Preload sorted entries and reload the extension. |

## Review Checklist

- [ ] VoIP background mode enabled in capabilities
- [ ] Single `CXProvider` instance created at app launch and retained
- [ ] `CXProviderDelegate` set before reporting any calls
- [ ] iOS 26.4+ PushKit path reports when `mustReport` is true and may skip when false
- [ ] iOS 13 SDK+ PushKit VoIP call pushes report to CallKit before completion
- [ ] VoIP APNs requests use `apns-expiration` of `0` or only a few seconds
- [ ] Hangups and detail updates use the app-server connection after the initial push
- [ ] `action.fulfill()` or `action.fail()` called for every provider delegate action
- [ ] `CXAnswerCallAction` fulfilled only after the call server/media connection is ready
- [ ] Audio engine started only after `provider(_:didActivate:)` callback
- [ ] Audio engine stopped in `provider(_:didDeactivate:)` callback
- [ ] Audio session category set to `.playAndRecord` with `.voiceChat` mode
- [ ] VoIP push token sent to server on every `didUpdate pushCredentials` callback
- [ ] `PKPushRegistry` created at every app launch (not lazily)
- [ ] Call Directory data is preloaded, not fetched per incoming call
- [ ] `CXCallDirectoryPhoneNumber` documented as country calling code + digits
- [ ] `CXCallDirectoryManager` names status check, reload, and settings-opening APIs
- [ ] `CXCallUpdate` populated with `localizedCallerName` and `remoteHandle`
- [ ] Outgoing calls report `startedConnectingAt` and `connectedAt` timestamps
- [ ] iOS 26 call translation keeps upstream audio active during mute
- [ ] Encrypted metadata filtering mentions the notification service extension entitlement

## References

- Extended patterns (hold, mute, group calls, delegate lifecycle): [references/callkit-patterns.md](references/callkit-patterns.md)
- [CallKit framework](https://sosumi.ai/documentation/callkit)
- [CXProvider](https://sosumi.ai/documentation/callkit/cxprovider)
- [CXCallController](https://sosumi.ai/documentation/callkit/cxcallcontroller)
- [CXCallAction](https://sosumi.ai/documentation/callkit/cxcallaction)
- [CXCallUpdate](https://sosumi.ai/documentation/callkit/cxcallupdate)
- [CXProviderConfiguration](https://sosumi.ai/documentation/callkit/cxproviderconfiguration)
- [CXProviderDelegate](https://sosumi.ai/documentation/callkit/cxproviderdelegate)
- [PKPushRegistry](https://sosumi.ai/documentation/pushkit/pkpushregistry)
- [PKPushRegistryDelegate](https://sosumi.ai/documentation/pushkit/pkpushregistrydelegate)
- [PKVoIPPushMetadata](https://sosumi.ai/documentation/pushkit/pkvoippushmetadata)
- [CXCallDirectoryProvider](https://sosumi.ai/documentation/callkit/cxcalldirectoryprovider)
- [CXCallDirectoryPhoneNumber](https://sosumi.ai/documentation/callkit/cxcalldirectoryphonenumber)
- [CXCallDirectoryManager](https://sosumi.ai/documentation/callkit/cxcalldirectorymanager)
- [CXSetTranslatingCallAction](https://sosumi.ai/documentation/callkit/cxsettranslatingcallaction)
- [reportNewIncomingVoIPPushPayload(_:completion:)](https://sosumi.ai/documentation/callkit/cxprovider/reportnewincomingvoippushpayload(_:completion:))
- [Making and receiving VoIP calls](https://sosumi.ai/documentation/callkit/making-and-receiving-voip-calls)
- [Responding to VoIP Notifications from PushKit](https://sosumi.ai/documentation/pushkit/responding-to-voip-notifications-from-pushkit)
