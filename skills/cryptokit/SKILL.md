---
name: cryptokit
description: "Use Apple CryptoKit for Swift cryptographic primitives. Use when hashing with SHA-2 or SHA-3, generating HMACs, encrypting with AES-GCM or ChaChaPoly, signing with P256/P384/P521/Curve25519 or ML-DSA keys, performing ECDH, HPKE, ML-KEM, or X-Wing key exchange, using Secure Enclave CryptoKit keys, or migrating CommonCrypto code to CryptoKit."
---

# CryptoKit

Apple CryptoKit provides a Swift-native API for cryptographic operations:
hashing, message authentication, symmetric encryption, public-key signing,
key agreement, HPKE, quantum-secure key encapsulation/signing, and Secure
Enclave-backed keys. Most core primitives are available on iOS 13+; check
availability for HPKE (iOS 17+) and SHA-3 / post-quantum APIs (iOS 26+).
Prefer CryptoKit over CommonCrypto or raw Security framework APIs for new
cryptographic primitive code targeting Swift 6.3+.

## Contents

- [Hashing](#hashing)
- [HMAC](#hmac)
- [Symmetric Encryption](#symmetric-encryption)
- [Public-Key Signing](#public-key-signing)
- [Key Agreement](#key-agreement)
- [HPKE](#hpke)
- [Post-Quantum CryptoKit](#post-quantum-cryptokit)
- [Secure Enclave](#secure-enclave)
- [Common Mistakes](#common-mistakes)
- [Review Checklist](#review-checklist)
- [References](#references)

## Hashing

Use SHA256/SHA384/SHA512 on iOS 13+; SHA3_256/SHA3_384/SHA3_512 require iOS 26+. All conform to `HashFunction`.

### One-shot hashing

```swift
import CryptoKit

let data = Data("Hello, world!".utf8)
let digest = SHA256.hash(data: data)
let hex = digest.compactMap { String(format: "%02x", $0) }.joined()
```

### SHA-3 availability

Use SHA-3 only behind an availability check unless the deployment target is
iOS 26+:

```swift
if #available(iOS 26.0, *) {
    let digest = SHA3_256.hash(data: data)
}
```

### Incremental hashing

For large data or streaming input, hash incrementally:

```swift
var hasher = SHA256()
hasher.update(data: chunk1)
hasher.update(data: chunk2)
let digest = hasher.finalize()
```

### Digest comparison

Compare CryptoKit digest values directly. Do not convert digests to
strings or arrays for security-sensitive equality checks.

```swift
let expected = SHA256.hash(data: reference)
let actual = SHA256.hash(data: received)
if expected == actual {
    // Data integrity verified
}
```

## HMAC

Use HMAC when a protocol requires keyed message authentication; verify with `isValidAuthenticationCode` rather than comparing serialized values yourself.

### Computing an authentication code

```swift
let key = SymmetricKey(size: .bits256)
let data = Data("message".utf8)

let mac = HMAC<SHA256>.authenticationCode(for: data, using: key)
```

### Verifying an authentication code

```swift
let isValid = HMAC<SHA256>.isValidAuthenticationCode(
    mac, authenticating: data, using: key
)
```

### Incremental HMAC

```swift
var hmac = HMAC<SHA256>(key: key)
hmac.update(data: chunk1)
hmac.update(data: chunk2)
let mac = hmac.finalize()
```

## Symmetric Encryption

CryptoKit provides two authenticated encryption ciphers: AES-GCM and
ChaChaPoly. Both produce a sealed box containing the nonce, ciphertext,
and authentication tag.

### AES-GCM

The default choice for symmetric encryption. Hardware-accelerated on Apple
silicon.

```swift
let key = SymmetricKey(size: .bits256)
let plaintext = Data("Secret message".utf8)

// Encrypt
let sealedBox = try AES.GCM.seal(plaintext, using: key)
let ciphertext = sealedBox.combined!  // nonce + ciphertext + tag

// Decrypt
let box = try AES.GCM.SealedBox(combined: ciphertext)
let decrypted = try AES.GCM.open(box, using: key)
```

### ChaChaPoly

Use ChaChaPoly when AES hardware acceleration is unavailable or when
interoperating with protocols that require ChaCha20-Poly1305 (e.g., TLS,
WireGuard).

```swift
let sealedBox = try ChaChaPoly.seal(plaintext, using: key)
let combined = sealedBox.combined  // Always non-optional for ChaChaPoly

let box = try ChaChaPoly.SealedBox(combined: combined)
let decrypted = try ChaChaPoly.open(box, using: key)
```

### Authenticated data

Both ciphers support additional authenticated data (AAD). The AAD is
authenticated but not encrypted -- useful for metadata that must remain
in the clear but be tamper-proof.

```swift
let header = Data("v1".utf8)
let sealedBox = try AES.GCM.seal(
    plaintext, using: key, authenticating: header
)
let decrypted = try AES.GCM.open(
    sealedBox, using: key, authenticating: header
)
```

Use `.bits256` as the default `SymmetricKey` size for AES-256-GCM or
ChaChaPoly. To create a key from existing data:

```swift
let key = SymmetricKey(data: existingKeyData)
```

## Public-Key Signing

CryptoKit supports ECDSA signing with NIST curves and Ed25519 via
Curve25519.

### NIST curves: P256, P384, P521

```swift
let signingKey = P256.Signing.PrivateKey()
let publicKey = signingKey.publicKey

// Sign
let signature = try signingKey.signature(for: data)

// Verify
let isValid = publicKey.isValidSignature(signature, for: data)
```

P384 and P521 use the same API -- substitute the curve name.

NIST keys support DER, PEM, X9.63, and raw representations. See
[references/cryptokit-patterns.md](references/cryptokit-patterns.md) for
serialization examples.

### Curve25519 / Ed25519

```swift
let signingKey = Curve25519.Signing.PrivateKey()
let publicKey = signingKey.publicKey

// Sign
let signature = try signingKey.signature(for: data)

// Verify
let isValid = publicKey.isValidSignature(signature, for: data)
```

Curve25519 keys use `rawRepresentation` only (no DER/PEM/X9.63).

### Choosing a curve

| Curve | Signature Scheme | Key Size | Typical Use |
|---|---|---|---|
| P256 | ECDSA | 256-bit | General purpose; Secure Enclave support |
| P384 | ECDSA | 384-bit | Higher security requirements |
| P521 | ECDSA | 521-bit | Maximum NIST security level |
| Curve25519 | Ed25519 | 256-bit | Fast; simple API; no Secure Enclave |

Use P256 by default. Use Curve25519 when interoperating with Ed25519-based
protocols.

## Key Agreement

Key agreement lets two parties derive a shared symmetric key from their
public/private key pairs using ECDH.

### ECDH with P256

```swift
// Alice
let aliceKey = P256.KeyAgreement.PrivateKey()

// Bob
let bobKey = P256.KeyAgreement.PrivateKey()

// Alice computes shared secret
let sharedSecret = try aliceKey.sharedSecretFromKeyAgreement(
    with: bobKey.publicKey
)

// Derive a symmetric key using HKDF
let symmetricKey = sharedSecret.hkdfDerivedSymmetricKey(
    using: SHA256.self,
    salt: Data("salt".utf8),
    sharedInfo: Data("my-app-v1".utf8),
    outputByteCount: 32
)
```

Bob computes the same `sharedSecret` using his private key and Alice's
public key. Both derive the same `symmetricKey`.

### ECDH with Curve25519

```swift
let aliceKey = Curve25519.KeyAgreement.PrivateKey()
let bobKey = Curve25519.KeyAgreement.PrivateKey()

let sharedSecret = try aliceKey.sharedSecretFromKeyAgreement(
    with: bobKey.publicKey
)

let symmetricKey = sharedSecret.hkdfDerivedSymmetricKey(
    using: SHA256.self,
    salt: Data(),
    sharedInfo: Data("context".utf8),
    outputByteCount: 32
)
```

### Key derivation functions

`SharedSecret` is not directly usable as a `SymmetricKey`. Always derive
a key using one of:

| Method | Standard | Use |
|---|---|---|
| `hkdfDerivedSymmetricKey` | HKDF (RFC 5869) | Recommended default |
| `x963DerivedSymmetricKey` | ANSI X9.63 | Interop with X9.63 systems |

Always provide a non-empty `sharedInfo` string to bind the derived key
to a specific protocol context.

## HPKE

HPKE is available on iOS 17+ for public-key encryption workflows. Prefer it over
hand-rolled ECDH + HKDF + AEAD protocols when encrypting to a recipient public key.

```swift
let info = Data("my-protocol-v1".utf8)
let recipientKey = Curve25519.KeyAgreement.PrivateKey()
var sender = try HPKE.Sender(
    recipientKey: recipientKey.publicKey,
    ciphersuite: .Curve25519_SHA256_ChachaPoly,
    info: info
)
let encapsulatedKey = sender.encapsulatedKey
let ciphertext = try sender.seal(
    plaintext,
    authenticating: Data("metadata".utf8)
)

var recipient = try HPKE.Recipient(
    privateKey: recipientKey,
    ciphersuite: .Curve25519_SHA256_ChachaPoly,
    info: info,
    encapsulatedKey: encapsulatedKey
)
```

`HPKE.Sender` and `HPKE.Recipient` are stateful; keep them as `var`, send
`encapsulatedKey` alongside the ciphertext, and open messages in the same
order they were sealed. See [references/cryptokit-patterns.md](references/cryptokit-patterns.md)
for ciphersuite selection and post-quantum HPKE.

## Post-Quantum CryptoKit

iOS 26+ adds quantum-secure APIs:

- Key encapsulation: `MLKEM768`, `MLKEM1024`
- Hybrid HPKE: `XWingMLKEM768X25519` with `.XWingMLKEM768X25519_SHA256_AES_GCM_256`
- Digital signatures: `MLDSA65`, `MLDSA87`
- Secure Enclave variants: `SecureEnclave.MLKEM768`, `SecureEnclave.MLKEM1024`,
  `SecureEnclave.MLDSA65`, `SecureEnclave.MLDSA87`

Use hybrid mechanisms for migration when both classical and quantum-secure
resistance matter. Account for much larger public keys, ciphertexts, and
signatures than P256 or Curve25519.

## Secure Enclave

The Secure Enclave provides hardware-backed key storage. Private keys
never leave the hardware. For classical elliptic-curve CryptoKit, Secure
Enclave supports P256 signing and key agreement. On iOS 26+ supported
hardware, CryptoKit also exposes Secure Enclave ML-KEM key encapsulation
and ML-DSA signing types.

### Availability check

```swift
guard SecureEnclave.isAvailable else {
    // Fall back to software keys
    return
}
```

### Creating a Secure Enclave signing key

```swift
let privateKey = try SecureEnclave.P256.Signing.PrivateKey()
let publicKey = privateKey.publicKey  // Standard P256.Signing.PublicKey

let signature = try privateKey.signature(for: data)
let isValid = publicKey.isValidSignature(signature, for: data)
```

### Access control

Use `SecAccessControl` with `.privateKeyUsage` when the key requires biometric
or passcode-gated use. Keep detailed Keychain policy decisions in the
`swift-security` domain.

### Persisting Secure Enclave keys

The `dataRepresentation` is an encrypted blob that only the same device's
Secure Enclave can restore. Store it in the Keychain.

```swift
// Export
let blob = privateKey.dataRepresentation

// Restore
let restored = try SecureEnclave.P256.Signing.PrivateKey(
    dataRepresentation: blob
)
```

### Secure Enclave key agreement

```swift
let seKey = try SecureEnclave.P256.KeyAgreement.PrivateKey()
let peerPublicKey: P256.KeyAgreement.PublicKey = // from peer

let sharedSecret = try seKey.sharedSecretFromKeyAgreement(
    with: peerPublicKey
)
```

## Common Mistakes

### 1. Using the shared secret directly as a key

```swift
// DON'T
let badKey = sharedSecret.withUnsafeBytes { bytes in
    SymmetricKey(data: Data(bytes))
}

// DO -- derive with HKDF
let goodKey = sharedSecret.hkdfDerivedSymmetricKey(
    using: SHA256.self,
    salt: salt,
    sharedInfo: info,
    outputByteCount: 32
)
```

### 2. Reusing nonces

```swift
// DON'T -- hardcoded nonce
let nonce = try AES.GCM.Nonce(data: Data(repeating: 0, count: 12))
let box = try AES.GCM.seal(data, using: key, nonce: nonce)

// DO -- let CryptoKit generate a random nonce (default behavior)
let box = try AES.GCM.seal(data, using: key)
```

### 3. Ignoring authentication tag verification

```swift
// DON'T -- manually strip tag and decrypt
// DO -- always use AES.GCM.open() or ChaChaPoly.open()
// which verifies the tag automatically
```

### 4. Using Insecure hashes for security

```swift
// DON'T -- MD5/SHA1 for integrity or security
import CryptoKit
let bad = Insecure.MD5.hash(data: data)

// DO -- use SHA256 or stronger
let good = SHA256.hash(data: data)
```

`Insecure.MD5` and `Insecure.SHA1` exist only for legacy compatibility
(checksum verification, protocol interop). Never use them for new
security-sensitive operations.

### 5. Storing symmetric keys in UserDefaults

```swift
// DON'T
UserDefaults.standard.set(rawKeyData, forKey: "encryptionKey")

// DO -- store in Keychain
// See references/cryptokit-patterns.md for Keychain storage patterns
```

### 6. Not checking Secure Enclave availability

```swift
// DON'T -- crash on simulator or unsupported hardware
let key = try SecureEnclave.P256.Signing.PrivateKey()

// DO
guard SecureEnclave.isAvailable else { /* fallback */ }
let key = try SecureEnclave.P256.Signing.PrivateKey()
```

## Review Checklist

- [ ] Using CryptoKit, not CommonCrypto or raw Security framework
- [ ] SHA256+ for hashing; no MD5/SHA1 for security purposes
- [ ] HMAC verification uses `isValidAuthenticationCode` (constant-time)
- [ ] AES-GCM or ChaChaPoly for symmetric encryption; 256-bit keys
- [ ] Nonces are random (default) -- not hardcoded or reused
- [ ] Authenticated data (AAD) used where metadata needs integrity
- [ ] SharedSecret derived via HKDF, not used directly
- [ ] sharedInfo parameter is non-empty and context-specific
- [ ] HPKE used instead of custom ECDH+HKDF+AEAD for recipient public-key encryption on iOS 17+
- [ ] SHA-3 and post-quantum APIs guarded with iOS 26+ availability
- [ ] Secure Enclave availability checked before use
- [ ] Secure Enclave key `dataRepresentation` stored in Keychain
- [ ] Private keys not logged, printed, or serialized unnecessarily
- [ ] Symmetric keys stored in Keychain, not UserDefaults or files
- [ ] Encryption export compliance considered (`ITSAppUsesNonExemptEncryption`)

## References

- Extended patterns (key serialization, Insecure module, Keychain integration, AES key wrapping, HPKE): [references/cryptokit-patterns.md](references/cryptokit-patterns.md)
- Apple documentation: [CryptoKit](https://sosumi.ai/documentation/cryptokit)
- Apple documentation: [HPKE](https://sosumi.ai/documentation/cryptokit/hpke)
- Apple documentation: [Quantum-secure workflows](https://sosumi.ai/documentation/cryptokit/enhancing-your-app-s-privacy-and-security-with-quantum-secure-workflows)
- Apple sample: [Performing Common Cryptographic Operations](https://sosumi.ai/documentation/cryptokit/performing-common-cryptographic-operations)
- Apple sample: [Storing CryptoKit Keys in the Keychain](https://sosumi.ai/documentation/cryptokit/storing-cryptokit-keys-in-the-keychain)
