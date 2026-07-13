# App Intents Advanced Reference

Extended App Intents patterns beyond the basics covered in the main skill.
Covers `@Parameter` variants, EntityPropertyQuery, assistant schemas, focus
filters, SiriKit migration, error handling, confirmation flows, authentication,
URL-representable types, and Spotlight indexing.

## Contents

- [`@Parameter Initializer Variants`](#parameter-initializer-variants)
- [Dependent Options and Intentional Defaults](#dependent-options-and-intentional-defaults)
- [EntityPropertyQuery (Filter and Sort)](#entitypropertyquery-filter-and-sort)
- [Assistant Schemas (iOS 18+)](#assistant-schemas-ios-18)
- [Focus Filter Intents](#focus-filter-intents)
- [SiriKit Migration (CustomIntentMigratedAppIntent)](#sirikit-migration-customintentmigratedappintent)
- [Error Handling and Dialog](#error-handling-and-dialog)
- [Confirmation Flows](#confirmation-flows)
- [Authentication Policies](#authentication-policies)
- [URLRepresentableIntent / Entity / Enum (iOS 18+)](#urlrepresentableintent-entity-enum-ios-18)
- [IndexedEntity for Spotlight (iOS 18+)](#indexedentity-for-spotlight-ios-18)
- [`@ComputedProperty(indexingKey:) for Spotlight (iOS 26+)`](#computedpropertyindexingkey-for-spotlight-ios-26)
- [Onscreen Content for Siri (iOS 26+)](#onscreen-content-for-siri-ios-26)
- [Parameter Summary Builder](#parameter-summary-builder)
- [Core Spotlight Direct Usage](#core-spotlight-direct-usage)

## `@Parameter` Initializer Variants

### 1. Basic (String, Bool, URL, Date)

```swift
@Parameter(title: "Name")
var name: String

@Parameter(title: "Name", description: "The user's full name")
var name: String

@Parameter(title: "Enabled", default: true)
var enabled: Bool

@Parameter(title: "Website")
var url: URL?
```

### 2. Numeric with Range and Control Style

```swift
@Parameter(title: "Volume", controlStyle: .slider, inclusiveRange: (0.0, 100.0))
var volume: Double

@Parameter(title: "Rating", controlStyle: .stepper, inclusiveRange: (1, 5))
var rating: Int

@Parameter(title: "Temperature", default: 72.0, inclusiveRange: (60.0, 90.0))
var temperature: Double
```

Numeric controls default to `.stepper`. `Int` supports `.stepper` and `.field`;
`Double` also supports `.slider`.

### 3. With Options Provider (Dynamic List)

Provide a dynamic set of options at runtime:

```swift
struct CategoryOptionsProvider: DynamicOptionsProvider {
    func results() async throws -> [String] {
        await CategoryStore.shared.allNames()
    }
}

@Parameter(title: "Category", optionsProvider: CategoryOptionsProvider())
var category: String
```

### 4. With Disambiguation Dialog

Request clarification when the system cannot resolve a value:

```swift
@Parameter(
    title: "Size",
    requestValueDialog: "What size would you like?",
    requestDisambiguationDialog: "Which size did you mean?"
)
var size: CupSize
```

### 5. With Resolvers

Transform raw input into the target type:

```swift
@Parameter(title: "Contact", resolvers: [ContactResolver()])
var contact: ContactEntity
```

### 6. Entity Parameter with Query

Specify one custom query for entity resolution when the entity's `defaultQuery`
is not the right search behavior:

```swift
@Parameter(title: "Trail", query: TrailStringQuery())
var trail: TrailEntity
```

### 7. Array Parameters

Use the current iOS 18+ `size:` overload when the system UI should enforce a
fixed or bounded number of entity values:

```swift
@Parameter(title: "Items", size: .init(exactly: 3))
var items: [ItemEntity]
```

Apple deprecated the original iOS 17 entity-array `size:` overloads, then added
replacement overloads in iOS 18. Do not treat the argument itself as deprecated.
Use `IntentCollectionSize(min:max:)` for a range, or omit `size:` only when the
system UI should allow an unconstrained array.

Validate the count again in `perform()` at the execution boundary:

```swift
guard items.count == 3 else {
    throw $items.needsValueError("Choose exactly three items.")
}
```

Apple references:

- [Current entity-array initializer with `size:` (iOS 18+)](https://sosumi.ai/documentation/appintents/intentparameter/init(title:description:default:size:inputconnectionbehavior:)-7i2i4)
- [`IntentCollectionSize`](https://sosumi.ai/documentation/appintents/intentcollectionsize)

### 8. File Parameters

```swift
@Parameter(title: "Document", supportedContentTypes: [.pdf, .plainText])
var document: IntentFile

@Parameter(title: "Image", supportedContentTypes: [.png, .jpeg])
var image: IntentFile?
```

### 9. Measurement Parameters

```swift
@Parameter(
    title: "Distance",
    defaultUnit: .miles,
    defaultUnitAdjustForLocale: true,
    supportsNegativeNumbers: false
)
var distance: Measurement<UnitLength>

@Parameter(title: "Weight", defaultUnit: .kilograms)
var weight: Measurement<UnitMass>

@Parameter(title: "Temperature", defaultUnit: .fahrenheit)
var temp: Measurement<UnitTemperature>
```

### 10. Input Connection Behavior

Control how parameters connect to Shortcuts input:

```swift
@Parameter(title: "Text", inputConnectionBehavior: .connectToPreviousIntentResult)
var text: String

@Parameter(title: "File", inputConnectionBehavior: .optionalIfProvided)
var file: IntentFile?
```

### Runtime Parameter Methods

Request values, disambiguation, and confirmation at runtime inside `perform()`:

```swift
func perform() async throws -> some IntentResult {
    // Request a missing value
    if quantity == nil {
        throw $quantity.needsValueError("How many would you like?")
    }

    // Disambiguate among options
    let resolved = try await $size.requestDisambiguation(
        among: [.small, .medium, .large],
        dialog: "Which size?"
    )

    // Confirm a value
    try await $amount.requestConfirmation(for: amount, dialog: "Charge \(amount)?")

    return .result()
}
```

## Dependent Options and Intentional Defaults

Use `@IntentParameterDependency` when an upstream intent parameter changes the
valid options for another parameter. It is available in iOS 17+ for
`DynamicOptionsProvider` implementations, including the `EntityQuery` family.

```swift
struct ConfigureProjectWidget: WidgetConfigurationIntent {
    static var title: LocalizedStringResource = "Project"

    @Parameter(title: "Workspace")
    var workspace: WorkspaceEntity?

    @Parameter(title: "Project")
    var project: ProjectEntity?
}

struct ProjectQuery: EntityQuery {
    @IntentParameterDependency<ConfigureProjectWidget>(\.$workspace)
    private var configuration

    func entities(for identifiers: [ProjectEntity.ID]) async throws -> [ProjectEntity] {
        try await ProjectStore.shared.projects(identifiedBy: identifiers)
            .map(ProjectEntity.init)
    }

    func suggestedEntities() async throws -> [ProjectEntity] {
        guard let workspaceID = configuration?.workspace?.id else {
            return []
        }
        return try await ProjectStore.shared.projects(in: workspaceID)
            .map(ProjectEntity.init)
    }

    func defaultResult() async -> ProjectEntity? {
        guard let workspaceID = configuration?.workspace?.id else {
            return nil
        }
        return try? await ProjectStore.shared.recentProject(in: workspaceID)
            .map(ProjectEntity.init)
    }
}
```

The dependency can be `nil` while the system is asking for options before the
upstream value is configured. Handle that state deliberately: return an empty list,
or return a small unfiltered set only when those choices remain valid. Dependencies
may read multiple parameters when an option requires more than one parent choice.

`EntityQuery` inherits `defaultResult()` through `DynamicOptionsProvider`. Implement
it only when the app has a stable, helpful default such as a current workspace or a
recent project. Do not silently choose the first fetched entity merely to avoid an
unconfigured parameter.

Apple references:

- [`IntentParameterDependency`](https://sosumi.ai/documentation/appintents/intentparameterdependency)
- [`DynamicOptionsProvider`](https://sosumi.ai/documentation/appintents/dynamicoptionsprovider)

## EntityPropertyQuery (Filter and Sort)

The most powerful query variant. Declare filterable properties and sortable
fields for structured Siri and Shortcuts queries.

```swift
enum TrailComparator: Sendable {
    case nameContains(String)
    case nameEquals(String)
    case lengthGreaterThan(Measurement<UnitLength>)
    case lengthLessThan(Measurement<UnitLength>)
    case lengthEquals(Measurement<UnitLength>)
}

struct TrailPropertyQuery: EntityPropertyQuery {
    typealias ComparatorMappingType = TrailComparator

    static var properties = QueryProperties {
        Property(\TrailEntity.$name) {
            ContainsComparator { TrailComparator.nameContains($0) }
            EqualToComparator { TrailComparator.nameEquals($0) }
        }
        Property(\TrailEntity.$trailLength) {
            GreaterThanComparator { TrailComparator.lengthGreaterThan($0) }
            LessThanComparator { TrailComparator.lengthLessThan($0) }
            EqualToComparator { TrailComparator.lengthEquals($0) }
        }
    }

    static var sortingOptions = SortingOptions {
        SortableBy(\TrailEntity.$name)
        SortableBy(\TrailEntity.$trailLength)
    }

    func entities(
        matching comparators: [TrailComparator],
        mode: ComparatorMode,
        sortedBy: [EntityQuerySort<TrailEntity>],
        limit: Int?
    ) async throws -> [TrailEntity] {
        var results = TrailStore.shared.allTrails.map { TrailEntity(from: $0) }

        results = results.filter { trail in
            let matches = comparators.map { comparator in
                switch comparator {
                case .nameContains(let value):
                    trail.name.localizedCaseInsensitiveContains(value)
                case .nameEquals(let value):
                    trail.name.localizedStandardCompare(value) == .orderedSame
                case .lengthGreaterThan(let value):
                    trail.trailLength > value
                case .lengthLessThan(let value):
                    trail.trailLength < value
                case .lengthEquals(let value):
                    trail.trailLength == value
                }
            }
            guard !matches.isEmpty else { return true }
            return mode == .and ? matches.allSatisfy { $0 } : matches.contains(true)
        }

        if let limit {
            results = Array(results.prefix(limit))
        }

        return results
    }

    func entities(for identifiers: [Trail.ID]) async throws -> [TrailEntity] {
        TrailStore.shared.allTrails
            .filter { identifiers.contains($0.id) }
            .map { TrailEntity(from: $0) }
    }

    func suggestedEntities() async throws -> [TrailEntity] {
        TrailStore.shared.featured.map { TrailEntity(from: $0) }
    }
}
```

The comparator closures map user-supplied values into a query-specific
`ComparatorMappingType`; `entities(matching:)` receives those mapped values, not
raw `EntityQueryComparator` objects.

### Available comparators

| Comparator | Supported Types |
|---|---|
| `EqualToComparator` | Equatable properties |
| `NotEqualToComparator` | Equatable properties |
| `ContainsComparator` | Sequence properties |
| `HasPrefixComparator` | `String` |
| `HasSuffixComparator` | `String` |
| `GreaterThanComparator` | Comparable properties |
| `LessThanComparator` | Comparable properties |
| `GreaterThanOrEqualToComparator` | Comparable properties |
| `LessThanOrEqualToComparator` | Comparable properties |
| `IsBetweenComparator` | Comparable properties supported by Shortcuts |

## Assistant Schemas (iOS 18+)

Assistant schemas define domain-specific intents that Apple Intelligence
understands natively. Annotate conforming types with schema macros.

### Declaration

```swift
// Preferred macro (iOS 18+)
@AppIntent(schema: .photos.openAsset)
struct OpenPhotoIntent: AppIntent { ... }

// CORRECT: Using preferred macro
@AppIntent(schema: .photos.openAsset)
struct OpenPhotoIntent: AppIntent {
    static var title: LocalizedStringResource = "Open Photo"

    @Parameter(title: "Asset")
    var target: PhotoEntity

    func perform() async throws -> some IntentResult {
        PhotoViewer.shared.open(target.id)
        return .result()
    }
}

@AppEntity(schema: .photos.asset)
struct PhotoEntity: AppEntity {
    var id: String
    static let defaultQuery = PhotoQuery()
    static var typeDisplayRepresentation: TypeDisplayRepresentation = "Photo"
    var displayRepresentation: DisplayRepresentation {
        DisplayRepresentation(title: "\(name)")
    }
    var name: String
}

@AppEnum(schema: .photos.assetType)
enum PhotoType: String, AppEnum {
    case photo, video, livePhoto
    static var typeDisplayRepresentation: TypeDisplayRepresentation = "Photo Type"
    static var caseDisplayRepresentations: [PhotoType: DisplayRepresentation] = [
        .photo: "Photo",
        .video: "Video",
        .livePhoto: "Live Photo"
    ]
}
```

Avoid the deprecated `AssistantIntent(schema:)`, `AssistantEntity(schema:)`, and
`AssistantEnum(schema:)` macros in new code.

### Domain catalog

Use Xcode completion and the current domain docs for exact schema cases. The
major Apple domains are:

| Domain | Example actions | Example content |
|---|---|---|
| Assistant | side-button conversational app launch | -- |
| Books | open book, create bookmark | book, audiobook |
| Browser | open tab, create bookmark, search web | tab, bookmark, window |
| Camera | capture photo, capture video | -- |
| File management | open, create, move, rename, delete file | file |
| Journaling | create, update, delete, search entry | journal entry |
| Mail | open mailbox, send draft | account, draft, mailbox, message |
| Photos | open asset, create album, search assets | album, asset, person |
| Presentations | open document, add slide | document, slide, template |
| Reader | open document, go to page | document, page |
| Spreadsheet | open document, add sheet | document, sheet, template |
| System and in-app search | search | -- |
| Visual intelligence | semantic content search | -- |
| Whiteboard | open board, create item | board, item |
| Word processor | open document, add page | document, page, template |

### isAssistantOnly

Control whether a schema-conforming type is exclusive to Apple Intelligence or
also available through other system surfaces:

```swift
@AppIntent(schema: .photos.openAsset)
struct OpenPhotoIntent: AppIntent {
    static let isAssistantOnly = false  // Also available in Shortcuts
    // ...
}
```

## Focus Filter Intents

Customize app behavior when a Focus mode activates.

```swift
struct WorkFocusFilter: SetFocusFilterIntent {
    static var title: LocalizedStringResource = "Work Focus"
    static var description = IntentDescription("Configure app for work mode.")

    @Parameter(title: "Show Only Work Projects", default: true)
    var workOnly: Bool

    @Parameter(title: "Mute Notifications", default: false)
    var muteNotifications: Bool

    var displayRepresentation: DisplayRepresentation {
        "Work Mode"
    }

    func perform() async throws -> some IntentResult {
        AppSettings.shared.workModeEnabled = workOnly
        AppSettings.shared.notificationsMuted = muteNotifications
        return .result()
    }
}
```

### Access current focus filter

```swift
let currentFilter = try? SetFocusFilterIntent.current
if let workFilter = currentFilter as? WorkFocusFilter {
    // Apply work-mode behavior
}
```

### Suggest filters for a focus context

```swift
extension WorkFocusFilter {
    static func suggestedFocusFilters(
        for context: FocusFilterSuggestionContext
    ) async -> [WorkFocusFilter] {
        [WorkFocusFilter(workOnly: true, muteNotifications: true)]
    }
}
```

## SiriKit Migration (CustomIntentMigratedAppIntent)

Replace SiriKit custom intents (`.intentdefinition` files) while preserving
existing user shortcuts and donations.

```swift
struct OrderSoupIntent: CustomIntentMigratedAppIntent {
    // Map to the old SiriKit intent class name -- must match exactly
    static var intentClassName: String = "OrderSoupIntent"

    static var title: LocalizedStringResource = "Order Soup"

    @Parameter(title: "Soup")
    var soup: SoupEntity

    @Parameter(title: "Quantity", default: 1)
    var quantity: Int

    func perform() async throws -> some IntentResult {
        let order = try await OrderService.shared.place(
            soup: soup.id,
            quantity: quantity
        )
        return .result(dialog: "Ordered \(quantity) bowls.")
    }
}
```

### Migration steps

1. Create a new `AppIntent` struct conforming to `CustomIntentMigratedAppIntent`.
2. Set `intentClassName` to the old SiriKit intent class name (exact match).
3. Recreate parameters using `@Parameter` instead of `.intentdefinition` props.
4. Implement `perform()` with async/await.
5. Existing user shortcuts and donations continue working via the class name.
6. Remove the `.intentdefinition` file once migration is verified.

### DeprecatedAppIntent (versioning within AppIntents)

Replace an old `AppIntent` with a newer version:

```swift
struct OldSearchIntent: DeprecatedAppIntent {
    typealias ReplacementIntent = NewSearchIntent
    static var deprecation: IntentDeprecation {
        .init(message: "Use the new search intent.")
    }
    static var title: LocalizedStringResource = "Search (Deprecated)"
    func perform() async throws -> some IntentResult { .result() }
}
```

## Error Handling and Dialog

### Standard error types (iOS 18+)

```swift
func perform() async throws -> some IntentResult {
    guard await PermissionManager.hasPhotoAccess else {
        throw AppIntentError.PermissionRequired.photos
    }

    guard let item = try await fetchItem() else {
        throw AppIntentError.Unrecoverable.entityNotFound
    }

    guard !requiresManualSetup else {
        throw AppIntentError.UserActionRequired.accountSetup
    }

    return .result()
}
```

| Error Type | When to Use |
|---|---|
| `AppIntentError.PermissionRequired` | Missing OS-level permission |
| `AppIntentError.Unrecoverable` | Fatal state with no immediate remedy |
| `AppIntentError.UserActionRequired` | User must sign in, confirm, or set up an account |

### Parameter-level errors

```swift
// Re-prompt for a value
throw $quantity.needsValueError("How many items?")

// Force disambiguation
throw $size.needsDisambiguation(among: [.small, .medium, .large])
```

### Foreground continuation

```swift
func perform() async throws -> some IntentResult {
    if needsUserInteraction {
        try await continueInForeground("Open the app to finish.")
    }
    // ...
    return .result()
}
```

### Dialog in results

```swift
func perform() async throws -> some IntentResult & ProvidesDialog {
    return .result(dialog: "Your soup order has been placed.")
}

func perform() async throws -> some IntentResult & ProvidesDialog & ReturnsValue<OrderEntity> {
    let order = try await placeOrder()
    return .result(
        value: OrderEntity(from: order),
        dialog: "Order #\(order.number) is confirmed."
    )
}
```

## Confirmation Flows

### Basic confirmation

```swift
func perform() async throws -> some IntentResult {
    try await requestConfirmation(
        actionName: .send,
        dialog: "Send \(quantity) messages?"
    )
    // User confirmed -- proceed
    return .result()
}
```

### Conditional confirmation

```swift
func perform() async throws -> some IntentResult {
    try await requestConfirmation(
        conditions: .always,
        actionName: .order,
        dialog: "Place order for \(quantity) \(soup.name)?"
    )
    return .result()
}
```

### Confirmation with SwiftUI content

```swift
func perform() async throws -> some IntentResult {
    try await requestConfirmation(
        actionName: .buy,
        dialog: "Purchase \(item.name) for \(item.price)?",
        view: OrderPreviewView(item: item)
    )
    return .result()
}
```

### User choice

```swift
func perform() async throws -> some IntentResult {
    let chosen = try await requestChoice(
        between: availableOptions,
        dialog: "Which option would you like?"
    )
    // Use chosen value
    return .result()
}
```

### ConfirmationActionName options

Built-in: `.add`, `.buy`, `.call`, `.create`, `.send`, `.share`, `.start`,
`.toggle`, `.turnOn`, `.turnOff`, `.open`, `.play`, `.post`, `.search`,
`.book`, `.download`, `.pay`, `.order`, `.run`, `.get`, `.go`, `.log`,
`.set`, `.view`, `.find`, `.filter`, `.continue`, `.do`, `.addData`,
`.checkIn`, `.request`, `.playSound`, `.startNavigation`.

Custom:

```swift
.custom(
    acceptLabel: "Confirm Purchase",
    acceptAlternatives: ["Yes", "Buy it"],
    denyLabel: "Cancel",
    denyAlternatives: ["No", "Never mind"],
    destructive: false
)
```

## Authentication Policies

Control when device authentication is required:

```swift
struct TransferMoneyIntent: AppIntent {
    static var authenticationPolicy: IntentAuthenticationPolicy = .requiresAuthentication
    static var title: LocalizedStringResource = "Transfer Money"

    func perform() async throws -> some IntentResult {
        // Device must be unlocked before this runs
        return .result()
    }
}
```

| Policy | Behavior |
|---|---|
| `.alwaysAllowed` | No authentication required |
| `.requiresAuthentication` | Device must be unlocked |
| `.requiresLocalDeviceAuthentication` | Face ID / Touch ID required |

```swift
// WRONG: Sensitive action without authentication
struct DeleteAccountIntent: AppIntent {
    // Missing authenticationPolicy -- runs on locked device
    func perform() async throws -> some IntentResult { ... }
}

// CORRECT: Require authentication for sensitive actions
struct DeleteAccountIntent: AppIntent {
    static var authenticationPolicy: IntentAuthenticationPolicy = .requiresLocalDeviceAuthentication
    static var title: LocalizedStringResource = "Delete Account"
    func perform() async throws -> some IntentResult { ... }
}
```

## URLRepresentableIntent / Entity / Enum (iOS 18+)

Represent intents, entities, and enums as URLs for deep linking.

### URLRepresentableIntent

```swift
struct OpenRecipeIntent: URLRepresentableIntent {
    static var title: LocalizedStringResource = "Open Recipe"

    @Parameter(title: "Recipe")
    var target: RecipeEntity

    static var parameterSummary: some ParameterSummary {
        Summary("Open \(\.$target)")
    }

    func perform() async throws -> some IntentResult & OpensIntent {
        return .result()
    }
}

extension OpenRecipeIntent {
    static var urlRepresentation: URLRepresentation {
        "https://myapp.com/recipes/\(\.$target)"
    }
}
```

### URLRepresentableEntity

```swift
struct RecipeEntity: URLRepresentableEntity {
    // ... standard AppEntity members ...

    static var urlRepresentation: URLRepresentation {
        "https://myapp.com/recipes/\(.id)"
    }
}
```

### URLRepresentableEnum

```swift
enum RecipeCategory: String, URLRepresentableEnum {
    case breakfast, lunch, dinner

    static var urlRepresentation: URLRepresentation {
        "https://myapp.com/category/\(.rawValue)"
    }

    // ... standard AppEnum members ...
}
```

URL representations must be universal links, not custom URL schemes.

## IndexedEntity for Spotlight (iOS 18+)

Conform to `IndexedEntity` to make entities searchable in Spotlight.

```swift
struct ArticleEntity: IndexedEntity {
    static let defaultQuery = ArticleQuery()
    static var typeDisplayRepresentation: TypeDisplayRepresentation = "Article"

    var id: String

    @Property(title: "Title")
    var title: String

    @Property(title: "Author")
    var author: String

    var displayRepresentation: DisplayRepresentation {
        DisplayRepresentation(title: "\(title)", subtitle: "\(author)")
    }

    // Start with defaultAttributeSet to keep displayRepresentation metadata
    var attributeSet: CSSearchableItemAttributeSet {
        let attrs = defaultAttributeSet
        attrs.authorNames = [author]
        return attrs
    }
}
```

After creating entities, add instances to a named Spotlight index:

```swift
try await CSSearchableIndex(name: "Articles").indexAppEntities(articleEntities)
```

If you return a fresh `CSSearchableItemAttributeSet` from `attributeSet`, add
the contents of `defaultAttributeSet` yourself when you still need the title,
subtitle, or image from `displayRepresentation`.

If your app already creates `CSSearchableItem` values, call
`associateAppEntity(_:priority:)` on the item's attribute set and provide an
`OpenIntent` for the entity type so Spotlight results can open the right app
content.

### Hide specific entities from Spotlight UI

```swift
extension ArticleEntity {
    var hideInSpotlight: Bool {
        isDraft  // Draft articles should not appear in search
    }
}
```

## `@ComputedProperty(indexingKey:)` for Spotlight (iOS 26+)

Use indexing keys on `@Property` and `@ComputedProperty` for structured
Spotlight metadata. The value is a Swift key path into
`CSSearchableItemAttributeSet`.

```swift
struct RecipeEntity: IndexedEntity {
    static let defaultQuery = RecipeQuery()
    static var typeDisplayRepresentation: TypeDisplayRepresentation = "Recipe"

    var id: String

    @Property(title: "Name", indexingKey: \.title)
    var name: String

    @Property(title: "Cuisine")
    var cuisine: String

    @ComputedProperty(indexingKey: \.contentDescription)
    var summary: String {
        "\(name) -- \(cuisine) cuisine"
    }

    @ComputedProperty(indexingKey: \.thumbnailURL)
    var imageURL: URL? {
        URL(string: "https://myapp.com/images/\(id).jpg")
    }

    var displayRepresentation: DisplayRepresentation {
        DisplayRepresentation(title: "\(name)", subtitle: "\(cuisine)")
    }
}
```

```swift
// Avoid duplicating a wrapped property's indexing key in attributeSet
struct RecipeEntity: IndexedEntity {
    @Property(title: "Name", indexingKey: \.title)
    var name: String

    var attributeSet: CSSearchableItemAttributeSet {
        let attrs = CSSearchableItemAttributeSet(contentType: .text)
        attrs.title = name  // Redundant: @Property already supplies this key
        return attrs
    }
}

// Prefer indexingKey for metadata already exposed on the entity
struct RecipeEntity: IndexedEntity {
    @Property(title: "Name", indexingKey: \.title)
    var name: String
}
```

### Available indexing keys

| Key | Property Type | Purpose |
|---|---|---|
| `\.title` | `String` | Primary searchable title |
| `\.contentDescription` | `String` | Detailed description |
| `\.thumbnailURL` | `URL?` | Thumbnail image |
| `\.keywords` | `[String]` | Additional search terms |
| `\.contentURL` | `URL?` | Content location |

## Onscreen Content for Siri (iOS 26+)

Make onscreen content available to Siri and Apple Intelligence without an
assistant schema:

```swift
struct ArticleEntity: AppEntity, Transferable {
    // Standard AppEntity conformance...

    static var transferRepresentation: some TransferRepresentation {
        CodableRepresentation(contentType: .article)
    }
}

// In your view controller or SwiftUI view:
let activity = NSUserActivity(activityType: "com.myapp.article")
activity.appEntityIdentifier = AppEntityIdentifier(article)
// Set as current activity
```

## Parameter Summary Builder

Use `When`, `Switch`, `Case`, and `DefaultCase` for conditional parameter
summaries that change based on parameter values:

```swift
struct ConfigureWidgetIntent: WidgetConfigurationIntent {
    static var title: LocalizedStringResource = "Configure Widget"

    @Parameter(title: "Style")
    var style: WidgetStyle

    @Parameter(title: "Show Details", default: false)
    var showDetails: Bool

    @Parameter(title: "Refresh Interval", default: .hourly)
    var interval: RefreshInterval

    static var parameterSummary: some ParameterSummary {
        When(\.$showDetails, .equalTo, true) {
            Summary("Show \(\.$style) widget") {
                \.$showDetails
                \.$interval
            }
        } otherwise: {
            Summary("Show \(\.$style) widget") {
                \.$showDetails
            }
        }
    }
}
```

### Switch/Case for multiple conditions

```swift
static var parameterSummary: some ParameterSummary {
    Switch(\.$style) {
        Case(.compact) {
            Summary("Compact widget")
        }
        Case(.detailed) {
            Summary("Detailed widget") {
                \.$interval
            }
        }
        DefaultCase {
            Summary("Widget") {
                \.$style
            }
        }
    }
}
```

## Core Spotlight Direct Usage

Use Core Spotlight directly when you need full control over indexing without
adopting App Intents, or when targeting iOS versions before IndexedEntity
(pre-iOS 18). For apps already using App Intents, prefer `IndexedEntity`
(iOS 18+) plus `@Property(indexingKey:)` / `@ComputedProperty(indexingKey:)`
(iOS 26+) where possible.

### When to Use Core Spotlight Directly vs IndexedEntity

| Approach | When to Use |
|---|---|
| `IndexedEntity` (iOS 18+) | App already uses App Intents; entities are also Siri/Shortcuts-visible |
| `@ComputedProperty(indexingKey:)` (iOS 26+) | Adds derived metadata to an `IndexedEntity` |
| Core Spotlight directly | No App Intents adoption; pre-iOS 18 targets; standalone indexing; fine-grained control over expiration, domain grouping, or batch operations |

### CSSearchableItem and CSSearchableItemAttributeSet

A `CSSearchableItem` uniquely identifies searchable content. Attach a
`CSSearchableItemAttributeSet` to describe the item's metadata.

Docs: [CSSearchableItem](https://sosumi.ai/documentation/corespotlight/cssearchableitem),
[CSSearchableItemAttributeSet](https://sosumi.ai/documentation/corespotlight/cssearchableitemattributeset)

```swift
import CoreSpotlight
import UniformTypeIdentifiers

func makeSearchableItem(
    id: String,
    title: String,
    description: String,
    thumbnailData: Data? = nil
) -> CSSearchableItem {
    let attributes = CSSearchableItemAttributeSet(contentType: .text)
    attributes.title = title
    attributes.contentDescription = description
    attributes.thumbnailData = thumbnailData

    // Optional: improve search ranking and categorization
    attributes.keywords = ["recipe", "cooking"]
    attributes.displayName = title
    attributes.contentURL = URL(string: "myapp://recipes/\(id)")

    let item = CSSearchableItem(
        uniqueIdentifier: id,
        domainIdentifier: "com.myapp.recipes",
        attributeSet: attributes
    )
    // Set an expiration date when the default automatic expiration is wrong
    item.expirationDate = Date.now.addingTimeInterval(60 * 60 * 24 * 90)
    return item
}
```

### CSSearchableIndex — Indexing and Deletion

Use `CSSearchableIndex` to add, update, and remove items. Use a named index in
production, and add a protection class when indexing sensitive content. Reserve
`default()` for prototyping and testing.

Docs: [CSSearchableIndex](https://sosumi.ai/documentation/corespotlight/cssearchableindex)

```swift
import CoreSpotlight

// Index a single item (add or update)
func indexItem(_ item: CSSearchableItem) async throws {
    let index = CSSearchableIndex(name: "recipes")
    try await index.indexSearchableItems([item])
}

// Delete specific items by identifier
func deleteItems(identifiers: [String]) async throws {
    let index = CSSearchableIndex(name: "recipes")
    try await index.deleteSearchableItems(
        withIdentifiers: identifiers
    )
}

// Delete all items in a domain (e.g., after user deletes a category)
func deleteItemsInDomain(_ domain: String) async throws {
    let index = CSSearchableIndex(name: "recipes")
    try await index.deleteSearchableItems(
        withDomainIdentifiers: [domain]
    )
}

// Delete everything (e.g., on logout)
func deleteAllItems() async throws {
    let index = CSSearchableIndex(name: "recipes")
    try await index.deleteAllSearchableItems()
}
```

### Batch Indexing Patterns

For large data sets, index in batches to minimize memory pressure and handle
errors gracefully. Use `beginBatch()` / `endBatch(withClientState:)` to
track progress and resume after crashes.

```swift
import CoreSpotlight

func batchIndexRecipes(_ recipes: [Recipe]) async throws {
    let index = CSSearchableIndex(name: "recipes")

    // Simple batched approach -- chunk into groups
    let batchSize = 100
    for batch in stride(from: 0, to: recipes.count, by: batchSize) {
        let end = min(batch + batchSize, recipes.count)
        let items = recipes[batch..<end].map { recipe in
            makeSearchableItem(
                id: recipe.id,
                title: recipe.name,
                description: recipe.summary,
                thumbnailData: recipe.thumbnailData
            )
        }
        try await index.indexSearchableItems(items)
    }
}

// Client-state-based batching for crash recovery
func batchIndexWithState(_ recipes: [Recipe]) async throws {
    let index = CSSearchableIndex(name: "recipes")

    // Check where we left off
    let lastState = try? await index.fetchLastClientState()
    let startOffset = lastState
        .flatMap { String(data: $0, encoding: .utf8) }
        .flatMap(Int.init) ?? 0

    let batchSize = 100
    for batch in stride(from: startOffset, to: recipes.count, by: batchSize) {
        let end = min(batch + batchSize, recipes.count)
        let items = recipes[batch..<end].map { recipe in
            makeSearchableItem(
                id: recipe.id,
                title: recipe.name,
                description: recipe.summary
            )
        }

        index.beginBatch()
        try await index.indexSearchableItems(items)

        let stateData = "\(end)".data(using: .utf8)!
        try await index.endBatch(withClientState: stateData)
    }
}
```

### Protected Index for Sensitive Content

Use a named index with a data protection class to encrypt indexed content:

```swift
let protectedIndex = CSSearchableIndex(
    name: "secure-notes",
    protectionClass: .complete  // Only accessible when device is unlocked
)

try await protectedIndex.indexSearchableItems(sensitiveItems)
```

### Handling Search Results (NSUserActivity)

When a user taps a Spotlight result, the system delivers an `NSUserActivity`
with `activityType` set to `CSSearchableItemActionType`. Extract the item
identifier from `userInfo` to navigate to the correct content.

```swift
import CoreSpotlight
import UIKit

// UIKit: In AppDelegate or SceneDelegate
func application(
    _ application: UIApplication,
    continue userActivity: NSUserActivity,
    restorationHandler: @escaping ([UIUserActivityRestoring]?) -> Void
) -> Bool {
    if userActivity.activityType == CSSearchableItemActionType,
       let identifier = userActivity.userInfo?[CSSearchableItemActivityIdentifier] as? String {
        navigateToItem(withIdentifier: identifier)
        return true
    }
    return false
}

// SwiftUI: Use onContinueUserActivity
struct ContentView: View {
    var body: some View {
        NavigationStack {
            RecipeListView()
        }
        .onContinueUserActivity(CSSearchableItemActionType) { activity in
            if let id = activity.userInfo?[CSSearchableItemActivityIdentifier] as? String {
                navigateToRecipe(id: id)
            }
        }
    }
}
```

### Query Continuation

When a user taps "Search in App" from Spotlight, handle the query string:

```swift
// activityType == CSQueryContinuationActionType
.onContinueUserActivity(CSQueryContinuationActionType) { activity in
    if let query = activity.userInfo?[CSSearchQueryString] as? String {
        searchViewModel.searchText = query
    }
}
```
