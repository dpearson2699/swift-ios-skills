# Rich Notifications

Rich notifications enhance the standard notification banner with images, video, audio, custom UI, and interactive elements. They use two extension types: Notification Service Extension (modifies content before display) and Notification Content Extension (provides custom UI in the expanded notification).

## Notification Service Extension

A Notification Service Extension runs when a notification with `mutable-content: 1` arrives. It has approximately 30 seconds to modify the notification content before the system displays it. If the extension does not call the content handler in time, the system displays the original notification.

### Creating the Extension

In Xcode: File > New > Target > Notification Service Extension. This creates a new target with a `NotificationService` class.

```swift
import UserNotifications

class NotificationService: UNNotificationServiceExtension {
    private var contentHandler: ((UNNotificationContent) -> Void)?
    private var bestAttemptContent: UNMutableNotificationContent?

    override func didReceive(
        _ request: UNNotificationRequest,
        withContentHandler contentHandler: @escaping (UNNotificationContent) -> Void
    ) {
        self.contentHandler = contentHandler
        bestAttemptContent = request.content.mutableCopy() as? UNMutableNotificationContent

        guard let content = bestAttemptContent else {
            contentHandler(request.content)
            return
        }

        // Modify the notification content here
        Task {
            await processNotification(content: content)
            contentHandler(content)
        }
    }

    /// Called if the extension is about to be terminated (ran out of time).
    /// Deliver the best attempt -- even a partially modified notification
    /// is better than nothing.
    override func serviceExtensionTimeWillExpire() {
        if let handler = contentHandler, let content = bestAttemptContent {
            handler(content)
        }
    }

    private func processNotification(content: UNMutableNotificationContent) async {
        // Download image if URL is provided
        if let imageUrlString = content.userInfo["imageUrl"] as? String {
            await attachImage(from: imageUrlString, to: content)
        }

        // Decrypt body if encrypted
        if let encrypted = content.userInfo["encryptedBody"] as? String {
            content.body = decrypt(encrypted)
        }
    }
}
```

### Downloading Images and Media

Download media from a URL and attach it to the notification. The attachment must be written to disk in the extension's temporary directory.

```swift
extension NotificationService {
    private func attachImage(
        from urlString: String,
        to content: UNMutableNotificationContent
    ) async {
        guard let url = URL(string: urlString) else { return }

        do {
            let (data, response) = try await URLSession.shared.data(from: url)

            // Determine file extension from MIME type
            let ext = fileExtension(for: response.mimeType)
            let tempDir = FileManager.default.temporaryDirectory
            let fileURL = tempDir.appendingPathComponent(UUID().uuidString + ext)

            try data.write(to: fileURL)

            let attachment = try UNNotificationAttachment(
                identifier: "image",
                url: fileURL,
                options: nil
            )
            content.attachments = [attachment]
        } catch {
            print("Failed to download notification image: \(error)")
            // Notification displays without the image -- graceful degradation
        }
    }

    private func fileExtension(for mimeType: String?) -> String {
        switch mimeType {
        case "image/jpeg": return ".jpg"
        case "image/png": return ".png"
        case "image/gif": return ".gif"
        case "video/mp4", "video/mpeg4": return ".mp4"
        case "audio/mpeg", "audio/mp3": return ".mp3"
        case "audio/wav": return ".wav"
        default: return ".jpg"
        }
    }
}
```

### Decrypting Encrypted Payloads

Use the service extension to decrypt sensitive notification content. The APNs payload carries an encrypted blob; the extension decrypts it before display.

```swift
extension NotificationService {
    private func decrypt(_ encryptedBase64: String) -> String {
        guard let data = Data(base64Encoded: encryptedBase64) else {
            return "New notification"  // fallback
        }
        // Use your encryption library (CryptoKit, etc.) to decrypt
        // The decryption key should be stored in the shared Keychain
        // accessible to both the main app and the extension via App Groups.
        do {
            let decrypted = try EncryptionService.shared.decrypt(data)
            return String(data: decrypted, encoding: .utf8) ?? "New notification"
        } catch {
            return "New notification"
        }
    }
}
```

### App Groups for Data Sharing

The service extension runs in a separate process from the main app. Use App Groups to share data (Keychain items, UserDefaults, files) between them.

1. Enable "App Groups" capability on both the main app target and the extension target.
2. Use the same group identifier (e.g., `group.com.example.myapp`).

```swift
// Shared UserDefaults
let sharedDefaults = UserDefaults(suiteName: "group.com.example.myapp")

// Shared file container
let sharedContainer = FileManager.default.containerURL(
    forSecurityApplicationGroupIdentifier: "group.com.example.myapp"
)

// Shared Keychain: set kSecAttrAccessGroup to your App Group identifier
// when storing/retrieving Keychain items.
```

