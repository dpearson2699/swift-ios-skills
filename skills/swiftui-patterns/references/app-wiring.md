# App Wiring and Dependency Graph

## Intent

Wire the app shell (TabView + NavigationStack + sheets) and install a global dependency graph (environment objects, services, streaming clients, SwiftData ModelContainer) in one place.

## Recommended Structure

1. Root view sets up tabs, per-tab routers, and sheets.
2. A dedicated view modifier installs global dependencies and lifecycle tasks (auth state, streaming watchers, push tokens, data containers).
3. Feature views pull only what they need from the environment; feature-specific state stays local.

## Root Shell Example

```swift
@MainActor
struct AppView: View {
    @State private var selectedTab: AppTab = .home
    @State private var tabRouter = TabRouter()

    var body: some View {
        TabView(selection: $selectedTab) {
            ForEach(AppTab.allCases) { tab in
                let router = tabRouter.router(for: tab)
                Tab(value: tab) {
                    NavigationStack(path: tabRouter.binding(for: tab)) {
                        tab.makeContentView()
                    }
                    .withSheetDestinations(sheet: Binding(
                        get: { router.presentedSheet },
                        set: { router.presentedSheet = $0 }
                    ))
                    .environment(router)
                } label: {
                    tab.label
                }
            }
        }
        .tabBarMinimizeBehavior(.onScrollDown)
        .withAppDependencyGraph()
    }
}
```

### AppTab Enum

```swift
@MainActor
enum AppTab: Identifiable, Hashable, CaseIterable {
    case home, notifications, settings
    var id: String { String(describing: self) }

    @ViewBuilder
    func makeContentView() -> some View {
        switch self {
        case .home: HomeView()
        case .notifications: NotificationsView()
        case .settings: SettingsView()
        }
    }

    @ViewBuilder
    var label: some View {
        switch self {
        case .home: Label("Home", systemImage: "house")
        case .notifications: Label("Notifications", systemImage: "bell")
        case .settings: Label("Settings", systemImage: "gear")
        }
    }
}
```

### Router Skeleton

```swift
@MainActor
@Observable
final class RouterPath {
    var path: [Route] = []
    var presentedSheet: SheetDestination?
}

enum Route: Hashable {
    case detail(id: String)
}
```

## Dependency Graph Modifier

Use a single modifier to install environment objects and handle lifecycle hooks. This keeps wiring consistent and avoids forgetting a dependency at call sites.

```swift
extension View {
    func withAppDependencyGraph(
        client: APIClient = .shared,
        auth: Auth = .shared,
        theme: Theme = .shared,
        toastCenter: ToastCenter = .shared
    ) -> some View {
        environment(client)
            .environment(auth)
            .environment(theme)
            .environment(toastCenter)
            .task(id: auth.currentAccount?.id) {
                // Re-seed services when account changes
                await client.configure(for: auth.currentAccount)
            }
    }
}
```

Notes:
- The `.task(id:)` hooks respond to account/client changes, re-seeding services and watcher state.
- Keep the modifier focused on global wiring; feature-specific state stays within features.
- Adjust types to match your project.

## SwiftData / ModelContainer

Install `ModelContainer` at the root so all feature views share the same store:

```swift
extension View {
    func withModelContainer() -> some View {
        modelContainer(for: [Draft.self, LocalTimeline.self, TagGroup.self])
    }
}
```

A single container avoids duplicated stores per sheet or tab and keeps data consistent.

## Sheet Routing (Enum-Driven)

Centralize sheets with a small enum and a helper modifier:

```swift
enum SheetDestination: Identifiable {
    case composer
    case settings
    var id: String { String(describing: self) }
}

extension View {
    func withSheetDestinations(sheet: Binding<SheetDestination?>) -> some View {
        sheet(item: sheet) { destination in
            switch destination {
            case .composer:
                ComposerView().withEnvironments()
            case .settings:
                SettingsView().withEnvironments()
            }
        }
    }
}
```

Enum-driven sheets keep presentation centralized and testable; adding a new sheet means one enum case and one switch branch.

## App Entry Point

```swift
@main
struct MyApp: App {
    @State var client = APIClient()
    @State var auth = Auth()
    @State var router = AppRouter(initialTab: .home)

    var body: some Scene {
        WindowGroup {
            AppView()
                .environment(client)
                .environment(auth)
                .environment(router)
        }
    }
}
```

## Deep Linking

Store `NavigationPath` as `Codable` for state restoration. Handle incoming URLs with `.onOpenURL`:

```swift
.onOpenURL { url in
    guard let route = Route(from: url) else { return }
    router.navigate(to: route)
}
```

See `deeplinks.md` for full URL routing patterns.

## When to Use

- Apps with multiple packages/modules that share environment objects and services
- Apps that need to react to account/client changes and rewire streaming/push safely
- Any app that wants consistent TabView + NavigationStack + sheet wiring without repeating environment setup

## Caveats

- Keep the dependency modifier slim; do not put feature state or heavy logic there
- Ensure `.task(id:)` work is lightweight or cancelled appropriately; long-running work belongs in services
- If unauthenticated clients exist, gate streaming/watch calls to avoid reconnect spam
