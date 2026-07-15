---
name: permissionkit
description: "Create child communication safety experiences using PermissionKit to request parental permission for children. Use when building apps that involve child-to-contact communication, need to check communication limits, request parent/guardian approval, or handle permission responses for minors."
---

# PermissionKit

Request permission from a parent or guardian to modify a child's communication
rules. PermissionKit creates communication safety experiences that let children ask for exceptions to communication limits set by their parents.

PermissionKit communication experiences are available only through iMessage.
Use it for parent/guardian approval flows, not as a general in-app contact
permission, moderation, or chat-safety framework.

## Contents

- [Availability and Setup](#availability-and-setup)
- [Core Concepts](#core-concepts)
- [Checking Communication Limits](#checking-communication-limits)
- [Creating Permission Questions](#creating-permission-questions)
- [Requesting Permission with AskCenter](#requesting-permission-with-askcenter)
- [SwiftUI Integration with PermissionButton](#swiftui-integration-with-permissionbutton)
- [Handling Responses](#handling-responses)
- [Significant App Update Topic](#significant-app-update-topic)
- [Common Mistakes](#common-mistakes)
- [Review Checklist](#review-checklist)
- [References](#references)

## Availability and Setup

Import `PermissionKit`. Do not invent PermissionKit entitlement keys; verify
current Apple documentation and Xcode capabilities before adding signing
requirements.

```swift
import PermissionKit
```

Use this centralized version matrix and verify it against the current SDK:

| Tier | APIs | iOS/iPadOS/Mac Catalyst/macOS/visionOS |
|---|---|---|
| Core | Topics, handles, questions, responses, choices, `CommunicationLimits` | 26.0+ |
| Errors | `AskError` | 26.1+ |
| Presentation | `AskCenter`, ask/response sequences, `PermissionButton`, significant-update topics | 26.2+ |

## Core Concepts

PermissionKit manages a flow where:

1. A child encounters a communication limit in your app
2. Your app creates a `PermissionQuestion` describing the request
3. The system presents the question to the child for them to send to their parent
4. The parent reviews and approves or denies the request
5. Your app receives a `PermissionResponse` with the parent's decision

### Key Types

| Type | Role |
|---|---|
| `AskCenter` | Singleton that manages permission requests and responses |
| `PermissionQuestion` | Describes the permission being requested |
| `PermissionResponse` | The parent's decision (approval or denial) |
| `PermissionChoice` | The specific answer (approve/decline) |
| `PermissionButton` | SwiftUI button that triggers the permission flow |
| `CommunicationTopic` | Topic for communication-related permission requests |
| `CommunicationHandle` | A phone number, email, or custom identifier |
| `CommunicationLimits` | Checks which communication handles are known to the system |
| `SignificantAppUpdateTopic` | Topic for significant app update permission requests |

## Checking Communication Limits

Use `CommunicationLimits.current` to check whether the system already knows a
communication handle for your app. This is not an "are communication limits
enabled?" probe. If limits are not enabled, `AskCenter.shared.ask(_:in:)`
throws `AskError.communicationLimitsNotEnabled`; handle that path when asking.

`knownHandles(in:)` also requires the calling app to have a non-nil, nonempty
bundle identifier. Corrected code should guard `Bundle.main.bundleIdentifier`
before calling it.

```swift
import PermissionKit

func needsPermissionPrompt(for handle: CommunicationHandle) async -> Bool {
    let limits = CommunicationLimits.current
    let isKnown = await limits.isKnownHandle(handle)
    return !isKnown
}

// Check multiple handles at once.
func filterKnownHandles(_ handles: Set<CommunicationHandle>) async -> Set<CommunicationHandle> {
    guard Bundle.main.bundleIdentifier?.isEmpty == false else { return [] }

    let limits = CommunicationLimits.current
    return await limits.knownHandles(in: handles)
}
```

### Creating Communication Handles

```swift
let phoneHandle = CommunicationHandle(
    value: "+1234567890",
    kind: .phoneNumber
)

let emailHandle = CommunicationHandle(
    value: "friend@example.com",
    kind: .emailAddress
)

let customHandle = CommunicationHandle(
    value: "user123",
    kind: .custom
)
```

## Creating Permission Questions

Build a `PermissionQuestion` with the contact information and communication
action type.

```swift
// Question for a single contact
let handle = CommunicationHandle(value: "+1234567890", kind: .phoneNumber)
let question = PermissionQuestion<CommunicationTopic>(handle: handle)

// Question for multiple contacts
let handles = [
    CommunicationHandle(value: "+1234567890", kind: .phoneNumber),
    CommunicationHandle(value: "friend@example.com", kind: .emailAddress)
]
let multiQuestion = PermissionQuestion<CommunicationTopic>(handles: handles)
```

### Using CommunicationTopic with Person Information

Provide display names and avatars for a richer permission prompt.

```swift
let personInfo = CommunicationTopic.PersonInformation(
    handle: CommunicationHandle(value: "+1234567890", kind: .phoneNumber),
    nameComponents: {
        var name = PersonNameComponents()
        name.givenName = "Alex"
        name.familyName = "Smith"
        return name
    }(),
    avatarImage: nil
)

let topic = CommunicationTopic(
    personInformation: [personInfo],
    actions: [.message, .audioCall]
)

let question = PermissionQuestion<CommunicationTopic>(communicationTopic: topic)
```

### Communication Actions

| Action | Description |
|---|---|
| `.message` | Text messaging |
| `.audioCall` | Voice call |
| `.videoCall` | Video call |
| `.call` | Generic call |
| `.chat` | Chat communication |
| `.follow` | Follow a user |
| `.beFollowed` | Allow being followed |
| `.friend` | Friend request |
| `.connect` | Connection request |
| `.communicate` | Generic communication |

## Requesting Permission with AskCenter

Use `AskCenter.shared` to request that the child send the permission question
to their parent or guardian. The async `ask` call starts the send flow; parent
decisions arrive later through `responses(for:)`. If the child cancels the send
flow, the system does not deliver a `PermissionResponse` for that question.

```swift
import PermissionKit

func requestPermission(
    for question: PermissionQuestion<CommunicationTopic>,
    in viewController: UIViewController
) async {
    do {
        try await AskCenter.shared.ask(question, in: viewController)
        // Question send flow was started; wait for responses(for:) separately.
    } catch let error as AskError {
        switch error {
        case .communicationLimitsNotEnabled:
            // Communication limits not active -- continue with normal app flow.
            break
        case .contactSyncNotSetup:
            // Contact sync not configured
            break
        case .invalidQuestion:
            // Question is malformed
            break
        case .notAvailable:
            // PermissionKit not available on this device
            break
        case .systemError(let underlying):
            print("System error: \(underlying)")
        case .unknown:
            break
        @unknown default:
            break
        }
    }
}
```

## SwiftUI Integration with PermissionButton

`PermissionButton` is a SwiftUI view that triggers the permission flow when
tapped. It uses the same response model as `AskCenter`: observe responses and
model a pending/canceled state instead of assuming every tap produces a parent
decision.

```swift
import SwiftUI
import PermissionKit

struct ContactPermissionView: View {
    let handle = CommunicationHandle(value: "+1234567890", kind: .phoneNumber)

    var body: some View {
        let question = PermissionQuestion<CommunicationTopic>(handle: handle)

        PermissionButton(question: question) {
            Label("Ask to Message", systemImage: "message")
        }
    }
}
```

For richer SwiftUI flows, custom topics, and long-lived managers, read
[references/permissionkit-patterns.md](references/permissionkit-patterns.md).

## Handling Responses

Listen for permission responses asynchronously. Track pending questions by
`question.id`, and give the UI a retry or expiration path because a child can
cancel the iMessage send flow without producing a response.
When combining known-handle checks with response handling, carry forward the
bundle-identifier guard from `knownHandles(in:)`.

```swift
enum PermissionRequestState {
    case pending, approved, denied, expired
}

var requestStates: [UUID: PermissionRequestState] = [:]

func expireIfStillPending(_ id: UUID) {
    guard requestStates[id] == .pending else { return }
    requestStates[id] = .expired
    // Re-enable asking or show retry/canceled UI.
}

func observeResponses() async {
    let responses = AskCenter.shared.responses(for: CommunicationTopic.self)

    for await response in responses {
        let choice = response.choice
        let question = response.question

        switch choice.answer {
        case .approval:
            // Parent approved -- enable communication
            requestStates[question.id] = .approved
            print("Approved for topic: \(question.topic)")
        case .denial:
            // Parent denied -- keep restriction
            requestStates[question.id] = .denied
            print("Denied")
        @unknown default:
            break
        }
    }
}
```

### PermissionChoice Properties

```swift
let choice: PermissionChoice = response.choice
print("Answer: \(choice.answer)")  // .approval or .denial
print("Choice ID: \(choice.id)")
print("Title: \(choice.title)")

// Convenience statics
let approved = PermissionChoice.approve
let declined = PermissionChoice.decline
```

## Significant App Update Topic

Request permission for significant app updates that require parental approval.
Your app determines what counts as significant based on applicable regulations
and should consult qualified legal counsel for compliance interpretation.
Use concise, understandable descriptions that state the concrete change parents
are approving.

```swift
let updateTopic = SignificantAppUpdateTopic(
    description: "This update adds multiplayer chat features"
)

let question = PermissionQuestion<SignificantAppUpdateTopic>(
    significantAppUpdateTopic: updateTopic
)

// Present the question
try await AskCenter.shared.ask(question, in: viewController)
requestStates[question.id] = .pending
scheduleExpiration(for: question.id)

// Listen for responses
for await response in AskCenter.shared.responses(for: SignificantAppUpdateTopic.self) {
    switch response.choice.answer {
    case .approval:
        // Proceed with update
        requestStates[response.question.id] = .approved
    case .denial:
        // Skip update
        requestStates[response.question.id] = .denied
    @unknown default:
        break
    }
}

// If no response arrives before your pending window expires, keep the update
// blocked or offer a retry. Child cancellation produces no denial response.
```

## Common Mistakes

| Mistake | Fix |
|---|---|
| Known-handle lookup is treated as proof that limits are enabled | Handle `.communicationLimitsNotEnabled` from the ask operation as the normal unconfigured path. |
| `AskError` is collapsed into one message | Distinguish limits-disabled, contact-sync, invalid-question, unavailable, system, and unknown cases. |
| Question has no handle or person information | Validate at least one meaningful communication target before presentation. |
| Ask is fire-and-forget | Observe response and pending state, while allowing child cancellation/abandonment. |
| Deprecated `CommunicationLimitsButton` is used | Use `PermissionButton`. |

## Review Checklist

- [ ] iMessage-only routing understood before choosing PermissionKit
- [ ] The centralized availability matrix is applied to every API in use
- [ ] `CommunicationHandle` created with correct `Kind` (phone, email, custom)
- [ ] Known-handle examples guard a non-nil, nonempty bundle identifier before
  `knownHandles(in:)`
- [ ] Person information includes name components for a clear permission prompt
- [ ] Communication actions match the app's actual communication capabilities
- [ ] Response handling updates UI on the main actor
- [ ] Error states provide clear guidance to the user

## References

- Extended patterns (response handling, multi-topic, UIKit): [references/permissionkit-patterns.md](references/permissionkit-patterns.md)
- [PermissionKit framework](https://sosumi.ai/documentation/permissionkit)
- [AskCenter](https://sosumi.ai/documentation/permissionkit/askcenter)
- [PermissionQuestion](https://sosumi.ai/documentation/permissionkit/permissionquestion)
- [PermissionButton](https://sosumi.ai/documentation/permissionkit/permissionbutton)
- [PermissionResponse](https://sosumi.ai/documentation/permissionkit/permissionresponse)
- [CommunicationTopic](https://sosumi.ai/documentation/permissionkit/communicationtopic)
- [CommunicationHandle](https://sosumi.ai/documentation/permissionkit/communicationhandle)
- [CommunicationLimits](https://sosumi.ai/documentation/permissionkit/communicationlimits)
- [SignificantAppUpdateTopic](https://sosumi.ai/documentation/permissionkit/significantappupdatetopic)
- [AskError](https://sosumi.ai/documentation/permissionkit/askerror)
- [Creating a communication experience](https://sosumi.ai/documentation/permissionkit/creating-a-communication-experience)
