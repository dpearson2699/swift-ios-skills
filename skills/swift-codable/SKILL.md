---
name: swift-codable
description: "Implement Swift Codable models for JSON and property-list encoding and decoding with JSONDecoder, JSONEncoder, CodingKeys, and custom init(from:) or encode(to:). Use when parsing API responses, remapping keys, flattening nested JSON, handling date or data decoding strategies, decoding heterogeneous arrays, or integrating Codable with URLSession, SwiftData, or UserDefaults."
---

# Swift Codable

Encode and decode Swift types using `Codable` (`Encodable & Decodable`) with
`JSONEncoder`, `JSONDecoder`, and related APIs. Targets Swift 6.3 / iOS 26+.

## Contents

- [Decode and Verify Workflow](#decode-and-verify-workflow)
- [Basic Conformance](#basic-conformance)
- [Custom CodingKeys](#custom-codingkeys)
- [Custom Decoding and Encoding](#custom-decoding-and-encoding)
- [Nested and Flattened Containers](#nested-and-flattened-containers)
- [Heterogeneous Arrays](#heterogeneous-arrays)
- [Date Decoding Strategies](#date-decoding-strategies)
- [Data and Key Strategies](#data-and-key-strategies)
- [Lossy Array Decoding](#lossy-array-decoding)
- [Single Value Containers](#single-value-containers)
- [Default Values for Missing Keys](#default-values-for-missing-keys)
- [Encoder and Decoder Configuration](#encoder-and-decoder-configuration)
- [Codable with URLSession](#codable-with-urlsession)
- [Codable with SwiftData](#codable-with-swiftdata)
- [Codable with UserDefaults](#codable-with-userdefaults)
- [Common Mistakes](#common-mistakes)
- [Review Checklist](#review-checklist)
- [References](#references)

## Decode and Verify Workflow

1. Decode representative success, missing, null, malformed, acronym-key, and
   date fixtures.
2. On failure, inspect `DecodingError`, its `codingPath`, and the raw payload.
3. Correct only the mismatched model, key, container, or strategy; do not hide
   contract failures with lossy decoding.
4. Rerun fixtures and encode/decode round trips where both directions are part
   of the contract.

## Basic Conformance

When all stored properties are themselves `Codable`, the compiler synthesizes
conformance automatically:

```swift
struct User: Codable {
    let id: Int
    let name: String
    let email: String
    let isVerified: Bool
}

let user = try JSONDecoder().decode(User.self, from: jsonData)
let encoded = try JSONEncoder().encode(user)
```

Prefer `Decodable` for read-only API responses and `Encodable` for write-only.
Use `Codable` only when both directions are required.

## Custom CodingKeys

Rename JSON keys without writing a custom decoder by declaring a `CodingKeys`
enum:

```swift
struct Product: Codable {
    let id: Int
    let displayName: String
    let imageURL: URL
    let priceInCents: Int

    enum CodingKeys: String, CodingKey {
        case id
        case displayName = "display_name"
        case imageURL = "image_url"
        case priceInCents = "price_in_cents"
    }
}
```

Every stored property must appear in the enum. Omitting a property from
`CodingKeys` excludes it from encoding/decoding -- provide a default value or
compute it separately.

## Custom Decoding and Encoding

Override `init(from:)` and `encode(to:)` for transformations the synthesized
conformance cannot handle:

```swift
struct Event: Codable {
    let name: String
    let timestamp: Date
    let tags: [String]

    enum CodingKeys: String, CodingKey {
        case name, timestamp, tags
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        name = try container.decode(String.self, forKey: .name)
        // Decode Unix timestamp as Double, convert to Date
        let epoch = try container.decode(Double.self, forKey: .timestamp)
        timestamp = Date(timeIntervalSince1970: epoch)
        // Default to empty array when key is missing
        tags = try container.decodeIfPresent([String].self, forKey: .tags) ?? []
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(name, forKey: .name)
        try container.encode(timestamp.timeIntervalSince1970, forKey: .timestamp)
        try container.encode(tags, forKey: .tags)
    }
}
```

## Nested and Flattened Containers

Use `nestedContainer(keyedBy:forKey:)` to navigate and flatten nested JSON:

```swift
// JSON: { "id": 1, "location": { "lat": 37.7749, "lng": -122.4194 } }
struct Place: Decodable {
    let id: Int
    let latitude: Double
    let longitude: Double

    enum CodingKeys: String, CodingKey { case id, location }
    enum LocationKeys: String, CodingKey { case lat, lng }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(Int.self, forKey: .id)
        let location = try container.nestedContainer(
            keyedBy: LocationKeys.self, forKey: .location)
        latitude = try location.decode(Double.self, forKey: .lat)
        longitude = try location.decode(Double.self, forKey: .lng)
    }
}
```

Chain multiple `nestedContainer` calls to flatten deeply nested structures.
Also use `nestedUnkeyedContainer(forKey:)` for nested arrays.

## Heterogeneous Arrays

Load [Advanced Codable Patterns](references/codable-advanced-patterns.md#heterogeneous-arrays)
for discriminator-based mixed arrays.

## Date Decoding Strategies

Configure `JSONDecoder.dateDecodingStrategy` to match your API:

```swift
let decoder = JSONDecoder()

// ISO 8601 (e.g., "2024-03-15T10:30:00Z")
decoder.dateDecodingStrategy = .iso8601

// Unix timestamp in seconds (e.g., 1710499800)
decoder.dateDecodingStrategy = .secondsSince1970

// Custom DateFormatter
let formatter = DateFormatter()
formatter.dateFormat = "yyyy-MM-dd"
formatter.locale = Locale(identifier: "en_US_POSIX")
formatter.timeZone = TimeZone(secondsFromGMT: 0)
decoder.dateDecodingStrategy = .formatted(formatter)

// Custom closure for multiple formats
decoder.dateDecodingStrategy = .custom { decoder in
    let container = try decoder.singleValueContainer()
    let string = try container.decode(String.self)
    if let date = ISO8601DateFormatter().date(from: string) { return date }
    throw DecodingError.dataCorruptedError(
        in: container, debugDescription: "Cannot decode date: \(string)")
}
```

Set the matching strategy on `JSONEncoder`:
`encoder.dateEncodingStrategy = .iso8601`

## Data and Key Strategies

```swift
let decoder = JSONDecoder()
decoder.dataDecodingStrategy = .base64           // Base64-encoded Data fields
decoder.keyDecodingStrategy = .convertFromSnakeCase  // simple keys only; not URL/ID spelling
// {"user_name": "Alice"} maps to `var userName: String` -- no CodingKeys needed

let encoder = JSONEncoder()
encoder.dataEncodingStrategy = .base64
encoder.keyEncodingStrategy = .convertToSnakeCase
```

Use key strategies only for mechanical snake_case-to-camelCase mappings.
`convertFromSnakeCase` maps by spelling, not Swift acronym/initialism policy:
`image_url`, `base_uri`, and `user_id` match `imageUrl`, `baseUri`, and
`userId` only. If the Swift model uses `imageURL`, `baseURI`, or `userID`,
declare explicit `CodingKeys`; the strategy will not synthesize those names.

## Lossy Array Decoding

Use lossy arrays only when partial success is part of the product contract; load
[Lossy Arrays](references/codable-advanced-patterns.md#lossy-arrays).

## Single Value Containers

Use `singleValueContainer()` for type-safe primitive wrappers; see
[Single-Value Wrappers](references/codable-advanced-patterns.md#single-value-wrappers).

## Default Values for Missing Keys

Stored defaults do not make synthesized decoding tolerate missing nonoptional
keys. Load [Missing-Key Defaults](references/codable-advanced-patterns.md#missing-key-defaults)
when the contract assigns explicit fallback behavior to missing or null values.

## Encoder and Decoder Configuration

Keep matching strategies at the transport/file-format boundary. Load
[Encoder Configuration](references/codable-advanced-patterns.md#encoder-configuration)
for nonconforming floats and property-list guidance.

## Codable with URLSession

```swift
func fetchUser(id: Int) async throws -> User {
    let url = URL(string: "https://api.example.com/users/\(id)")!
    let (data, response) = try await URLSession.shared.data(from: url)
    guard let http = response as? HTTPURLResponse,
          (200...299).contains(http.statusCode) else {
        throw APIError.invalidResponse
    }
    let decoder = JSONDecoder()
    decoder.keyDecodingStrategy = .convertFromSnakeCase
    decoder.dateDecodingStrategy = .iso8601
    return try decoder.decode(User.self, from: data)
}

// Generic API envelope. Configure a decoder inside this helper because
// fetchUser's decoder is out of scope.
struct APIResponse<T: Decodable>: Decodable {
    let data: T
    let meta: Meta?
    struct Meta: Decodable { let page: Int; let totalPages: Int }
}

func decodeUsersEnvelope(from data: Data) throws -> [User] {
    let decoder = JSONDecoder()
    decoder.keyDecodingStrategy = .convertFromSnakeCase
    decoder.dateDecodingStrategy = .iso8601
    return try decoder.decode(APIResponse<[User]>.self, from: data).data
}
```

## Codable with SwiftData

Keep schema values typed and route persistence design to `swiftdata`; see
[Persistence Boundaries](references/codable-advanced-patterns.md#persistence-boundaries).

## Codable with UserDefaults

Use primitives for small preferences. Load
[Persistence Boundaries](references/codable-advanced-patterns.md#persistence-boundaries)
for a small Codable `RawRepresentable`/`@AppStorage` handoff; use a real
persistence layer for larger or durable data.

## Common Mistakes

**1. Not handling missing defaulted fields:**
```swift
// DON'T -- crashes if key is absent
let value = try container.decode(String.self, forKey: .bio)
// DO -- falls back when the key is absent or null
let value = try container.decodeIfPresent(String.self, forKey: .bio) ?? ""
```

**2. Failing entire array when one element is invalid:**
```swift
// DON'T -- one bad element kills the whole decode
let items = try container.decode([Item].self, forKey: .items)
// DO -- decode elements individually only when partial success is allowed
```

**3. Date strategy mismatch:**
```swift
// DON'T -- default strategy expects Double, but API sends ISO string
let decoder = JSONDecoder()  // dateDecodingStrategy defaults to .deferredToDate
// DO -- set strategy to match your API format
decoder.dateDecodingStrategy = .iso8601
```

**4. Force-unwrapping decoded optionals:**
```swift
// DON'T
let user = try? decoder.decode(User.self, from: data)
print(user!.name)
// DO
guard let user = try? decoder.decode(User.self, from: data) else { return }
```

**5. Using Codable when only Decodable is needed:**
```swift
// DON'T -- unnecessarily constrains the type to also be Encodable
struct APIResponse: Codable { let id: Int; let message: String }
// DO -- use Decodable for read-only API responses
struct APIResponse: Decodable { let id: Int; let message: String }
```

**6. Manual CodingKeys for simple snake_case APIs:**
```swift
// DON'T -- verbose boilerplate for every model
enum CodingKeys: String, CodingKey {
    case userName = "user_name"
    case avatarUrl = "avatar_url"
}
// DO -- configure once on the decoder for simple cases
decoder.keyDecodingStrategy = .convertFromSnakeCase
// Keep CodingKeys for `imageURL`, `baseURI`, `userID`, and similar names.
```

## Review Checklist

- [ ] Types conform to `Decodable` only when encoding is not needed
- [ ] `decodeIfPresent` used with defaults for optional or missing keys
- [ ] `keyDecodingStrategy = .convertFromSnakeCase` used for simple snake_case APIs, with CodingKeys retained for acronym spellings
- [ ] `dateDecodingStrategy` matches the API date format
- [ ] Arrays of unreliable data use lossy decoding to skip invalid elements
- [ ] Custom `init(from:)` validates and transforms data instead of post-decode fixups
- [ ] `JSONEncoder.outputFormatting` includes `.sortedKeys` for deterministic test output
- [ ] Wrapper types (UserID, etc.) use `singleValueContainer` for clean JSON
- [ ] Generic `APIResponse<T>` wrapper used for consistent API envelope handling
- [ ] No force-unwrapping of decoded values
- [ ] Persistence boundary is explicit: SwiftData only for compatible noncomputed model properties, `@AppStorage`/UserDefaults only for small primitive or `RawRepresentable` preferences

## References

- [Advanced Codable patterns](references/codable-advanced-patterns.md) -- mixed arrays, lossy decoding, wrappers, defaults, configuration, and persistence boundaries
- [Codable](https://sosumi.ai/documentation/swift/codable/) -- protocol combining Encodable and Decodable
- [JSONDecoder](https://sosumi.ai/documentation/foundation/jsondecoder/) -- decodes JSON data into Codable types
- [JSONEncoder](https://sosumi.ai/documentation/foundation/jsonencoder/) -- encodes Codable types as JSON data
- [CodingKey](https://sosumi.ai/documentation/swift/codingkey/) -- protocol for encoding/decoding keys
- [JSONDecoder.KeyDecodingStrategy.convertFromSnakeCase](https://sosumi.ai/documentation/foundation/jsondecoder/keydecodingstrategy-swift.enum/convertfromsnakecase) -- snake-case conversion behavior and limitations
- [Encoding and Decoding Custom Types](https://sosumi.ai/documentation/foundation/encoding-and-decoding-custom-types/) -- Apple guide on custom Codable conformance
- [Using JSON with Custom Types](https://sosumi.ai/documentation/foundation/archives_and_serialization/using_json_with_custom_types/) -- Apple sample code for JSON patterns
- [Preserving your app's model data across launches](https://sosumi.ai/documentation/swiftdata/preserving-your-apps-model-data-across-launches) -- SwiftData model property compatibility
