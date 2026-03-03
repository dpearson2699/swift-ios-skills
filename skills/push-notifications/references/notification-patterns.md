# Notification Patterns

Detailed implementation patterns for push notifications in iOS apps. Covers the complete lifecycle from AppDelegate wiring through debugging delivery issues.

## Complete AppDelegate Adaptor Setup

The full AppDelegate wiring for a SwiftUI app that handles both remote and local notifications.

```swift
import SwiftUI
import UserNotifications

@main
struct MyApp: App {
    @UIApplicationDelegateAdaptor(AppDelegate.self) var appDelegate
    @State private var router = DeepLinkRouter()

    init() {
        // Set delegate as early as possible so no notifications are missed.
        // App.init runs before application(_:didFinishLaunchingWithOptions:).
        UNUserNotificationCenter.current().delegate = NotificationDelegate.shared
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environment(router)
                .task { await setupNotifications() }
        }
    }

    private func setupNotifications() async {
        registerNotificationCategories()

        let center = UNUserNotificationCenter.current()
        let settings = await center.notificationSettings()

        switch settings.authorizationStatus {
        case .notDetermined:
            let granted = try? await center.requestAuthorization(
                options: [.alert, .sound, .badge]
            )
            if granted == true {
                await MainActor.run {
                    UIApplication.shared.registerForRemoteNotifications()
                }
            }
        case .authorized, .provisional, .ephemeral:
            await MainActor.run {
                UIApplication.shared.registerForRemoteNotifications()
            }
        case .denied:
            // User denied -- do not prompt again. Show in-app UI if needed.
            break
        @unknown default:
            break
        }
    }
}
```

### AppDelegate Class

```swift
class AppDelegate: NSObject, UIApplicationDelegate {
    func application(
        _ application: UIApplication,
        didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil
    ) -> Bool {
        // Delegate may also be set here if not set in App.init.
        // Setting in App.init is preferred because it runs earlier.
        return true
    }

    func application(
        _ application: UIApplication,
        didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data
    ) {
        let token = deviceToken.map { String(format: "%02x", $0) }.joined()
        print("APNs device token: \(token)")

        // Always send token to server -- tokens can change between launches.
        Task { @MainActor in
            await TokenService.shared.upload(token: token)
        }
    }

    func application(
        _ application: UIApplication,
        didFailToRegisterForRemoteNotificationsWithError error: Error
    ) {
        #if targetEnvironment(simulator)
        // Simulator cannot register for remote notifications. This is expected.
        print("Simulator: APNs registration not available.")
        #else
        print("APNs registration failed: \(error.localizedDescription)")
        // Log to your analytics/crash reporting service
        #endif
    }

    // Silent push / background notification handler
    func application(
        _ application: UIApplication,
        didReceiveRemoteNotification userInfo: [AnyHashable: Any]
    ) async -> UIBackgroundFetchResult {
        await BackgroundNotificationHandler.shared.handle(userInfo: userInfo)
    }
}
```

## Full UNUserNotificationCenterDelegate

```swift
@MainActor
final class NotificationDelegate: NSObject, UNUserNotificationCenterDelegate, Sendable {
    static let shared = NotificationDelegate()

    private override init() { super.init() }

    /// Called when a notification arrives while the app is in the foreground.
    /// Return which presentation options to use. Without this method,
    /// foreground notifications are silently suppressed.
    func userNotificationCenter(
        _ center: UNUserNotificationCenter,
        willPresent notification: UNNotification
    ) async -> UNNotificationPresentationOptions {
        let userInfo = notification.request.content.userInfo

        // Example: suppress banner for the chat screen the user is already viewing
        if let chatId = userInfo["chatId"] as? String,
           NavigationState.shared.currentChatId == chatId {
            // Still update badge/list but do not show a banner
            return [.badge, .list, .sound]
        }

        return [.banner, .sound, .badge, .list]
    }

    /// Called when the user taps the notification or a notification action button.
    func userNotificationCenter(
        _ center: UNUserNotificationCenter,
        didReceive response: UNNotificationResponse
    ) async {
        let userInfo = response.notification.request.content.userInfo
        let categoryIdentifier = response.notification.request.content.categoryIdentifier

        switch response.actionIdentifier {
        case UNNotificationDefaultActionIdentifier:
            await routeNotificationTap(category: categoryIdentifier, userInfo: userInfo)

        case UNNotificationDismissActionIdentifier:
            // User swiped away the notification. Only fires if the category
            // was created with .customDismissAction option.
            break

        default:
            // Custom action button
            await handleAction(
                response.actionIdentifier,
                category: categoryIdentifier,
                response: response,
                userInfo: userInfo
            )
        }
    }

    // MARK: - Routing

    private func routeNotificationTap(
        category: String,
        userInfo: [AnyHashable: Any]
    ) async {
        switch category {
        case "MESSAGE_CATEGORY":
            guard let chatId = userInfo["chatId"] as? String else { return }
            DeepLinkRouter.shared.navigate(to: .chat(id: chatId))

        case "WORKOUT_CATEGORY":
            guard let workoutId = userInfo["workoutId"] as? String else { return }
            DeepLinkRouter.shared.navigate(to: .workout(id: workoutId))

        default:
            // Unknown category -- open the app to its default state
            break
        }
    }

    private func handleAction(
        _ actionIdentifier: String,
        category: String,
        response: UNNotificationResponse,
        userInfo: [AnyHashable: Any]
    ) async {
        switch (category, actionIdentifier) {
        case ("MESSAGE_CATEGORY", "REPLY_ACTION"):
            guard let textResponse = response as? UNTextInputNotificationResponse,
                  let chatId = userInfo["chatId"] as? String else { return }
            await MessageService.shared.sendReply(
                text: textResponse.userText,
                chatId: chatId
            )

        case ("MESSAGE_CATEGORY", "LIKE_ACTION"):
            guard let messageId = userInfo["messageId"] as? String else { return }
            await MessageService.shared.likeMessage(id: messageId)

        case ("MESSAGE_CATEGORY", "MARK_READ_ACTION"):
            guard let chatId = userInfo["chatId"] as? String else { return }
            await MessageService.shared.markAsRead(chatId: chatId)

        default:
            break
        }
    }
}
```