**Extension memory limit:** Notification Service Extensions have a strict memory limit (approximately 24 MB). Do not load large frameworks or perform memory-intensive operations. If the extension exceeds memory limits, the system terminates it and shows the original notification.

## Notification Attachments

`UNNotificationAttachment` supports images, GIFs, video, and audio. The system displays a thumbnail in the collapsed notification and the full media in the expanded view.

### Supported Formats and Limits

| Type | Formats | Max Size |
|------|---------|----------|
| Image | JPEG, PNG, GIF | 10 MB |
| Audio | AIFF, WAV, MP3, M4A | 5 MB |
| Video | MPEG, MPEG-2, MPEG-4, AVI | 50 MB |

### Creating Attachments

```swift
// From a local file URL
let attachment = try UNNotificationAttachment(
    identifier: "photo",
    url: localFileURL,
    options: nil
)

// With options for thumbnailing
let attachment = try UNNotificationAttachment(
    identifier: "photo",
    url: localFileURL,
    options: [
        UNNotificationAttachmentOptionsThumbnailClippingRectKey:
            CGRect(x: 0, y: 0, width: 1, height: 0.5).dictionaryRepresentation,
        UNNotificationAttachmentOptionsThumbnailTimeKey: 0  // for video: thumbnail at 0 seconds
    ]
)

// Attach to content
content.attachments = [attachment]
```

**Important:** The file URL must point to a file that the notification system can access. For service extensions, write to the extension's temporary directory. For local notifications, write to a location accessible by the notification system (not the app's sandbox). The system moves the file after attachment creation, so the original URL becomes invalid.

### Multiple Attachments

You can attach multiple items, but only the first attachment is shown as the thumbnail in the collapsed notification. The expanded view can show all attachments.

```swift
content.attachments = [imageAttachment, audioAttachment]
// imageAttachment appears as the thumbnail
```

### GIF Animations

GIFs animate automatically in the expanded notification view. No special handling needed -- attach the GIF file as any other image.

```swift
let gifURL = tempDir.appendingPathComponent("animation.gif")
try gifData.write(to: gifURL)
let attachment = try UNNotificationAttachment(
    identifier: "animation",
    url: gifURL,
    options: nil
)
```

## Notification Content Extension

A Notification Content Extension provides a custom view controller that displays when the user long-presses (or expands) a notification. Use it for richer UI than attachments alone can provide.

### Creating the Extension

In Xcode: File > New > Target > Notification Content Extension. This creates a new target with a storyboard and a `NotificationViewController`.

### Configuration (Info.plist)

The extension's `Info.plist` must declare which notification categories it handles:

```xml
<key>NSExtension</key>
<dict>
    <key>NSExtensionAttributes</key>
    <dict>
        <key>UNNotificationExtensionCategory</key>
        <!-- Single category -->
        <string>MESSAGE_CATEGORY</string>
        <!-- Or multiple categories -->
        <array>
            <string>MESSAGE_CATEGORY</string>
            <string>PHOTO_CATEGORY</string>
        </array>
        <!-- Optional: size ratio (height / width). Default 1.0 -->
        <key>UNNotificationExtensionInitialContentSizeRatio</key>
        <real>0.5</real>
        <!-- Optional: hide the default notification body below the custom UI -->
        <key>UNNotificationExtensionDefaultContentHidden</key>
        <true/>
        <!-- Optional: allow user interaction in the custom UI -->
        <key>UNNotificationExtensionUserInteractionEnabled</key>
        <true/>
    </dict>
    <key>NSExtensionMainStoryboard</key>
    <string>MainInterface</string>
    <key>NSExtensionPointIdentifier</key>
    <string>com.apple.usernotifications.content-extension</string>
</dict>
```

### View Controller Implementation

