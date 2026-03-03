# MV Patterns Reference

Default to Model-View (MV) in SwiftUI. Views are lightweight state expressions; models and services own business logic. Do not introduce view models unless the existing code already requires them.

## Core Principles

- Views orchestrate UI flow using `@State`, `@Environment`, `@Query`, `.task`, and `.onChange`
- Services and shared models live in the environment, are testable in isolation, and encapsulate complexity
- Split large views into smaller subviews rather than introducing a view model
- Test models, services, and business logic; views should stay simple and declarative

## Why Not MVVM

SwiftUI views are structs -- lightweight, disposable, and recreated frequently. Adding a ViewModel means fighting the framework's core design. Apple's own WWDC sessions (*Data Flow Through SwiftUI*, *Data Essentials in SwiftUI*, *Discover Observation in SwiftUI*) barely mention ViewModels.

Every ViewModel adds:
- More complexity and objects to synchronize
- More indirection and cognitive overhead
- Manual data fetching that duplicates SwiftUI/SwiftData mechanisms

## MV Pattern in Practice

### View with Environment-Injected Service

```swift
struct FeedView: View {
    @Environment(FeedClient.self) private var client
    @Environment(AppTheme.self) private var theme

    enum ViewState {
        case loading, error(String), loaded([Post])
    }

    @State private var viewState: ViewState = .loading
    @State private var isRefreshing = false

    var body: some View {
        NavigationStack {
            List {
                switch viewState {
                case .loading:
                    ProgressView("Loading feed...")
                        .frame(maxWidth: .infinity)
                        .listRowSeparator(.hidden)
                case .error(let message):
                    ContentUnavailableView("Error", systemImage: "exclamationmark.triangle",
                                           description: Text(message))
                    .listRowSeparator(.hidden)
                case .loaded(let posts):
                    ForEach(posts) { post in
                        PostRowView(post: post)
                    }
                }
            }
            .listStyle(.plain)
            .refreshable { await loadFeed() }
            .task { await loadFeed() }
        }
    }

    private func loadFeed() async {
        do {
            let posts = try await client.getFeed()
            viewState = .loaded(posts)
        } catch {
            viewState = .error(error.localizedDescription)
        }
    }
}
```

### Using .task(id:) and .onChange

SwiftUI modifiers act as small state reducers:

```swift
.task(id: searchText) {
    guard !searchText.isEmpty else { return }
    await searchFeed(query: searchText)
}
.onChange(of: isInSearch, initial: false) {
    guard !isInSearch else { return }
    Task { await fetchSuggestedFeed() }
}
```

### App-Level Environment Setup

```swift
@main
struct MyApp: App {
    @State var client = APIClient()
    @State var auth = Auth()
    @State var router = AppRouter(initialTab: .feed)

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environment(client)
                .environment(auth)
                .environment(router)
        }
    }
}
```

All dependencies are injected once and available everywhere.

### SwiftData: The Perfect MV Example

SwiftData was built to work directly in views:

```swift
struct BookListView: View {
    @Query private var books: [Book]
    @Environment(\.modelContext) private var modelContext

    var body: some View {
        List {
            ForEach(books) { book in
                BookRowView(book: book)
                    .swipeActions {
                        Button("Delete", role: .destructive) {
                            modelContext.delete(book)
                        }
                    }
            }
        }
    }
}
```

Forcing a ViewModel here means manual fetching, manual refresh, and boilerplate everywhere.

## When a View Model Already Exists

If a view model exists in the codebase:
- Make it non-optional when possible
- Pass dependencies via `init`, then forward them into the view model in the view's `init`
- Store as `@State` in the root view that owns it
- Avoid `bootstrapIfNeeded` patterns

```swift
@State private var viewModel: SomeViewModel

init(dependency: Dependency) {
    _viewModel = State(initialValue: SomeViewModel(dependency: dependency))
}
```

## Testing Strategy

- Unit test services and business logic
- Test models and transformations
- Use SwiftUI previews for visual regression
- Use UI automation for end-to-end tests
- Views should be simple enough that they do not need dedicated unit tests

## Source

Based on guidance from "SwiftUI in 2025: Forget MVVM" (Thomas Ricouard) and Apple WWDC sessions on SwiftUI data flow.
