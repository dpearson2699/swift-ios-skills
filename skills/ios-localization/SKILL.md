---
name: ios-localization
description: "Implement, review, or improve localization and internationalization in iOS/macOS apps — String Catalogs (.xcstrings), generated localizable symbols, stable key naming, LocalizedStringKey, LocalizedStringResource, pluralization, FormatStyle for numbers/dates/measurements, right-to-left layout, Dynamic Type, and locale-aware formatting. Use when adding multi-language support, setting up String Catalogs, enabling generated symbols for compile-time-safe localization keys, handling plural forms, formatting dates/numbers/currencies for different locales, testing localizations, or making UI work correctly in RTL languages like Arabic and Hebrew."
---

# iOS Localization & Internationalization

Localize Apple-platform apps with String Catalogs, modern string types,
locale-aware formatting, and right-to-left layout.

## Contents

- [String Catalogs and Generated Symbols](#string-catalogs-and-generated-symbols)
- [String Types -- Decision Guide](#string-types-decision-guide)
- [String Interpolation in Localized Strings](#string-interpolation-in-localized-strings)
- [Pluralization](#pluralization)
- [FormatStyle -- Locale-Aware Formatting](#formatstyle-locale-aware-formatting)
- [Right-to-Left (RTL) Layout](#right-to-left-rtl-layout)
- [Common Mistakes](#common-mistakes)
- [Localization Review Checklist](#review-checklist)
- [References](#references)

## String Catalogs and Generated Symbols

String Catalogs are the recommended Xcode 15+ workflow for new localization work. They keep localizable strings, pluralization rules, and device variations together in an Xcode-managed JSON file with a visual editor. Legacy `.strings` and `.stringsdict` files can coexist during migration, but new Swift and SwiftUI code should default to String Catalogs.

**How automatic extraction works:**

Xcode scans for these patterns on each build:

```swift
// SwiftUI -- automatically extracted (LocalizedStringKey)
Text("Welcome back")              // key: "Welcome back"
Label("Settings", systemImage: "gear")
Button("Save") { }
Toggle("Dark Mode", isOn: $dark)

// Programmatic -- automatically extracted
String(localized: "No items found")
LocalizedStringResource("Order placed")

// NOT extracted -- plain String, not localized
let msg = "Hello"                 // just a String, invisible to Xcode
```

Xcode adds discovered keys to the String Catalog automatically. Mark translations as Needs Review, Translated, or Stale in the editor.

For detailed String Catalog workflows, migration, and testing strategies, see [references/string-catalogs.md](references/string-catalogs.md).

Generated symbols are an Xcode 26 typed-access layer on top of String Catalogs;
they do not change the catalog's Xcode 15 availability.

**Enable:** Build Settings > Localization > Generate String Catalog Symbols → `Yes` (on by default in new Xcode 26 projects). Requires catalog format version `1.1`.

**Workflow:** Add a key manually via the (+) button in the String Catalog editor — manual keys have the **Generate Swift Symbol** checkbox enabled by default. Auto-extracted keys can also opt in via Refactor > Convert Strings to Symbols. Use stable manual keys for generated-symbol strings. Avoid source-copy-derived keys for API-facing strings because wording edits can rename generated identifiers and churn call sites.

```swift
// Generated from key "room_available" in Localizable.xcstrings
Text(.roomAvailable)

// Parameterized key "landmarks_count" with %1$(count)lld
Text(.landmarksCount(count: 42))

// Non-default table "Booking.xcstrings"
Text(.Booking.confirmBookingCta)
```

Xcode derives symbol names by camelCasing the key: `settings.notifications.toggle` → `.settingsNotificationsToggle`. You can convert existing extracted strings to symbols via Refactor > Convert Strings to Symbols (reversible).

Generated symbols are `internal`. For cross-module access, create a public wrapper extension. For heavier multi-module setups, use [xcstrings-tool](https://github.com/liamnichols/xcstrings-tool) instead.

For the full generated symbols reference — extraction states, symbol derivation rules, and cross-module patterns — see [references/string-catalogs.md](references/string-catalogs.md).

## String Types -- Decision Guide

### LocalizedStringKey (SwiftUI default)

SwiftUI views accept `LocalizedStringKey` for their text parameters. String literals are implicitly converted -- no extra work needed.

```swift
// These all create a LocalizedStringKey lookup automatically:
Text("Welcome back")
Label("Profile", systemImage: "person")
Button("Delete") { deleteItem() }
.navigationTitle("Home")
```

Use `LocalizedStringKey` when passing strings directly to SwiftUI view initializers. Do not construct `LocalizedStringKey` manually in most cases.

### String(localized:) -- Modern NSLocalizedString replacement

Use for any localized string outside a SwiftUI view initializer. Returns a plain `String`. The literal/interpolated initializer is available iOS 15+; resolving a `LocalizedStringResource` is iOS 16+.

```swift
// Basic
let title = String(localized: "Welcome back")

// With default value (key differs from English text)
let msg = String(localized: "error.network",
                 defaultValue: "Check your internet connection")

// With table and bundle
let label = String(localized: "onboarding.title",
                   table: "Onboarding",
                   bundle: .module)

// With comment for translators
let btn = String(localized: "Save",
                 comment: "Button title to save the current document")
```

For Swift package localization failures, answer with this explicit resource checklist before bundle debugging:
1. `Package.swift` declares `defaultLocalization`.
2. The target `resources` list processes the catalog location, such as `.process("Resources")`.
3. `Localizable.xcstrings` is actually inside that processed target-resource path.
Only after those pass, debug lookup with `bundle: .module` or `Text(..., bundle: .module)`.

Existing `NSLocalizedString` literal keys can still be exported or migrated by Xcode tooling, but new Swift code should prefer `String(localized:)`, SwiftUI literals, `LocalizedStringResource`, or generated symbols.

### LocalizedStringResource -- Pass localization info without resolving

Use when a string must be carried as a localizable value for later resolution, especially for App Intents, widgets, notifications, generated localizable symbols, and system APIs that accept `LocalizedStringResource` directly. Use `String(localized:)` when code needs the resolved string immediately. Available iOS 16+.

```swift
// App Intents require LocalizedStringResource
struct OrderCoffeeIntent: AppIntent {
    static var title: LocalizedStringResource = "Order Coffee"
}

// Widgets
struct MyWidget: Widget {
    var body: some WidgetConfiguration {
        StaticConfiguration(kind: "timer",
                            provider: Provider()) { entry in
            TimerView(entry: entry)
        }
        .configurationDisplayName(LocalizedStringResource("Timer"))
    }
}

// Pass around without resolving yet
func showAlert(title: LocalizedStringResource, message: LocalizedStringResource) {
    // Resolved at display time with the user's current locale
    let resolved = String(localized: title)
}
```

### When to use each type

| Context | Type | Why |
|---------|------|-----|
| SwiftUI view text parameters | `LocalizedStringKey` (implicit) | SwiftUI handles lookup automatically |
| Computed strings in view models / services | `String(localized:)` | Returns resolved `String` for logic |
| App Intents, widgets, system APIs | `LocalizedStringResource` | Framework resolves at display time |
| Error messages shown to users | `String(localized:)` | Resolved in catch blocks |
| Logging / analytics (not user-facing) | Plain `String` | No localization needed |

## String Interpolation in Localized Strings

Interpolated values in localized strings become positional arguments that translators can reorder.

```swift
// English: "Welcome, Alice! You have 3 new messages."
// German:  "Willkommen, Alice! Sie haben 3 neue Nachrichten."
// Japanese: "Alice さん、新しいメッセージが 3 件あります。"
let text = String(localized: "Welcome, \(name)! You have \(count) new messages.")
```

In the String Catalog, this appears with `%@` and `%lld` placeholders that translators can reorder:
- English: `"Welcome, %@! You have %lld new messages."`
- Japanese: `"%@さん、新しいメッセージが%lld件あります。"`

**Type-safe interpolation** (preferred over format specifiers):
```swift
// Interpolation provides type safety
String(localized: "Score: \(score, format: .number)")
String(localized: "Due: \(date, format: .dateTime.month().day())")
```

## Pluralization

String Catalogs handle pluralization natively -- no `.stringsdict` XML required.

### Setup in String Catalog

When a localized string contains an integer interpolation, Xcode detects it and offers plural variants in the String Catalog editor. Supply translations for each CLDR plural category:

| Category | English example | Arabic example |
|----------|----------------|----------------|
| zero | (not used) | 0 items |
| one | 1 item | 1 item |
| two | (not used) | 2 items (dual) |
| few | (not used) | 3-10 items |
| many | (not used) | 11-99 items |
| other | 2+ items | 100+ items |

English uses only `one` and `other`. Arabic uses all six. Always supply `other` as the fallback.

```swift
// Code -- single interpolation triggers plural support
Text("\(unreadCount) unread messages")

// String Catalog entries (English):
//   one:   "%lld unread message"
//   other: "%lld unread messages"
```

### Device Variations

String Catalogs support device-specific text (iPhone vs iPad vs Mac):

```swift
// In String Catalog editor, enable "Vary by Device" for a key
// iPhone: "Tap to continue"
// iPad:   "Tap or click to continue"
// Mac:    "Click to continue"
```

### Grammar Agreement (iOS 15+)

Use Foundation's automatic grammar agreement markup when nearby words must
inflect for a value's number or gender. Preserve the complete inflecting phrase
for translators; see [Automatic Grammar Agreement](https://sosumi.ai/documentation/foundation/automatic-grammar-agreement).

## FormatStyle -- Locale-Aware Formatting

Never hard-code date, number, or measurement formats. Use `FormatStyle` (iOS 15+) so formatting adapts to the user's locale automatically.

Locale-aware formatting matters even in single-language apps because user locale affects separators, calendars, currency, units, names, and list formatting. When giving user-facing formatting advice, explicitly recommend testing or previewing output under multiple locales such as `en_US`, `de_DE`, `ar_SA`, and `ja_JP`.

`ios-localization` owns `FormatStyle` guidance when the issue is locale-aware user-facing display, including numbers, dates, currency, units, names, lists, calendars, separators, and locale preview/testing. For custom `FormatStyle`, `ParseableFormatStyle`, parsing, `Date.IntervalFormatStyle`, `URL.FormatStyle`, or reusable formatter API design, route to `swift-formatstyle`; keep `ios-localization` advice to locale risks and testing unless implementation is explicitly requested.

### Dates

```swift
let now = Date.now

// Preset styles
now.formatted(date: .long, time: .shortened)
// US: "January 15, 2026 at 3:30 PM"
// DE: "15. Januar 2026 um 15:30"
// JP: "2026年1月15日 15:30"

// Component-based
now.formatted(.dateTime.month(.wide).day().year())
// US: "January 15, 2026"

// In SwiftUI
Text(now, format: .dateTime.month().day().year())
```

### Numbers

```swift
let count = 1234567
count.formatted()                     // "1,234,567" (US) / "1.234.567" (DE)
count.formatted(.number.precision(.fractionLength(2)))
count.formatted(.percent)             // For 0.85 -> "85%" (US) / "85 %" (FR)

// Currency
let price = Decimal(29.99)
price.formatted(.currency(code: "USD"))  // "$29.99" (US) / "29,99 $US" (FR)
price.formatted(.currency(code: "EUR"))  // "29,99 EUR" (DE)
```

### Measurements

```swift
let distance = Measurement(value: 5, unit: UnitLength.kilometers)
distance.formatted(.measurement(width: .wide))
// US: "3.1 miles" (auto-converts!) / DE: "5 Kilometer"

let temp = Measurement(value: 22, unit: UnitTemperature.celsius)
temp.formatted(.measurement(width: .abbreviated))
// US: "72 F" (auto-converts!) / FR: "22 C"
```

### Duration, PersonName, Lists

```swift
// Duration
let dur = Duration.seconds(3661)
dur.formatted(.time(pattern: .hourMinuteSecond))  // "1:01:01"

// Person names
let name = PersonNameComponents(givenName: "John", familyName: "Doe")
name.formatted(.name(style: .long))   // "John Doe" (US) / "Doe John" (JP)

// Lists
let items = ["Apples", "Oranges", "Bananas"]
items.formatted(.list(type: .and))    // "Apples, Oranges, and Bananas" (EN)
                                      // "Apples, Oranges et Bananas" (FR)
```

For the complete FormatStyle reference, custom styles, and RTL layout, see [references/formatstyle-locale.md](references/formatstyle-locale.md).

## Right-to-Left (RTL) Layout

SwiftUI automatically mirrors layouts for RTL languages (Arabic, Hebrew, Urdu, Persian). Most views require zero changes.

### What SwiftUI auto-mirrors

- `HStack` children reverse order
- `.leading` / `.trailing` alignment and padding swap sides
- `NavigationStack` back button moves to trailing edge
- `List` disclosure indicators flip
- Text alignment follows reading direction

### What needs manual attention

```swift
// Testing RTL in previews
MyView()
    .environment(\.layoutDirection, .rightToLeft)
    .environment(\.locale, Locale(identifier: "ar"))

// Images that should mirror (directional arrows, progress indicators)
Image(systemName: "chevron.right")
    .flipsForRightToLeftLayoutDirection(true)

// Images that should NOT mirror: logos, photos, clocks, music notes

// Forced LTR for specific content (phone numbers, code)
Text("+1 (555) 123-4567")
    .environment(\.layoutDirection, .leftToRight)
```

### Layout rules

- **DO** use `.leading` / `.trailing` -- they auto-flip for RTL
- **DON'T** use `.left` / `.right` -- they are fixed and break RTL
- **DO** use `HStack` / `VStack` -- they respect layout direction
- **DON'T** use absolute `offset(x:)` for directional positioning

## Common Mistakes

### DON'T: Use NSLocalizedString in new Swift code
```swift
// LEGACY -- Xcode can export literal keys, but new Swift code should use modern APIs
let title = NSLocalizedString("welcome_title", comment: "Welcome screen title")
```

### DO: Use String(localized:) or let SwiftUI handle it
```swift
// CORRECT
let title = String(localized: "welcome_title",
                   defaultValue: "Welcome!",
                   comment: "Welcome screen title")
// Or in SwiftUI, just:
Text("Welcome!")
```

### DON'T: Concatenate localized strings
```swift
// WRONG -- word order varies by language
let greeting = String(localized: "Hello") + ", " + name + "!"
```

### DO: Use string interpolation
```swift
// CORRECT -- translators can reorder placeholders
let greeting = String(localized: "Hello, \(name)!")
```

### DON'T: Hard-code date/number formats
```swift
// WRONG -- US-only format
let formatter = DateFormatter()
formatter.dateFormat = "MM/dd/yyyy"  // Meaningless in most countries
```

### DO: Use FormatStyle
```swift
// CORRECT -- adapts to user locale
Text(date, format: .dateTime.month().day().year())
```

### DON'T: Use fixed-width layouts
```swift
// WRONG -- German text is ~30% longer than English
Text(title).frame(width: 120)
```

### DO: Use flexible layouts
```swift
// CORRECT
Text(title).fixedSize(horizontal: false, vertical: true)
// Or use VStack/wrapping that accommodates expansion
```

### DON'T: Use .left / .right for alignment
```swift
// WRONG -- does not flip for RTL
HStack { Spacer(); text }.padding(.left, 16)
```

### DO: Use .leading / .trailing
```swift
// CORRECT
HStack { Spacer(); text }.padding(.leading, 16)
```

### DON'T: Put user-facing strings as plain String outside SwiftUI
```swift
// WRONG -- not localized
let errorMessage = "Something went wrong"
showAlert(message: errorMessage)
```

### DO: Use LocalizedStringResource for deferred resolution
```swift
// CORRECT
let errorMessage = LocalizedStringResource("Something went wrong")
showAlert(message: String(localized: errorMessage))
```

### DON'T: Use natural-language text as the key for manually-managed strings
```swift
// WRONG -- typo silently creates a new key, stales the old one, no compiler error
Text("Wlecome Back")  // was "Welcome Back" -- silent localization break
```

### DO: Use stable symbol-style keys and enable generated symbols
```swift
// CORRECT -- key is stable; UI text lives in the catalog's default value
Text(.welcomeBack)  // generated from key "welcome_back" in String Catalog
// Or without generated symbols:
String(localized: "welcome_back", defaultValue: "Welcome Back")
```

### DON'T: Skip pseudolocalization testing
Testing only in English hides truncation, layout, and RTL bugs.

### DO: Test with German (long) and Arabic (RTL) at minimum
Use Xcode scheme settings to override the app language without changing device locale.

## Review Checklist

- [ ] All user-facing strings use localization (`LocalizedStringKey` in SwiftUI or `String(localized:)`)
- [ ] No string concatenation for user-visible text
- [ ] Dates and numbers use `FormatStyle`, not hardcoded formats
- [ ] Pluralization handled via String Catalog plural variants (not manual if/else)
- [ ] Layout uses `.leading` / `.trailing`, not `.left` / `.right`
- [ ] UI tested with long text (German) and RTL (Arabic)
- [ ] String Catalog includes all target languages
- [ ] Images needing RTL mirroring use `.flipsForRightToLeftLayoutDirection(true)`
- [ ] App Intents and widgets use `LocalizedStringResource`
- [ ] No `NSLocalizedString` usage in new code
- [ ] Comments provided for ambiguous keys (context for translators)
- [ ] `@ScaledMetric` used for spacing that must scale with Dynamic Type
- [ ] Currency formatting uses explicit currency code, not locale default
- [ ] Pseudolocalization tested (accented, right-to-left, double-length)
- [ ] Manually-managed keys use stable symbol-style names, not English text as the key
- [ ] Generate String Catalog Symbols enabled for targets with manually-managed keys
- [ ] Ensure localized string types are Sendable; use @MainActor for locale-change UI updates

## References

- FormatStyle patterns: [references/formatstyle-locale.md](references/formatstyle-locale.md)
- String Catalogs guide: [references/string-catalogs.md](references/string-catalogs.md)
