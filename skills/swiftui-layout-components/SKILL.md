---
name: swiftui-layout-components
description: "Build SwiftUI layouts using stacks, grids, lists, scroll views, forms, and controls. Covers VStack/HStack/ZStack, LazyVGrid/LazyHGrid, List with sections and swipe actions, ScrollView with ScrollPosition and scroll-driven reveal surfaces, Form with validation, Toggle/Picker/Slider, .searchable, and overlay patterns. Use when building data-driven layouts, collection views, paged detail reveals, settings screens, search interfaces, or transient overlay UI."
---

# SwiftUI Layout & Components

Layout and component patterns for SwiftUI apps targeting iOS 26+ with Swift 6.3. Covers stack and grid layouts, list patterns, scroll views, forms, controls, search, and overlays. Patterns are backward-compatible to iOS 17 unless noted.

## Contents

- [Layout Fundamentals](#layout-fundamentals)
- [Grid Layouts](#grid-layouts)
- [List Patterns](#list-patterns)
- [ScrollView](#scrollview)
- [Form and Controls](#form-and-controls)
- [Searchable](#searchable)
- [Overlay and Presentation](#overlay-and-presentation)
- [Common Mistakes](#common-mistakes)
- [Review Checklist](#review-checklist)
- [References](#references)

## Layout Fundamentals

### Standard Stacks

Use `VStack`, `HStack`, and `ZStack` for small, fixed-size content. They render all children immediately.

```swift
VStack(alignment: .leading) {
    Text(title).font(.headline)
    Text(subtitle).font(.subheadline).foregroundStyle(.secondary)
}
```

### Lazy Stacks

Use `LazyVStack` and `LazyHStack` inside `ScrollView` for large or dynamic collections. They create child views on demand as they scroll into view.

```swift
ScrollView {
    LazyVStack {
        ForEach(items) { item in
            ItemRow(item: item)
        }
    }
    .padding(.horizontal)
}
```

**When to use which:**
- **Non-lazy stacks:** Small, fixed content (headers, toolbars, forms with few fields)
- **Lazy stacks:** Large or unknown-size collections, feeds, chat messages

## Grid Layouts

Use `LazyVGrid` for icon pickers, media galleries, and dense visual selections. Use `.adaptive` columns for layouts that scale across device sizes, or `.flexible` columns for a fixed column count.

```swift
// Adaptive grid -- columns adjust to fit
let columns = [GridItem(.adaptive(minimum: 120, maximum: 1024))]

LazyVGrid(columns: columns) {
    ForEach(items) { item in
        ThumbnailView(item: item)
            .aspectRatio(1, contentMode: .fit)
    }
}
```

```swift
// Fixed 3-column grid
let columns = Array(repeating: GridItem(.flexible(minimum: 100), spacing: 4), count: 3)

LazyVGrid(columns: columns, spacing: 4) {
    ForEach(items) { item in
        ThumbnailView(item: item)
    }
}
```

Use `.aspectRatio` for cell sizing. Never place `GeometryReader` inside lazy containers -- it forces eager measurement and defeats lazy loading. Use `.onGeometryChange` (iOS 16+) if you need to read dimensions.

See [references/grids.md](references/grids.md) for full grid patterns and design choices.

## List Patterns

Use `List` for feed-style content and settings rows where built-in row reuse, selection, and accessibility matter.

```swift
List {
    Section("General") {
        NavigationLink("Display") { DisplaySettingsView() }
        NavigationLink("Haptics") { HapticsSettingsView() }
    }
    Section("Account") {
        Button("Sign Out", role: .destructive) { }
    }
}
.listStyle(.insetGrouped)
```

**Key patterns:**
- `.listStyle(.plain)` for feed layouts, `.insetGrouped` for settings
- `.scrollContentBackground(.hidden)` + custom background for themed surfaces
- `.listRowInsets(...)` and `.listRowSeparator(.hidden)` for spacing and separator control
- **Edge scrolling:** use `List` + `ScrollPosition` with `.scrollPosition($scrollPosition)` for top/bottom scroll actions
- **Item or section jumps:** use `ScrollView` + lazy stacks with `.scrollTargetLayout()` and stable targets for reliable jump-to-id behavior
- Use `.refreshable { }` for pull-to-refresh feeds
- Use `.contentShape(Rectangle())` on rows that should be tappable end-to-end
- For layout review or migration guidance, lead with container choice and constraints; keep code snippets tiny, and defer spring, transition, and timing choices to `swiftui-animation`

**iOS 26:** Apply `.scrollEdgeEffectStyle(.soft, for: .top)` for modern scroll edge effects.

See [references/list.md](references/list.md) for full list patterns including feed lists with scroll-to-top.

## ScrollView

Use `ScrollView` with lazy stacks when you need custom layout, mixed content, or horizontal scrolling.

```swift
ScrollView(.horizontal, showsIndicators: false) {
    LazyHStack {
        ForEach(chips) { chip in
            ChipView(chip: chip)
        }
    }
}
```

**ScrollPosition:** Enables declarative, bidirectional scroll position tracking and programmatic scrolling.

```swift
@State private var scrollPosition = ScrollPosition(edge: .bottom)

ScrollView {
    LazyVStack {
        ForEach(messages) { message in
            MessageRow(message: message)
        }
    }
    .scrollTargetLayout()
}
.scrollPosition($scrollPosition)
.onChange(of: messages.last?.id) {
    withAnimation { scrollPosition.scrollTo(edge: .bottom) }
}
```

**`safeAreaInset(edge:)`** pins content (input bars, toolbars) above the keyboard without affecting scroll layout.

**iOS 26 additions:**
- `.scrollEdgeEffectStyle(.soft, for: .top)` -- fading edge effect
- `.backgroundExtensionEffect()` -- mirror/blur at safe area edges (use sparingly, one per screen)
- `.safeAreaBar(edge:)` -- attach bar views that integrate with scroll effects

See [references/scrollview.md](references/scrollview.md) for full
`ScrollPosition`, paged reveal, zoom/crop conflict, and iOS 26 edge-effect
patterns.

## Form and Controls

### Form

Use `Form` for structured settings and input screens. Group related controls into `Section` blocks.

```swift
Form {
    Section("Notifications") {
        Toggle("Mentions", isOn: $prefs.mentions)
        Toggle("Follows", isOn: $prefs.follows)
    }
    Section("Appearance") {
        Picker("Theme", selection: $theme) {
            ForEach(Theme.allCases, id: \.self) { Text($0.title).tag($0) }
        }
        Slider(value: $fontScale, in: 0.5...1.5, step: 0.1)
    }
}
.formStyle(.grouped)
.scrollContentBackground(.hidden)
```

Use `@FocusState` to manage keyboard focus in input-heavy forms. Wrap in `NavigationStack` only when presented standalone or in a sheet.

### Controls

| Control | Usage |
|---------|-------|
| `Toggle` | Boolean preferences |
| `Picker` | Discrete choices; `.segmented` for 2-4 options |
| `Slider` | Numeric ranges with visible value label |
| `DatePicker` | Date/time selection |
| `TextField` | Text input with `.keyboardType`, `.textInputAutocapitalization` |

Bind controls directly to `@State`, `@Binding`, or `@AppStorage`. Group related controls in `Form` sections. Use `.disabled(...)` to reflect locked or inherited settings. Use `Label` inside toggles to combine icon + text when it adds clarity.

Avoid `.pickerStyle(.segmented)` for large sets; use menu or inline styles. Don't hide labels for sliders; always show context.

See [references/form.md](references/form.md) for full form examples.

## Searchable

Add native search UI with `.searchable`. Use `.searchScopes` for multiple modes and `.task(id:)` for debounced async results.

```swift
@MainActor
struct ExploreView: View {
  @State private var searchQuery = ""
  @State private var searchScope: SearchScope = .all
  @State private var isSearching = false
  @State private var results: [SearchResult] = []

  var body: some View {
    List {
      if isSearching {
        ProgressView()
      } else {
        ForEach(results) { result in
          SearchRow(result: result)
        }
      }
    }
    .searchable(
      text: $searchQuery,
      placement: .navigationBarDrawer(displayMode: .always),
      prompt: Text("Search")
    )
    .searchScopes($searchScope) {
      ForEach(SearchScope.allCases, id: \.self) { scope in
        Text(scope.title)
      }
    }
    .task(id: searchQuery) {
      await runSearch()
    }
  }

  private func runSearch() async {
    guard !searchQuery.isEmpty else {
      results = []
      return
    }
    isSearching = true
    defer { isSearching = false }
    try? await Task.sleep(for: .milliseconds(250))
    results = await fetchResults(query: searchQuery, scope: searchScope)
  }
}
```

Show a placeholder when search is empty. Debounce input to avoid overfetching. Keep search state local to the view. Avoid running searches for empty strings.

## Overlay and Presentation

Use `.overlay(alignment:)` for transient UI (toasts, banners) without affecting layout.

```swift
struct AppRootView: View {
  @State private var toast: Toast?

  var body: some View {
    content
      .overlay(alignment: .top) {
        if let toast {
          ToastView(toast: toast)
            .transition(.move(edge: .top).combined(with: .opacity))
            .onAppear {
              Task {
                try? await Task.sleep(for: .seconds(2))
                withAnimation { self.toast = nil }
              }
            }
        }
      }
  }
}
```

Prefer overlays for transient UI rather than embedding in layout stacks. Use transitions and short auto-dismiss timers. Keep overlays aligned to a clear edge (`.top` or `.bottom`). Avoid overlays that block all interaction unless explicitly needed. Don't stack many overlays; use a queue or replace the current toast.

For modal routing, sheet detents, and full-screen presentation policy, hand off to the `swiftui-navigation` skill.

## Common Mistakes

1. Placing `GeometryReader` inside lazy containers defeats lazy loading; use `.onGeometryChange` when dimensions are needed.
2. Array indices make unstable `ForEach` IDs and produce incorrect diffing.
3. Same-axis nested scroll views create gesture conflicts.
4. Heavy custom or expanding `List` rows belong in `ScrollView` + `LazyVStack`.
5. Large option sets should use menu or inline picker styles, not `.segmented`.
6. Omit stack/grid `spacing:` for platform-adaptive defaults unless a specific gap is intentional.
7. Drive a scroll reveal from one normalized progress value, not parallel booleans or a duplicate drag gesture.
8. Keep per-frame scroll geometry local and avoid changing the geometry used to calculate progress.

## Review Checklist

- [ ] `LazyVStack`/`LazyHStack` used for large or dynamic collections
- [ ] Stable `Identifiable` IDs on all `ForEach` items (not array indices)
- [ ] No `GeometryReader` inside lazy containers
- [ ] `List` style matches context (`.plain` for feeds, `.insetGrouped` for settings)
- [ ] `Form` used for structured input screens (not custom stacks)
- [ ] `.searchable` debounces input with `.task(id:)`
- [ ] `.refreshable` added where data source supports pull-to-refresh
- [ ] Overlays use transitions and auto-dismiss timers
- [ ] `.contentShape(Rectangle())` on tappable rows
- [ ] `@FocusState` manages keyboard focus in forms
- [ ] Stack/grid `spacing:` omitted unless a specific value is required
- [ ] Scroll-driven reveals use one normalized progress value and keep geometry updates in a narrow subtree
- [ ] Conflicting zoom/crop interactions disable scrolling, and discrete visibility effects do not drive continuous animation

## References

- Grid patterns: [references/grids.md](references/grids.md)
- List and section patterns: [references/list.md](references/list.md)
- ScrollView and lazy stacks: [references/scrollview.md](references/scrollview.md)
- Form patterns: [references/form.md](references/form.md)
- Architecture and state management: see `swiftui-patterns` skill
- Navigation patterns: see `swiftui-navigation` skill
