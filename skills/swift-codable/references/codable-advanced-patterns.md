# Advanced Codable Patterns

Use these patterns after the model's core keys, nested containers, and decoding
strategies are established.

## Contents

- [Heterogeneous Arrays](#heterogeneous-arrays)
- [Lossy Arrays](#lossy-arrays)
- [Single-Value Wrappers](#single-value-wrappers)
- [Missing-Key Defaults](#missing-key-defaults)
- [Encoder Configuration](#encoder-configuration)
- [Persistence Boundaries](#persistence-boundaries)

## Heterogeneous Arrays

Decode a discriminator first, then decode only fields owned by that case:

```swift
enum ContentBlock: Decodable {
    case text(String)
    case image(URL)

    enum CodingKeys: String, CodingKey { case type, content, url }

    init(from decoder: Decoder) throws {
        let values = try decoder.container(keyedBy: CodingKeys.self)
        switch try values.decode(String.self, forKey: .type) {
        case "text": self = .text(try values.decode(String.self, forKey: .content))
        case "image": self = .image(try values.decode(URL.self, forKey: .url))
        default:
            throw DecodingError.dataCorruptedError(
                forKey: .type, in: values,
                debugDescription: "Unknown content type"
            )
        }
    }
}
```

## Lossy Arrays

Default array decoding fails when any element is invalid. Use lossy decoding
only when the product contract permits partial data, and report skipped items.

```swift
struct LossyArray<Element: Decodable>: Decodable {
    let elements: [Element]

    init(from decoder: Decoder) throws {
        var values = try decoder.unkeyedContainer()
        var decoded: [Element] = []
        while !values.isAtEnd {
            if let value = try? values.decode(Element.self) {
                decoded.append(value)
            } else {
                _ = try? values.decode(DiscardedValue.self)
            }
        }
        elements = decoded
    }
}

private struct DiscardedValue: Decodable {}
```

## Single-Value Wrappers

```swift
struct UserID: Codable, Hashable {
    let rawValue: String

    init(from decoder: Decoder) throws {
        rawValue = try decoder.singleValueContainer().decode(String.self)
    }

    func encode(to encoder: Encoder) throws {
        var value = encoder.singleValueContainer()
        try value.encode(rawValue)
    }
}
```

## Missing-Key Defaults

A stored property default does not make synthesized decoding tolerate a missing
nonoptional key. Decode manually when missing or null has an explicit fallback:

```swift
let values = try decoder.container(keyedBy: CodingKeys.self)
theme = try values.decodeIfPresent(String.self, forKey: .theme) ?? "system"
```

Preserve the distinction between a missing key, explicit null, and malformed
data when the API contract assigns them different meanings.

## Encoder Configuration

Configure matching date, data, float, and key strategies once per transport or
file format. Use `PropertyListEncoder`/`PropertyListDecoder` for property lists;
do not send plist configuration through JSON helpers.

## Persistence Boundaries

- SwiftData: persist supported Codable value types as typed model properties;
  route schema and unsupported-storage decisions to `swiftdata`.
- UserDefaults: store primitive preferences directly. For a small Codable
  preference, a `RawRepresentable` wrapper with JSON-string storage can support
  `@AppStorage`; route larger or durable data to a real persistence layer.
