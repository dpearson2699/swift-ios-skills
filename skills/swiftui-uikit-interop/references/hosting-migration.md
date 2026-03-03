# UIKit-to-SwiftUI Migration Patterns

Patterns for incrementally migrating a UIKit app to SwiftUI. Each pattern is self-contained with rationale, implementation, and gotchas.

---

## 1. Screen-by-Screen Migration

Replace one `UIViewController` at a time with a `UIHostingController` wrapping a SwiftUI view. This is the safest migration path -- each screen is an isolated unit.

### Strategy

1. Pick a leaf screen (one that does not contain child view controllers).
2. Rewrite its UI in SwiftUI.
3. Replace the UIKit view controller with `UIHostingController` wherever it was instantiated.
4. Wire navigation from the parent UIKit code into the hosting controller.

### Implementation

```swift
// BEFORE: UIKit screen pushed onto a navigation stack
let detailVC = ItemDetailViewController(item: item)
navigationController?.pushViewController(detailVC, animated: true)

// AFTER: SwiftUI screen wrapped in UIHostingController
let detailView = ItemDetailView(item: item)
let hostingVC = UIHostingController(rootView: detailView)
navigationController?.pushViewController(hostingVC, animated: true)
```

### Passing Dismiss/Navigation Callbacks

When the SwiftUI screen needs to pop itself or trigger navigation in the UIKit stack:

```swift
struct ItemDetailView: View {
    let item: Item
    var onDelete: (() -> Void)?

    @Environment(\.dismiss) private var dismiss

    var body: some View {
        VStack {
            Text(item.title)
            Button("Delete", role: .destructive) {
                onDelete?()
                dismiss()
            }
        }
    }
}

// In UIKit:
let detailView = ItemDetailView(item: item) {
    self.dataSource.delete(item)
    self.navigationController?.popViewController(animated: true)
}
let hostingVC = UIHostingController(rootView: detailView)
```

### Gotchas

- **Navigation bar.** `UIHostingController` inherits navigation bar visibility from its parent `UINavigationController`. Use `.navigationTitle()` and `.toolbar()` in the SwiftUI view -- they propagate to the UIKit navigation bar automatically.
- **Large titles.** Set `hostingVC.navigationItem.largeTitleDisplayMode` in UIKit code if the SwiftUI `.navigationBarTitleDisplayMode()` modifier does not apply correctly.
- **Tab bar insets.** `UIHostingController` respects `additionalSafeAreaInsets`. If the content overlaps the tab bar, verify safe area propagation.

---

## 2. UIHostingController as Child

Embed SwiftUI sections within an existing UIKit screen. Use when migrating part of a screen (a header, a card, a section) before rewriting the entire controller.

### Implementation

```swift
final class DashboardViewController: UIViewController {
    private var statsHostingController: UIHostingController<StatsCardView>?

    override func viewDidLoad() {
        super.viewDidLoad()

        let statsView = StatsCardView(stats: currentStats)
        let hostingVC = UIHostingController(rootView: statsView)

        // Enable intrinsic sizing so Auto Layout can size the hosted view
        if #available(iOS 16.0, *) {
            hostingVC.sizingOptions = [.intrinsicContentSize]
        }

        addChild(hostingVC)
        hostingVC.view.translatesAutoresizingMaskIntoConstraints = false
        containerView.addSubview(hostingVC.view)

        NSLayoutConstraint.activate([
            hostingVC.view.topAnchor.constraint(equalTo: containerView.topAnchor),
            hostingVC.view.leadingAnchor.constraint(equalTo: containerView.leadingAnchor),
            hostingVC.view.trailingAnchor.constraint(equalTo: containerView.trailingAnchor),
            hostingVC.view.bottomAnchor.constraint(equalTo: containerView.bottomAnchor),
        ])

        hostingVC.didMove(toParent: self)
        statsHostingController = hostingVC
    }

    func updateStats(_ stats: Stats) {
        statsHostingController?.rootView = StatsCardView(stats: stats)
    }
}
```

### With @Observable Model

Pass an `@Observable` model to avoid reassigning `rootView` manually. SwiftUI tracks changes automatically:

