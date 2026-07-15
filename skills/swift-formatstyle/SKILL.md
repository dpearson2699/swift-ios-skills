---
name: swift-formatstyle
description: "Formats and parses locale-aware numbers, decimals, currencies, percentages, dates, durations, measurements, names, lists, byte counts, and URLs with Foundation FormatStyle and ParseableFormatStyle. Use when replacing legacy Formatter subclasses, designing reusable format APIs, using SwiftUI Text(_:format:), correcting availability, or testing user-facing formatted output across locales."
---

# Swift FormatStyle

Use Foundation's type-safe `FormatStyle` APIs for user-facing display and `ParseableFormatStyle` when the same convention must accept input. Route String Catalogs, plurals, localized copy, bundles, and RTL layout to `ios-localization`; formatting still requires locale review even when no text is translated.

## Contents

- [Workflow](#workflow)
- [Quick Reference](#quick-reference)
- [Selection and Availability](#selection-and-availability)
- [Parsing](#parsing)
- [SwiftUI Integration](#swiftui-integration)
- [Custom FormatStyle](#custom-formatstyle)
- [Common Mistakes](#common-mistakes)
- [Review Checklist](#review-checklist)
- [References](#references)

## Workflow

1. Identify the value's semantic type and whether output is display-only or must round-trip through parsing.
2. Select the narrowest built-in style and keep the user's current locale unless a wire format explicitly requires another locale.
3. Render the exact UI with representative locales such as `en_US`, `de_DE`, `ar_SA`, and `ja_JP`.
4. Check separators, numbering systems, calendars, currency and unit conventions, text direction, and layout.
5. If output or parsing fails, fix the style or surrounding copy, restore the input fixture, and rerun the same locale matrix.

Load [FormatStyle Recipes](references/formatstyle-recipes.md) when implementation needs concrete modifiers, date intervals, relative dates, duration patterns, measurements, names, lists, byte counts, or URL component controls.

## Quick Reference

| Value | Default style | Important constraint |
|---|---|---|
| `Int`, `Double` | `.number` | Configure precision, rounding, grouping, notation, or sign only as required. |
| `Decimal` | `.number`, `.percent`, `.currency(code:)` | Prefer for exact decimal display and parsing. |
| Currency | `.currency(code:)` | Pass an ISO 4217 code; never hardcode a symbol. |
| Percent | `.percent` | Confirm whether the input is a fraction (`0.85`) or whole percent (`85`). |
| `Date` | `.dateTime`, `.relative`, `.interval` | Relative output should usually stand alone, not be embedded in a sentence. |
| `Duration` | `.time(pattern:)`, `.units(allowed:width:)` | Requires iOS 16+; choose compact clock output versus labeled units. |
| `Measurement` | `.measurement(width:usage:)` | `usage:` controls locale-aware conversion policy. |
| `PersonNameComponents` | `.name(style:)` | Do not manually concatenate name parts. |
| Collections | `.list(type:width:)` | Let locale rules choose separators and conjunctions. |
| Byte count | `.byteCount(style:)` | Choose file, memory, decimal, or binary semantics deliberately. |
| `URL` | `.url` | Requires iOS 16+; query, port, and fragment are opt-in display components. |

## Selection and Availability

- Prefer `FormatStyle` over legacy `NumberFormatter`, `DateFormatter`, `DateComponentsFormatter`, and manual interpolation for new iOS 15+ code.
- `Duration` format styles and `URL.FormatStyle` require iOS 16+.
- `Date.AnchoredRelativeFormatStyle` requires iOS 18+ and formats relative to a fixed anchor rather than the current moment.
- Omit `.locale(...)` for normal UI so the style inherits the user's locale. Use a fixed locale only for an explicit protocol or test fixture.
- Treat relative date output as standalone text unless the entire sentence is localized around it.

Docs: [FormatStyle](https://sosumi.ai/documentation/foundation/formatstyle)

## Parsing

Use the matching parseable style when users edit or import formatted values:

```swift
let style = Decimal.FormatStyle.Currency(code: "USD")
    .locale(Locale(identifier: "en_US"))

let value = try Decimal("$3,500.63", format: style)
let display = value.formatted(style)
```

The fixed locale above is appropriate only because the input contract is explicitly `en_US`. For normal UI input, use the user's locale and test round trips with representative decimal separators, currency placement, calendars, and numbering systems.

## SwiftUI Integration

Prefer `Text(_:format:)` so SwiftUI owns the formatted value:

```swift
Text(price, format: .currency(code: currencyCode))
Text(date, format: .dateTime.month().day().year())
Text(duration, format: .units(allowed: [.minutes, .seconds]))
```

For every user-facing formatted `Text`, preview or test the exact screen across the locale matrix. Use `Text(.now, style: .timer)`, `Text(.now, style: .relative)`, or `Text(timerInterval:)` for live-updating time displays rather than manually scheduling string refreshes.

## Custom FormatStyle

Create a custom style only when built-in composition cannot express the domain convention. `FormatStyle` refines `Codable` and `Hashable`; keep styles as reusable values and add `ParseableFormatStyle` only when input must round-trip.

```swift
struct AbbreviatedCountStyle: FormatStyle {
    func format(_ value: Int) -> String {
        switch value {
        case ..<1_000: "\(value)"
        case 1_000..<1_000_000: String(format: "%.1fK", Double(value) / 1_000)
        default: String(format: "%.1fM", Double(value) / 1_000_000)
        }
    }
}

extension FormatStyle where Self == AbbreviatedCountStyle {
    static var abbreviatedCount: Self { .init() }
}
```

Custom styles still need locale and accessibility review; a compact English suffix may not be suitable for every locale.

## Common Mistakes

| Mistake | Fix |
|---|---|
| Manual formatting or legacy formatter allocation in view code | Use the matching `FormatStyle` and `Text(_:format:)`. |
| Hardcoded currency symbol or locale | Pass an ISO currency code and inherit the user locale unless the contract says otherwise. |
| Binary floating-point for exact decimal input | Use `Decimal.FormatStyle` and its matching parse strategy. |
| Assuming `URL.formatted()` preserves every component | Opt in to `.port(.always)`, `.query(.always)`, or `.fragment(.always)` only when those components should display. |
| Relative date output embedded in a larger sentence | Keep it standalone or localize the complete sentence. |
| Clock-style duration used for prose | Use `.units(allowed:width:)` for labeled output. |
| Measurement conversion left implicit | Select a `usage:` appropriate to the UI. |
| One-locale spot check | Run the same exact-screen fixture across representative locales and fix/rerun failures. |

## Review Checklist

- [ ] Semantic value type and display-versus-parse requirement identified
- [ ] Built-in `FormatStyle` used where it can express the convention
- [ ] Availability gated beside iOS 16+ and iOS 18+ APIs
- [ ] Currency uses an ISO 4217 code; exact decimal values use `Decimal`
- [ ] User locale inherited unless a protocol explicitly fixes it
- [ ] Relative date text stands alone or the full sentence is localized
- [ ] URL components and measurement `usage:` are deliberate
- [ ] SwiftUI uses `Text(_:format:)` for formatted values
- [ ] Exact rendered UI and parse round trips pass the representative-locale matrix

## References

- Detailed recipes and modifiers: [references/formatstyle-recipes.md](references/formatstyle-recipes.md)
- Apple docs: [FormatStyle](https://sosumi.ai/documentation/foundation/formatstyle) · [ParseableFormatStyle](https://sosumi.ai/documentation/foundation/parseableformatstyle) · [Date.FormatStyle](https://sosumi.ai/documentation/foundation/date/formatstyle) · [Duration.TimeFormatStyle](https://sosumi.ai/documentation/swift/duration/timeformatstyle) · [URL.FormatStyle](https://sosumi.ai/documentation/foundation/url/formatstyle)