```swift
import UIKit
import UserNotifications
import UserNotificationsUI

class NotificationViewController: UIViewController, UNNotificationContentExtension {
    @IBOutlet weak var titleLabel: UILabel!
    @IBOutlet weak var bodyLabel: UILabel!
    @IBOutlet weak var imageView: UIImageView!

    func didReceive(_ notification: UNNotification) {
        let content = notification.request.content
        titleLabel.text = content.title
        bodyLabel.text = content.body

        // Display the first attachment
        if let attachment = content.attachments.first,
           attachment.url.startAccessingSecurityScopedResource() {
            defer { attachment.url.stopAccessingSecurityScopedResource() }
            if let data = try? Data(contentsOf: attachment.url) {
                imageView.image = UIImage(data: data)
            }
        }
    }

    /// Called when the user taps a notification action while the content
    /// extension is visible.
    func didReceive(
        _ response: UNNotificationResponse,
        completionHandler completion: @escaping (UNNotificationContentExtensionResponseOption) -> Void
    ) {
        switch response.actionIdentifier {
        case "LIKE_ACTION":
            // Update UI to show "liked" state
            animateLikeConfirmation()
            // Dismiss after a short delay
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
                completion(.dismiss)
            }

        case "REPLY_ACTION":
            if let textResponse = response as? UNTextInputNotificationResponse {
                // Handle reply inline without opening the app
                showReplySentConfirmation(text: textResponse.userText)
                DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) {
                    completion(.dismiss)
                }
            }

        default:
            // Forward to the app's notification delegate
            completion(.dismissAndForwardAction)
        }
    }
}
```

### Response Options

| Option | Behavior |
|--------|----------|
| `.doNotDismiss` | Keep the content extension visible. Use for multi-step interactions. |
| `.dismiss` | Dismiss the notification. The action is handled entirely in the extension. |
| `.dismissAndForwardAction` | Dismiss and forward the action to `UNUserNotificationCenterDelegate.didReceive`. Use when the app needs to handle the action. |

### Media Playback in Notifications

The content extension can play audio or video. Implement `mediaPlayPauseButtonType` and `mediaPlayPauseButtonFrame` for a system-provided play/pause button.

```swift
class MediaNotificationViewController: UIViewController, UNNotificationContentExtension {
    var player: AVPlayer?

    override var mediaPlayPauseButtonType: UNNotificationContentExtensionMediaPlayPauseButtonType {
        return .overlay  // .none, .default, .overlay
    }

    override var mediaPlayPauseButtonFrame: CGRect {
        return CGRect(x: 0, y: 0, width: view.bounds.width, height: view.bounds.height)
    }

    func mediaPlay() {
        player?.play()
    }

    func mediaPause() {
        player?.pause()
    }

    func didReceive(_ notification: UNNotification) {
        guard let attachment = notification.request.content.attachments.first,
              attachment.url.startAccessingSecurityScopedResource() else { return }

        let playerItem = AVPlayerItem(url: attachment.url)
        player = AVPlayer(playerItem: playerItem)

        let playerLayer = AVPlayerLayer(player: player)
        playerLayer.frame = view.bounds
        view.layer.addSublayer(playerLayer)
    }
}
```

### Interactive Custom UI

With `UNNotificationExtensionUserInteractionEnabled` set to `true`, the content extension supports gesture recognizers, buttons, and other interactive elements.

```swift
class InteractiveNotificationViewController: UIViewController, UNNotificationContentExtension {
    private var ratingStars: [UIButton] = []
    private var selectedRating = 0

    override func viewDidLoad() {
        super.viewDidLoad()
        setupRatingUI()
    }

    func didReceive(_ notification: UNNotification) {
        // Configure with notification content
    }

    private func setupRatingUI() {
        let stack = UIStackView()
        stack.axis = .horizontal
        stack.spacing = 8
        stack.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(stack)

        for i in 1...5 {
            let button = UIButton(type: .system)
            button.setImage(UIImage(systemName: "star"), for: .normal)
            button.tag = i
            button.addTarget(self, action: #selector(starTapped(_:)), for: .touchUpInside)
            stack.addArrangedSubview(button)
            ratingStars.append(button)
        }

        NSLayoutConstraint.activate([
            stack.centerXAnchor.constraint(equalTo: view.centerXAnchor),
            stack.centerYAnchor.constraint(equalTo: view.centerYAnchor),
        ])
    }

    @objc private func starTapped(_ sender: UIButton) {
        selectedRating = sender.tag
        for (index, button) in ratingStars.enumerated() {
            let imageName = index < selectedRating ? "star.fill" : "star"
            button.setImage(UIImage(systemName: imageName), for: .normal)
        }
        // Send rating to server
        Task {
            await submitRating(selectedRating)
        }
    }
}
```

## Communication Notifications

Communication notifications display the sender's avatar and name prominently. They use SiriKit intents (`INSendMessageIntent`) to provide sender information.

### Setup

1. Add the `Intents` framework to the Notification Service Extension target.
2. Configure `INSendMessageIntent` in the service extension before delivery.

