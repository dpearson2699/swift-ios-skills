---
name: device-integrity
description: "Verify device legitimacy and app integrity using DeviceCheck (DCDevice per-device bits) and App Attest (DCAppAttestService key generation, attestation, and assertion flows). Use when implementing fraud prevention, detecting compromised devices, validating app authenticity with Apple's servers, protecting sensitive API endpoints with attested requests, or adding device verification to a backend architecture."
---

# Device Integrity

Verify that requests to your server come from a genuine Apple device running a
legitimate instance of your app. DeviceCheck provides per-device bits for
simple flags (e.g., "claimed promo offer"). App Attest uses Secure Enclave keys
and Apple attestation to cryptographically prove app legitimacy on sensitive
requests.

## Contents

- [DCDevice (DeviceCheck Tokens)](#dcdevice-devicecheck-tokens)
- [DCAppAttestService (App Attest)](#dcappattestservice-app-attest)
- [App Attest Key Generation](#app-attest-key-generation)
- [App Attest Attestation Flow](#app-attest-attestation-flow)
- [App Attest Assertion Flow](#app-attest-assertion-flow)
- [Server Verification Guidance](#server-verification-guidance)
- [Error Handling](#error-handling)
- [Common Patterns](#common-patterns)
- [Common Mistakes](#common-mistakes)
- [Review Checklist](#review-checklist)
- [References](#references)

## DCDevice (DeviceCheck Tokens)

[`DCDevice`](https://sosumi.ai/documentation/devicecheck/dcdevice) generates a
unique, ephemeral token that identifies a device. Treat each token as
single-use: generate a new token for each server operation instead of caching or
reusing one. The token is sent to your server, which then communicates with
Apple's servers to read or set two per-device bits. Available on iOS 11+.

### Token Generation

```swift
import DeviceCheck

func generateDeviceToken() async throws -> Data {
    guard DCDevice.current.isSupported else {
        throw DeviceIntegrityError.deviceCheckUnsupported
    }

    return try await DCDevice.current.generateToken()
}
```

### Sending the Token to Your Server

```swift
func sendTokenToServer(_ token: Data) async throws {
    let tokenString = token.base64EncodedString()

    var request = URLRequest(url: serverURL.appending(path: "verify-device"))
    request.httpMethod = "POST"
    request.setValue("application/json", forHTTPHeaderField: "Content-Type")
    request.httpBody = try JSONEncoder().encode(["device_token": tokenString])

    let (_, response) = try await URLSession.shared.data(for: request)
    guard let httpResponse = response as? HTTPURLResponse,
          httpResponse.statusCode == 200 else {
        throw DeviceIntegrityError.serverVerificationFailed
    }
}
```

### Server-Side Overview

The server exchanges each fresh token with Apple's authenticated DeviceCheck API.
Load [DeviceCheck Server Endpoints](references/device-integrity-patterns.md#devicecheck-server-endpoints)
for endpoint and environment details.

### What the Two Bits Are For

Apple stores two Boolean values per device per developer team. You decide what
they mean. Common uses:

- **Bit 0:** Device has claimed a promotional offer.
- **Bit 1:** Device has been flagged for fraud.

Bits persist across app reinstall. You control when to reset them via the
server API.

## DCAppAttestService (App Attest)

[`DCAppAttestService`](https://sosumi.ai/documentation/devicecheck/dcappattestservice)
validates that a specific instance of your app on a specific device is
legitimate. It uses a hardware-backed key in the Secure Enclave to create
cryptographic attestations and assertions. Available on iOS 14+.

The flow has three phases:
1. **Key generation** -- create a key pair in the Secure Enclave.
2. **Attestation** -- Apple certifies the key belongs to a genuine Apple device running your app.
3. **Assertion** -- sign server requests with the attested key to prove ongoing legitimacy.

### Checking Support

```swift
import DeviceCheck

let attestService = DCAppAttestService.shared

guard attestService.isSupported else {
    // Fall back to DCDevice token or other risk assessment.
    // App Attest is not available on simulators or all device models.
    return
}
```

For app extensions, App Attest is supported only in Action, extensible SSO, and
watchOS extensions. Treat other extension types as unsupported even if
`isSupported` returns `true`.

## App Attest Key Generation

Generate one cryptographic key pair per user account on each device. The
private key stays in the Secure Enclave. The returned `keyId` is the only
identifier your app can later use to access the key, so record and reuse the
account/device-scoped `keyId`; do not share one key across users. Avoid
unnecessary regeneration because each new key affects App Attest key-count risk
metrics. Only treat the `keyId` as usable after your server verifies
attestation. If server verification fails, discard the `keyId` and generate a
new key before retrying.

```swift
import DeviceCheck

actor AppAttestManager {
    private let service = DCAppAttestService.shared
    private var keyId: String?

    /// Generate and record a key pair for App Attest.
    func generateKeyIfNeeded() async throws -> String {
        if let existingKeyId = loadKeyIdFromKeychain() {
            self.keyId = existingKeyId
            return existingKeyId
        }

        let newKeyId = try await service.generateKey()
        saveKeyIdToKeychain(newKeyId)
        self.keyId = newKeyId
        return newKeyId
    }

    // MARK: - Keychain helpers (simplified)

    private func saveKeyIdToKeychain(_ keyId: String) {
        let data = Data(keyId.utf8)
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: "app-attest-key-id-\(currentAccountID)",
            kSecAttrService as String: Bundle.main.bundleIdentifier ?? "",
            kSecValueData as String: data,
            kSecAttrAccessible as String: kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
        ]
        SecItemDelete(query as CFDictionary) // Remove old if exists
        SecItemAdd(query as CFDictionary, nil)
    }

    private func loadKeyIdFromKeychain() -> String? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: "app-attest-key-id-\(currentAccountID)",
            kSecAttrService as String: Bundle.main.bundleIdentifier ?? "",
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne
        ]
        var result: AnyObject?
        let status = SecItemCopyMatching(query as CFDictionary, &result)
        guard status == errSecSuccess, let data = result as? Data else { return nil }
        return String(data: data, encoding: .utf8)
    }
}
```

## App Attest Attestation Flow

Attestation proves that the key was generated on a genuine Apple device running
a legitimate instance of your app. You perform attestation once per key, then
store the verified public key and receipt on your server. The app stores the
`keyId` for future assertions after the server accepts the attestation.

### Client-Side Attestation

```swift
import DeviceCheck
import CryptoKit

extension AppAttestManager {
    /// Attest the key with Apple. Send the attestation object to your server.
    func attestKey() async throws -> Data {
        guard let keyId else {
            throw DeviceIntegrityError.keyNotGenerated
        }

        // 1. Request a one-time challenge from your server
        let challenge = try await fetchServerChallenge()

        // 2. Hash the challenge (Apple requires a SHA-256 hash)
        let challengeHash = Data(SHA256.hash(data: challenge))

        // 3. Ask Apple to attest the key
        let attestation = try await service.attestKey(keyId, clientDataHash: challengeHash)

        // 4. Send the attestation object to your server for verification
        try await sendAttestationToServer(
            keyId: keyId,
            attestation: attestation,
            challenge: challenge
        )

        return attestation
    }

    private func fetchServerChallenge() async throws -> Data {
        let url = serverURL.appending(path: "attest/challenge")
        let (data, _) = try await URLSession.shared.data(from: url)
        return data
    }

    private func sendAttestationToServer(
        keyId: String,
        attestation: Data,
        challenge: Data
    ) async throws {
        var request = URLRequest(url: serverURL.appending(path: "attest/verify"))
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        let payload: [String: String] = [
            "key_id": keyId,
            "attestation": attestation.base64EncodedString(),
            "challenge": challenge.base64EncodedString()
        ]
        request.httpBody = try JSONEncoder().encode(payload)

        let (_, response) = try await URLSession.shared.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw DeviceIntegrityError.attestationVerificationFailed
        }
    }
}
```

### Server-Side Attestation Verification

The server must verify the attestation before the client treats `keyId` as usable,
then store the verified public key and receipt. Load
[Server-Side Attestation Verification](references/device-integrity-patterns.md#server-side-attestation-verification)
for the certificate, App ID, environment, counter, credential, and nonce checks.

## App Attest Assertion Flow

After attestation, use assertions to sign sensitive requests. Each assertion
proves the request came from the attested app instance and includes a
server-issued, one-time challenge to prevent replay.

### Client-Side Assertion

```swift
import DeviceCheck
import CryptoKit

extension AppAttestManager {
    /// Generate an assertion for encoded client data.
    /// Client data should include a one-time server challenge and request context.
    func generateAssertion(for clientData: Data) async throws -> Data {
        guard let keyId else {
            throw DeviceIntegrityError.keyNotGenerated
        }

        let clientDataHash = Data(SHA256.hash(data: clientData))

        return try await service.generateAssertion(keyId, clientDataHash: clientDataHash)
    }
}
```

### Using Assertions in Network Requests

```swift
struct AppAttestClientData: Encodable {
    let challenge: String
    let method: String
    let path: String
    let bodySHA256: String
}

extension AppAttestManager {
    /// Perform an attested API request.
    func makeAttestedRequest(
        to url: URL,
        method: String = "POST",
        body: Data
    ) async throws -> (Data, URLResponse) {
        let challenge = try await fetchAssertionChallenge()
        let bodyHash = Data(SHA256.hash(data: body)).base64EncodedString()
        let clientData = try JSONEncoder().encode(
            AppAttestClientData(
                challenge: challenge,
                method: method,
                path: url.path,
                bodySHA256: bodyHash
            )
        )
        let assertion = try await generateAssertion(for: clientData)

        var request = URLRequest(url: url)
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue(assertion.base64EncodedString(), forHTTPHeaderField: "X-App-Attest-Assertion")
        request.setValue(clientData.base64EncodedString(), forHTTPHeaderField: "X-App-Attest-Client-Data")
        request.httpBody = body

        return try await URLSession.shared.data(for: request)
    }

    private func fetchAssertionChallenge() async throws -> String {
        let url = serverURL.appending(path: "assert/challenge")
        let (data, _) = try await URLSession.shared.data(from: url)
        return String(decoding: data, as: UTF8.self)
    }
}
```

### Server-Side Assertion Verification

The server must verify each assertion's signature, RP ID, counter, one-time
challenge, and request binding before authorizing the request. Load
[Server-Side Assertion Verification](references/device-integrity-patterns.md#server-side-assertion-verification)
for the complete algorithm.

## Server Verification Guidance

See [references/device-integrity-patterns.md](references/device-integrity-patterns.md) for full server architecture guidance including attestation vs. assertion comparison, recommended endpoint design, and risk assessment.

### Security Boundaries

App Attest proves app-instance integrity for selected requests. It does not
replace user authentication, OAuth/JWT/session handling, API token design,
entitlement or subscription authorization, TLS, certificate pinning, or general
networking security. Treat those as handoffs to authentication, networking, or
broader security guidance, and still enforce normal authentication and
authorization after App Attest passes.

## Error Handling

Handle `DCError` codes from DeviceCheck operations. Key cases:

- `.serverUnavailable` — retry with exponential backoff
- `.invalidKey` — the key was already attested, assertion used an unattested key, or the service rejected the key
- `.featureUnsupported` — fall back to `DCDevice` tokens
- `.invalidInput` — malformed `clientDataHash` or `keyId`

For `attestKey`, retry `.serverUnavailable` later with the same `keyId` and the
same `clientDataHash`. For other attestation errors, discard the key identifier
and create a new key before retrying. See
[references/device-integrity-patterns.md](references/device-integrity-patterns.md)
for full error handling code, retry strategy, and rejected-key recovery.

## Common Patterns

### Environment Entitlement

Set the App Attest environment in your entitlements file. Use `development`
during testing and `production` for App Store builds. Load
[Environment Entitlement](references/device-integrity-patterns.md#environment-entitlement)
for the XML, default sandbox behavior, distribution behavior, and extension limits.

See [references/device-integrity-patterns.md](references/device-integrity-patterns.md) for the full integration manager pattern, gradual rollout guidance, and error type definition.

## Common Mistakes

1. **Generating a new key on every launch.** Generate once per user account on a device, persist the `keyId`, and keep key counts low.
2. **Reusing `DCDevice` tokens.** Treat generated tokens as single-use. Generate a new token for each server operation.
3. **Skipping the fallback for unsupported devices or extensions.** Not all devices and extension types support App Attest. Use `DCDevice` tokens or other risk assessment as fallback.
4. **Trusting attestation client-side.** All verification must happen on your server.
5. **Signing only the raw request body.** Assertion client data must include a one-time server challenge and enough request context for the server to bind the assertion to the request.
6. **Verifying the wrong attestation nonce.** Compare the certificate extension with `SHA256(authData || SHA256(challenge))`, not `SHA256(challenge)` alone.
7. **Not implementing replay protection.** The server must validate one-time challenges and track the assertion counter.
8. **Mixing development and production environments.** Sandbox keys and receipts do not work in production, and production keys and receipts do not work in sandbox.
9. **Not handling `DCError.invalidKey`.** Check for repeated attestation, unattested assertion keys, or service rejection; regenerate only after the state is known bad.

## Review Checklist

- [ ] `DCDevice` tokens generated per server operation and never cached for reuse
- [ ] `DCAppAttestService.isSupported` checked before use; unsupported devices and extension types have a fallback
- [ ] Key generated once per user account on each device and `keyId` persisted only for that app account/device
- [ ] Attestation performed once per key; server stores verified public key and receipt
- [ ] Server validates attestation certificate chain, App ID hash, environment `aaguid`, credential ID, and nonce `SHA256(authData || SHA256(challenge))`
- [ ] Assertions include one-time challenge plus request context; server verifies signature, RP ID, counter, challenge, and request binding
- [ ] Protected endpoints still enforce normal user authentication and entitlement authorization after App Attest passes
- [ ] `DCError` cases handled: `.serverUnavailable` retries attestation with the same key/hash; bad keys are discarded and regenerated
- [ ] App Attest environment entitlement and sandbox/production server routing are consistent
- [ ] Gradual rollout considered; feature flag in place for enabling/disabling

## References

- Extended patterns: [references/device-integrity-patterns.md](references/device-integrity-patterns.md)
- [DeviceCheck framework](https://sosumi.ai/documentation/devicecheck)
- [DCDevice](https://sosumi.ai/documentation/devicecheck/dcdevice)
- [DCAppAttestService](https://sosumi.ai/documentation/devicecheck/dcappattestservice)
- [Establishing your app's integrity](https://sosumi.ai/documentation/devicecheck/establishing-your-app-s-integrity)
- [Validating apps that connect to your server](https://sosumi.ai/documentation/devicecheck/validating-apps-that-connect-to-your-server)
- [Attestation Object Validation Guide](https://sosumi.ai/documentation/devicecheck/attestation-object-validation-guide)
- [App Attest Environment](https://sosumi.ai/documentation/bundleresources/entitlements/com.apple.developer.devicecheck.appattest-environment)
