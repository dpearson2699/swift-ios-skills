# CoreNFC Extended Patterns

Overflow reference for the `core-nfc` skill. Contains advanced patterns that exceed the main skill file's scope.

## Contents

- [ISO 7816 APDU Commands](#iso-7816-apdu-commands)
- [ISO 15693 Tag Reading](#iso-15693-tag-reading)
- [MIFARE Tag Operations](#mifare-tag-operations)
- [FeliCa Tag Operations](#felica-tag-operations)
- [Multi-Record NDEF Messages](#multi-record-ndef-messages)
- [Parsing NDEF Payload Content](#parsing-ndef-payload-content)
- [NDEF Tag Locking](#ndef-tag-locking)
- [SwiftUI NFC Scanner](#swiftui-nfc-scanner)
- [Error Handling Reference](#error-handling-reference)

## ISO 7816 APDU Commands

Send APDU commands to ISO 7816-compliant smart cards and tags:

```swift
import CoreNFC

func readISO7816(
    tag: NFCISO7816Tag,
    session: NFCTagReaderSession
) {
    // Select application by AID
    let selectAID = NFCISO7816APDU(
        instructionClass: 0x00,
        instructionCode: 0xA4,
        p1Parameter: 0x04,
        p2Parameter: 0x00,
        data: Data([0xD2, 0x76, 0x00, 0x00, 0x85, 0x01, 0x01]),
        expectedResponseLength: -1
    )

    tag.sendCommand(apdu: selectAID) { data, sw1, sw2, error in
        guard error == nil, sw1 == 0x90, sw2 == 0x00 else {
            session.invalidate(errorMessage: "Select failed.")
            return
        }

        // Read binary
        let readBinary = NFCISO7816APDU(
            instructionClass: 0x00,
            instructionCode: 0xB0,
            p1Parameter: 0x00,
            p2Parameter: 0x00,
            data: Data(),
            expectedResponseLength: 256
        )

        tag.sendCommand(apdu: readBinary) { data, sw1, sw2, error in
            guard error == nil else {
                session.invalidate(errorMessage: "Read failed.")
                return
            }
            print("Read \(data.count) bytes, SW: \(sw1) \(sw2)")
            session.alertMessage = "Tag read successfully."
            session.invalidate()
        }
    }
}
```

### Common APDU Commands

| Command | CLA | INS | Description |
|---|---|---|---|
| SELECT | 0x00 | 0xA4 | Select an application or file |
| READ BINARY | 0x00 | 0xB0 | Read data from a transparent file |
| UPDATE BINARY | 0x00 | 0xD6 | Write data to a transparent file |
| READ RECORD | 0x00 | 0xB2 | Read a record from a record-oriented file |
| GET DATA | 0x00 | 0xCA | Retrieve a data object |

## ISO 15693 Tag Reading

```swift
func readISO15693(
    tag: NFCISO15693Tag,
    session: NFCTagReaderSession
) {
    // Read a single block
    tag.readSingleBlock(
        requestFlags: [.highDataRate, .address],
        blockNumber: 0
    ) { data, error in
        guard let data, error == nil else {
            session.invalidate(errorMessage: "Read failed.")
            return
        }
        print("Block 0: \(data.map { String(format: "%02x", $0) }.joined())")
    }

    // Read multiple blocks
    tag.readMultipleBlocks(
        requestFlags: [.highDataRate, .address],
        blockRange: NSRange(location: 0, length: 4)
    ) { blocks, error in
        guard let blocks, error == nil else { return }
        for (index, block) in blocks.enumerated() {
            print("Block \(index): \(block.count) bytes")
        }
        session.alertMessage = "Read \(blocks.count) blocks."
        session.invalidate()
    }
}
```

### Getting System Info

```swift
tag.getSystemInfo(requestFlags: [.highDataRate, .address]) {
    identifier, dsfid, afi, blockSize, blockCount, icReference, error in
    guard error == nil else { return }
    print("UID: \(identifier.map { String(format: "%02x", $0) }.joined())")
    print("Block size: \(blockSize), Block count: \(blockCount)")
}
```

## MIFARE Tag Operations

```swift
func readMiFare(
    tag: NFCMiFareTag,
    session: NFCTagReaderSession
) {
    // Identify MIFARE family
    switch tag.mifareFamily {
    case .ultralight:
        readMiFareUltralight(tag: tag, session: session)
    case .desfire:
        session.invalidate(
            errorMessage: "Use app-specific DESFire commands for this card."
        )
    case .plus:
        print("MIFARE Plus tag detected")
        session.invalidate()
    case .unknown:
        print("Unknown MIFARE tag")
        session.invalidate()
    @unknown default:
        session.invalidate()
    }
}

func readMiFareUltralight(
    tag: NFCMiFareTag,
    session: NFCTagReaderSession
) {
    // READ command: reads 4 pages starting at page 4
    let readCommand = Data([0x30, 0x04])

    tag.sendMiFareCommand(commandPacket: readCommand) { data, error in
        guard error == nil else {
            session.invalidate(errorMessage: "Read failed.")
            return
        }
        print("Read \(data.count) bytes from MIFARE Ultralight")
        session.alertMessage = "Tag read successfully."
        session.invalidate()
    }
}
```

## FeliCa Tag Operations

FeliCa discovery requires `.iso18092` polling and
`com.apple.developer.nfc.readersession.felica.systemcodes` entries in
Info.plist. Each system code must be explicit; wildcard values are not allowed.

```swift
func readFeliCa(
    tag: NFCFeliCaTag,
    session: NFCTagReaderSession
) {
    tag.requestSystemCode { systemCodes, error in
        guard error == nil else {
            session.invalidate(errorMessage: "System code request failed.")
            return
        }

        let codes = systemCodes.map {
            $0.map { String(format: "%02x", $0) }.joined()
        }
        print("FeliCa system codes: \(codes.joined(separator: ", "))")
        session.alertMessage = "FeliCa tag read successfully."
        session.invalidate()
    }
}
```

## Multi-Record NDEF Messages

Build messages with multiple records of different types:

```swift
func buildMultiRecordMessage() -> NFCNDEFMessage {
    var records: [NFCNDEFPayload] = []

    // Text record
    if let textPayload = NFCNDEFPayload.wellKnownTypeTextPayload(
        string: "Product: Widget Pro",
        locale: Locale(identifier: "en")
    ) {
        records.append(textPayload)
    }

    // URL record
    if let urlPayload = NFCNDEFPayload.wellKnownTypeURIPayload(
        url: URL(string: "https://example.com/product/123")!
    ) {
        records.append(urlPayload)
    }

    // Custom external type record
    let externalPayload = NFCNDEFPayload(
        format: .nfcExternal,
        type: "com.example:product".data(using: .utf8)!,
        identifier: Data(),
        payload: """
        {"sku":"WP-001","batch":"2026-03"}
        """.data(using: .utf8)!
    )
    records.append(externalPayload)

    return NFCNDEFMessage(records: records)
}
```

## Parsing NDEF Payload Content

```swift
func processRecord(_ record: NFCNDEFPayload) {
    switch record.typeNameFormat {
    case .nfcWellKnown:
        if let url = record.wellKnownTypeURIPayload() {
            print("URL: \(url)")
        } else if let (text, locale) = record.wellKnownTypeTextPayload() {
            print("Text (\(locale)): \(text)")
        }
    case .absoluteURI:
        print(String(decoding: record.payload, as: UTF8.self))
    case .media, .nfcExternal:
        print("Type: \(String(decoding: record.type, as: UTF8.self))")
    case .empty, .unknown, .unchanged:
        break
    @unknown default:
        break
    }
}
```

Process every record in an `NFCNDEFMessage`; do not assume the first record is
the only application payload.

### Checking Message Size Against Tag Capacity

```swift
func writeIfFits(
    message: NFCNDEFMessage,
    to tag: any NFCNDEFTag,
    session: NFCNDEFReaderSession
) {
    tag.queryNDEFStatus { status, capacity, error in
        guard status == .readWrite else {
            session.invalidate(errorMessage: "Tag is not writable.")
            return
        }

        let messageLength = message.length
        guard messageLength <= capacity else {
            session.invalidate(
                errorMessage: "Message (\(messageLength) bytes) exceeds "
                + "tag capacity (\(capacity) bytes)."
            )
            return
        }

        tag.writeNDEF(message) { error in
            if let error {
                session.invalidate(
                    errorMessage: "Write failed: \(error.localizedDescription)"
                )
            } else {
                session.alertMessage = "Written \(messageLength) bytes."
                session.invalidate()
            }
        }
    }
}
```

## NDEF Tag Locking

Lock a tag to make it permanently read-only. This is irreversible.

```swift
func lockTag(
    _ tag: any NFCNDEFTag,
    session: NFCNDEFReaderSession
) {
    tag.queryNDEFStatus { status, _, error in
        guard status == .readWrite else {
            session.invalidate(errorMessage: "Tag is already read-only.")
            return
        }

        tag.writeLock { error in
            if let error {
                session.invalidate(
                    errorMessage: "Lock failed: \(error.localizedDescription)"
                )
            } else {
                session.alertMessage = "Tag locked permanently."
                session.invalidate()
            }
        }
    }
}
```

## SwiftUI NFC Scanner

Wrap the NFC reader in an `@Observable` model for SwiftUI integration:

```swift
import CoreNFC
import SwiftUI

@Observable
@MainActor
final class NFCScannerModel: NSObject {
    var scannedText: String = ""
    var scannedURL: URL?
    var isScanning = false
    var errorMessage: String?

    private var session: NFCNDEFReaderSession?

    var isAvailable: Bool {
        NFCNDEFReaderSession.readingAvailable
    }

    func startScan() {
        guard isAvailable else {
            errorMessage = "NFC not available on this device."
            return
        }

        session = NFCNDEFReaderSession(
            delegate: self,
            queue: nil,
            invalidateAfterFirstRead: true
        )
        session?.alertMessage = "Hold your iPhone near an NFC tag."
        session?.begin()
        isScanning = true
        errorMessage = nil
    }
}

extension NFCScannerModel: NFCNDEFReaderSessionDelegate {
    nonisolated func readerSessionDidBecomeActive(
        _ session: NFCNDEFReaderSession
    ) { }

    nonisolated func readerSession(
        _ session: NFCNDEFReaderSession,
        didDetectNDEFs messages: [NFCNDEFMessage]
    ) {
        Task { @MainActor in
            for message in messages {
                for record in message.records {
                    if let url = record.wellKnownTypeURIPayload() {
                        scannedURL = url
                    }
                    if let (text, _) = record.wellKnownTypeTextPayload() {
                        scannedText = text
                    }
                }
            }
            isScanning = false
        }
    }

    nonisolated func readerSession(
        _ session: NFCNDEFReaderSession,
        didInvalidateWithError error: Error
    ) {
        Task { @MainActor in
            let nfcError = error as? NFCReaderError
            if nfcError?.code != .readerSessionInvalidationErrorUserCanceled,
               nfcError?.code != .readerSessionInvalidationErrorFirstNDEFTagRead {
                errorMessage = error.localizedDescription
            }
            isScanning = false
            self.session = nil
        }
    }
}

struct NFCScannerView: View {
    @State private var scanner = NFCScannerModel()

    var body: some View {
        VStack {
            if !scanner.isAvailable {
                ContentUnavailableView(
                    "NFC Unavailable",
                    systemImage: "wave.3.right.circle.fill",
                    description: Text("This device does not support NFC.")
                )
            } else {
                Button("Scan NFC Tag") {
                    scanner.startScan()
                }
                .buttonStyle(.borderedProminent)
                .disabled(scanner.isScanning)

                if let url = scanner.scannedURL {
                    Text("URL: \(url.absoluteString)")
                }
                if !scanner.scannedText.isEmpty {
                    Text("Text: \(scanner.scannedText)")
                }
                if let error = scanner.errorMessage {
                    Text(error).foregroundStyle(.red)
                }
            }
        }
        .padding()
    }
}
```

## Error Handling Reference

### NFCReaderError Codes

| Code | Meaning |
|---|---|
| `.readerSessionInvalidationErrorUserCanceled` | User tapped Cancel in the NFC sheet |
| `.readerSessionInvalidationErrorFirstNDEFTagRead` | Session ended after first read (when `invalidateAfterFirstRead` is true) |
| `.readerSessionInvalidationErrorSessionTimeout` | 60-second session timeout elapsed |
| `.readerSessionInvalidationErrorSessionTerminatedUnexpectedly` | System terminated the session |
| `.readerTransceiveErrorTagConnectionLost` | Tag moved out of range during communication |
| `.readerTransceiveErrorRetryExceeded` | Too many failed communication attempts |
| `.readerTransceiveErrorTagNotConnected` | Attempted to communicate without connecting first |
| `.readerSessionInvalidationErrorSystemIsBusy` | Another NFC session is active |

### Graceful Error Recovery

```swift
nonisolated func readerSession(
    _ session: NFCNDEFReaderSession,
    didInvalidateWithError error: Error
) {
    let nfcError = error as? NFCReaderError
    Task { @MainActor in
        switch nfcError?.code {
        case .readerSessionInvalidationErrorUserCanceled:
            break  // User chose to cancel
        case .readerSessionInvalidationErrorFirstNDEFTagRead:
            break  // Expected when invalidateAfterFirstRead is true
        case .readerSessionInvalidationErrorSessionTimeout:
            errorMessage = "Scan timed out. Try again."
        case .readerTransceiveErrorTagConnectionLost:
            errorMessage = "Tag moved away. Hold steady and try again."
        default:
            errorMessage = error.localizedDescription
        }
        self.session = nil
    }
}
```