```swift
@Observable
final class DashboardModel {
    var stats: Stats = .empty
    var isLoading = false
}

struct StatsCardView: View {
    let model: DashboardModel

    var body: some View {
        // Automatically re-renders when model.stats changes
        if model.isLoading {
            ProgressView()
        } else {
            StatsGrid(stats: model.stats)
        }
    }
}

// In UIKit:
let model = DashboardModel()
let hostingVC = UIHostingController(rootView: StatsCardView(model: model))

// Later -- just mutate the model, no rootView reassignment needed
model.stats = newStats
```

### Gotchas

- **Background color.** `UIHostingController`'s view has an opaque system background by default. Set `hostingVC.view.backgroundColor = .clear` if embedding over existing content.
- **sizingOptions on iOS 16+.** Without `.intrinsicContentSize`, the hosted view may report zero size in Auto Layout, causing the container to collapse.
- **Memory.** Store the hosting controller in a property. If it is only held as a child, removing it from the parent deallocates it and the SwiftUI view disappears.

---

## 3. Navigation Bridging

Mix UIKit and SwiftUI screens in the same `UINavigationController` stack.

### UIKit Pushing SwiftUI

```swift
// From a UIKit view controller, push a SwiftUI screen
func showProfile(for user: User) {
    let profileView = ProfileView(user: user)
    let hostingVC = UIHostingController(rootView: profileView)
    hostingVC.title = user.name
    navigationController?.pushViewController(hostingVC, animated: true)
}
```

### SwiftUI Pushing UIKit

Use a coordinator or `UIViewControllerRepresentable` bridge:

```swift
struct ProfileView: View {
    let user: User
    @State private var showLegacyEditor = false

    var body: some View {
        List {
            // ... profile content
            Button("Edit (Legacy)") { showLegacyEditor = true }
        }
        .sheet(isPresented: $showLegacyEditor) {
            LegacyEditorWrapper(user: user)
        }
    }
}

struct LegacyEditorWrapper: UIViewControllerRepresentable {
    let user: User

    func makeUIViewController(context: Context) -> UINavigationController {
        let editor = ProfileEditorViewController(user: user)
        return UINavigationController(rootViewController: editor)
    }

    func updateUIViewController(_ uiViewController: UINavigationController, context: Context) {}
}
```

### Passing NavigationController Reference

For deep integration where SwiftUI needs to push onto the UIKit navigation stack:

```swift
struct NavigationBridge {
    weak var navigationController: UINavigationController?

    func push(_ viewController: UIViewController, animated: Bool = true) {
        navigationController?.pushViewController(viewController, animated: animated)
    }

    func push<V: View>(_ view: V, title: String? = nil, animated: Bool = true) {
        let hostingVC = UIHostingController(rootView: view)
        hostingVC.title = title
        navigationController?.pushViewController(hostingVC, animated: animated)
    }
}

// Inject via environment
private struct NavigationBridgeKey: EnvironmentKey {
    static let defaultValue = NavigationBridge()
}

extension EnvironmentValues {
    var navigationBridge: NavigationBridge {
        get { self[NavigationBridgeKey.self] }
        set { self[NavigationBridgeKey.self] = newValue }
    }
}
```

### Gotchas

- **Back button.** When pushing `UIHostingController` onto a `UINavigationController`, the back button works automatically. Do not add a manual back button in the SwiftUI view.
- **Double navigation bars.** If the SwiftUI view uses `NavigationStack`, it creates its own navigation bar inside the UIKit one. Remove `NavigationStack` from SwiftUI views presented inside `UINavigationController`.
- **Toolbar items.** SwiftUI `.toolbar` items propagate to the UIKit navigation bar when hosted in `UIHostingController`. This works reliably on iOS 16+.

---

## 4. Data Sharing Between UIKit and SwiftUI

### Using @Observable (iOS 17+)

The cleanest approach. Create an `@Observable` model, pass it to both UIKit and SwiftUI code:

