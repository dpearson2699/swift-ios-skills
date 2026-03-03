# Components Index

Use this file to find component-specific guidance. Each entry lists when to use it.

## Architecture and Wiring

| Component | File | When to Use |
|-----------|------|-------------|
| App wiring | `app-wiring.md` | Wire TabView + NavigationStack + sheets at root; install global dependencies |
| Lightweight clients | `lightweight-clients.md` | Small, closure-based API clients injected into stores |
| Deep links | `deeplinks.md` | In-app navigation from URLs |

## Navigation

| Component | File | When to Use |
|-----------|------|-------------|
| NavigationStack | `navigationstack.md` | Push navigation and programmatic routing, per-tab history |
| TabView | `tabview.md` | Tab-based app or any tabbed feature set |
| Sheets | `sheets.md` | Centralized, enum-driven sheet/modal presentation |
| Split views | `split-views.md` | iPad/macOS multi-column layouts or custom secondary columns |

## Lists and Layout

| Component | File | When to Use |
|-----------|------|-------------|
| List and Section | `list.md` | Feed-style content, settings rows, grouped data |
| ScrollView and Lazy stacks | `scrollview.md` | Custom layouts, horizontal scrollers |
| Grids | `grids.md` | Icon pickers, media galleries, tiled layouts |

## Input and Controls

| Component | File | When to Use |
|-----------|------|-------------|
| Form and Settings | `form.md` | Settings, grouped inputs, structured data entry |
| Controls | `controls.md` | Toggles, pickers, sliders, and settings controls |
| Focus handling | `focus.md` | Chaining fields and keyboard focus management |
| Searchable | `searchable.md` | Native search UI with scopes and async results |
| Input toolbar | `input-toolbar.md` | Chat/composer screens with sticky bottom input bar |

## Presentation and Feedback

| Component | File | When to Use |
|-----------|------|-------------|
| Overlay and toasts | `overlay.md` | Transient UI like banners or toasts |
| Loading and placeholders | `loading-placeholders.md` | Redacted skeletons, empty states, loading UX |
| Matched transitions | `matched-transitions.md` | Smooth source-to-destination animations |
| Haptics | `haptics.md` | Tactile feedback tied to key actions |

## Platform-Specific

| Component | File | When to Use |
|-----------|------|-------------|
| Top bar overlays | `top-bar.md` | Pinned selectors or pills above scroll content (iOS 26+ and fallback) |
| Title menus | `title-menus.md` | Filter or context menus in the navigation title |
| Menu bar commands | `menu-bar.md` | macOS/iPadOS menu bar commands |
| macOS Settings | `macos-settings.md` | macOS Settings window with SwiftUI Settings scene |

## Media and Theming

| Component | File | When to Use |
|-----------|------|-------------|
| Async images and media | `media.md` | Remote media, previews, media viewers |
| Theming and dynamic type | `theming.md` | App-wide theme tokens, colors, type scaling |

## Adding Entries

- Create `<component>.md` with intent, minimal usage pattern, pitfalls, and performance notes
- Add the component to the appropriate table above with a short "when to use" description
