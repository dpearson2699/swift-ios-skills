# App Intents Advanced Reference

Extended App Intents patterns beyond the basics covered in the main skill.
Covers @Parameter variants, EntityPropertyQuery, assistant schemas, focus
filters, SiriKit migration, error handling, confirmation flows, authentication,
URL-representable types, and Spotlight indexing.

## @Parameter Initializer Variants

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
@Parameter(title: "Volume", controlStyle: .slider, inclusiveRange: (0, 100))
var volume: Int

@Parameter(title: "Rating", controlStyle: .stepper, inclusiveRange: (1, 5))
var rating: Int

@Parameter(title: "Temperature", default: 72.0, inclusiveRange: (60.0, 90.0))
var temperature: Double
```

Control styles: `.field` (default text field), `.slider`, `.stepper`.

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

Specify a custom query for entity resolution:

```swift
@Parameter(title: "Trail", query: [TrailStringQuery(), TrailPropertyQuery()])
var trail: TrailEntity
```

### 7. Array Parameters with Size Constraints

```swift
// Fixed size
@Parameter(title: "Items", size: 3)
var items: [ItemEntity]

// Per-widget-family size
@Parameter(
    title: "Items",
    size: [.systemSmall: 1, .systemMedium: 3, .systemLarge: 6]
)
var items: [ItemEntity]
```

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

## EntityPropertyQuery (Filter and Sort)

The most powerful query variant. Declare filterable properties and sortable
fields for structured Siri and Shortcuts queries.

```swift
struct TrailPropertyQuery: EntityPropertyQuery {
    static var properties = QueryProperties {
        Property(\TrailEntity.$name) {
            ContainsComparator()
            EqualToComparator()
        }
        Property(\TrailEntity.$trailLength) {
            GreaterThanComparator()
            LessThanComparator()
            EqualToComparator()
        }
    }

    static var sortingOptions = SortingOptions {
        SortableBy(\TrailEntity.$name)
        SortableBy(\TrailEntity.$trailLength)
    }