```swift
@Observable
final class AppState {
    var currentUser: User?
    var unreadCount: Int = 0
    var theme: AppTheme = .system
}

// UIKit side -- read properties directly
let state = AppState()
func viewDidLoad() {
    titleLabel.text = state.currentUser?.name
}

// SwiftUI side -- observation is automatic
struct HeaderView: View {
    let state: AppState

    var body: some View {
        HStack {
            Text(state.currentUser?.name ?? "Guest")
            if state.unreadCount > 0 {
                Badge(count: state.unreadCount)
            }
        }
    }
}
```

### Reactive Updates in UIKit with Combine

If UIKit code needs to react to `@Observable` changes, bridge with a `withObservationTracking` loop or use `Combine`:

```swift
import Combine
import Observation

final class DashboardViewController: UIViewController {
    let state: AppState
    private var observationTask: Task<Void, Never>?

    override func viewDidLoad() {
        super.viewDidLoad()
        startObserving()
    }

    private func startObserving() {
        observationTask = Task { @MainActor [weak self] in
            while !Task.isCancelled {
                guard let self else { return }
                withObservationTracking {
                    self.updateUI(unreadCount: self.state.unreadCount)
                } onChange: {
                    // Triggers next iteration
                }
                try? await Task.sleep(for: .zero) // Yield to allow onChange to fire
            }
        }
    }

    private func updateUI(unreadCount: Int) {
        badgeLabel.text = "\(unreadCount)"
    }

    deinit { observationTask?.cancel() }
}
```

### Legacy: ObservableObject with Combine

For iOS 15-16 or existing `ObservableObject` models, subscribe to `objectWillChange`:

```swift
final class SettingsViewController: UIViewController {
    let settings: SettingsModel  // ObservableObject
    private var cancellable: AnyCancellable?

    override func viewDidLoad() {
        super.viewDidLoad()
        cancellable = settings.objectWillChange
            .receive(on: RunLoop.main)
            .sink { [weak self] _ in
                self?.updateUI()
            }
    }
}
```

### Gotchas

- **`@Observable` does not trigger UIKit updates automatically.** Unlike SwiftUI views, UIKit code must manually observe changes via `withObservationTracking` or `Combine`.
- **Thread safety.** Mutate `@Observable` properties on `@MainActor` when they drive UI in both UIKit and SwiftUI.
- **Retain cycles.** Use `[weak self]` in Combine sinks and task closures. Store cancellables and tasks, then cancel in `deinit`.

---

## 5. UIHostingConfiguration (iOS 16+)

Render SwiftUI content inside `UICollectionViewCell` and `UITableViewCell` without managing a child `UIHostingController`. This is the preferred approach for cells in a UIKit collection or table view.

### UICollectionView with SwiftUI Cells

```swift
@available(iOS 16.0, *)
func collectionView(
    _ collectionView: UICollectionView,
    cellForItemAt indexPath: IndexPath
) -> UICollectionViewCell {
    let cell = collectionView.dequeueReusableCell(
        withReuseIdentifier: "cell",
        for: indexPath
    )
    let item = dataSource[indexPath.item]

    cell.contentConfiguration = UIHostingConfiguration {
        HStack {
            AsyncImage(url: item.imageURL) { image in
                image.resizable().scaledToFill()
            } placeholder: {
                ProgressView()
            }
            .frame(width: 60, height: 60)
            .clipShape(RoundedRectangle(cornerRadius: 8))

            VStack(alignment: .leading) {
                Text(item.title).font(.headline)
                Text(item.subtitle).font(.subheadline).foregroundStyle(.secondary)
            }
        }
    }
    .margins(.all, 12)

    return cell
}
```

### UITableView with SwiftUI Cells

```swift
@available(iOS 16.0, *)
func tableView(
    _ tableView: UITableView,
    cellForRowAt indexPath: IndexPath
) -> UITableViewCell {
    let cell = tableView.dequeueReusableCell(withIdentifier: "cell", for: indexPath)
    let item = items[indexPath.row]

    cell.contentConfiguration = UIHostingConfiguration {
        ItemRowView(item: item)
    }

    return cell
}
```

### Self-Sizing

`UIHostingConfiguration` cells self-size automatically. Ensure:
- The table/collection view uses `UICollectionViewCompositionalLayout` with estimated dimensions, or `tableView.rowHeight = UITableView.automaticDimension`.
- The SwiftUI content has defined height (via content or explicit `.frame`).

