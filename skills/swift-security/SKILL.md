---
name: swift-security
description: Use when working with iOS/macOS Keychain Services (SecItem queries, kSecClass, OSStatus errors), biometric authentication (LAContext, Face ID, Touch ID), CryptoKit (AES-GCM, ChaChaPoly, ECDSA, ECDH, HPKE, ML-KEM), Secure Enclave, secure credential storage (OAuth tokens, API keys), certificate pinning (SecTrust, SPKI), keychain sharing across apps/extensions, migrating secrets from UserDefaults or plists, or OWASP MASVS/MASTG mobile compliance on Apple platforms.
license: MIT
---

# Swift Security

Use this skill for client-side Apple platform security work: Keychain Services,
access control, biometric-gated secrets, CryptoKit, Secure Enclave keys,
credential storage, certificate trust, keychain sharing, legacy secret
migration, security testing, and OWASP mobile compliance mapping.

Default to iOS 17+ and Swift concurrency examples when the deployment target is
unknown. Keep iOS 13+ compatibility notes when the user asks for older targets.
Treat iOS 26 CryptoKit post-quantum APIs as availability-gated.

## Contents

- [Workflow](#workflow)
- [Reference Loading](#reference-loading)
- [Security Invariants](#security-invariants)
- [Sibling Boundaries](#sibling-boundaries)
- [Review Checklist](#review-checklist)
- [Common Mistakes](#common-mistakes)
- [Output Rules](#output-rules)
- [References](#references)

## Workflow

Classify the request before loading references.

1. Review existing code: run the [Review Checklist](#review-checklist), then
   load [common-anti-patterns.md](references/common-anti-patterns.md) plus the
   domain reference for each failing area. Report severity, evidence, and the
   corrected pattern.
2. Improve or migrate code: identify the migration type, load the migration
   and target-domain references, preserve existing data, verify the new item,
   then remove legacy storage only after success.
3. Implement new security code: load the minimum domain references, use the
   provided correct patterns, include OSStatus handling and tests, then run the
   relevant checklist.

Do not load every reference file by default. This skill is intentionally split
for progressive disclosure; load only the files needed by the user's task.

### Minimum Safe Keychain Write

Use separate add, identity, and update dictionaries; handle every `OSStatus`:

```swift
func saveSecret(_ data: Data, account: String) throws {
    let identity: [CFString: Any] = [
        kSecClass: kSecClassGenericPassword,
        kSecAttrService: "com.example.app",
        kSecAttrAccount: account,
    ]
    var add = identity
    add[kSecValueData] = data
    add[kSecAttrAccessible] = kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly

    switch SecItemAdd(add as CFDictionary, nil) {
    case errSecSuccess:
        return
    case errSecDuplicateItem:
        let status = SecItemUpdate(
            identity as CFDictionary,
            [kSecValueData: data] as CFDictionary
        )
        guard status == errSecSuccess else { throw KeychainError(status: status) }
    case let status:
        throw KeychainError(status: status)
    }
}
```

Load [keychain-fundamentals.md](references/keychain-fundamentals.md) for read,
delete, access-control, locked-device, and test patterns.

## Reference Loading

| If the task involves | Load |
| --- | --- |
| General keychain CRUD or OSStatus handling | [keychain-fundamentals.md](references/keychain-fundamentals.md) |
| Choosing `kSecClass` or item identity | [keychain-item-classes.md](references/keychain-item-classes.md) |
| Accessibility classes or `SecAccessControl` | [keychain-access-control.md](references/keychain-access-control.md) |
| Face ID, Touch ID, or biometric-gated secrets | [biometric-authentication.md](references/biometric-authentication.md) |
| Secure Enclave keys | [secure-enclave.md](references/secure-enclave.md) |
| Hashing, HMAC, AES-GCM, ChaChaPoly, HKDF, PBKDF2 | [cryptokit-symmetric.md](references/cryptokit-symmetric.md) |
| Signing, ECDH, HPKE, ML-KEM, ML-DSA | [cryptokit-public-key.md](references/cryptokit-public-key.md) |
| OAuth tokens, API keys, logout, refresh rotation | [credential-storage-patterns.md](references/credential-storage-patterns.md) |
| App/extension keychain sharing | [keychain-sharing.md](references/keychain-sharing.md) |
| Certificate trust, SPKI pinning, mTLS | [certificate-trust.md](references/certificate-trust.md) |
| UserDefaults/plist/NSCoding migration | [migration-legacy-stores.md](references/migration-legacy-stores.md) |
| Unit, integration, simulator, device, or CI tests | [testing-security-code.md](references/testing-security-code.md) |
| OWASP MASVS/MASTG or enterprise audit mapping | [compliance-owasp-mapping.md](references/compliance-owasp-mapping.md) |
| Full security review | [common-anti-patterns.md](references/common-anti-patterns.md), then each touched domain reference |

## Security Invariants

Use directive language only for these security invariants and the matching
anti-patterns in [common-anti-patterns.md](references/common-anti-patterns.md).
For architecture choices outside this list, use advisory language.

- Never store tokens, passwords, API keys, signing keys, or refresh tokens in
  `UserDefaults`, `Info.plist`, `.xcconfig`, source code, logs, files, or
  `NSCoding` archives. Use Keychain or fetch secrets at runtime.
- Never ignore `OSStatus`. Every `SecItemAdd`, `SecItemCopyMatching`,
  `SecItemUpdate`, and `SecItemDelete` path must handle success and expected
  failures such as `errSecDuplicateItem`, `errSecItemNotFound`, and
  `errSecInteractionNotAllowed`.
- Never use `LAContext.evaluatePolicy()` as the only gate for a secret. Bind
  protected secrets to keychain items with `SecAccessControl`, then let
  keychain access trigger LocalAuthentication.
- Always set `kSecAttrAccessible` or `kSecAttrAccessControl` explicitly when
  adding keychain items.
- Always use add-or-update for persistent keychain writes. Do not delete-then-add
  as a normal update path.
- Keep `SecItem*` work off the main actor. Use an actor or serial queue for
  keychain access.
- On macOS AppKit targets, target the data protection keychain with
  `kSecUseDataProtectionKeychain: true` unless deliberately working with
  legacy file-based keychain items.
- Never reuse an AES-GCM nonce with the same key.
- Never use raw ECDH `SharedSecret` bytes as a symmetric key. Derive with HKDF
  or X9.63 derivation.
- Never use `Insecure.MD5` or `Insecure.SHA1` for security purposes.

## Sibling Boundaries

This skill owns client-side storage, cryptographic primitives, hardware-backed
keys, and trust evaluation. Route adjacent work deliberately:

- Use `authentication` for Sign in with Apple, passkeys, OAuth UI flows,
  `ASAuthorizationController`, credential state, and account sign-in UX.
- Use `cryptokit` for primitive CryptoKit API syntax and examples when storage,
  key lifecycle, protocol/trust design, Secure Enclave policy, certificate
  trust, misuse review, or compliance is not part of the task.
- Keep application-level E2E encryption security reviews here when the work
  involves key ownership, derivation, storage, rotation/recovery, Secure Enclave,
  HPKE/PQC migration, protocol trust boundaries, or misuse analysis.
- Use `device-integrity` for DeviceCheck and App Attest attestation/assertion
  flows.
- Use `ios-networking` for URLSession, request pipelines, ATS configuration,
  retries, caching, reachability, and transport architecture.
- Use `app-store-review` for privacy manifests, ATT, App Review guideline
  compliance, and submission readiness.

This skill may mention those areas only to identify a security handoff.

## Review Checklist

Use this checklist for code reviews and migration plans. Mark each item pass,
fail, or not applicable; for each failure, cite the reference file and severity.

- Secrets are not stored in `UserDefaults`, plists, source, logs, files, or
  archives.
- Every `SecItem*` call checks `OSStatus` and handles common recoverable errors.
- Biometric access to secrets is keychain-bound with `SecAccessControl`, not a
  standalone `Bool` from `LAContext.evaluatePolicy()`.
- Keychain add dictionaries set an explicit accessibility policy.
- Keychain writes use add-or-update rather than delete-then-add.
- Keychain work is isolated from UI/main-actor code.
- The selected `kSecClass` matches the item type and primary-key attributes.
- CryptoKit code avoids nonce reuse, raw shared-secret use, weak hashes, and
  hardcoded keys.
- Custom encryption designs identify key ownership, derivation, storage,
  rotation/recovery, availability gates, and protocol/trust boundaries.
- Secure Enclave code checks availability, handles simulator/device differences,
  persists only `dataRepresentation`, and designs for device-bound keys.
- App/extension sharing uses full Team ID access groups and matching
  entitlements on every target.
- Certificate trust uses current `SecTrust` APIs, validates hostname/policy, and
  uses SPKI or CA pinning when pinning is required.
- macOS keychain code intentionally chooses data protection or file-based
  keychain behavior.
- Tests cover success, duplicate, missing item, locked-device, simulator/device,
  and migration paths where applicable.
- OWASP MASVS/MASTG mappings are included when compliance is requested.

## Common Mistakes

- Generating partial keychain examples without duplicate handling or
  `errSecItemNotFound` handling.
- Adding biometric UI but leaving the secret readable without keychain access
  control.
- Choosing `kSecAttrAccessibleWhenUnlocked` implicitly by omitting the attribute.
- Using `kSecAttrAccessibleAlways` or
  `kSecAttrAccessibleAlwaysThisDeviceOnly`, both deprecated.
- Mixing `kSecAttrAccessible` and `kSecAttrAccessControl` on the same add query.
- Treating Secure Enclave keys as importable, exportable, syncable, or suitable
  for symmetric encryption.
- Claiming SHA-3, ML-KEM, ML-DSA, or X-Wing CryptoKit APIs are available before
  iOS 26.
- Treating HPKE as available before iOS 17.
- Implementing certificate pinning by hashing only raw key bytes instead of the
  correct SPKI representation.
- Expanding this skill into account-login, networking, App Attest, or App Store
  review guidance instead of handing off to sibling skills.

## Output Rules

- For security findings, state severity: CRITICAL for exploitable secret or
  cryptography failures, HIGH for silent security boundary/data-loss issues, and
  MEDIUM for brittle or incomplete hardening.
- Include wrong and corrected code examples for implementation reviews when a
  concrete anti-pattern is present.
- Include minimum iOS/macOS availability when recommending versioned APIs.
- Cite the reference file that supports each substantive security pattern.
- For keychain code, include `OSStatus` handling and explicit accessibility in
  examples.
- For implementation or migration answers, end with `## Reference Files` and
  list the loaded references with a one-line purpose.
- Do not invent WWDC session numbers or source citations. If a claim is not
  present in the loaded references or official Apple documentation, say it needs
  verification.

## References

- [keychain-fundamentals.md](references/keychain-fundamentals.md) - SecItem CRUD, OSStatus handling, add-or-update, macOS data protection keychain.
- [keychain-item-classes.md](references/keychain-item-classes.md) - `kSecClass` selection, primary keys, certificates, identities.
- [keychain-access-control.md](references/keychain-access-control.md) - Accessibility constants, `SecAccessControl`, background access, data protection.
- [biometric-authentication.md](references/biometric-authentication.md) - Keychain-bound biometrics, `LAContext`, enrollment-change handling.
- [secure-enclave.md](references/secure-enclave.md) - Secure Enclave constraints, persistence, biometric keys, iOS 26 PQ APIs.
- [cryptokit-symmetric.md](references/cryptokit-symmetric.md) - SHA, HMAC, AES-GCM, ChaChaPoly, HKDF, PBKDF2.
- [cryptokit-public-key.md](references/cryptokit-public-key.md) - Signing, key agreement, HPKE, ML-KEM, ML-DSA, key formats.
- [credential-storage-patterns.md](references/credential-storage-patterns.md) - OAuth tokens, API keys, rotation, logout cleanup.
- [keychain-sharing.md](references/keychain-sharing.md) - Access groups, extensions, iCloud sync, macOS access groups.
- [certificate-trust.md](references/certificate-trust.md) - SecTrust, SPKI/CA pinning, `NSPinnedDomains`, client certificates.
- [migration-legacy-stores.md](references/migration-legacy-stores.md) - UserDefaults/plist/NSCoding migration and cleanup.
- [common-anti-patterns.md](references/common-anti-patterns.md) - Review backbone for insecure generated code.
- [testing-security-code.md](references/testing-security-code.md) - Protocol mocks, real keychain tests, CI/device split.
- [compliance-owasp-mapping.md](references/compliance-owasp-mapping.md) - OWASP Mobile Top 10, MASVS, MASTG evidence mapping.
