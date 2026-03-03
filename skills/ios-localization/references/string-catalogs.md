# String Catalogs (.xcstrings) -- Detailed Reference

## What is a String Catalog?

A String Catalog is a single `.xcstrings` file (JSON-based) that holds every localizable string in a target, along with all translations, plural forms, and device variations. It replaces the combination of `.strings` and `.stringsdict` files that previously required manual synchronization.

**Availability:** Xcode 15+, all Apple platforms.

## Creating a String Catalog

1. File > New > File > String Catalog
2. Name it `Localizable.xcstrings` (the default table name, matching the legacy `Localizable.strings`)
3. Place it in the target's source directory
4. Add target languages in Project > Info > Localizations

For a non-default table name (e.g., `Onboarding.xcstrings`), reference it explicitly:

```swift
String(localized: "welcome.title", table: "Onboarding")
```

## Automatic String Extraction

On every build, Xcode scans source files and extracts strings from known localizable initializers. Extraction is compiler-driven -- it recognizes these patterns:

### SwiftUI (LocalizedStringKey)
```swift
Text("Hello, world")                        // extracted
Label("Settings", systemImage: "gear")      // extracted
Button("Save") { }                          // extracted
Toggle("Enable notifications", isOn: $on)   // extracted
NavigationTitle("Home")                      // extracted
Section("Account") { }                      // extracted

// NOT extracted -- computed or variable strings
Text(viewModel.title)                       // not extracted (runtime value)
Text(verbatim: "v1.2.3")                    // not extracted (verbatim skips localization)
```

### Foundation (String(localized:))
```swift
String(localized: "No results found")               // extracted
String(localized: "error.title",
       defaultValue: "Something went wrong",
       comment: "Generic error alert title")         // extracted with default + comment
```

### LocalizedStringResource
```swift
LocalizedStringResource("Order placed")              // extracted
static var title: LocalizedStringResource = "Title"  // extracted
```

### What is NOT extracted
```swift
let x: String = "Not localized"          // plain String assignment
print("debug info")                      // not user-facing
NSLocalizedString("legacy", comment: "") // NOT auto-extracted into .xcstrings
```

If automatic extraction misses a string, add it manually in the String Catalog editor.

## Manual Key Management

Open the `.xcstrings` file in Xcode to use the visual editor:

- **Add key**: Click + at the bottom of the key list
- **Remove key**: Select key, press Delete (marks as Stale, removed on next build if no code reference)
- **Edit comment**: Select key, edit the Comment field (provides translator context)
- **Mark state**: Right-click a translation to set Needs Review / Reviewed
- **Vary by plural**: Select a key, click Vary > Plural to add plural categories
- **Vary by device**: Select a key, click Vary > Device to add iPhone/iPad/Mac variants

### Key naming conventions

Use structured key names for large projects:

```
onboarding.welcome.title        -> "Welcome"
onboarding.welcome.subtitle     -> "Get started in minutes"
settings.notifications.toggle   -> "Enable Notifications"
error.network.title             -> "Connection Error"
error.network.message           -> "Check your internet and try again"
```

For SwiftUI, the literal text IS the key by default. Use `String(localized:defaultValue:)` when you want a structured key that differs from the English text.

## Handling Strings in Non-SwiftUI Code

### View models, services, and utilities

```swift
class OrderService {
    func statusMessage(for order: Order) -> String {
        switch order.status {
        case .shipped:
            return String(localized: "order.status.shipped",
                          defaultValue: "Your order has shipped!",
                          comment: "Order status when item is in transit")
        case .delivered:
            return String(localized: "order.status.delivered",
                          defaultValue: "Delivered on \(order.deliveryDate!, format: .dateTime.month().day())",
                          comment: "Order status with delivery date")
        case .processing:
            return String(localized: "order.status.processing",
                          defaultValue: "Processing your order...",
                          comment: "Order status while being prepared")
        }
    }
}
```

### Specifying table and bundle

```swift
// From a specific table
String(localized: "greeting",
       table: "Onboarding",
       comment: "First-launch greeting")

// From a specific bundle (framework or Swift package)
String(localized: "button.save",
       table: "SharedUI",
       bundle: .module,
       comment: "Save button in shared component")
```

## Bundle Access Patterns

### Main app
```swift
// Uses Bundle.main by default -- no bundle argument needed
String(localized: "Hello")
```

### Swift Package (SPM)
```swift
// .module refers to the package's resource bundle
String(localized: "Hello", bundle: .module)

// In SwiftUI, Text uses the module's bundle automatically
// if the .xcstrings file is in the package's resources
Text("Hello")  // looks up in the package's Localizable.xcstrings
```