```swift
import Intents
import UserNotifications

extension NotificationService {
    func configureCommunicationNotification(
        content: UNMutableNotificationContent,
        senderName: String,
        senderImageURL: String?,
        conversationId: String
    ) async {
        // Create the sender identity
        let handle = INPersonHandle(value: conversationId, type: .unknown)
        var avatar: INImage? = nil

        // Download sender avatar
        if let urlString = senderImageURL,
           let url = URL(string: urlString) {
            if let (data, _) = try? await URLSession.shared.data(from: url) {
                avatar = INImage(imageData: data)
            }
        }

        let sender = INPerson(
            personHandle: handle,
            nameComponents: try? PersonNameComponents(senderName),
            displayName: senderName,
            image: avatar,
            contactIdentifier: nil,
            customIdentifier: conversationId
        )

        // Create the messaging intent
        let intent = INSendMessageIntent(
            recipients: nil,
            outgoingMessageType: .outgoingMessageText,
            content: content.body,
            speakableGroupName: nil,
            conversationIdentifier: conversationId,
            serviceName: nil,
            sender: sender,
            attachments: nil
        )

        // Donate the interaction so Siri learns about this contact
        let interaction = INInteraction(intent: intent, response: nil)
        interaction.direction = .incoming
        try? await interaction.donate()

        // Update the notification content with the intent
        do {
            let updatedContent = try content.updating(from: intent)
            // Copy updated properties back to mutable content
            // The updating(from:) method returns a new UNNotificationContent,
            // so we need to use the content handler with the updated version.
            // In practice, call the content handler with updatedContent directly.
        } catch {
            print("Failed to update content with intent: \(error)")
        }
    }
}
```

### Handling in the Service Extension

The complete flow integrates communication notifications into the standard service extension:

```swift
override func didReceive(
    _ request: UNNotificationRequest,
    withContentHandler contentHandler: @escaping (UNNotificationContent) -> Void
) {
    guard let content = request.content.mutableCopy() as? UNMutableNotificationContent else {
        contentHandler(request.content)
        return
    }

    Task {
        // Download and attach image
        if let imageUrl = content.userInfo["imageUrl"] as? String {
            await attachImage(from: imageUrl, to: content)
        }

        // Configure as communication notification if sender info is present
        if let senderName = content.userInfo["senderName"] as? String,
           let conversationId = content.userInfo["conversationId"] as? String {
            let senderImage = content.userInfo["senderImageUrl"] as? String

            let handle = INPersonHandle(value: conversationId, type: .unknown)
            var avatar: INImage? = nil
            if let urlString = senderImage,
               let url = URL(string: urlString),
               let (data, _) = try? await URLSession.shared.data(from: url) {
                avatar = INImage(imageData: data)
            }

            let sender = INPerson(
                personHandle: handle,
                nameComponents: try? PersonNameComponents(senderName),
                displayName: senderName,
                image: avatar,
                contactIdentifier: nil,
                customIdentifier: conversationId
            )

            let intent = INSendMessageIntent(
                recipients: nil,
                outgoingMessageType: .outgoingMessageText,
                content: content.body,
                speakableGroupName: nil,
                conversationIdentifier: conversationId,
                serviceName: nil,
                sender: sender,
                attachments: nil
            )

            let interaction = INInteraction(intent: intent, response: nil)
            interaction.direction = .incoming
            try? await interaction.donate()

            if let updatedContent = try? content.updating(from: intent) {
                contentHandler(updatedContent)
                return
            }
        }

        contentHandler(content)
    }
}
```

## Extension Gotchas

**Service extension not running:**
- Verify `mutable-content: 1` is set in the APNs payload.
- The notification must have an alert (title or body). Silent pushes do not trigger the service extension.
- Check that the extension's bundle identifier is `<main-app-bundle-id>.NotificationServiceExtension`.
- Confirm the extension is included in the same App Group as the main app if sharing data.

**Content extension not showing:**
- Verify the `UNNotificationExtensionCategory` in Info.plist matches the `categoryIdentifier` in the notification.
- Check that the storyboard or programmatic UI is properly configured.
- Ensure `UNNotificationExtensionInitialContentSizeRatio` is set to a reasonable value.

**Memory pressure:**
- Service extensions have approximately 24 MB of memory.
- Content extensions have more memory but should still be conservative.
- Avoid loading large frameworks (no SwiftUI, no heavy networking libraries).
- Use `URLSession` directly for network requests in extensions.

**Network access in extensions:**
- Extensions can make network requests. Use `URLSession` with the `.default` configuration.
- Keep requests fast -- the service extension has approximately 30 seconds total.
- Handle network failures gracefully; fall back to showing what the original payload contains.

