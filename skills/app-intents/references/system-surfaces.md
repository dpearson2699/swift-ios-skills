# App Intents System Surfaces

Load this reference when implementing Siri donation/prediction, interactive
widgets, Control Center controls, or Spotlight indexing with App Intents.

## Contents

- [Siri Integration](#siri-integration)
- [Interactive Widget Intents](#interactive-widget-intents)
- [Control Center Widgets (iOS 18+)](#control-center-widgets-ios-18)
- [Spotlight and IndexedEntity (iOS 18+)](#spotlight-and-indexedentity-ios-18)
- [References](#references)

## Siri Integration

### Donating intents

Donate intents so the system learns user patterns and suggests them in Spotlight:

```swift
let intent = OrderSoupIntent()
intent.soup = favoriteSoupEntity
try await intent.donate()
```

### Predictable intents

Conform to `PredictableIntent` for Siri prediction of upcoming actions.

## Interactive Widget Intents

Use `AppIntent` with `Button`/`Toggle` in widgets. Use
`WidgetConfigurationIntent` for configurable widget parameters.
Treat configuration intents as parameter contracts; put mutations in a separate
action intent. For sensitive actions such as smart-home control, payments, or
deletion, use an appropriate `authenticationPolicy` and/or
`requestConfirmation(...)` before changing state.

```swift
struct ToggleFavoriteIntent: AppIntent {
    static var title: LocalizedStringResource = "Toggle Favorite"
    @Parameter(title: "Item ID") var itemID: String

    func perform() async throws -> some IntentResult {
        FavoriteStore.shared.toggle(itemID)
        return .result()
    }
}

// In widget view:
Button(intent: ToggleFavoriteIntent(itemID: entry.id)) {
    Image(systemName: entry.isFavorite ? "heart.fill" : "heart")
}
```

### WidgetConfigurationIntent

```swift
struct BookWidgetConfig: WidgetConfigurationIntent {
    static var title: LocalizedStringResource = "Favorite Book"
    @Parameter(title: "Book", default: "The Swift Programming Language") var bookTitle: String
}

// Connect to WidgetKit:
struct MyWidget: Widget {
    var body: some WidgetConfiguration {
        AppIntentConfiguration(kind: "FavoriteBook", intent: BookWidgetConfig.self, provider: MyTimelineProvider()) { entry in
            BookWidgetView(entry: entry)
        }
    }
}
```

## Control Center Widgets (iOS 18+)

Expose controls in Control Center and Lock Screen with `ControlConfigurationIntent`
and `ControlWidget`. Parameters without defaults must be optional.
Trigger state changes from a separate action intent with explicit entity
parameters, not from the configuration intent. Use `AppIntent` or `OpenIntent`
for control buttons and `SetValueIntent` for control toggles.

```swift
struct LightControlConfig: ControlConfigurationIntent {
    static var title: LocalizedStringResource = "Light Control"
    @Parameter(title: "Light", default: .livingRoom) var light: LightEntity
}

struct SetLightIntent: SetValueIntent {
    static var title: LocalizedStringResource = "Set Light"
    static var authenticationPolicy: IntentAuthenticationPolicy = .requiresAuthentication

    init() {}

    init(light: LightEntity) {
        self.light = light
    }

    @Parameter(title: "Light") var light: LightEntity
    @Parameter(title: "Light is on") var value: Bool

    func perform() async throws -> some IntentResult {
        try await LightService.shared.setLight(light.id, isOn: value)
        return .result()
    }
}

struct LightControl: ControlWidget {
    var body: some ControlWidgetConfiguration {
        AppIntentControlConfiguration(kind: "LightControl", intent: LightControlConfig.self) { config in
            ControlWidgetToggle(config.light.name, isOn: config.light.isOn, action: SetLightIntent(light: config.light))
        }
    }
}
```

The system supplies `SetValueIntent.value` with the toggle's requested new state.
Do not derive or invert that value yourself. Persist the new state before
`perform()` returns so WidgetKit reloads the control consistently.

Apple reference: [Creating controls to perform actions across the system](https://sosumi.ai/documentation/widgetkit/creating-controls-to-perform-actions-across-the-system)

## Spotlight and IndexedEntity (iOS 18+)

Conform to `IndexedEntity` for Spotlight search. On iOS 26+, use `indexingKey`
for structured metadata:

```swift
struct RecipeEntity: IndexedEntity {
    static let defaultQuery = RecipeQuery()
    static var typeDisplayRepresentation: TypeDisplayRepresentation = "Recipe"
    var id: String  // Stable recipe UUID or slug; do not use recycled row IDs

    @Property(title: "Name", indexingKey: \.title) var name: String  // iOS 26+
    @ComputedProperty(indexingKey: \.contentDescription)              // iOS 26+
    var summary: String { "\(name) -- a delicious recipe" }

    var displayRepresentation: DisplayRepresentation {
        DisplayRepresentation(title: "\(name)")
    }

    var attributeSet: CSSearchableItemAttributeSet {
        let attrs = defaultAttributeSet
        attrs.keywords = ["recipe"]
        return attrs
    }
}

struct RecipeQuery: EntityQuery {
    func entities(for identifiers: [RecipeEntity.ID]) async throws -> [RecipeEntity] {
        identifiers.compactMap { id in
            RecipeStore.shared.recipe(id: id).map(RecipeEntity.init)
        }
    }
}

struct OpenRecipeIntent: OpenIntent {
    static var title: LocalizedStringResource = "Open Recipe"
    @Parameter(title: "Recipe") var target: RecipeEntity
}
```

`IndexedEntity` describes metadata; still index instances in a named Spotlight
index, e.g. `CSSearchableIndex(name: "...").indexAppEntities(entities)`.
If you customize `attributeSet`, start from `defaultAttributeSet`; returning a
fresh attribute set replaces display representation and property-derived
metadata. Prefer `indexingKey` for metadata already exposed on the entity.
Update and delete changed records in that same named index:

```swift
let recipeIndex = CSSearchableIndex(name: "Recipes")
try await recipeIndex.indexAppEntities(changedRecipes)
try await recipeIndex.deleteAppEntities(
    identifiedBy: deletedRecipeIDs,
    ofType: RecipeEntity.self
)
```

For large syncs, use `beginBatch()`, `endBatch(withClientState:)`, and
`fetchLastClientState()` so indexing can resume after a crash or jetsam.

## References

- [App Intents](https://sosumi.ai/documentation/appintents)
- [Getting started with the App Intents framework](https://sosumi.ai/documentation/appintents/getting-started-with-the-app-intents-framework)
- [Core Spotlight](https://sosumi.ai/documentation/corespotlight)
- [WidgetKit](https://sosumi.ai/documentation/widgetkit)