## Deep Link Router

An `@Observable` router that bridges notification taps to SwiftUI navigation. The router holds a pending destination that the view layer observes and consumes.

```swift
@Observable
@MainActor
final class DeepLinkRouter {
    static let shared = DeepLinkRouter()

    var pendingDestination: AppDestination?

    func navigate(to destination: AppDestination) {
        pendingDestination = destination
    }
}

enum AppDestination: Hashable {
    case chat(id: String)
    case workout(id: String)
    case profile(userId: String)
    case settings
}

// In the root view:
struct RootView: View {
    @Environment(DeepLinkRouter.self) private var router
    @State private var selectedTab: Tab = .home
    @State private var homePath = NavigationPath()
    @State private var chatPath = NavigationPath()

    var body: some View {
        TabView(selection: $selectedTab) {
            Tab("Home", systemImage: "house", value: .home) {
                NavigationStack(path: $homePath) {
                    HomeView()
                        .navigationDestination(for: AppDestination.self) { dest in
                            destinationView(for: dest)
                        }
                }
            }
            Tab("Chat", systemImage: "message", value: .chat) {
                NavigationStack(path: $chatPath) {
                    ChatListView()
                        .navigationDestination(for: AppDestination.self) { dest in
                            destinationView(for: dest)
                        }
                }
            }
        }
        .onChange(of: router.pendingDestination) { _, destination in
            guard let destination else { return }
            handleDeepLink(destination)
            router.pendingDestination = nil
        }
    }

    private func handleDeepLink(_ destination: AppDestination) {
        switch destination {
        case .chat:
            selectedTab = .chat
            chatPath = NavigationPath()
            chatPath.append(destination)
        case .workout:
            selectedTab = .home
            homePath = NavigationPath()
            homePath.append(destination)
        case .profile, .settings:
            selectedTab = .home
            homePath = NavigationPath()
            homePath.append(destination)
        }
    }

    @ViewBuilder
    private func destinationView(for destination: AppDestination) -> some View {
        switch destination {
        case .chat(let id): ChatDetailView(chatId: id)
        case .workout(let id): WorkoutDetailView(workoutId: id)
        case .profile(let userId): ProfileView(userId: userId)
        case .settings: SettingsView()
        }
    }
}
```

## Silent Push Handler

Silent pushes wake the app in the background to fetch new content. The system gives approximately 30 seconds of background execution time. Return the correct `UIBackgroundFetchResult` so the system can learn the app's data patterns and schedule future wakes efficiently.

```swift
@MainActor
final class BackgroundNotificationHandler: Sendable {
    static let shared = BackgroundNotificationHandler()

    func handle(userInfo: [AnyHashable: Any]) async -> UIBackgroundFetchResult {
        guard let action = userInfo["action"] as? String else {
            return .noData
        }

        do {
            switch action {
            case "sync":
                let hasNewData = try await DataSyncService.shared.performSync()
                return hasNewData ? .newData : .noData

            case "refresh-config":
                try await ConfigService.shared.refreshRemoteConfig()
                return .newData

            case "clear-cache":
                await CacheManager.shared.clearExpired()
                return .newData

            default:
                return .noData
            }
        } catch {
            print("Background notification handling failed: \(error)")
            return .failed
        }
    }
}
```

