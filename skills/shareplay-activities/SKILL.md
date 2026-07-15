---
name: shareplay-activities
description: "Build shared real-time experiences using GroupActivities and SharePlay. Use when implementing shared media playback, collaborative app features, synchronized game state, or any FaceTime, Messages, AirDrop, or nearby visionOS group activity on iOS, macOS, tvOS, or visionOS."
---

# GroupActivities / SharePlay

Build shared real-time experiences using the GroupActivities framework. SharePlay
connects people over FaceTime, Messages, AirDrop, and nearby visionOS sharing,
synchronizing media playback, app state, or custom data.

## Contents

- [Setup](#setup)
- [Defining a GroupActivity](#defining-a-groupactivity)
- [Session Lifecycle](#session-lifecycle)
- [Sending and Receiving Messages](#sending-and-receiving-messages)
- [Coordinated Media Playback](#coordinated-media-playback)
- [Starting SharePlay from Your App](#starting-shareplay-from-your-app)
- [GroupSessionJournal: File Transfer](#groupsessionjournal-file-transfer)
- [Common Mistakes](#common-mistakes)
- [Review Checklist](#review-checklist)
- [References](#references)

## Setup

### Capability

Add the **Group Activities** capability to the app target in Xcode. Xcode adds
the required entitlement and updates the provisioning profile:

```xml
<key>com.apple.developer.group-session</key>
<true/>
```

Configure this only for app targets. Group Activities are not available in
widgets, extensions, or App Clips.

### Checking Eligibility

```swift
import GroupActivities

let observer = GroupStateObserver()

// Check if a FaceTime call or Messages conversation is active
if observer.isEligibleForGroupSession {
    showSharePlayButton()
}
```

Observe changes reactively:

```swift
for await isEligible in observer.$isEligibleForGroupSession.values {
    showSharePlayButton(isEligible)
}
```

## Defining a GroupActivity

Conform to `GroupActivity` and provide metadata:

```swift
import GroupActivities

struct WatchTogetherActivity: GroupActivity {
    let movieID: String
    let movieTitle: String

    var metadata: GroupActivityMetadata {
        var meta = GroupActivityMetadata()
        meta.title = movieTitle
        meta.type = .watchTogether
        meta.fallbackURL = URL(string: "https://example.com/movie/\(movieID)")
        return meta
    }
}
```

### Activity Types

| Type | Use Case |
|---|---|
| `.generic` | Default for custom activities |
| `.watchTogether` | Video playback |
| `.listenTogether` | Audio playback |
| `.createTogether` | Collaborative creation (drawing, editing) |
| `.exploreTogether` | Shared browsing, planning, or exploration |
| `.learnTogether` | Shared learning or studying |
| `.readTogether` | Shared reading |
| `.shopTogether` | Shared shopping |
| `.workoutTogether` | Shared fitness sessions |

`GroupActivity` is `Codable`; stored activity data must be codable. Add
`Transferable` only for SwiftUI `ShareLink`, SharePlay over AirDrop, or
AppKit/UIKit share sheets. Keep payloads minimal: use identifiers or URLs
instead of large data.

## Session Lifecycle

### Listening for Sessions

Set up a long-lived task to receive sessions when another participant starts
the activity:

```swift
@Observable
@MainActor
final class SharePlayManager {
    private var session: GroupSession<WatchTogetherActivity>?
    private var messenger: GroupSessionMessenger?
    private var sessionTasks: [Task<Void, Never>] = []

    func observeSessions() {
        Task {
            for await session in WatchTogetherActivity.sessions() {
                self.configureSession(session)
            }
        }
    }

    private func configureSession(
        _ session: GroupSession<WatchTogetherActivity>
    ) {
        self.session = session
        self.messenger = GroupSessionMessenger(session: session)

        // Observe session state changes
        let stateTask = Task {
            for await state in session.$state.values {
                handleState(state)
            }
        }
        sessionTasks.append(stateTask)

        // Observe participant changes
        let participantTask = Task {
            for await participants in session.$activeParticipants.values {
                handleParticipants(participants)
            }
        }
        sessionTasks.append(participantTask)

        // Join the session
        session.join()
    }

    private func cleanUp() {
        sessionTasks.forEach { $0.cancel() }
        sessionTasks.removeAll()
        session = nil
        messenger = nil
    }
}
```

### Session States

| State | Description |
|---|---|
| `.waiting` | Session exists but local participant has not joined |
| `.joined` | Local participant is actively in the session |
| `.invalidated(reason:)` | Session ended (check reason for details) |

### Handling State Changes

```swift
private func handleState(_ state: GroupSession<WatchTogetherActivity>.State) {
    switch state {
    case .waiting:
        print("Waiting to join")
    case .joined:
        print("Joined session")
        loadActivity(session?.activity)
    case .invalidated(let reason):
        print("Session ended: \(reason)")
        cleanUp()
    @unknown default:
        break
    }
}

private func handleParticipants(_ participants: Set<Participant>) {
    print("Active participants: \(participants.count)")
}
```

### Leaving and Ending

```swift
// Leave the session (other participants continue)
session?.leave()

// End the session for all participants
session?.end()
```

## Sending and Receiving Messages

Use `GroupSessionMessenger` to sync small, time-sensitive app state between
participants.

### Defining Messages

Messages must be `Codable`; keep each message under 256 KB.

```swift
struct SyncMessage: Codable {
    let action: String
    let timestamp: Date
    let data: [String: String]
}
```

### Sending

```swift
func sendSync(_ message: SyncMessage) async throws {
    guard let messenger else { return }

    try await messenger.send(message, to: .all)
}

// Send to specific participants
try await messenger.send(message, to: .only(participant))
```

### Receiving

```swift
func observeMessages() {
    guard let messenger else { return }

    Task {
        for await (message, context) in messenger.messages(of: SyncMessage.self) {
            let sender = context.source
            handleReceivedMessage(message, from: sender)
        }
    }
}
```

### Delivery Modes

```swift
// Reliable (default) -- checked and retried for crucial state
let reliableMessenger = GroupSessionMessenger(
    session: session,
    deliveryMode: .reliable
)

// Unreliable -- lower latency, no delivery guarantee
let unreliableMessenger = GroupSessionMessenger(
    session: session,
    deliveryMode: .unreliable
)
```

Use `.reliable` for state-changing actions such as selections or turns. Use
`.unreliable` for high-frequency ephemeral data such as cursor positions,
drawing strokes, and reactions.

## Coordinated Media Playback

For video/audio, use `AVPlaybackCoordinator` with `AVPlayer`:

```swift
import AVFoundation
import GroupActivities

func configurePlayback(
    session: GroupSession<WatchTogetherActivity>,
    player: AVPlayer
) {
    // Connect the player's coordinator to the session
    let coordinator = player.playbackCoordinator
    coordinator.coordinateWithSession(session)
}
```

Once connected, AVFoundation synchronizes play/pause, seeking, rate, playback speed,
and time. Do not put AVPlayer transport fields in messenger messages or snapshots,
including late-joiner snapshots; use custom messages only for state outside playback.

## Starting SharePlay from Your App

### Using GroupActivitySharingController (UIKit)

```swift
import GroupActivities
import UIKit

func startSharePlay() async throws {
    let activity = WatchTogetherActivity(
        movieID: "123",
        movieTitle: "Great Movie"
    )

    switch await activity.prepareForActivation() {
    case .activationPreferred:
        // A conversation is active and the user chose to share.
        _ = try await activity.activate()

    case .activationDisabled:
        // The user chose local playback, or sharing is unavailable.
        startLocalExperience()

    case .cancelled:
        break

    @unknown default:
        break
    }
}
```

When no conversation is active (i.e., `isEligibleForGroupSession` is false),
use `GroupActivitySharingController` to let the user pick contacts first:

```swift
let controller = try GroupActivitySharingController(activity)
present(controller, animated: true)
```

Use the `shareplay` SF Symbol for custom controls. Treat `GroupActivityMetadata`
as discovery copy: concise title, subtitle, image, and type aligned with the
entry point. Keep sibling domains out: GameKit owns auth, matchmaking,
leaderboards, achievements, and voice/chat; TabletopKit owns seats, board
equipment, spatial placement, turns, rules, and authoritative tabletop state;
AVKit owns playback UI. SharePlay owns invitations, lifecycle, participants, and
coordination handoffs. See [references/shareplay-patterns.md](references/shareplay-patterns.md) for SwiftUI `ShareLink`, AirDrop, and direct activation patterns.

## GroupSessionJournal: File Transfer

For larger, non-time-sensitive attachments, use `GroupSessionJournal` instead
of `GroupSessionMessenger`. Journal items must conform to `Transferable`, are
available to late joiners, and are limited to 100 MB. It requires iOS/iPadOS/tvOS
17+, macOS 14+, or visionOS 1+. For larger/protected assets, share a pointer or manifest and use server storage or app-managed file transfer.

```swift
import GroupActivities

let journal = GroupSessionJournal(session: session)

// Upload a Transferable file or data item
let attachment = try await journal.add(sharedImageItem)

// Observe incoming attachments
Task {
    for await attachments in journal.attachments {
        for attachment in attachments {
            let data = try await attachment.load(Data.self)
            handleReceivedFile(data)
        }
    }
}
```

## Common Mistakes

### DON'T: Forget to call session.join()

Configure the stored session, messenger, and observers, then call `join()`. The
canonical long-lived manager in Session Lifecycle shows the required order.

### DON'T: Forget to leave or end sessions

```swift
// WRONG -- session stays alive after the user navigates away
func viewDidDisappear() {
    // Nothing -- session leaks
}

// CORRECT -- leave when the view is dismissed
func viewDidDisappear() {
    session?.leave()
    session = nil
    messenger = nil
}
```

### DON'T: Assume all participants have the same state

```swift
// WRONG -- broadcasting state without handling late joiners
func onJoin() {
    // New participant has no idea what the current state is
}

// CORRECT -- send full state to new participants
func handleParticipants(_ participants: Set<Participant>) {
    let newParticipants = participants.subtracting(knownParticipants)
    for participant in newParticipants {
        Task {
            try await messenger?.send(currentState, to: .only(participant))
        }
    }
    knownParticipants = participants
}
```

### DON'T: Use SharePlay transports for large/protected assets

```swift
// WRONG -- messenger is small/time-sensitive; journal is Transferable and <=100 MB
let imageData = try Data(contentsOf: imageURL)     // 300 KB
try await messenger.send(imageData, to: .all)      // Too large
// CORRECT -- journal attachments up to 100 MB; otherwise share a pointer/manifest
let journal = GroupSessionJournal(session: session)
try await journal.add(sharedImageItem)
// Larger/protected assets: server storage or app-managed file transfer
```

### DON'T: Send redundant messages for media playback

```swift
// WRONG -- manually syncing play/pause when using AVPlayer
func play() {
    player.play()
    try await messenger.send(PlayMessage(), to: .all)
}

// CORRECT -- let AVPlaybackCoordinator handle it
player.playbackCoordinator.coordinateWithSession(session)
player.play()  // Automatically synced to all participants
```

### DON'T: Observe sessions in a view that gets recreated

Own the `sessions()` listener in a long-lived manager, not a recreatable view.
Use the manager lifecycle shown above and cancel its child tasks on invalidation.

## Review Checklist

- [ ] Group Activities capability added to the app target only
- [ ] `GroupActivity` struct is `Codable` with meaningful metadata
- [ ] `Transferable` conformance added when using `ShareLink`, AirDrop, or share sheets
- [ ] `sessions()` observed in a long-lived object (not a SwiftUI view body)
- [ ] `session.join()` called after receiving and configuring the session
- [ ] `session.leave()` called when the user navigates away or dismisses
- [ ] `GroupSessionMessenger` messages stay under 256 KB with appropriate `deliveryMode`
- [ ] Late-joining participants receive current state on connection
- [ ] `$state` and `$activeParticipants` publishers observed for lifecycle changes
- [ ] `GroupSessionJournal` used for non-time-sensitive `Transferable` attachments
- [ ] `AVPlaybackCoordinator` used for media sync (not manual messages)
- [ ] `GroupStateObserver.isEligibleForGroupSession` checked before showing SharePlay UI
- [ ] `GroupActivitySharingController` used when no conversation is active
- [ ] Session invalidation handled with cleanup of messenger, journal, and tasks

## References

- Extended patterns (SwiftUI sharing, collaborative canvas, spatial Personas): [references/shareplay-patterns.md](references/shareplay-patterns.md)
- [Configuring Group Activities](https://sosumi.ai/documentation/xcode/configuring-group-activities)
- [GroupActivities framework](https://sosumi.ai/documentation/groupactivities)
- [GroupActivity protocol](https://sosumi.ai/documentation/groupactivities/groupactivity)
- [GroupSession](https://sosumi.ai/documentation/groupactivities/groupsession)
- [GroupSessionMessenger](https://sosumi.ai/documentation/groupactivities/groupsessionmessenger)
- [GroupSessionJournal](https://sosumi.ai/documentation/groupactivities/groupsessionjournal)
- [GroupStateObserver](https://sosumi.ai/documentation/groupactivities/groupstateobserver)
- [GroupActivitySharingController](https://sosumi.ai/documentation/groupactivities/groupactivitysharingcontroller-ybcy)
- [Defining your app's SharePlay activities](https://sosumi.ai/documentation/groupactivities/defining-your-apps-shareplay-activities)
- [Presenting SharePlay activities from your app's UI](https://sosumi.ai/documentation/groupactivities/promoting-shareplay-activities-from-your-apps-ui)
- [Synchronizing data during a SharePlay activity](https://sosumi.ai/documentation/groupactivities/synchronizing-data-during-a-shareplay-activity)
- [Supporting coordinated media playback](https://sosumi.ai/documentation/avfoundation/supporting-coordinated-media-playback)
- [SharePlay HIG](https://sosumi.ai/design/human-interface-guidelines/shareplay)
