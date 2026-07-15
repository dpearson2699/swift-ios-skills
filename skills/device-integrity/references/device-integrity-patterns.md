# Device Integrity Extended Patterns

Overflow reference for the `device-integrity` skill. Contains server verification details, advanced error handling, and integration patterns.

## Contents

- [DeviceCheck Server Endpoints](#devicecheck-server-endpoints)
- [Server-Side Attestation Verification](#server-side-attestation-verification)
- [Server-Side Assertion Verification](#server-side-assertion-verification)
- [Server Architecture](#server-architecture)
- [Error Handling](#error-handling)
- [Retry Strategy](#retry-strategy)
- [Handling Rejected Keys](#handling-rejected-keys)
- [Full Integration Manager](#full-integration-manager)
- [Gradual Rollout](#gradual-rollout)
- [Environment Entitlement](#environment-entitlement)

## DeviceCheck Server Endpoints

The server authenticates with a DeviceCheck private key from the Apple
Developer portal and signs a JWT for each request:

| Endpoint | Purpose |
|---|---|
| `https://api.devicecheck.apple.com/v1/query_two_bits` | Read the two bits for a device |
| `https://api.devicecheck.apple.com/v1/update_two_bits` | Set the two bits for a device |
| `https://api.devicecheck.apple.com/v1/validate_device_token` | Validate a token without reading bits |

Use `https://api.development.devicecheck.apple.com` only while testing and
`https://api.devicecheck.apple.com` in production.

## Server-Side Attestation Verification

Your server must:
1. Verify the attestation object is a valid CBOR-encoded structure.
2. Extract the certificate chain and validate it against Apple's App Attest root CA.
3. Compute `clientDataHash = SHA256(challenge)`, append it to the decoded
   `authData`, then compute `nonce = SHA256(authData || clientDataHash)`.
4. Extract the credential certificate extension with OID
   `1.2.840.113635.100.8.2` and verify its octet string equals `nonce`.
5. Verify the public-key hash matches the app-provided `keyId`.
6. Verify the `RP ID` hash matches `SHA256(teamID + "." + bundleID)`.
7. Verify the initial counter is `0`, the `aaguid` matches the expected
   development or production environment, and `credentialId` equals `keyId`.
8. Store the verified public key and receipt for future assertion verification.
9. Mark the challenge consumed only after every verification step succeeds,
   ideally in the same transaction that stores the key state.

See [Validating apps that connect to your server](https://sosumi.ai/documentation/devicecheck/validating-apps-that-connect-to-your-server) for the full server verification algorithm.

## Server-Side Assertion Verification

Your server must:
1. Decode the assertion (CBOR).
2. Recompute `clientDataHash = SHA256(clientData)`, where `clientData`
   includes a one-time server challenge and request context.
3. Verify the signature using the stored public key over
   `SHA256(authenticatorData || clientDataHash)`.
4. Verify the `RP ID` hash and the counter (greater than the stored counter, or
   greater than `0` for the first assertion).
5. Confirm the embedded challenge matches the issued challenge and the request
   context binds the assertion to the received request.
6. Mark the challenge consumed and update the stored counter only after every
   verification step succeeds, ideally atomically.

## Server Architecture

### Attestation vs. Assertion

| Phase | When | What It Proves | Frequency |
|-------|------|---------------|-----------|
| **Attestation** | After key generation | The key lives on a genuine Apple device running a legitimate instance of your app | Once per key |
| **Assertion** | With each sensitive request | The request came from the attested app instance | Per request |

### Recommended Server Architecture

1. **Challenge endpoint** -- generate a random nonce with at least 16 bytes of entropy, store it server-side with a short TTL (e.g., 5 minutes), purpose, and expected request/key context.
2. **Attestation verification endpoint** -- validate the attestation object, store the public key and receipt keyed by `keyId`.
3. **Assertion verification middleware** -- verify assertions on sensitive endpoints (purchases, account changes).

Reject expired, missing, mismatched, or already-consumed challenges. Consume a
challenge only after the corresponding attestation or assertion is fully
verified; consuming on receipt can block safe retries after transient failures.

### Risk Assessment

Combine App Attest with [fraud risk assessment](https://sosumi.ai/documentation/devicecheck/assessing-fraud-risk) for defense in depth. App Attest alone does not guarantee the user is not abusing the app -- it confirms the app is genuine.

App Attest is not a user authentication, session, entitlement, TLS, certificate
pinning, or subscription validation system. Keep those controls in the
appropriate authentication, networking, or broader security layer, and require
them in addition to App Attest on protected endpoints.

## Error Handling

### DCError Codes

```swift
import DeviceCheck

func handleAttestError(_ error: Error) {
    if let dcError = error as? DCError {
        switch dcError.code {
        case .unknownSystemFailure:
            // Transient system error -- retry with exponential backoff
            break
        case .featureUnsupported:
            // Device or OS does not support this feature
            // Fall back to alternative verification
            break
        case .invalidKey:
            // Already-attested key, unattested assertion key, or service rejection
            // Inspect local/server state; discard and regenerate only when bad
            break
        case .invalidInput:
            // The clientDataHash or keyId was malformed
            break
        case .serverUnavailable:
            // Retry attestation later with the same keyId and clientDataHash
            break
        @unknown default:
            break
        }
    }
}
```

## Retry Strategy

```swift
import CryptoKit

extension AppAttestManager {
    func attestKeyWithRetry(challenge: Data, maxAttempts: Int = 3) async throws -> Data {
        guard let keyId else {
            throw DeviceIntegrityError.keyNotGenerated
        }

        let clientDataHash = Data(SHA256.hash(data: challenge))
        var lastError: Error?

        for attempt in 0..<maxAttempts {
            do {
                return try await service.attestKey(keyId, clientDataHash: clientDataHash)
            } catch let error as DCError where error.code == .serverUnavailable {
                lastError = error
                if attempt < maxAttempts - 1 {
                    try await Task.sleep(for: .seconds(pow(2.0, Double(attempt + 1))))
                }
            } catch {
                throw error // Non-retryable errors propagate immediately
            }
        }

        throw lastError ?? DeviceIntegrityError.attestationFailed
    }
}
```

Use the same `challenge`, `keyId`, and `clientDataHash` for each retry after
`.serverUnavailable`. Do not fetch a fresh challenge for that retry loop unless
you are also starting over with a new attestation attempt.

## Handling Rejected Keys

`DCError.invalidKey` means the app called `attestKey` for an already-attested
key, called `generateAssertion` with an unattested key, or the App Attest service
rejected the key. If local/server state confirms the key cannot be used, delete
the stored `keyId` and generate a new key:

```swift
extension AppAttestManager {
    func handleRejectedKey() async throws -> String {
        deleteKeyIdFromKeychain()
        keyId = nil
        return try await generateKeyIfNeeded()
    }

    private func deleteKeyIdFromKeychain() {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: "app-attest-key-id",
            kSecAttrService as String: Bundle.main.bundleIdentifier ?? ""
        ]
        SecItemDelete(query as CFDictionary)
    }
}
```

## Full Integration Manager

Combine the patterns above into a single `actor` that manages the full lifecycle:
1. Check `isSupported` and fall back to `DCDevice` tokens on unsupported devices.
2. Call `generateKeyIfNeeded()` for each user account on each device, reuse the
   account/device-scoped `keyId`, and limit new key generation to new
   account/device/install enrollment or confirmed bad-key recovery.
3. Attest once per key; if `.serverUnavailable` occurs, retry with the same
   challenge, key, and `clientDataHash`.
4. For each sensitive request, obtain a one-time assertion challenge and sign
   client data that includes the challenge plus request context.
5. Handle `DCError.invalidKey` by checking whether the key was already attested,
   not yet attested, or rejected before regenerating.

## Gradual Rollout

Apple recommends a gradual rollout. Gate App Attest behind a remote feature
flag and fall back to `DCDevice` tokens on unsupported devices. For large apps,
ramp production adoption gradually and be prepared to reduce attestation traffic
if `.serverUnavailable` or rate-limit behavior increases during rollout.

## Environment Entitlement

Set the App Attest environment in your entitlements file. Use `development`
during testing and `production` for App Store builds:

```xml
<key>com.apple.developer.devicecheck.appattest-environment</key>
<string>production</string>
```

When the entitlement is omitted during development, the app uses the App Attest
sandbox by default. After distribution through TestFlight, the App Store, or the
Apple Developer Enterprise Program, the app ignores the entitlement value and
uses production. Sandbox keys and receipts do not work in production, and
production keys and receipts do not work in sandbox.

If an App Clip or extension uses App Attest, configure the capability for that
target too. App Attest is supported only in Action, extensible SSO, and watchOS
extensions; other extension types are unsupported even if `isSupported` returns
`true`.

### Error Type

```swift
enum DeviceIntegrityError: Error {
    case deviceCheckUnsupported
    case keyNotGenerated
    case attestationFailed
    case attestationVerificationFailed
    case assertionFailed
    case serverVerificationFailed
}
```

## Apple Documentation Links

- [DeviceCheck framework](https://sosumi.ai/documentation/devicecheck)
- [DCDevice](https://sosumi.ai/documentation/devicecheck/dcdevice)
- [DCAppAttestService](https://sosumi.ai/documentation/devicecheck/dcappattestservice)
- [Establishing your app's integrity](https://sosumi.ai/documentation/devicecheck/establishing-your-app-s-integrity)
- [Validating apps that connect to your server](https://sosumi.ai/documentation/devicecheck/validating-apps-that-connect-to-your-server)
- [Assessing fraud risk](https://sosumi.ai/documentation/devicecheck/assessing-fraud-risk)
- [Preparing to use the app attest service](https://sosumi.ai/documentation/devicecheck/preparing-to-use-the-app-attest-service)
- [Attestation Object Validation Guide](https://sosumi.ai/documentation/devicecheck/attestation-object-validation-guide)
- [App Attest Environment](https://sosumi.ai/documentation/bundleresources/entitlements/com.apple.developer.devicecheck.appattest-environment)