**Important:** The Background Modes capability with "Remote notifications" must be enabled in the Xcode project for silent push to work. Without it, `didReceiveRemoteNotification` is never called for silent pushes.

## Notification Scheduling Manager

A service that encapsulates local notification scheduling, making it testable and reusable.

```swift
@MainActor
final class NotificationScheduler {
    private let center = UNUserNotificationCenter.current()

    // MARK: - Schedule

    func scheduleReminder(
        id: String,
        title: String,
        body: String,
        at date: Date,
        repeats: Bool = false,
        categoryIdentifier: String? = nil,
        userInfo: [String: String] = [:]
    ) async throws {
        let content = UNMutableNotificationContent()
        content.title = title
        content.body = body
        content.sound = .default
        content.userInfo = userInfo
        if let category = categoryIdentifier {
            content.categoryIdentifier = category
        }

        let components = Calendar.current.dateComponents(
            [.year, .month, .day, .hour, .minute],
            from: date
        )
        let trigger = UNCalendarNotificationTrigger(
            dateMatching: components,
            repeats: repeats
        )

        let request = UNNotificationRequest(
            identifier: id,
            content: content,
            trigger: trigger
        )

        try await center.add(request)
    }

    func scheduleDailyReminder(
        id: String,
        title: String,
        body: String,
        hour: Int,
        minute: Int
    ) async throws {
        let content = UNMutableNotificationContent()
        content.title = title
        content.body = body
        content.sound = .default

        var components = DateComponents()
        components.hour = hour
        components.minute = minute

        let trigger = UNCalendarNotificationTrigger(
            dateMatching: components,
            repeats: true
        )

        let request = UNNotificationRequest(
            identifier: id,
            content: content,
            trigger: trigger
        )

        try await center.add(request)
    }

    // MARK: - Manage

    func cancelNotification(id: String) {
        center.removePendingNotificationRequests(withIdentifiers: [id])
        center.removeDeliveredNotifications(withIdentifiers: [id])
    }

    func cancelAll() {
        center.removeAllPendingNotificationRequests()
        center.removeAllDeliveredNotifications()
    }

    func pendingNotifications() async -> [UNNotificationRequest] {
        await center.pendingNotificationRequests()
    }

    func isScheduled(id: String) async -> Bool {
        let pending = await center.pendingNotificationRequests()
        return pending.contains { $0.identifier == id }
    }
}
```

## Token Refresh and Update Flow

Device tokens can change between app launches. Treat the token as ephemeral and always send the latest to your server.

```swift
@MainActor
@Observable
final class TokenService {
    static let shared = TokenService()

    private(set) var currentToken: String?

    func upload(token: String) async {
        // Skip if token has not changed since last successful upload
        if token == currentToken { return }

        do {
            try await APIClient.shared.registerDeviceToken(token)
            currentToken = token
            UserDefaults.standard.set(token, forKey: "lastUploadedAPNsToken")
        } catch {
            print("Failed to upload APNs token: \(error)")
            // Retry on next launch -- didRegisterForRemoteNotifications fires again
        }
    }

    /// Call when the user logs out to disassociate the token from their account.
    func invalidate() async {
        guard let token = currentToken else { return }
        try? await APIClient.shared.unregisterDeviceToken(token)
        currentToken = nil
        UserDefaults.standard.removeObject(forKey: "lastUploadedAPNsToken")
    }
}
```

**Logout flow:** When a user logs out, unregister the device token from your server. Otherwise the old user's account continues receiving pushes on this device.

## Category Registration

Register categories at app launch, before any notification arrives. Calling `setNotificationCategories` replaces the entire set, so register all categories in one call.

```swift
func registerNotificationCategories() {
    // Message category
    let replyAction = UNTextInputNotificationAction(
        identifier: "REPLY_ACTION",
        title: "Reply",
        options: [],
        textInputButtonTitle: "Send",
        textInputPlaceholder: "Type a reply..."
    )
    let markReadAction = UNNotificationAction(
        identifier: "MARK_READ_ACTION",
        title: "Mark as Read",
        options: []
    )
    let messageCategory = UNNotificationCategory(
        identifier: "MESSAGE_CATEGORY",
        actions: [replyAction, markReadAction],
        intentIdentifiers: [],
        categorySummaryFormat: "%u more messages from %@",
        options: [.customDismissAction]
    )

    // Workout category
    let startAction = UNNotificationAction(
        identifier: "START_WORKOUT_ACTION",
        title: "Start",
        options: [.foreground]
    )
    let skipAction = UNNotificationAction(
        identifier: "SKIP_WORKOUT_ACTION",
        title: "Skip",
        options: [.destructive]
    )
    let workoutCategory = UNNotificationCategory(
        identifier: "WORKOUT_CATEGORY",
        actions: [startAction, skipAction],
        intentIdentifiers: [],
        options: []
    )

    UNUserNotificationCenter.current().setNotificationCategories([
        messageCategory,
        workoutCategory,
    ])
}
```

