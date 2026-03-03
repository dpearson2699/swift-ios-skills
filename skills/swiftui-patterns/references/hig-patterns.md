# HIG Patterns Reference

iOS Human Interface Guidelines patterns for layout, typography, color, accessibility, and feedback in SwiftUI.

## Layout and Spacing

### Standard Margins

```swift
private let standardMargin: CGFloat = 16
private let compactMargin: CGFloat = 8
private let largeMargin: CGFloat = 24

extension EdgeInsets {
    static let standard = EdgeInsets(top: 16, leading: 16, bottom: 16, trailing: 16)
    static let listRow = EdgeInsets(top: 12, leading: 16, bottom: 12, trailing: 16)
}
```

### Safe Area Handling

```swift
ScrollView {
    LazyVStack(spacing: 16) {
        ForEach(items) { item in
            ItemRow(item: item)
        }
    }
    .padding(.horizontal)
}
.safeAreaInset(edge: .bottom) {
    HStack {
        Button("Cancel") { }
            .buttonStyle(.bordered)
        Spacer()
        Button("Confirm") { }
            .buttonStyle(.borderedProminent)
    }
    .padding()
    .background(.regularMaterial)
}
```

### Adaptive Layouts

Use `horizontalSizeClass` to adapt between compact and regular widths:

```swift
@Environment(\.horizontalSizeClass) private var sizeClass

private var columns: [GridItem] {
    switch sizeClass {
    case .compact:
        [GridItem(.flexible())]
    case .regular:
        [GridItem(.flexible()), GridItem(.flexible()), GridItem(.flexible())]
    default:
        [GridItem(.flexible())]
    }
}
```

## Typography

### System Font Styles

Use system font styles for automatic Dynamic Type support:

| Style | Size | Weight | Usage |
|-------|------|--------|-------|
| `.largeTitle` | 34pt | Bold | Screen titles |
| `.title` | 28pt | Semibold | Section headers |
| `.title2` | 22pt | Semibold | Sub-section headers |
| `.title3` | 20pt | Semibold | Group headers |
| `.headline` | 17pt | Semibold | Row titles |
| `.body` | 17pt | Regular | Primary content |
| `.callout` | 16pt | Regular | Secondary content |
| `.subheadline` | 15pt | Regular | Supporting text |
| `.footnote` | 13pt | Regular | Tertiary info |
| `.caption` | 12pt | Regular | Labels |
| `.caption2` | 11pt | Regular | Small labels |

### Custom Font with Dynamic Type

```swift
extension Font {
    static func customBody(_ name: String) -> Font {
        .custom(name, size: 17, relativeTo: .body)
    }
}
```

## Color System

### Semantic Colors

Use semantic colors for automatic light/dark mode support:

```swift
// Labels
Color.primary           // Primary text
Color.secondary         // Secondary text
Color(uiColor: .tertiaryLabel)

// Backgrounds
Color(uiColor: .systemBackground)
Color(uiColor: .secondarySystemBackground)
Color(uiColor: .systemGroupedBackground)

// Fills and Separators
Color(uiColor: .systemFill)
Color(uiColor: .separator)
```

### Tint Colors

```swift
// Apply app-wide tint
ContentView()
    .tint(.blue)
```

Use `Color.accentColor` for interactive elements and `Color.red` for destructive actions.

## Navigation Patterns

### Hierarchical (NavigationSplitView)

Use for iPad/macOS multi-column layouts:

```swift
NavigationSplitView {
    List(items, selection: $selectedItem) { item in
        NavigationLink(value: item) { ItemRow(item: item) }
    }
    .navigationTitle("Items")
} detail: {
    if let item = selectedItem {
        ItemDetailView(item: item)
    } else {
        ContentUnavailableView("Select an Item", systemImage: "sidebar.leading")
    }
}
```

### Tab-Based

Use `TabView` with a `NavigationStack` per tab. See `tabview.md` for full patterns.

### Toolbar

```swift
.toolbar {
    ToolbarItem(placement: .topBarLeading) { EditButton() }
    ToolbarItemGroup(placement: .topBarTrailing) {
        Button("Filter", systemImage: "line.3.horizontal.decrease.circle") { }
        Button("Add", systemImage: "plus") { }
    }
    ToolbarItemGroup(placement: .bottomBar) {
        Button("Archive", systemImage: "archivebox") { }
        Spacer()
        Text("\(itemCount) items").font(.footnote).foregroundStyle(.secondary)
        Spacer()
        Button("Share", systemImage: "square.and.arrow.up") { }
    }
}
```

### Search Integration

```swift
.searchable(text: $searchText, placement: .navigationBarDrawer(displayMode: .always))
.searchScopes($searchScope) {
    ForEach(SearchScope.allCases, id: \.self) { scope in
        Text(scope.rawValue.capitalized).tag(scope)
    }
}
```

## Feedback

### Haptic Feedback

```swift
// Impact
UIImpactFeedbackGenerator(style: .medium).impactOccurred()

// Notification
UINotificationFeedbackGenerator().notificationOccurred(.success)

// Selection
UISelectionFeedbackGenerator().selectionChanged()
```

See `haptics.md` for structured haptic patterns.

## Accessibility

### VoiceOver Support

```swift
VStack(alignment: .leading, spacing: 8) {
    Text(item.title).font(.headline)
    Text(item.subtitle).font(.subheadline).foregroundStyle(.secondary)
    HStack {
        Image(systemName: "star.fill")
        Text("\(item.rating, specifier: "%.1f")")
    }
}
.accessibilityElement(children: .combine)
.accessibilityLabel("\(item.title), \(item.subtitle)")
.accessibilityValue("Rating: \(item.rating) stars")
.accessibilityHint("Double tap to view details")
.accessibilityAddTraits(.isButton)
```

### Dynamic Type Support

Adapt layout for accessibility sizes:

```swift
@Environment(\.dynamicTypeSize) private var dynamicTypeSize

var body: some View {
    if dynamicTypeSize.isAccessibilitySize {
        VStack(alignment: .leading, spacing: 12) {
            leadingContent
            trailingContent
        }
    } else {
        HStack {
            leadingContent
            Spacer()
            trailingContent
        }
    }
}
```

## Error and Empty States

Use `ContentUnavailableView` for both:

```swift
// Error state
ContentUnavailableView {
    Label("Unable to Load", systemImage: "exclamationmark.triangle")
} description: {
    Text(error.localizedDescription)
} actions: {
    Button("Try Again") { Task { await retry() } }
        .buttonStyle(.borderedProminent)
}

// Empty state
ContentUnavailableView {
    Label("No Photos", systemImage: "camera")
} description: {
    Text("Take your first photo to get started.")
} actions: {
    Button("Take Photo") { showCamera = true }
        .buttonStyle(.borderedProminent)
}
```
