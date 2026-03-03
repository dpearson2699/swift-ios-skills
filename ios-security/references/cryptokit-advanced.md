# CryptoKit Advanced Patterns

Extended CryptoKit usage beyond the basics covered in the main skill. Includes
digital signatures, key agreement, alternative ciphers, key derivation, and
post-quantum cryptography.

## ChaChaPoly (Alternative to AES-GCM)

Same sealed-box API as AES-GCM. Use for interoperability with non-Apple systems
or when AES hardware acceleration is unavailable.

```swift
import CryptoKit

let key = SymmetricKey(size: .bits256)

// Encrypt
let sealed = try ChaChaPoly.seal(data, using: key)
let combined = sealed.combined

// Decrypt
let box = try ChaChaPoly.SealedBox(combined: combined)
let decrypted = try ChaChaPoly.open(box, using: key)
```

## Digital Signatures (P256 / ECDSA)

```swift
// Generate key pair
let privateKey = P256.Signing.PrivateKey()
let publicKey = privateKey.publicKey

// Sign
let signature = try privateKey.signature(for: data)

// Verify
let isValid = publicKey.isValidSignature(signature, for: data)

// Export public key (raw, DER, or PEM)
let rawData = publicKey.rawRepresentation
let derData = publicKey.derRepresentation
let pemString = publicKey.pemRepresentation

// Import public key
let imported = try P256.Signing.PublicKey(rawRepresentation: rawData)
let importedDER = try P256.Signing.PublicKey(derRepresentation: derData)
let importedPEM = try P256.Signing.PublicKey(pemRepresentation: pemString)
```

Also available: `P384.Signing` and `P521.Signing` for stronger curves.

## Key Agreement (Diffie-Hellman)

### Curve25519

```swift
let myPrivateKey = Curve25519.KeyAgreement.PrivateKey()
let myPublicKey = myPrivateKey.publicKey

// After exchanging public keys...
let sharedSecret = try myPrivateKey.sharedSecretFromKeyAgreement(
    with: theirPublicKey
)

// Derive symmetric key from shared secret using HKDF
let symmetricKey = sharedSecret.hkdfDerivedSymmetricKey(
    using: SHA256.self,
    salt: salt,
    sharedInfo: Data("app-encryption".utf8),
    outputByteCount: 32
)
```

### P256 Key Agreement

```swift
let privateKey = P256.KeyAgreement.PrivateKey()
let publicKey = privateKey.publicKey

let sharedSecret = try privateKey.sharedSecretFromKeyAgreement(
    with: theirPublicKey
)
```

Also available: `P384.KeyAgreement` and `P521.KeyAgreement`.

## Key Derivation with HKDF

Derive one or more keys from input key material:

```swift
// Simple derivation
let derived = HKDF<SHA256>.deriveKey(
    inputKeyMaterial: inputKey,
    salt: salt,
    info: Data("context-string".utf8),
    outputByteCount: 32
)

// Two-step: extract then expand (for advanced use)
let prk = HKDF<SHA256>.extract(inputKeyMaterial: inputKey, salt: salt)
let key1 = HKDF<SHA256>.expand(
    pseudoRandomKey: prk,
    info: Data("key-1".utf8),
    outputByteCount: 32
)
let key2 = HKDF<SHA256>.expand(
    pseudoRandomKey: prk,
    info: Data("key-2".utf8),
    outputByteCount: 32
)
```

## Authenticated Encryption with Associated Data (AEAD)

Both AES-GCM and ChaChaPoly support authenticating additional data that is not
encrypted but is included in the authentication tag:

```swift
let sealed = try AES.GCM.seal(
    plaintext,
    using: key,
    authenticating: associatedData  // e.g., message headers
)

let decrypted = try AES.GCM.open(
    sealed,
    using: key,
    authenticating: associatedData
)
```

## AES Key Wrapping

Wrap and unwrap symmetric keys for secure transport:

```swift
let keyToWrap = SymmetricKey(size: .bits256)
let wrappingKey = SymmetricKey(size: .bits256)

// Wrap
let wrapped = try AES.KeyWrap.wrap(keyToWrap, using: wrappingKey)

// Unwrap
let unwrapped = try AES.KeyWrap.unwrap(wrapped, using: wrappingKey)
```

## Secure Enclave Key Agreement

The Secure Enclave also supports P256 key agreement:

```swift
let accessControl = SecAccessControlCreateWithFlags(
    nil,
    kSecAttrAccessibleWhenPasscodeSetThisDeviceOnly,
    [.privateKeyUsage, .biometryCurrentSet],
    nil
)!

let sePrivateKey = try SecureEnclave.P256.KeyAgreement.PrivateKey(
    accessControl: accessControl
)

let sharedSecret = try sePrivateKey.sharedSecretFromKeyAgreement(
    with: theirPublicKey
)
```

## Post-Quantum Cryptography

CryptoKit includes post-quantum algorithms for future-proofing. These are
available on newer OS versions.

### ML-KEM (Key Encapsulation)

```swift
// ML-KEM 768 (128-bit security)
let privateKey = try MLKEM768.PrivateKey()
let publicKey = privateKey.publicKey

// Encapsulate (sender side)
let result = try publicKey.encapsulate()
let sharedKey = result.sharedSecret      // SymmetricKey
let encapsulated = result.encapsulated   // Send to key owner

// Decapsulate (receiver side)
let decapsulatedKey = try privateKey.decapsulate(encapsulated)
// decapsulatedKey == sharedKey
```

Also available: `MLKEM1024` for 192-bit security.

### ML-DSA (Digital Signatures)

```swift
// ML-DSA 65 (128-bit security)
let signingKey = try MLDSA65.PrivateKey()
let verifyingKey = signingKey.publicKey

let signature = try signingKey.signature(for: data)
let isValid = verifyingKey.isValidSignature(signature, for: data)
```

Also available: `MLDSA87` for 192-bit security.

### Hybrid Post-Quantum (HPKE)

For hybrid classical + post-quantum encryption:

```swift
let ciphersuite = HPKE.Ciphersuite.XWingMLKEM768X25519_SHA256_AES_GCM_256

let sender = try HPKE.Sender(
    recipientKey: recipientPublicKey,
    ciphersuite: ciphersuite,
    info: Data("app-context".utf8)
)

let ciphertext = try sender.seal(plaintext)
// Send sender.encapsulatedKey and ciphertext to recipient
```

## Storing CryptoKit Keys in Keychain

For non-Secure-Enclave keys that need persistence:

```swift
let privateKey = P256.Signing.PrivateKey()

// Store
let keyData = privateKey.rawRepresentation
let query: [String: Any] = [
    kSecClass as String: kSecClassKey,
    kSecAttrKeyType as String: kSecAttrKeyTypeECSECPrimeRandom,
    kSecAttrKeySizeInBits as String: 256,
    kSecAttrApplicationTag as String: "com.app.signing-key".data(using: .utf8)!,
    kSecValueData as String: keyData,
    kSecAttrAccessible as String: kSecAttrAccessibleWhenUnlockedThisDeviceOnly
]
SecItemAdd(query as CFDictionary, nil)

// Retrieve
let searchQuery: [String: Any] = [
    kSecClass as String: kSecClassKey,
    kSecAttrApplicationTag as String: "com.app.signing-key".data(using: .utf8)!,
    kSecReturnData as String: true
]
var result: AnyObject?
SecItemCopyMatching(searchQuery as CFDictionary, &result)
if let data = result as? Data {
    let restored = try P256.Signing.PrivateKey(rawRepresentation: data)
}
```