## Testing Notifications

### Simulator Limitations

- **Remote notifications cannot be received** via APNs on the simulator.
- **Drag-and-drop `.apns` files** onto the simulator to simulate remote notifications.
- **Local notifications** work normally on the simulator.
- `didFailToRegisterForRemoteNotificationsWithError` always fires on the simulator.

### Simulating Remote Notifications

Create a `.apns` file and drag it onto the running simulator:

```json
{
    "Simulator Target Bundle": "com.example.myapp",
    "aps": {
        "alert": {
            "title": "Test Notification",
            "body": "This is a simulated push notification."
        },
        "badge": 1,
        "sound": "default",
        "category": "MESSAGE_CATEGORY"
    },
    "messageId": "test-123",
    "chatId": "chat-abc"
}
```

Or use the `xcrun simctl push` command:

```bash
xcrun simctl push booted com.example.myapp payload.apns
```

### Testing on Device

Use the APNs sandbox environment during development. The device token from a development build uses the sandbox; production builds use the production APNs endpoint.

For quick testing without a server, use tools like:
- **Xcode Console** to send test payloads via the APNs provider API
- Third-party push testing tools that send directly to APNs with your key/certificate

### Debugging Delivery

1. **Check entitlements:** Ensure the push notification entitlement is in the app's provisioning profile. The `aps-environment` key must be present.

2. **Verify token format:** The token must be a hex string (64 characters for most devices). If your server receives something shorter or with non-hex characters, the conversion is wrong.

3. **Check APNs response codes:**

| Status | Meaning | Action |
|--------|---------|--------|
| 200 | Success | Notification accepted by APNs |
| 400 | Bad request | Check payload format (max 4096 bytes) |
| 403 | Forbidden | Certificate/key mismatch or expired |
| 405 | Method not allowed | Must use POST with HTTP/2 |
| 410 | Gone | Device token is no longer valid; remove from server |
| 413 | Payload too large | Reduce payload size (max 4096 bytes) |
| 429 | Too many requests | APNs is throttling; back off |
| 500 | Internal server error | APNs issue; retry later |

4. **Console.app:** Connect the device, open Console.app on Mac, filter by `dasd` or `apsd` or your app's bundle identifier. Look for delivery confirmations or rejection reasons.

5. **Common reasons notifications do not arrive:**
   - App is in Low Power Mode and the system defers delivery
   - Focus / Do Not Disturb is active and the app is not in the allowed list
   - The device has no internet connection
   - The device token has changed and the server is using a stale token (status 410)
   - Silent pushes are rate-limited by the system (typically a few per hour)
   - The notification payload exceeds 4096 bytes
   - The APNs certificate or key has expired

6. **Background push debugging:** Silent pushes are heavily throttled. The system decides when and whether to wake the app. During development, the system is more generous. In production, expect delays. Use `BGTaskScheduler` for more reliable background processing.

## Badge Management

Reset the badge count when the user opens the app so stale badge numbers do not persist.

```swift
// In AppDelegate or SceneDelegate
func sceneDidBecomeActive(_ scene: UIScene) {
    UNUserNotificationCenter.current().setBadgeCount(0)
}

// Or in SwiftUI with the scene phase
struct ContentView: View {
    @Environment(\.scenePhase) private var scenePhase

    var body: some View {
        MainView()
            .onChange(of: scenePhase) { _, phase in
                if phase == .active {
                    Task {
                        try? await UNUserNotificationCenter.current().setBadgeCount(0)
                    }
                }
            }
    }
}
```

`setBadgeCount(_:)` (iOS 16+) is the modern replacement for setting `UIApplication.shared.applicationIconBadgeNumber`, which is deprecated.

## Provisional to Full Authorization Upgrade

If you started with provisional notifications, you can later ask for full authorization. The system shows the permission prompt again.

```swift
@MainActor
func upgradeToFullAuthorization() async -> Bool {
    let center = UNUserNotificationCenter.current()
    let settings = await center.notificationSettings()

    guard settings.authorizationStatus == .provisional else {
        return settings.authorizationStatus == .authorized
    }

    do {
        // This presents the system prompt to the user
        let granted = try await center.requestAuthorization(
            options: [.alert, .sound, .badge]
        )
        return granted
    } catch {
        return false
    }
}
```
