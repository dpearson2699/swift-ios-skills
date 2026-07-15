# FormatStyle Recipes

Load this reference when concrete formatting modifiers or less common built-in styles are needed.

## Contents

- [Numbers and Decimals](#numbers-and-decimals)
- [Currency and Percent](#currency-and-percent)
- [Dates](#dates)
- [Durations](#durations)
- [Measurements and Names](#measurements-and-names)
- [Lists and Byte Counts](#lists-and-byte-counts)
- [URLs](#urls)

## Numbers and Decimals

```swift
1234.5.formatted(.number.precision(.fractionLength(0...2)))
1234.5.formatted(.number.precision(.significantDigits(3)))
1234.formatted(.number.rounded(rule: .down, increment: 100))
1_200_000.formatted(.number.notation(.compactName))
42.formatted(.number.notation(.scientific))
(-42).formatted(.number.sign(strategy: .always()))

let amount = Decimal(string: "12345.67")!
amount.formatted(.number)
amount.formatted(.number.grouping(.never))
let parsed = try? Decimal("3.500,63", format: .number.locale(.init(identifier: "de_DE")))
```

Docs: [IntegerFormatStyle](https://sosumi.ai/documentation/foundation/integerformatstyle) · [Decimal.FormatStyle](https://sosumi.ai/documentation/foundation/decimal/formatstyle)

## Currency and Percent

```swift
29.99.formatted(.currency(code: "USD"))
Decimal(string: "12345.67")!.formatted(.currency(code: "EUR"))
0.8567.formatted(.percent.precision(.fractionLength(1)))
```

Confirm the percent input contract: floating-point `.percent` commonly treats `0.85` as 85%, while integer `42.formatted(.percent)` displays 42%.

## Dates

```swift
let now = Date.now
now.formatted(.dateTime.weekday(.wide).month(.wide).day())
now.formatted(date: .long, time: .shortened)
now.formatted(.iso8601)

let yesterday = Calendar.current.date(byAdding: .day, value: -1, to: now)!
yesterday.formatted(.relative(presentation: .named))
(start..<end).formatted(.interval.month().day().hour().minute())
(start..<end).formatted(.components(style: .wide, fields: [.day, .hour]))
```

Use `Date.AnchoredRelativeFormatStyle` on iOS 18+ when the anchor must be fixed rather than `Date.now`. Preview relative output as standalone text; embedding it can produce ungrammatical localized sentences.

Docs: [Date.FormatStyle](https://sosumi.ai/documentation/foundation/date/formatstyle) · [Date.RelativeFormatStyle](https://sosumi.ai/documentation/foundation/date/relativeformatstyle) · [Date.IntervalFormatStyle](https://sosumi.ai/documentation/foundation/date/intervalformatstyle)

## Durations

```swift
let duration = Duration.seconds(3661)

duration.formatted(.time(pattern: .hourMinuteSecond))
Duration.seconds(3.75).formatted(
    .time(pattern: .minuteSecond(padMinuteToLength: 2, fractionalSecondsLength: 2))
)
duration.formatted(
    .units(allowed: [.hours, .minutes, .seconds], width: .abbreviated,
           maximumUnitCount: 2)
)
```

Use `.time(pattern:)` for separator-based clock output and `.units(allowed:width:)` for labeled prose. Both require iOS 16+.

## Measurements and Names

```swift
let temperature = Measurement(value: 72, unit: UnitTemperature.fahrenheit)
temperature.formatted(.measurement(width: .abbreviated))

let distance = Measurement(value: 5, unit: UnitLength.kilometers)
distance.formatted(.measurement(width: .abbreviated, usage: .road))

var name = PersonNameComponents()
name.givenName = "Thomas"
name.familyName = "Clark"
name.nickname = "Tom"
name.formatted(.name(style: .short))
```

Do not manually concatenate person names. Style resolution accounts for script, user preferences, locale, and requested style.

## Lists and Byte Counts

```swift
["Alice", "Bob", "Charlie"].formatted(.list(type: .and))
[1, 2, 3].formatted(.list(memberStyle: .number, type: .or))
Int64(1_048_576).formatted(.byteCount(style: .memory))
Int64(1_048_576).formatted(.byteCount(style: .binary))
```

## URLs

`URL.FormatStyle` requires iOS 16+. Scheme, host, and path are the normal display surface; port, query, and fragment are opt-in.

```swift
let url = URL(string: "https://www.example.com:8080/path?q=1#section")!
url.formatted(.url.scheme(.never).host().path())
url.formatted(.url.scheme(.never).host().path().port(.always).query(.always))
url.formatted(.url.scheme(.never).host().path().fragment(.always))
```

Treat this as display formatting, not URL sanitization or a security boundary.