**Debugging extensions:**
- In Xcode, select the extension scheme and attach to the extension process.
- Use `Debug > Attach to Process by PID or Name` with the extension's process name.
- Use `os_log` or `print` statements and view them in Console.app filtered by the extension's bundle identifier.
- Set breakpoints in the extension target and trigger a notification to hit them.

## Complete Service Extension Example

A production-ready service extension that handles image download, body decryption, and communication notifications:

```swift
import UserNotifications
import Intents

class NotificationService: UNNotificationServiceExtension {
    private var contentHandler: ((UNNotificationContent) -> Void)?
    private var bestAttemptContent: UNMutableNotificationContent?

    override func didReceive(
        _ request: UNNotificationRequest,
        withContentHandler contentHandler: @escaping (UNNotificationContent) -> Void
    ) {
        self.contentHandler = contentHandler
        bestAttemptContent = request.content.mutableCopy() as? UNMutableNotificationContent

        guard let content = bestAttemptContent else {
            contentHandler(request.content)
            return
        }

        Task {
            // Step 1: Decrypt body if needed
            if let encrypted = content.userInfo["encryptedBody"] as? String,
               let decrypted = decryptBody(encrypted) {
                content.body = decrypted
            }

            // Step 2: Download and attach image
            if let imageUrl = content.userInfo["imageUrl"] as? String {
                await attachMedia(from: imageUrl, to: content)
            }

            // Step 3: Configure communication notification
            if let senderName = content.userInfo["senderName"] as? String,
               let convId = content.userInfo["conversationId"] as? String {
                if let updated = await configureAsCommunication(
                    content: content,
                    senderName: senderName,
                    senderImageURL: content.userInfo["senderImage"] as? String,
                    conversationId: convId
                ) {
                    contentHandler(updated)
                    return
                }
            }

            contentHandler(content)
        }
    }

    override func serviceExtensionTimeWillExpire() {
        if let handler = contentHandler, let content = bestAttemptContent {
            handler(content)
        }
    }

    // MARK: - Private

    private func decryptBody(_ base64: String) -> String? {
        guard let data = Data(base64Encoded: base64) else { return nil }
        // Use shared Keychain via App Group to retrieve encryption key
        let defaults = UserDefaults(suiteName: "group.com.example.myapp")
        guard let keyData = defaults?.data(forKey: "encryptionKey") else { return nil }
        // Decrypt using CryptoKit or similar
        return try? Decryptor.decrypt(data, key: keyData)
    }

    private func attachMedia(
        from urlString: String,
        to content: UNMutableNotificationContent
    ) async {
        guard let url = URL(string: urlString) else { return }
        do {
            let (data, response) = try await URLSession.shared.data(from: url)
            let ext = fileExtension(for: response.mimeType)
            let fileURL = FileManager.default.temporaryDirectory
                .appendingPathComponent(UUID().uuidString + ext)
            try data.write(to: fileURL)
            let attachment = try UNNotificationAttachment(
                identifier: UUID().uuidString,
                url: fileURL,
                options: nil
            )
            content.attachments = [attachment]
        } catch {
            // Image download failed -- notification displays without media
        }
    }

    private func configureAsCommunication(
        content: UNMutableNotificationContent,
        senderName: String,
        senderImageURL: String?,
        conversationId: String
    ) async -> UNNotificationContent? {
        let handle = INPersonHandle(value: conversationId, type: .unknown)
        var avatar: INImage? = nil

        if let urlStr = senderImageURL,
           let url = URL(string: urlStr),
           let (data, _) = try? await URLSession.shared.data(from: url) {
            avatar = INImage(imageData: data)
        }

        let sender = INPerson(
            personHandle: handle,
            nameComponents: try? PersonNameComponents(senderName),
            displayName: senderName,
            image: avatar,
            contactIdentifier: nil,
            customIdentifier: conversationId
        )

        let intent = INSendMessageIntent(
            recipients: nil,
            outgoingMessageType: .outgoingMessageText,
            content: content.body,
            speakableGroupName: nil,
            conversationIdentifier: conversationId,
            serviceName: nil,
            sender: sender,
            attachments: nil
        )

        let interaction = INInteraction(intent: intent, response: nil)
        interaction.direction = .incoming
        try? await interaction.donate()

        return try? content.updating(from: intent)
    }

    private func fileExtension(for mimeType: String?) -> String {
        switch mimeType {
        case "image/jpeg": return ".jpg"
        case "image/png": return ".png"
        case "image/gif": return ".gif"
        case "video/mp4": return ".mp4"
        case "audio/mpeg": return ".mp3"
        default: return ".jpg"
        }
    }
}
```