### Framework
```swift
// Reference the framework's bundle
let frameworkBundle = Bundle(for: MyFrameworkClass.self)
String(localized: "Hello",
       bundle: .init(frameworkBundle.bundleURL))
```

## Multi-Module / SPM Localization

Each Swift package target that contains user-facing strings needs its own String Catalog.

### Package.swift setup
```swift
.target(
    name: "SharedUI",
    dependencies: [],
    resources: [
        .process("Resources")  // Localizable.xcstrings goes here
    ]
)
```

### Directory structure
```
Sources/
  SharedUI/
    Resources/
      Localizable.xcstrings    <- String Catalog for this module
    Views/
      ButtonStyles.swift
```

### Accessing strings from the package
```swift
// Inside the package -- .module resolves automatically
public struct SaveButton: View {
    public var body: some View {
        Button(String(localized: "Save", bundle: .module)) { }
    }
}
```

**Important:** SwiftUI `Text("Save")` inside an SPM target looks up in `.module` automatically only if the `.xcstrings` file is properly included in the target's resources. Verify by checking that Xcode shows the file under the target in the project navigator.

## Pluralization in String Catalogs

### Setup

1. Write code with integer interpolation:
   ```swift
   Text("\(itemCount) items in your cart")
   ```
2. Build the project -- Xcode adds the key to the String Catalog
3. Open the String Catalog, select the key
4. Click "Vary by Plural" in the inspector
5. Fill in plural forms for each language

### English plural forms
```
one:   "%lld item in your cart"
other: "%lld items in your cart"
```

### Arabic plural forms (all six categories)
```
zero:  "لا توجد عناصر في سلتك"
one:   "عنصر واحد في سلتك"
two:   "عنصران في سلتك"
few:   "%lld عناصر في سلتك"        (3-10)
many:  "%lld عنصرًا في سلتك"       (11-99)
other: "%lld عنصر في سلتك"         (100+)
```

### Multiple plural variables

When a string has two integer interpolations, the String Catalog shows a matrix of plural combinations:

```swift
Text("\(photoCount) photos in \(albumCount) albums")
// English needs: one/one, one/other, other/one, other/other
```

## Device Variations

Enable "Vary by Device" for a key to provide different text on iPhone, iPad, Apple Watch, Mac, Apple TV, and Apple Vision Pro.

```swift
// Code is the same everywhere:
Text("Tap to continue")

// String Catalog provides:
// iPhone: "Tap to continue"
// iPad:   "Tap or click to continue"
// Mac:    "Click to continue"
// Vision: "Look and tap to continue"
```

## Exporting for Translators (XLIFF / xcloc)

### Export

1. Product > Export Localizations... (or `xcodebuild -exportLocalizations`)
2. Select target languages
3. Xcode creates `.xcloc` bundles (one per language)
4. Send `.xcloc` files to translators (they contain XLIFF 1.2 inside)

### Command-line export
```bash
xcodebuild -exportLocalizations \
    -project MyApp.xcodeproj \
    -localizationPath ./Localizations \
    -exportLanguage de -exportLanguage ja -exportLanguage ar
```

### Import

1. Product > Import Localizations...
2. Select the completed `.xcloc` file
3. Xcode merges translations into the String Catalog
4. Review changes in the diff viewer

### Command-line import
```bash
xcodebuild -importLocalizations \
    -project MyApp.xcodeproj \
    -localizationPath ./Localizations/de.xcloc
```

## String Catalog JSON Structure

The `.xcstrings` file is JSON. Understanding the structure enables programmatic manipulation (CI validation, batch updates, translation memory integration).

```json
{
  "sourceLanguage": "en",
  "version": "1.0",
  "strings": {
    "Welcome, %@!": {
      "comment": "Greeting shown on home screen with user name",
      "localizations": {
        "en": {
          "stringUnit": {
            "state": "translated",
            "value": "Welcome, %@!"
          }
        },
        "de": {
          "stringUnit": {
            "state": "translated",
            "value": "Willkommen, %@!"
          }
        }
      }
    },
    "%lld items": {
      "localizations": {
        "en": {
          "variations": {
            "plural": {
              "one": {
                "stringUnit": {
                  "state": "translated",
                  "value": "%lld item"
                }
              },
              "other": {
                "stringUnit": {
                  "state": "translated",
                  "value": "%lld items"
                }
              }
            }
          }
        }
      }
    }
  }
}
```

