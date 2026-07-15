---
name: app-intents
description: "Implement App Intents for Siri, Shortcuts, Spotlight, widgets, Control Center, and Apple Intelligence on iOS. Covers AppIntent actions, AppEntity and EntityQuery models, AppShortcutsProvider phrases, IndexedEntity Spotlight indexing, WidgetConfigurationIntent, SnippetIntent, and assistant schemas. Use when exposing app actions or entities to system surfaces."
---

# App Intents (iOS 26+)

Implement, review, and extend App Intents to expose app functionality to Siri,
Shortcuts, Spotlight, widgets, Control Center, and Apple Intelligence.

## Contents

- [Triage Workflow](#triage-workflow)
- [AppIntent Protocol](#appintent-protocol)
- [`@Parameter`](#parameter)
- [AppEntity](#appentity)
- [EntityQuery (4 Variants)](#entityquery-4-variants)
- [AppEnum](#appenum)
- [AppShortcutsProvider](#appshortcutsprovider)
- [System Surface Integration](#system-surface-integration)
- [iOS 26 Additions](#ios-26-additions)
- [Common Mistakes](#common-mistakes)
- [Review Checklist](#review-checklist)
- [References](#references)

## Triage Workflow

### Step 1: Choose the action, boundary, and surface

Start from 1-3 valuable actions people want outside the app, not from its screen hierarchy. Record one design row per action: user goal; inline result or app destination; shared domain operation; parameters and entity query; confirmation/authentication; target surface and protocol. Use one explicit runtime route for app handoff instead of scattering navigation side effects through intents.

Then choose the system feature and protocol that fit that action:

| Surface | Protocol | Since |
|---|---|---|
| Siri / Shortcuts | `AppIntent` | iOS 16 |
| Configurable widget | `WidgetConfigurationIntent` | iOS 17 |
| Control Center | `ControlConfigurationIntent` | iOS 18 |
| Spotlight search | `IndexedEntity` | iOS 18 |
| Apple Intelligence | `@AppIntent(schema:)` | iOS 18 |
| Interactive snippets | `SnippetIntent` | iOS 26 |
| Visual Intelligence | `IntentValueQuery` | iOS 26 |

### Step 2: Define the data model

- Prefer `AppEntity` shadow models for app data exposed to the system.
- Create `AppEnum` types for fixed parameter choices.
- Choose the right `EntityQuery` variant for resolution.
- Mark searchable entities with `IndexedEntity` and `indexingKey` metadata.

### Step 3: Implement the intent

- Conform to `AppIntent` (or a specialized sub-protocol).
- Declare `@Parameter` properties for all user-facing inputs.
- Implement `perform() async throws -> some IntentResult`.
- Add `parameterSummary` for Shortcuts UI.
- Register phrases via `AppShortcutsProvider`.

### Step 4: Verify

- Build and run in the target system surface to confirm discovery, parameter resolution, cancellation, confirmation, authentication, result rendering, and app handoff.
- If a step fails, reset the fixture, fix the smallest intent/entity/query boundary, and rerun the same action from the same surface before adding another action.
- Test Siri phrases with the intent preview in Xcode.
- Confirm `IndexedEntity` instances are indexed in a named Spotlight index.
- Check widget configuration for `WidgetConfigurationIntent` intents.

## AppIntent Protocol

The system instantiates the struct via `init()`, sets parameters, then calls
`perform()`. Declare a `title` and `parameterSummary` for Shortcuts UI.

```swift
struct OrderSoupIntent: AppIntent {
    static var title: LocalizedStringResource = "Order Soup"
    static var description = IntentDescription("Place a soup order.")

    @Parameter(title: "Soup") var soup: SoupEntity
    @Parameter(title: "Quantity", default: 1) var quantity: Int

    static var parameterSummary: some ParameterSummary {
        Summary("Order \(\.$soup)") { \.$quantity }
    }

    func perform() async throws -> some IntentResult {
        try await OrderService.shared.place(soup: soup.id, quantity: quantity)
        return .result(dialog: "Ordered \(quantity) \(soup.name).")
    }
}
```

Optional members: `description` (`IntentDescription`), `openAppWhenRun` (`Bool`),
`isDiscoverable` (`Bool`), `authenticationPolicy` (`IntentAuthenticationPolicy`).

## `@Parameter`

Declare each user-facing input with `@Parameter`. Non-optional parameters are
required; the system requests values when needed. Defaults pre-fill a useful
value. Optional parameters are not requested automatically, so ask for them in
`perform()` when the intent cannot continue without a value.

```swift
// Required; the system asks for a value when needed
@Parameter(title: "Count")
var count: Int

// Required and pre-filled
@Parameter(title: "Count", default: 1)
var count: Int

// Optional; request it yourself if it becomes necessary
@Parameter(title: "Count")
var count: Int?
```

### Supported value types

Primitives: `Bool`, `Int`, `Double`, `String`, `Duration`, `Date`, `Decimal`,
`Measurement`, and `URL`. Collections: `Array` and `Set` of supported element
types. Framework: `IntentPerson`, `IntentFile`. Custom: any `AppEntity` or
`AppEnum`.

### Common initializer patterns

```swift
// Basic
@Parameter(title: "Name")
var name: String

// With default
@Parameter(title: "Count", default: 5)
var count: Int

// Numeric slider
@Parameter(title: "Volume", controlStyle: .slider, inclusiveRange: (0, 100))
var volume: Int

// Options provider (dynamic list)
@Parameter(title: "Category", optionsProvider: CategoryOptionsProvider())
var category: Category

// File with content types
@Parameter(title: "Document", supportedContentTypes: [.pdf, .plainText])
var document: IntentFile

// Measurement with unit
@Parameter(title: "Distance", defaultUnit: .miles, supportsNegativeNumbers: false)
var distance: Measurement<UnitLength>
```

See [references/appintents-advanced.md](references/appintents-advanced.md) for all initializer variants.

## AppEntity

Prefer shadow models that mirror app data and expose only system-facing fields.
Direct model conformance is allowed when the model is lightweight, stable, and
appropriate for App Intents lifecycles.

```swift
struct SoupEntity: AppEntity {
    static let defaultQuery = SoupEntityQuery()
    static var typeDisplayRepresentation: TypeDisplayRepresentation = "Soup"
    var id: String

    @Property(title: "Name") var name: String
    @Property(title: "Price") var price: Double

    var displayRepresentation: DisplayRepresentation {
        DisplayRepresentation(title: "\(name)", subtitle: "$\(String(format: "%.2f", price))")
    }

    init(from soup: Soup) {
        self.id = soup.id; self.name = soup.name; self.price = soup.price
    }
}
```

Required: `id`, `defaultQuery` (static), `displayRepresentation`,
`typeDisplayRepresentation` (static). Mark properties with `@Property(title:)`
to expose for filtering/sorting. Properties without `@Property` remain internal.

## EntityQuery (4 Variants)

### 1. EntityQuery (base -- resolve by ID)

```swift
struct SoupEntityQuery: EntityQuery {
    func entities(for identifiers: [String]) async throws -> [SoupEntity] {
        SoupStore.shared.soups.filter { identifiers.contains($0.id) }.map { SoupEntity(from: $0) }
    }
    func suggestedEntities() async throws -> [SoupEntity] {
        SoupStore.shared.featured.map { SoupEntity(from: $0) }
    }
}
```

### 2. EntityStringQuery (free-text search)

```swift
struct SoupStringQuery: EntityStringQuery {
    func entities(matching string: String) async throws -> [SoupEntity] {
        SoupStore.shared.search(string).map { SoupEntity(from: $0) }
    }
    func entities(for identifiers: [String]) async throws -> [SoupEntity] {
        SoupStore.shared.soups.filter { identifiers.contains($0.id) }.map { SoupEntity(from: $0) }
    }
}
```

### 3. EnumerableEntityQuery (finite set)

```swift
struct AllSoupsQuery: EnumerableEntityQuery {
    func allEntities() async throws -> [SoupEntity] {
        SoupStore.shared.allSoups.map { SoupEntity(from: $0) }
    }
    func entities(for identifiers: [String]) async throws -> [SoupEntity] {
        SoupStore.shared.soups.filter { identifiers.contains($0.id) }.map { SoupEntity(from: $0) }
    }
}
```

### 4. UniqueAppEntityQuery (singleton, iOS 18+)

Use for single-instance entities like app settings.

```swift
struct AppSettingsEntity: UniqueAppEntity {
    static let defaultQuery = AppSettingsQuery()
    static var typeDisplayRepresentation: TypeDisplayRepresentation = "Settings"
    var displayRepresentation: DisplayRepresentation { "App Settings" }

    var id: String { "app-settings" }
}

struct AppSettingsQuery: UniqueAppEntityQuery {
    func uniqueEntity() async throws -> AppSettingsEntity {
        AppSettingsEntity()
    }
}
```

See [references/appintents-advanced.md](references/appintents-advanced.md) for `EntityPropertyQuery` with
filter/sort support.

When one parameter determines another parameter's valid entity choices, use
`@IntentParameterDependency` in the query or options provider. The advanced
reference covers the nil-upstream case and intentional defaults.

## AppEnum

Define fixed sets of selectable values. `RawValue` must conform to
`LosslessStringConvertible`; prefer `String` raw values for readable, stable
identifiers.

```swift
enum SoupSize: String, AppEnum {
    case small, medium, large

    static var typeDisplayRepresentation: TypeDisplayRepresentation = "Size"

    static var caseDisplayRepresentations: [SoupSize: DisplayRepresentation] = [
        .small: "Small",
        .medium: "Medium",
        .large: "Large"
    ]
}
```

```swift
// Valid, but less readable in saved shortcuts and URL representations
enum Priority: Int, AppEnum {
    case low = 1, medium = 2, high = 3
}

// Preferred
enum Priority: String, AppEnum {
    case low, medium, high
    // ...
}
```

## AppShortcutsProvider

Register pre-built shortcuts that appear in Siri and the Shortcuts app without
user configuration.

```swift
struct MyAppShortcuts: AppShortcutsProvider {
    static var appShortcuts: [AppShortcut] {
        AppShortcut(
            intent: OrderSoupIntent(),
            phrases: [
                "Order \(\.$soup) in \(.applicationName)",
                "Get soup from \(.applicationName)"
            ],
            shortTitle: "Order Soup",
            systemImageName: "cup.and.saucer"
        )
    }

    static var shortcutTileColor: ShortcutTileColor = .navy
}
```

### Phrase rules

- Every phrase MUST include `\(.applicationName)`.
- Phrases can reference parameters: `\(\.$soup)`.
- Call `updateAppShortcutParameters()` when dynamic option values change.
- Use `negativePhrases` to prevent false Siri activations.

## System Surface Integration

Read [references/system-surfaces.md](references/system-surfaces.md) when
implementing Siri donation/prediction, interactive widgets, Control Center
configuration/action separation, or Spotlight `IndexedEntity` indexing.

## iOS 26 Additions

### SnippetIntent

Display interactive snippets in system UI:

```swift
struct OrderStatusSnippet: SnippetIntent {
    static var title: LocalizedStringResource = "Order Status"
    func perform() async throws -> some IntentResult & ShowsSnippetView {
        let status = await OrderTracker.currentStatus()
        return .result(view: OrderStatusSnippetView(status: status))
    }
}

struct CheckOrderStatusIntent: AppIntent {
    static var title: LocalizedStringResource = "Check Order Status"
    func perform() async throws -> some IntentResult & ShowsSnippetIntent {
        .result(snippetIntent: OrderStatusSnippet())
    }
}
```

The system may call `perform()` multiple times, including after snippet button
or toggle actions; keep `SnippetIntent.perform()` side-effect-free and do
mutations in the calling action intent or a separate button/toggle action. A
snippet-only intent is not discoverable in Shortcuts or Spotlight unless
`isDiscoverable` is `true`.

### IntentValueQuery (Visual Intelligence)

```swift
@available(iOS 26, *)
@UnionValue
enum ShoppingVisualResult {
    case product(ProductEntity)
    case store(StoreEntity)
}

@available(iOS 26, *)
struct ShoppingVisualQuery: IntentValueQuery {
    func values(for input: SemanticContentDescriptor) async throws -> [ShoppingVisualResult] {
        try Task.checkCancellation()
        async let productMatches = ProductStore.shared.matches(
            labels: input.labels,
            pixelBuffer: input.pixelBuffer,
            limit: 5
        )
        async let storeMatches = StoreStore.shared.matches(
            labels: input.labels,
            pixelBuffer: input.pixelBuffer,
            limit: 3
        )
        let ranked = await rank(productMatches, storeMatches)
        return Array(ranked.prefix(8))
    }
}
```

Only one `IntentValueQuery` can take `SemanticContentDescriptor`; use
`@UnionValue` when one query must return multiple app entity types. Treat
`labels` as high-level English descriptors, not exhaustive synonyms or app
taxonomy; combine them with `pixelBuffer` when available. Return small, ranked,
cancellation-friendly results, and provide an `OpenIntent`, URL representation,
or in-app search handoff for details and more results. Do not implement camera
capture, Vision `VN*` requests, barcode classification, or Spotlight indexing
inside the App Intents query; call an existing bounded app search or image-match
service instead, with explicit result caps and timeouts when work may exceed a
system UI budget.

## Common Mistakes

1. **Exposing too much app model state through AppEntity.** Prefer dedicated
   shadow models with stable persistent IDs and only system-facing properties.

2. **Missing `\(.applicationName)` in phrases.** Every `AppShortcut` phrase
   MUST include the application name token. Siri uses it for disambiguation.

3. **Treating optional `@Parameter` as required.** Optional parameters are not
   requested automatically; call `requestValue` / `needsValueError` when the
   intent cannot proceed without one.

   ```swift
   // Optional, so request it yourself if needed
   @Parameter(title: "Count")
   var count: Int?
   ```

4. **Using unstable AppEnum raw values.** `Int` is valid, but `String` raw values
   are usually clearer for persistence and URL representations.

5. **Forgetting `suggestedEntities()`.** Without it, the Shortcuts picker shows no defaults.
6. **Throwing for missing entities in `entities(for:)`.** Omit missing entities instead.
7. **Stale Spotlight index.** Re-index entities with a named `CSSearchableIndex`.
8. **Missing `typeDisplayRepresentation`.** Both `AppEntity` and `AppEnum` require it.
9. **Using deprecated `@Assistant*` schema macros.** Use `@AppIntent(schema:)`, `@AppEntity(schema:)`, and `@AppEnum(schema:)`.
10. **Blocking or side-effecting perform().** Use `await` for I/O; keep `SnippetIntent.perform()` side-effect-free because the system may rerun it.
11. **Mutating sensitive state from system surfaces without a guard.** Use confirmation and/or authentication for actions such as door locks, lights, purchases, and deletes.

## Review Checklist

- [ ] Every `AppIntent` has a descriptive `title` (verb + noun, title case)
- [ ] Required `@Parameter` values are non-optional; optional values are requested when needed
- [ ] `AppEntity` types expose stable IDs and only system-facing properties
- [ ] `AppEntity` has `displayRepresentation` and `typeDisplayRepresentation`
- [ ] `EntityQuery.entities(for:)` omits missing IDs; `suggestedEntities()` implemented
- [ ] Dependent options use `@IntentParameterDependency`; `defaultResult()` is present only when a genuinely useful default exists
- [ ] `AppEnum` prefers stable `String` raw values with `caseDisplayRepresentations`
- [ ] `AppShortcutsProvider` phrases include `\(.applicationName)`; `parameterSummary` defined
- [ ] `IndexedEntity` properties use key-path `indexingKey` values and entities are indexed
- [ ] Control Center intents conform to `ControlConfigurationIntent`; widget intents to `WidgetConfigurationIntent`; no-default control parameters are optional
- [ ] Sensitive App Intents request confirmation and/or authentication before mutating state
- [ ] Visual Intelligence `IntentValueQuery` uses `SemanticContentDescriptor`, bounded results, opening paths, and iOS 26 availability
- [ ] No deprecated `@AssistantIntent` / `@AssistantEntity` / `@AssistantEnum` schema macros
- [ ] `perform()` uses async/await (no blocking); runs in expected isolation context; intent types are `Sendable`

## References

- Read [references/system-surfaces.md](references/system-surfaces.md) for Siri, widgets, Control Center, and Spotlight integration patterns.
- See [references/appintents-advanced.md](references/appintents-advanced.md) for `@Parameter` variants, EntityPropertyQuery, assistant schemas, focus filters, SiriKit migration, error handling, confirmation flows, authentication, URL-representable types, and Spotlight indexing details.
