---
name: cryptotokenkit
description: "Access security tokens and smart cards using CryptoTokenKit. Use when building TKTokenDriver or TKSmartCardTokenDriver extensions, communicating with smart cards via TKSmartCard/TKSmartCardSlotManager, using iOS 26+ NFC smart-card sessions, registering smart cards, querying token-backed keychain items with kSecAttrTokenID, monitoring TKTokenWatcher, or configuring certificate-based smart-card authentication."
---

# CryptoTokenKit

Use CryptoTokenKit for token driver extensions, smart-card communication,
token sessions, token-backed keychain integration, and certificate-based
authentication in Swift 6.3 apps.

**Platform availability:** CryptoTokenKit classes are available across Apple
platforms, but capability depends on extension point, entitlement, hardware, and
OS version. The smart-card app extension flow for login/keychain unlock is macOS.
`TKSmartCardSlotManager.default` is optional and returns `nil` unless smart-card
access is enabled. iOS/iPadOS 26+ add NFC smart-card slots and registration.

## Contents

- [Architecture Overview](#architecture-overview)
- [Token Extensions](#token-extensions)
- [Token Sessions](#token-sessions)
- [Smart Card Communication](#smart-card-communication)
- [Keychain Integration](#keychain-integration)
- [Certificate Authentication](#certificate-authentication)
- [Token Watching](#token-watching)
- [Error Handling](#error-handling)
- [Common Mistakes](#common-mistakes)
- [Review Checklist](#review-checklist)
- [References](#references)

## Architecture Overview

CryptoTokenKit bridges hardware security tokens (smart cards, USB tokens)
with authentication and keychain services. The framework has three main usage
modes:

**Smart-card token extensions** -- macOS app extensions that make a hardware
token's cryptographic items available to system login and keychain unlock. The
driver handles token lifecycle, session management, and cryptographic operations.

**Client-side token access** -- Apps query the keychain for items backed by
tokens. CryptoTokenKit exposes token items as standard keychain entries when a
token is present.

**NFC smart-card access** -- iOS/iPadOS 26+ apps create a temporary NFC smart
card slot and communicate with the presented contactless card through
`TKSmartCard`.

**Boundary routing:** Own token/smart-card sessions, token-backed keychain
items, and certificate-based smart-card auth. Route passkeys/WebAuthn and
account sign-in to `authentication`; route Secure Enclave, CryptoKit primitives,
keychain architecture, certificate pinning, and trust policy to `swift-security`.

### Key Types

| Type | Role | Platform |
|---|---|---|
| `TKTokenDriver` / `TKToken` / `TKTokenSession` | Token driver, token, and session primitives | iOS 10+, macOS 10.12+ |
| `TKSmartCardTokenDriver` | Entry point for smart card token extensions | iOS 10+, macOS 10.12+; macOS extension flow |
| `TKSmartCard` / `TKSmartCardSlotManager` | Low-level APDU communication and slot discovery | iOS 9+, macOS 10.10+; `default` is optional |
| `TKTokenWatcher` | Observes token insertion and removal | iOS 10+, macOS 10.12+ |
| `TKSmartCardSlotNFCSession` | NFC-backed smart card slot session | iOS/iPadOS 26+ |
| `TKSmartCardTokenRegistrationManager` | Registers NFC smart cards for later keychain use | iOS/iPadOS 26+ |

## Token Extensions

For system login and keychain unlock on macOS, a token driver is an app
extension that makes a hardware token's cryptographic capabilities available to
the system. The host app exists only as a delivery mechanism for the extension.

A smart card token extension has three core classes:

1. **TokenDriver** (subclass of `TKSmartCardTokenDriver`) -- entry point
2. **Token** (subclass of `TKSmartCardToken`) -- represents the token
3. **TokenSession** (subclass of `TKSmartCardTokenSession`) -- handles operations

### Driver Class

```swift
import CryptoTokenKit

final class TokenDriver: TKSmartCardTokenDriver, TKSmartCardTokenDriverDelegate {
    func tokenDriver(
        _ driver: TKSmartCardTokenDriver,
        createTokenFor smartCard: TKSmartCard,
        aid: Data?
    ) throws -> TKSmartCardToken {
        return try Token(
            smartCard: smartCard,
            aid: aid,
            instanceID: "com.example.token:\(smartCard.slot.name)",
            tokenDriver: driver
        )
    }
}
```

### Token Class

The token reads certificates and keys from hardware and populates its
keychain contents:

```swift
final class Token: TKSmartCardToken, TKTokenDelegate {
    init(
        smartCard: TKSmartCard, aid: Data?,
        instanceID: String, tokenDriver: TKSmartCardTokenDriver
    ) throws {
        try super.init(
            smartCard: smartCard, aid: aid,
            instanceID: instanceID, tokenDriver: tokenDriver
        )
        self.delegate = self

        let certData = try readCertificate(from: smartCard)
        guard let cert = SecCertificateCreateWithData(nil, certData as CFData) else {
            throw TKError(.corruptedData)
        }

        let certItem = TKTokenKeychainCertificate(certificate: cert, objectID: "cert-auth")
        let keyItem = TKTokenKeychainKey(certificate: cert, objectID: "key-auth")
        keyItem?.canSign = true
        keyItem?.canDecrypt = false
        keyItem?.isSuitableForLogin = true

        self.keychainContents?.fill(with: [certItem!, keyItem!])
    }

    func createSession(_ token: TKToken) throws -> TKTokenSession {
        TokenSession(token: token)
    }
}
```

### Info.plist and Registration

The extension's `Info.plist` must name the driver class:

```
NSExtension
  NSExtensionAttributes
    com.apple.ctk.driver-class = $(PRODUCT_MODULE_NAME).TokenDriver
  NSExtensionPointIdentifier = com.apple.ctk-tokens
```

Register the extension once by launching the host app as `_securityagent`:

```shell
sudo -u _securityagent /Applications/TokenHost.app/Contents/MacOS/TokenHost
```

## Token Sessions

`TKTokenSession` manages authentication state and performs cryptographic
operations via its delegate.

```swift
final class TokenSession: TKSmartCardTokenSession, TKTokenSessionDelegate {
    func tokenSession(
        _ session: TKTokenSession,
        supports operation: TKTokenOperation,
        keyObjectID: TKToken.ObjectID,
        algorithm: TKTokenKeyAlgorithm
    ) -> Bool {
        switch operation {
        case .signData:
            return algorithm.isAlgorithm(.rsaSignatureDigestPKCS1v15SHA256)
                || algorithm.isAlgorithm(.ecdsaSignatureDigestX962SHA256)
        case .decryptData:
            return algorithm.isAlgorithm(.rsaEncryptionOAEPSHA256)
        case .performKeyExchange:
            return algorithm.isAlgorithm(.ecdhKeyExchangeStandard)
        default:
            return false
        }
    }

    func tokenSession(
        _ session: TKTokenSession,
        sign dataToSign: Data,
        keyObjectID: TKToken.ObjectID,
        algorithm: TKTokenKeyAlgorithm
    ) throws -> Data {
        let smartCard = try getSmartCard()
        return try smartCard.withSession {
            try performCardSign(smartCard: smartCard, data: dataToSign, keyID: keyObjectID)
        }
    }

    func tokenSession(
        _ session: TKTokenSession,
        decrypt ciphertext: Data,
        keyObjectID: TKToken.ObjectID,
        algorithm: TKTokenKeyAlgorithm
    ) throws -> Data {
        let smartCard = try getSmartCard()
        return try smartCard.withSession {
            try performCardDecrypt(smartCard: smartCard, data: ciphertext, keyID: keyObjectID)
        }
    }
}
```

### PIN Authentication

Return a `TKTokenAuthOperation` from `beginAuthFor:` to prompt the user
for PIN entry before cryptographic operations:

```swift
func tokenSession(
    _ session: TKTokenSession,
    beginAuthFor operation: TKTokenOperation,
    constraint: Any
) throws -> TKTokenAuthOperation {
    let pinAuth = TKTokenSmartCardPINAuthOperation()
    pinAuth.pinFormat.charset = .numeric
    pinAuth.pinFormat.minPINLength = 4
    pinAuth.pinFormat.maxPINLength = 8
    pinAuth.smartCard = (session as? TKSmartCardTokenSession)?.smartCard
    pinAuth.apduTemplate = buildVerifyAPDU()
    pinAuth.pinByteOffset = 5
    return pinAuth
}
```

## Smart Card Communication

`TKSmartCard` provides low-level APDU communication with smart cards.
`TKSmartCardSlotManager.default` is optional; treat `nil` as unavailable
hardware, missing entitlement/access, or unsupported runtime capability.

### Discovering Card Readers

```swift
import CryptoTokenKit

func discoverSmartCards() {
    guard let slotManager = TKSmartCardSlotManager.default else {
        print("Smart card services unavailable")
        return
    }

    for slotName in slotManager.slotNames {
        slotManager.getSlot(withName: slotName) { slot in
            guard let slot else { return }
            if slot.state == .validCard, let card = slot.makeSmartCard() {
                communicateWith(card: card)
            }
        }
    }
}
```

### Sending APDU Commands

Use `send(ins:p1:p2:data:le:)` for structured APDU communication.
Always wrap calls in `withSession`:

```swift
func selectApplication(card: TKSmartCard, aid: Data) throws {
    try card.withSession {
        let (sw, response) = try card.send(
            ins: 0xA4, p1: 0x04, p2: 0x00, data: aid, le: nil
        )
        guard sw == 0x9000 else {
            throw TKError(.communicationError)
        }
    }
}
```

For raw APDU bytes or non-standard formats, use `transmit(_:reply:)` with
manual `beginSession`/`endSession` lifecycle management.

### NFC Smart Card Sessions (iOS/iPadOS 26+)

On iOS/iPadOS 26+, guard `isNFCSupported()` before calling
`createNFCSlot(message:completion:)` to communicate with contactless cards:

```swift
@available(iOS 26.0, iPadOS 26.0, *)
func readNFCSmartCard() {
    guard let slotManager = TKSmartCardSlotManager.default,
          slotManager.isNFCSupported() else { return }

    slotManager.createNFCSlot(message: "Hold card near iPhone") { session, error in
        guard let session else {
            handleNFCError(error)
            return
        }
        defer { session.end() }

        guard let slotName = session.slotName,
              let slot = slotManager.slotNamed(slotName),
              let card = slot.makeSmartCard() else { return }
        // Communicate with the NFC card using card.send(...)
    }
}
```

## Keychain Integration

When a token is present, CryptoTokenKit exposes its items as standard
keychain entries. Query them using the `kSecAttrTokenID` attribute:

```swift
import Security

func findTokenKey(tokenID: String) throws -> SecKey {
    let query: [String: Any] = [
        kSecClass as String: kSecClassKey,
        kSecAttrTokenID as String: tokenID,
        kSecReturnRef as String: true
    ]
    var result: CFTypeRef?
    let status = SecItemCopyMatching(query as CFDictionary, &result)
    guard status == errSecSuccess, let key = result else {
        throw TKError(.objectNotFound)
    }
    return key as! SecKey
}
```

Use `kSecReturnPersistentRef` instead of `kSecReturnRef` to obtain a
persistent reference that survives across app launches. The reference
becomes invalid when the token is removed -- handle `errSecItemNotFound`
by prompting the user to reinsert the token.

Query certificates the same way with `kSecClass: kSecClassCertificate`.

## Certificate Authentication

### Token Key Requirements

For user login, the token must contain at least one key capable of signing
with: EC signature digest X962, RSA signature digest PSS, or RSA signature
digest PKCS1v15.

For keychain unlock, the token needs:
- 256-bit EC key (`kSecAttrKeyTypeECSECPrimeRandom`) supporting
  `ecdhKeyExchangeStandard`, or
- 2048/3072/4096-bit RSA key (`kSecAttrKeyTypeRSA`) supporting
  `rsaEncryptionOAEPSHA256` decryption

### Smart Card Authentication Preferences (macOS)

Configure in the `com.apple.security.smartcard` domain (MDM or systemwide):

| Key | Default | Description |
|---|---|---|
| `allowSmartCard` | `true` | Enable smart card authentication |
| `checkCertificateTrust` | `0` | Certificate trust level (0-3) |
| `oneCardPerUser` | `false` | Pair a single smart card to an account |
| `enforceSmartCard` | `false` | Require smart card for login |

Trust levels: `0` = trust all, `1` = validity + issuer, `2` = + soft
revocation, `3` = + hard revocation.

## Token Watching

`TKTokenWatcher` monitors token insertion and removal. Available on iOS 10+
and macOS 10.12+. Enumerate `tokenIDs`, install an insertion handler, then add a
removal handler for each observed token. Keep the watcher alive for as long as
monitoring is required. For slot-level reader state, use
[Smart Card Slot Monitoring](references/cryptotokenkit-patterns.md#smart-card-slot-monitoring).

## Error Handling

CryptoTokenKit operations throw `TKError`. Key error codes:

| Code | Meaning |
|---|---|
| `.notImplemented` | Operation not supported by this token |
| `.communicationError` | Communication with token failed |
| `.corruptedData` | Data from token is corrupted |
| `.canceledByUser` | User canceled the operation |
| `.authenticationFailed` | PIN or password incorrect |
| `.objectNotFound` | Requested key or certificate not found |
| `.tokenNotFound` | Token is no longer present |
| `.authenticationNeeded` | Authentication required before operation |

## Common Mistakes

### DON'T: Query token keychain items without checking token presence

```swift
// WRONG -- query may fail if token was removed
let key = try findTokenKey(tokenID: savedTokenID)

// CORRECT -- verify the token is still present first
let watcher = TKTokenWatcher()
guard watcher.tokenIDs.contains(savedTokenID) else {
    promptUserToInsertToken()
    return
}
let key = try findTokenKey(tokenID: savedTokenID)
```

### DON'T: Treat API availability as an access guarantee

```swift
// WRONG -- may be nil without entitlement, hardware, or runtime support
let manager = TKSmartCardSlotManager.default!  // Crashes when unavailable

// CORRECT -- guard availability/access before using smart card slots
guard let manager = TKSmartCardSlotManager.default else {
    print("Smart card services unavailable")
    return
}
```

### DON'T: Skip session management for card communication

```swift
// WRONG -- sending commands without a session
card.transmit(apdu) { response, error in /* may fail */ }

// CORRECT -- use withSession or beginSession/endSession
try card.withSession {
    let (sw, response) = try card.send(
        ins: 0xCA, p1: 0x00, p2: 0x6E, data: nil, le: 0
    )
}
```

### DON'T: Ignore status words in APDU responses

```swift
// WRONG -- assuming success
let (_, response) = try card.send(ins: 0xA4, p1: 0x04, p2: 0x00, data: aid, le: nil)

// CORRECT -- check status word
let (sw, response) = try card.send(ins: 0xA4, p1: 0x04, p2: 0x00, data: aid, le: nil)
guard sw == 0x9000 else {
    throw SmartCardError.commandFailed(statusWord: sw)
}
```

### DON'T: Hard-code blanket algorithm support

The `supports` delegate method must reflect what the hardware actually
implements. Returning `true` unconditionally causes runtime failures when
the system attempts unsupported operations.

## Review Checklist

- [ ] Platform availability verified for the exact capability (`TKTokenWatcher` iOS 10+, NFC smart-card sessions iOS/iPadOS 26+)
- [ ] `TKSmartCardSlotManager.default` guarded for missing entitlement, hardware, or runtime support
- [ ] macOS token extension target uses `NSExtensionPointIdentifier` = `com.apple.ctk-tokens`
- [ ] `com.apple.ctk.driver-class` set to the correct driver class in Info.plist
- [ ] Extension registered via `_securityagent` launch during installation
- [ ] `TKTokenSessionDelegate` checks specific algorithms, not blanket `true`
- [ ] Smart card sessions opened and closed (`withSession` or `beginSession`/`endSession`)
- [ ] APDU status words checked after every `send` call
- [ ] Token presence verified via `TKTokenWatcher` before keychain queries
- [ ] `TKError` cases handled with appropriate user feedback
- [ ] Keychain contents populated with correct `objectID` values
- [ ] `TKTokenKeychainKey` capabilities (`canSign`, `canDecrypt`) match hardware
- [ ] Certificate trust level configured appropriately for deployment environment
- [ ] `errSecItemNotFound` handled for persistent references when token is removed
- [ ] iOS 26+ NFC sessions ended with `TKSmartCardSlotNFCSession.end()`

## References

- Extended patterns (PIV commands, TLV parsing, generic token drivers, APDU helpers, secure PIN): [references/cryptotokenkit-patterns.md](references/cryptotokenkit-patterns.md)
- [TKTokenDriver](https://sosumi.ai/documentation/cryptotokenkit/tktokendriver)
- [TKToken](https://sosumi.ai/documentation/cryptotokenkit/tktoken)
- [TKTokenSession](https://sosumi.ai/documentation/cryptotokenkit/tktokensession)
- [TKSmartCard](https://sosumi.ai/documentation/cryptotokenkit/tksmartcard)
- [TKSmartCardSlotManager](https://sosumi.ai/documentation/cryptotokenkit/tksmartcardslotmanager)
- [com.apple.security.smartcard entitlement](https://sosumi.ai/documentation/BundleResources/Entitlements/com.apple.security.smartcard)
- [TKSmartCardSlotNFCSession](https://sosumi.ai/documentation/cryptotokenkit/tksmartcardslotnfcsession)
- [TKSmartCardTokenRegistrationManager](https://sosumi.ai/documentation/cryptotokenkit/tksmartcardtokenregistrationmanager)
- [TKTokenWatcher](https://sosumi.ai/documentation/cryptotokenkit/tktokenwatcher)
- [Authenticating Users with a Cryptographic Token](https://sosumi.ai/documentation/cryptotokenkit/authenticating-users-with-a-cryptographic-token)
- [Using Cryptographic Assets Stored on a Smart Card](https://sosumi.ai/documentation/cryptotokenkit/using-cryptographic-assets-stored-on-a-smart-card)
- [Configuring Smart Card Authentication](https://sosumi.ai/documentation/cryptotokenkit/configuring-smart-card-authentication)