### Translation states
- `"new"` -- Xcode extracted the key but no translation exists
- `"translated"` -- Translation provided
- `"needs_review"` -- Marked for review (source string changed or manual flag)
- `"stale"` -- Key no longer found in code (removed on next clean build)

## Testing Strategies

### Scheme language override

Edit Scheme > Run > Options > App Language. Choose any added language to launch the app in that locale without changing the device/simulator system language.

### Pseudolocalization options

Xcode provides built-in pseudolocalization modes (Edit Scheme > Run > Options > App Language):

| Option | Effect | Catches |
|--------|--------|---------|
| Accented Pseudolanguage | Adds accents: "Hello" -> "[Hellо]" | Hardcoded strings (unlocalized text is obvious) |
| Right-to-Left Pseudolanguage | Forces RTL layout | Layout mirroring bugs |
| Double-Length Pseudolanguage | Doubles all strings | Truncation and overflow |
| Bounded String Pseudolanguage | Wraps strings in brackets | Missing localizations |

### UI tests with locale override

```swift
func testGermanLayout() {
    let app = XCUIApplication()
    app.launchArguments += ["-AppleLanguages", "(de)"]
    app.launchArguments += ["-AppleLocale", "de_DE"]
    app.launch()

    // Verify no truncation on key screens
    let saveButton = app.buttons["Speichern"]
    XCTAssertTrue(saveButton.exists)
    XCTAssertTrue(saveButton.isHittable)
}
```

### Snapshot testing per locale

Use a snapshot testing library to capture screenshots in multiple locales and compare them for layout regressions:

```swift
let locales = ["en_US", "de_DE", "ar_SA", "ja_JP"]
for locale in locales {
    app.launchArguments = ["-AppleLanguages", "(\(locale.prefix(2)))"]
    app.launch()
    // Capture and compare snapshot
}
```

### Translation coverage validation

Check that all keys are translated before release:

```bash
# Parse the .xcstrings JSON and check for "new" or empty states
python3 -c "
import json, sys
with open('Localizable.xcstrings') as f:
    data = json.load(f)
missing = []
for key, info in data['strings'].items():
    for lang, loc in info.get('localizations', {}).items():
        unit = loc.get('stringUnit', {})
        if unit.get('state') in ('new', None) or not unit.get('value'):
            missing.append(f'{lang}: {key}')
if missing:
    print('Missing translations:')
    for m in missing: print(f'  {m}')
    sys.exit(1)
print('All translations complete.')
"
```

## Migration from .strings / .stringsdict

### Automatic migration

1. Select the `.strings` file in the project navigator
2. Right-click > Migrate to String Catalog...
3. Xcode creates a `.xcstrings` file with all existing keys and translations
4. Verify in the String Catalog editor
5. Remove the old `.strings` / `.stringsdict` files from the target

### Manual migration

If automatic migration fails (complex bundle setups, CocoaPods):

1. Create a new `Localizable.xcstrings`
2. Build to extract keys from code
3. Copy translations from old `.strings` files into the String Catalog editor
4. Copy plural rules from `.stringsdict` into plural variants
5. Remove old files

### Migration checklist

- [ ] All `.strings` keys present in the new String Catalog
- [ ] All `.stringsdict` plural rules converted to String Catalog plural variants
- [ ] Bundle references updated (if custom bundle was used)
- [ ] Build succeeds with no missing-localization warnings
- [ ] Test every language the app supports
- [ ] Remove old `.strings` and `.stringsdict` files from the target
- [ ] Commit the `.xcstrings` file (it is JSON, diffs well in version control)

### Coexistence

String Catalogs and `.strings` files can coexist in the same target during migration. Xcode resolves keys from the String Catalog first, then falls back to `.strings`. Remove legacy files after verifying the migration.

## Best Practices

1. **One String Catalog per target** -- keep `Localizable.xcstrings` as the single source of truth for each target.
2. **Use comments** -- provide context for every ambiguous key. Translators cannot see your UI.
3. **Review extraction on every build** -- new keys appear with state "new". Translate them promptly.
4. **Version control the .xcstrings file** -- it is JSON and diffs clearly. Review translation changes in PRs.
5. **Automate coverage checks** -- integrate translation-coverage validation in CI to catch missing translations before release.
6. **Export regularly** -- send updated `.xcloc` bundles to translators after each sprint or feature merge.
7. **Test with pseudolocalizations in CI** -- run UI tests with double-length and RTL pseudo-languages to catch layout issues early.