    func entities(
        matching comparators: [EntityQueryComparator],
        mode: ComparatorMode,
        sortedBy: [EntityQuerySort<TrailEntity>],
        limit: Int?
    ) async throws -> [TrailEntity] {
        var results = TrailStore.shared.allTrails.map { TrailEntity(from: $0) }

        for comparator in comparators {
            switch comparator {
            case let comparator as ContainsComparator<String>:
                results = results.filter { $0.name.localizedCaseInsensitiveContains(comparator.value) }
            case let comparator as GreaterThanComparator<Measurement<UnitLength>>:
                results = results.filter { $0.trailLength > comparator.value }
            default:
                break
            }
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

### Available comparators

| Comparator | Supported Types |
|---|---|
| `EqualToComparator` | All comparable types |
| `NotEqualToComparator` | All comparable types |
| `ContainsComparator` | `String` |
| `HasPrefixComparator` | `String` |
| `HasSuffixComparator` | `String` |
| `GreaterThanComparator` | Numeric, `Date`, `Measurement` |
| `LessThanComparator` | Numeric, `Date`, `Measurement` |
| `GreaterThanOrEqualToComparator` | Numeric, `Date`, `Measurement` |
| `LessThanOrEqualToComparator` | Numeric, `Date`, `Measurement` |
| `IsBetweenComparator` | Numeric, `Date`, `Measurement` |

## Assistant Schemas (iOS 18+)

Assistant schemas define domain-specific intents that Apple Intelligence
understands natively. Annotate conforming types with schema macros.

### Declaration

```swift
// WRONG: Using deprecated macro
@AssistantIntent(schema: .photos.openAsset)
struct OpenPhotoIntent: AppIntent { ... }

// CORRECT: Use current macro
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

### Domain catalog (14+ domains)

| Domain | Example Intents | Example Entities |
|---|---|---|
| `.books` | openBook, createBookmark | book, audiobook |
| `.browser` | openTab, createBookmark, searchWeb | tab, bookmark, window |
| `.camera` | capturePhoto, captureVideo | -- |
| `.reader` | openDocument, goToPage | document, page |
| `.files` | openFile, createFile | file |
| `.assistant` | activate | -- |
| `.journal` | createEntry, openEntry | entry |
| `.mail` | openMailbox, sendDraft | account, draft, mailbox, message |
| `.photos` | openAsset, createAlbum, searchAssets | album, asset, recognizedPerson |
| `.presentation` | openDocument, addSlide | document, slide, template |
| `.spreadsheet` | openDocument, addSheet | document, sheet, template |
| `.system` | search | -- |
| `.whiteboard` | openBoard, createItem | board, item |
| `.wordProcessor` | openDocument, addPage | document, page, template |
| `.visualIntelligence` | semanticContentSearch | -- |

### isAssistantOnly

Control whether a schema-conforming type is exclusive to Apple Intelligence or
also available through other system surfaces:

```swift
@AppIntent(schema: .photos.openAsset)
struct OpenPhotoIntent: AppIntent {
    static var isAssistantOnly: Bool { false }  // Also available in Shortcuts
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
        throw PermissionRequired(
            "Photo library access is required.",
            recoverySuggestion: "Grant access in Settings > Privacy."
        )
    }

    guard let item = try await fetchItem() else {
        throw Unrecoverable("The item no longer exists.")
    }

    guard !requiresManualSetup else {
        throw UserActionRequired("Open the app to complete setup.")
    }

    return .result()
}
```

| Error Type | When to Use |
|---|---|
| `PermissionRequired` | Missing OS-level permission |
| `Unrecoverable` | Fatal -- intent cannot proceed |
| `UserActionRequired` | User must act in the app |

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
    static var urlRepresentation: some URLRepresentation {
        URLRepresentation {
            "https://myapp.com/recipes/\(\.$target)"
        }
    }
}
```

### URLRepresentableEntity

```swift
struct RecipeEntity: URLRepresentableEntity {
    // ... standard AppEntity members ...

    static var urlRepresentation: some URLRepresentation {
        URLRepresentation {
            "https://myapp.com/recipes/\(\.id)"
        }
    }
}
```

### URLRepresentableEnum

```swift
enum RecipeCategory: String, URLRepresentableEnum {
    case breakfast, lunch, dinner

    static var urlRepresentation: some URLRepresentation {
        URLRepresentation {
            "https://myapp.com/category/\(\.self)"
        }
    }

    // ... standard AppEnum members ...
}
```

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

    // Custom attribute set for improved search accuracy
    var attributeSet: CSSearchableItemAttributeSet? {
        let attrs = CSSearchableItemAttributeSet(contentType: .text)
        attrs.title = title
        attrs.authorNames = [author]
        return attrs
    }
}
```

### Hide specific entities from Spotlight UI

```swift
extension ArticleEntity {
    var hideInSpotlight: Bool {
        isDraft  // Draft articles should not appear in search
    }
}
```

## @ComputedProperty(indexingKey:) for Spotlight (iOS 26+)

Use indexing keys on `@Property` and `@ComputedProperty` for structured Spotlight
metadata without manual `CSSearchableItemAttributeSet` configuration.

```swift
struct RecipeEntity: IndexedEntity {
    static let defaultQuery = RecipeQuery()
    static var typeDisplayRepresentation: TypeDisplayRepresentation = "Recipe"

    var id: String

    @Property(title: "Name", indexingKey: .title)
    var name: String

    @Property(title: "Cuisine")
    var cuisine: String

    @ComputedProperty(indexingKey: .description)
    var summary: String {
        "\(name) -- \(cuisine) cuisine"
    }

    @ComputedProperty(indexingKey: .thumbnailURL)
    var imageURL: URL? {
        URL(string: "https://myapp.com/images/\(id).jpg")
    }

    var displayRepresentation: DisplayRepresentation {
        DisplayRepresentation(title: "\(name)", subtitle: "\(cuisine)")
    }
}
```

```swift
// WRONG: Manual attributeSet when indexing keys are available (iOS 26+)
struct RecipeEntity: IndexedEntity {
    @Property(title: "Name")
    var name: String

    var attributeSet: CSSearchableItemAttributeSet? {
        let attrs = CSSearchableItemAttributeSet(contentType: .text)
        attrs.title = name  // Redundant on iOS 26
        return attrs
    }
}

// CORRECT: Use indexingKey for structured metadata (iOS 26+)
struct RecipeEntity: IndexedEntity {
    @Property(title: "Name", indexingKey: .title)
    var name: String
}
```

### Available indexing keys

| Key | Property Type | Purpose |
|---|---|---|
| `.title` | `String` | Primary searchable title |
| `.description` | `String` | Detailed description |
| `.thumbnailURL` | `URL?` | Thumbnail image |
| `.keywords` | `[String]` | Additional search terms |
| `.contentURL` | `URL?` | Content location |

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