### Background Customization

```swift
cell.contentConfiguration = UIHostingConfiguration {
    ItemRowView(item: item)
}
.background {
    RoundedRectangle(cornerRadius: 12)
        .fill(.background)
}
.margins(.horizontal, 16)
.minSize(height: 60)
```

### Gotchas

- **Performance.** Each `UIHostingConfiguration` creates a lightweight hosting controller. For very large lists (10,000+ items), profile with Instruments to ensure smooth scrolling.
- **State management.** The SwiftUI content inside `UIHostingConfiguration` is recreated on each cell reuse. Do not store `@State` that needs to persist across reuse -- use the data model instead.
- **Swipe actions.** Configure swipe actions in UIKit (`leadingSwipeActionsConfigurationForRowAt`), not inside the SwiftUI content.
- **No `@Environment` propagation by default.** Environment values from the UIKit context are not automatically available. Inject them explicitly in the `UIHostingConfiguration` closure.

---

## 6. Environment Bridging

Pass SwiftUI environment values into hosted SwiftUI views from UIKit, and access UIKit traits from SwiftUI.

### Injecting Environment into UIHostingController

```swift
let model = AppState()
let settingsView = SettingsView()
    .environment(model)
    .environment(\.locale, Locale(identifier: "en_US"))

let hostingVC = UIHostingController(rootView: settingsView)
```

Apply environment modifiers to the root view before passing it to the hosting controller. The hosting controller does not support adding environment values after creation (you would need to reassign `rootView`).

### Trait Collection to SwiftUI Environment

`UIHostingController` automatically bridges these UIKit trait collections to SwiftUI environment values:

| UIKit Trait | SwiftUI Environment |
|------------|-------------------|
| `userInterfaceStyle` | `\.colorScheme` |
| `horizontalSizeClass` | `\.horizontalSizeClass` |
| `verticalSizeClass` | `\.verticalSizeClass` |
| `preferredContentSizeCategory` | `\.dynamicTypeSize` |
| `layoutDirection` | `\.layoutDirection` |
| `legibilityWeight` | `\.legibilityWeight` |

These update automatically when the UIKit trait environment changes (device rotation, split view resize, accessibility settings change).

### Custom Environment Values Across the Bridge

Define a custom environment key and set it from UIKit:

```swift
private struct UserRoleKey: EnvironmentKey {
    static let defaultValue: UserRole = .guest
}

extension EnvironmentValues {
    var userRole: UserRole {
        get { self[UserRoleKey.self] }
        set { self[UserRoleKey.self] = newValue }
    }
}

// UIKit side:
let role = authManager.currentRole
let profileView = ProfileView().environment(\.userRole, role)
let hostingVC = UIHostingController(rootView: profileView)

// SwiftUI side:
struct ProfileView: View {
    @Environment(\.userRole) private var role

    var body: some View {
        if role == .admin {
            AdminDashboard()
        } else {
            UserDashboard()
        }
    }
}
```

### Updating Environment After Creation

To change environment values after the hosting controller is created, wrap the root view in a container that takes a binding or observable:

```swift
struct EnvironmentBridge<Content: View>: View {
    let state: AppState  // @Observable
    let content: Content

    var body: some View {
        content
            .environment(state)
            .environment(\.userRole, state.currentRole)
    }
}

// UIKit:
let state = AppState()
let bridge = EnvironmentBridge(state: state, content: SettingsView())
let hostingVC = UIHostingController(rootView: bridge)

// Later: mutating state.currentRole updates the environment automatically
state.currentRole = .admin
```

### Gotchas

- **`@Environment(\.dismiss)` in hosted views.** This works when the `UIHostingController` is presented modally (via `present(_:animated:)`). It does NOT work when the hosting controller is pushed onto a `UINavigationController` -- use the navigation controller's `popViewController` instead.
- **Missing environment.** If a SwiftUI view expects an `@Environment` object and it is not provided, the app crashes at runtime. Always set required environment values before creating the hosting controller.
- **Overriding traits.** Use `hostingVC.overrideUserInterfaceStyle` to force light/dark mode for a hosted SwiftUI view. This propagates to `\.colorScheme` automatically.
