---
name: core-nfc
description: "Read and write NFC tags using CoreNFC. Use when scanning NDEF tags, reading ISO7816/ISO15693/FeliCa/MIFARE tags, writing NDEF messages, handling NFC session lifecycle, configuring NFC entitlements, or implementing background tag reading in iOS apps."
---

# CoreNFC

Read and write NFC tags on iPhone using the CoreNFC framework. Covers NDEF
reader sessions, tag reader sessions, NDEF message construction, entitlements,
and background tag reading.

## Contents

- [Setup](#setup)
- [NDEF Reader Session](#ndef-reader-session)
- [Tag Reader Session](#tag-reader-session)
- [Writing NDEF Messages](#writing-ndef-messages)
- [NDEF Payload Types](#ndef-payload-types)
- [Background Tag Reading](#background-tag-reading)
- [Common Mistakes](#common-mistakes)
- [Review Checklist](#review-checklist)
- [References](#references)

## Setup

### Project Configuration

1. Add the **Near Field Communication Tag Reading** capability in Xcode
2. Add `NFCReaderUsageDescription` to Info.plist with a user-facing reason string
3. Add the `com.apple.developer.nfc.readersession.formats` entitlement with the current `TAG` value; do not add legacy `NDEF`
4. For ISO 7816 tags, add supported application identifiers to `com.apple.developer.nfc.readersession.iso7816.select-identifiers` in Info.plist
5. For FeliCa tags, add supported system codes to `com.apple.developer.nfc.readersession.felica.systemcodes`; do not use wildcard system codes

### Device Requirements

NFC reading requires iPhone 7 or later. Always check for reader session
availability before creating NFC UI or sessions. Use the concrete reader
session type you are about to create.

```swift
import CoreNFC

guard NFCNDEFReaderSession.readingAvailable else {
    // Device does not support NFC or feature is restricted
    showUnsupportedMessage()
    return
}
```

### Key Types

| Type | Role |
|---|---|
| `NFCNDEFReaderSession` | Scans for NDEF-formatted tags |
| `NFCTagReaderSession` | Scans for ISO7816, ISO15693, FeliCa, MIFARE tags |
| `NFCNDEFMessage` | Collection of NDEF payload records |
| `NFCNDEFPayload` | Single record within an NDEF message |
| `NFCNDEFTag` | Protocol for interacting with an NDEF-capable tag |

## NDEF Reader Session

Use `NFCNDEFReaderSession` to read NDEF-formatted data from tags. This is the
simplest path for reading standard tag content like URLs, text, and MIME data.

```swift
import CoreNFC

final class NDEFReader: NSObject, NFCNDEFReaderSessionDelegate {
    private var session: NFCNDEFReaderSession?

    func beginScanning() {
        guard NFCNDEFReaderSession.readingAvailable else { return }

        session = NFCNDEFReaderSession(
            delegate: self,
            queue: nil,
            invalidateAfterFirstRead: false
        )
        session?.alertMessage = "Hold your iPhone near an NFC tag."
        session?.begin()
    }

    // MARK: - NFCNDEFReaderSessionDelegate

    func readerSessionDidBecomeActive(_ session: NFCNDEFReaderSession) {
        // Session is scanning
    }

    func readerSession(
        _ session: NFCNDEFReaderSession,
        didDetectNDEFs messages: [NFCNDEFMessage]
    ) {
        for message in messages {
            for record in message.records {
                processRecord(record)
            }
        }
    }

    func readerSession(
        _ session: NFCNDEFReaderSession,
        didInvalidateWithError error: Error
    ) {
        let nfcError = error as? NFCReaderError
        if nfcError?.code != .readerSessionInvalidationErrorFirstNDEFTagRead,
           nfcError?.code != .readerSessionInvalidationErrorUserCanceled {
            print("Session invalidated: \(error.localizedDescription)")
        }
        self.session = nil
    }
}
```

### Reading with Tag Connection

For read-write operations, use the tag-detection delegate method to connect
to individual tags:

```swift
func readerSession(
    _ session: NFCNDEFReaderSession,
    didDetect tags: [any NFCNDEFTag]
) {
    guard let tag = tags.first else {
        session.restartPolling()
        return
    }

    session.connect(to: tag) { error in
        if let error {
            session.invalidate(errorMessage: "Connection failed: \(error)")
            return
        }

        tag.queryNDEFStatus { status, capacity, error in
            guard error == nil else {
                session.invalidate(errorMessage: "Query failed.")
                return
            }

            switch status {
            case .notSupported:
                session.invalidate(errorMessage: "Tag is not NDEF compliant.")
            case .readOnly:
                tag.readNDEF { message, error in
                    if let message {
                        self.processMessage(message)
                    }
                    session.invalidate()
                }
            case .readWrite:
                tag.readNDEF { message, error in
                    if let message {
                        self.processMessage(message)
                    }
                    session.alertMessage = "Tag read successfully."
                    session.invalidate()
                }
            @unknown default:
                session.invalidate()
            }
        }
    }
}
```

## Tag Reader Session

Use `NFCTagReaderSession` when you need direct access to the native tag
protocol (ISO 7816, ISO 15693, FeliCa, or MIFARE).

| Polling option | Tags |
|---|---|
| `.iso14443` | ISO 7816-compatible and MIFARE |
| `.iso15693` | ISO 15693 |
| `.iso18092` | FeliCa |

Do not use this session for payment-related AIDs. Load
[nfc-patterns.md](references/nfc-patterns.md) for protocol-specific connection,
APDU, command, and response handling.

## Writing NDEF Messages

Write NDEF data to a connected tag. Always check `readWrite` status first.

```swift
func writeToTag(
    tag: any NFCNDEFTag,
    session: NFCNDEFReaderSession,
    url: URL
) {
    tag.queryNDEFStatus { status, capacity, error in
        guard status == .readWrite else {
            session.invalidate(errorMessage: "Tag is read-only.")
            return
        }

        guard let payload = NFCNDEFPayload.wellKnownTypeURIPayload(
            url: url
        ) else {
            session.invalidate(errorMessage: "Invalid URL.")
            return
        }

        let message = NFCNDEFMessage(records: [payload])

        tag.writeNDEF(message) { error in
            if let error {
                session.invalidate(
                    errorMessage: "Write failed: \(error.localizedDescription)"
                )
            } else {
                session.alertMessage = "Tag written successfully."
                session.invalidate()
            }
        }
    }
}
```

## NDEF Payload Types

### Creating Common Payloads

```swift
// URL payload
let urlPayload = NFCNDEFPayload.wellKnownTypeURIPayload(
    url: URL(string: "https://example.com")!
)

// Text payload
let textPayload = NFCNDEFPayload.wellKnownTypeTextPayload(
    string: "Hello NFC",
    locale: Locale(identifier: "en")
)

// Custom payload
let customPayload = NFCNDEFPayload(
    format: .nfcExternal,
    type: "com.example:mytype".data(using: .utf8)!,
    identifier: Data(),
    payload: "custom-data".data(using: .utf8)!
)
```

### Parsing Payload Content

Load [Parsing NDEF Payload Content](references/nfc-patterns.md#parsing-ndef-payload-content)
for the complete type-name-format switch and multi-record handling.

## Background Tag Reading

On iPhone XS and later, iOS can read NFC tags in the background without
opening your app. The NDEF message must contain a URI record
(`typeNameFormat == .nfcWellKnown`, type `U`). If there are multiple URI
records, the system uses the first one.

For app-specific routing, write a universal link to the tag and configure the
Associated Domains capability for that domain. Background tag reading also
supports specific system URL schemes such as web, email, SMS, telephone,
FaceTime, Maps, and HomeKit setup. It does not support custom URL schemes, and
the system does not route by bundle ID or arbitrary NDEF content type.

When a user taps a compatible tag, iOS displays a notification that opens
your app. Handle the tag data via `NSUserActivity`:

```swift
func scene(
    _ scene: UIScene,
    continue userActivity: NSUserActivity
) {
    guard userActivity.activityType ==
        NSUserActivityTypeBrowsingWeb else { return }

    let message = userActivity.ndefMessagePayload
    guard message.records.first?.typeNameFormat != .empty else { return }

    for record in message.records {
        processRecord(record)
    }
}
```

## Common Mistakes

### DON'T: Use stale or missing NFC entitlements

Without the `com.apple.developer.nfc.readersession.formats` entitlement,
reader sessions cannot access NFC hardware. Use the current `TAG` value for
Core NFC reader sessions; do not copy older examples that add `NDEF`.

### DON'T: Ignore session invalidation errors

The session invalidates for multiple reasons. Distinguishing user cancellation
from real errors prevents false error alerts.

```swift
// WRONG -- shows error when user cancels
func readerSession(
    _ session: NFCNDEFReaderSession,
    didInvalidateWithError error: Error
) {
    showAlert("NFC Error: \(error.localizedDescription)")
}

// CORRECT -- filter expected invalidation reasons
func readerSession(
    _ session: NFCNDEFReaderSession,
    didInvalidateWithError error: Error
) {
    let nfcError = error as? NFCReaderError
    switch nfcError?.code {
    case .readerSessionInvalidationErrorUserCanceled,
         .readerSessionInvalidationErrorFirstNDEFTagRead:
        break  // Normal termination
    default:
        showAlert("NFC Error: \(error.localizedDescription)")
    }
    self.session = nil
}
```

### DON'T: Hold a strong reference to a stale session

Once a session is invalidated, it cannot be restarted. Nil out your reference
and create a new session for the next scan.

```swift
// WRONG -- reusing invalidated session
func scanAgain() {
    session?.begin()  // Does nothing, session is dead
}

// CORRECT -- create a new session
func scanAgain() {
    session = NFCNDEFReaderSession(
        delegate: self, queue: nil, invalidateAfterFirstRead: false
    )
    session?.begin()
}
```

## Review Checklist

- [ ] NFC capability added in Signing & Capabilities
- [ ] `NFCReaderUsageDescription` set in Info.plist
- [ ] `com.apple.developer.nfc.readersession.formats` entitlement uses `TAG`, not legacy `NDEF`
- [ ] `NFCNDEFReaderSession.readingAvailable` or `NFCTagReaderSession.readingAvailable` checked before creating sessions
- [ ] Session delegate set before calling `begin()`
- [ ] Session reference set to nil after invalidation
- [ ] `didInvalidateWithError` distinguishes user cancellation from actual errors
- [ ] NDEF status queried before write operations
- [ ] Tag capacity checked before writing large messages
- [ ] ISO 7816 application identifiers listed in Info.plist if using `NFCTagReaderSession`
- [ ] FeliCa system codes listed in Info.plist when polling `.iso18092`
- [ ] Background tag reading uses a URI NDEF record and universal links or supported system URL schemes
- [ ] Custom URL schemes, bundle IDs, or arbitrary NDEF content types are not used for background routing
- [ ] Payment-related AIDs are routed away from `NFCTagReaderSession`
- [ ] Only one reader session active at a time

## References

- Extended patterns (ISO 7816 commands, multi-tag scanning, NDEF locking): [references/nfc-patterns.md](references/nfc-patterns.md)
- [Core NFC framework](https://sosumi.ai/documentation/corenfc)
- [NFCNDEFReaderSession](https://sosumi.ai/documentation/corenfc/nfcndefreadersession)
- [NFCTagReaderSession](https://sosumi.ai/documentation/corenfc/nfctagreadersession)
- [NFCNDEFMessage](https://sosumi.ai/documentation/corenfc/nfcndefmessage)
- [NFCNDEFPayload](https://sosumi.ai/documentation/corenfc/nfcndefpayload)
- [NFCNDEFTag](https://sosumi.ai/documentation/corenfc/nfcndeftag)
- [NFCNDEFReaderSessionDelegate](https://sosumi.ai/documentation/corenfc/nfcndefreadersessiondelegate)
- [NFCTagReaderSessionDelegate](https://sosumi.ai/documentation/corenfc/nfctagreadersessiondelegate)
- [Building an NFC Tag-Reader App](https://sosumi.ai/documentation/corenfc/building_an_nfc_tag-reader_app)
- [Adding Support for Background Tag Reading](https://sosumi.ai/documentation/corenfc/adding-support-for-background-tag-reading)
- [Near Field Communication Tag Reader Session Formats Entitlement](https://sosumi.ai/documentation/bundleresources/entitlements/com.apple.developer.nfc.readersession.formats)
- [ISO7816 application identifiers for NFC Tag Reader Session](https://sosumi.ai/documentation/bundleresources/entitlements/com.apple.developer.nfc.readersession.iso7816.select-identifiers)
- [ISO18092 system codes for NFC Tag Reader Session](https://sosumi.ai/documentation/bundleresources/entitlements/com.apple.developer.nfc.readersession.felica.systemcodes)
