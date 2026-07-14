# List and Section

## Contents

- [Intent](#intent)
- [Core patterns](#core-patterns)
- [Example: feed list with scroll-to-top](#example-feed-list-with-scroll-to-top)
- [Example: settings-style list](#example-settings-style-list)
- [Design choices to keep](#design-choices-to-keep)
- [iOS 26 Scroll Edge Effects](#ios-26-scroll-edge-effects)
- [Pitfalls](#pitfalls)

## Intent

Use `List` for feed-style content and settings-style rows where built-in row reuse, selection, and accessibility matter.

## Core patterns

- Prefer `List` for long, vertically scrolling content with repeated rows.
- Use `Section` headers to group related rows.
- **Edge scrolls:** use `List` + `ScrollPosition` with
  `.scrollPosition($scrollPosition)` for top/bottom scroll actions on iOS 18+.
- **Item or section jumps:** use `ScrollView` + `LazyVStack` with
  `.scrollTargetLayout()` and stable explicit IDs for reliable jump-to-id
  behavior; do not assume `List` section headers are scroll targets.
- Use `.listStyle(.plain)` for modern feed layouts.
- Use `.listStyle(.grouped)` for multi-section discovery/search pages where section grouping helps.
- Apply `.scrollContentBackground(.hidden)` + a custom background when you need a themed surface.
- Use `.listRowInsets(...)` and `.listRowSeparator(.hidden)` to tune row spacing and separators.
- Use `.environment(\.defaultMinListRowHeight, ...)` to control dense list layouts.

## Example: feed list with scroll-to-top

```swift
@MainActor
struct TimelineListView: View {
  @Environment(\.selectedTabScrollToTop) private var selectedTabScrollToTop
  @State private var scrollPosition = ScrollPosition(idType: String.self)

  var body: some View {
    List {
      ForEach(items) { item in
        TimelineRow(item: item)
          .id(item.id)
          .listRowInsets(.init(top: 12, leading: 16, bottom: 12, trailing: 16))
          .listRowSeparator(.hidden)
      }
    }
    .listStyle(.plain)
    .environment(\.defaultMinListRowHeight, 1)
    .scrollPosition($scrollPosition)
    .onChange(of: selectedTabScrollToTop) {
      withAnimation {
        scrollPosition.scrollTo(edge: .top)
      }
    }
  }
}
```

## Example: settings-style list

```swift
@MainActor
struct SettingsView: View {
  var body: some View {
    List {
      Section("General") {
        NavigationLink("Display") { DisplaySettingsView() }
        NavigationLink("Haptics") { HapticsSettingsView() }
      }
      Section("Account") {
        Button("Sign Out", role: .destructive) {}
      }
    }
    .listStyle(.insetGrouped)
  }
}
```

## Design choices to keep

- Use `List` for dynamic feeds, settings, and any UI where row semantics help.
- Use stable IDs for rows to keep diffing and scroll positioning reliable.
- Prefer `.contentShape(Rectangle())` on rows that should be tappable end-to-end.
- Use `.refreshable` for pull-to-refresh feeds when the data source supports it.
- Treat dynamically changing row heights as a practical `List` gotcha:
  expanding or collapsing row content may snap instead of smoothly
  interpolating. Keep `List` rows structurally simple, or move complex
  expanding content to `ScrollView` + `LazyVStack`. Frame this as a
  container/layout decision, not as a full animation recipe. Do not prescribe
  spring parameters, transition styles, or animation timing here; defer those
  choices to `swiftui-animation`.

## iOS 26 Scroll Edge Effects

Apply edge effects to lists for modern scroll behavior:

```swift
List {
    // rows
}
.scrollEdgeEffectStyle(.soft, for: .top)
```

See `scrollview.md` for the full scroll edge effect and `backgroundExtensionEffect()` API reference.

## Pitfalls

- Avoid heavy custom layouts inside a `List` row; use `ScrollView` + `LazyVStack` instead.
- Be careful mixing `List` and nested `ScrollView`; it can cause gesture conflicts.
