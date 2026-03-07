---
name: ios-localization
description: "Implement, review, or improve localization and internationalization in iOS/macOS apps — String Catalogs (.xcstrings), LocalizedStringKey, LocalizedStringResource, pluralization, FormatStyle for numbers/dates/measurements, right-to-left layout, Dynamic Type, and locale-aware formatting. Use when adding multi-language support, setting up String Catalogs, handling plural forms, formatting dates/numbers/currencies for different locales, testing localizations, or making UI work correctly in RTL languages like Arabic and Hebrew."
---

# iOS Localization & Internationalization

Localize iOS 26+ apps using String Catalogs, modern string types, FormatStyle, and RTL-aware layout. Localization mistakes cause App Store rejections in non-English markets, mistranslated UI, and broken layouts. Ship with correct localization from the start.

## String Catalogs (.xcstrings)

String Catalogs replaced `.strings` and `.stringsdict` files starting in Xcode 15 / iOS 17. They unify all localizable strings, pluralization rules, and device variations into a single JSON-based file with a visual editor.

**Why String Catalogs exist:**
- `.strings` files required manual key management and fell out of sync
- `.stringsdict` required complex XML for plurals
- String Catalogs auto-extract strings from code, track translation state, and support plurals natively

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

For detailed String Catalog workflows, migration, and testing strategies, see `references/string-catalogs.md`.

## String Types -- Decision Guide

### LocalizedStringKey (SwiftUI default)

SwiftUI views accept `LocalizedStringKey` for their text parameters. String literals are implicitly converted -- no extra work needed.

```swift
// These all create a LocalizedStringKey lookup automatically:
Text("Welcome back")
Label("Profile", systemImage: "person")
Button("Delete") { deleteItem() }
NavigationTitle("Home")
```

Use `LocalizedStringKey` when passing strings directly to SwiftUI view initializers. Do not construct `LocalizedStringKey` manually in most cases.

### String(localized:) -- Modern NSLocalizedString replacement

Use for any localized string outside a SwiftUI view initializer. Returns a plain `String`. Available iOS 16+.

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

### LocalizedStringResource -- Pass localization info without resolving

Use when you need to pass a localized string to an API that resolves it later (App Intents, widgets, notifications, system frameworks). Available iOS 16+.

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

### Grammar Agreement (iOS 17+)

Use `^[...]` inflection syntax for automatic grammatical agreement:

```swift
// Automatically adjusts for gender/number in supported languages
Text("^[\(count) \("photo")](inflect: true) added")
// English: "1 photo added" / "3 photos added"
// Spanish: "1 foto agregada" / "3 fotos agregadas"
```

## FormatStyle -- Locale-Aware Formatting

Never hard-code date, number, or measurement formats. Use `FormatStyle` (iOS 15+) so formatting adapts to the user's locale automatically.

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

For the complete FormatStyle reference, custom styles, and RTL layout, see `references/formatstyle-locale.md`.

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

### DON'T: Use NSLocalizedString in new code
```swift
// WRONG -- legacy API, verbose, no compiler integration with String Catalogs
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

### DON'T: Skip pseudolocalization testing
Testing only in English hides truncation, layout, and RTL bugs.

### DO: Test with German (long) and Arabic (RTL) at minimum
Use Xcode scheme settings to override the app language without changing device locale.

## Localization Review Checklist

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
- [ ] Ensure localized string types are Sendable; use @MainActor for locale-change UI updates

