# Representable Recipes

Complete working recipes for common UIKit wrapping scenarios. Each recipe includes the full `UIViewRepresentable` or `UIViewControllerRepresentable` struct, the Coordinator with delegate methods, a SwiftUI usage example, and gotchas specific to that wrapper.

---

## 1. WKWebView Wrapper

Load URLs, handle navigation, expose back/forward state, and bridge JavaScript.

```swift
import SwiftUI
import WebKit

struct WebView: UIViewRepresentable {
    let url: URL
    @Binding var isLoading: Bool
    @Binding var canGoBack: Bool
    @Binding var canGoForward: Bool
    var onNavigationFinished: ((URL?) -> Void)?

    func makeCoordinator() -> Coordinator { Coordinator(self) }

    func makeUIView(context: Context) -> WKWebView {
        let config = WKWebViewConfiguration()
        let webView = WKWebView(frame: .zero, configuration: config)
        webView.navigationDelegate = context.coordinator
        webView.allowsBackForwardNavigationGestures = true

        // KVO for loading and navigation state
        context.coordinator.observe(webView)

        webView.load(URLRequest(url: url))
        return webView
    }

    func updateUIView(_ uiView: WKWebView, context: Context) {
        // Only reload if the URL changed
        if uiView.url != url {
            uiView.load(URLRequest(url: url))
        }
    }

    static func dismantleUIView(_ uiView: WKWebView, coordinator: Coordinator) {
        coordinator.cancellables.removeAll()
    }

    func goBack(_ webView: WKWebView) { webView.goBack() }
    func goForward(_ webView: WKWebView) { webView.goForward() }

    final class Coordinator: NSObject, WKNavigationDelegate {
        var parent: WebView
        var cancellables: [NSKeyValueObservation] = []

        init(_ parent: WebView) { self.parent = parent }

        func observe(_ webView: WKWebView) {
            cancellables.append(
                webView.observe(\.isLoading) { [weak self] webView, _ in
                    self?.parent.isLoading = webView.isLoading
                }
            )
            cancellables.append(
                webView.observe(\.canGoBack) { [weak self] webView, _ in
                    self?.parent.canGoBack = webView.canGoBack
                }
            )
            cancellables.append(
                webView.observe(\.canGoForward) { [weak self] webView, _ in
                    self?.parent.canGoForward = webView.canGoForward
                }
            )
        }

        func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
            parent.onNavigationFinished?(webView.url)
        }

        func webView(
            _ webView: WKWebView,
            decidePolicyFor navigationAction: WKNavigationAction
        ) async -> WKNavigationActionPolicy {
            .allow
        }
    }
}
```

### Usage

```swift
struct BrowserView: View {
    @State private var isLoading = false
    @State private var canGoBack = false
    @State private var canGoForward = false

    var body: some View {
        WebView(
            url: URL(string: "https://example.com")!,
            isLoading: $isLoading,
            canGoBack: $canGoBack,
            canGoForward: $canGoForward
        )
        .overlay(alignment: .top) {
            if isLoading { ProgressView() }
        }
    }
}
```

### Gotchas

- **WKWebView must not be created in `updateUIView`.** It is expensive to allocate and resets all navigation state.
- **KVO observations must be cleaned up.** Store `NSKeyValueObservation` references and clear them in `dismantleUIView`.
- **JavaScript bridge:** If adding `WKScriptMessageHandler`, use the coordinator as the handler and register it on the configuration before creating the web view.

---

## 2. MKMapView Wrapper

Display a map with annotations, track region changes, and toggle map type.

```swift
import SwiftUI
import MapKit

struct MapViewRepresentable: UIViewRepresentable {
    @Binding var region: MKCoordinateRegion
    @Binding var mapType: MKMapType
    var annotations: [MKPointAnnotation]
    var onRegionChanged: ((MKCoordinateRegion) -> Void)?

    func makeCoordinator() -> Coordinator { Coordinator(self) }

    func makeUIView(context: Context) -> MKMapView {
        let mapView = MKMapView()
        mapView.delegate = context.coordinator
        mapView.showsUserLocation = true
        return mapView
    }

    func updateUIView(_ uiView: MKMapView, context: Context) {
        // Update map type
        if uiView.mapType != mapType {
            uiView.mapType = mapType
        }

        // Update region -- guard against tiny differences to avoid feedback loops
        let currentCenter = uiView.region.center
        let threshold = 0.0001
        if abs(currentCenter.latitude - region.center.latitude) > threshold ||
           abs(currentCenter.longitude - region.center.longitude) > threshold {
            uiView.setRegion(region, animated: true)
        }

        // Diff annotations
        let existing = Set(uiView.annotations.compactMap { $0 as? MKPointAnnotation })
        let incoming = Set(annotations)
        let toRemove = existing.subtracting(incoming)
        let toAdd = incoming.subtracting(existing)
        uiView.removeAnnotations(Array(toRemove))
        uiView.addAnnotations(Array(toAdd))
    }

    final class Coordinator: NSObject, MKMapViewDelegate {
        var parent: MapViewRepresentable

        init(_ parent: MapViewRepresentable) { self.parent = parent }

        func mapView(_ mapView: MKMapView, regionDidChangeAnimated animated: Bool) {
            parent.region = mapView.region
            parent.onRegionChanged?(mapView.region)
        }

        func mapView(
            _ mapView: MKMapView,
            viewFor annotation: MKAnnotation
        ) -> MKAnnotationView? {
            guard !(annotation is MKUserLocation) else { return nil }
            let id = "pin"
            let view = mapView.dequeueReusableAnnotationView(withIdentifier: id)
                ?? MKMarkerAnnotationView(annotation: annotation, reuseIdentifier: id)
            view.annotation = annotation
            return view
        }
    }
}
```

### Usage

```swift
struct MapScreen: View {
    @State private var region = MKCoordinateRegion(
        center: CLLocationCoordinate2D(latitude: 37.7749, longitude: -122.4194),
        span: MKCoordinateSpan(latitudeDelta: 0.05, longitudeDelta: 0.05)
    )
    @State private var mapType: MKMapType = .standard

    var body: some View {
        MapViewRepresentable(
            region: $region,
            mapType: $mapType,
            annotations: []
        )
        .ignoresSafeArea()
    }
}
```

### Gotchas

- **Region update loops.** The delegate writes to `@Binding region`, which triggers `updateUIView`, which calls `setRegion`, which triggers the delegate again. The threshold guard is essential.
- **Annotation diffing.** MKMapView does not handle duplicate annotations well. Always diff before adding/removing.
- **Native SwiftUI Map.** For iOS 17+, prefer the native `Map` view unless you need delegate-level control (custom overlays, clustering, etc.).

---

## 3. UITextView Wrapper (Attributed Text)

Wrap `UITextView` for rich text editing with `NSAttributedString` binding and placeholder support.

```swift
import SwiftUI

struct RichTextEditor: UIViewRepresentable {
    @Binding var attributedText: NSAttributedString
    var placeholder: String = ""
    @Binding var isFirstResponder: Bool

    func makeCoordinator() -> Coordinator { Coordinator(self) }

    func makeUIView(context: Context) -> UITextView {
        let textView = UITextView()
        textView.delegate = context.coordinator
        textView.font = .preferredFont(forTextStyle: .body)
        textView.adjustsFontForContentSizeCategory = true
        textView.backgroundColor = .clear
        textView.textContainerInset = UIEdgeInsets(top: 8, left: 4, bottom: 8, right: 4)

        // Placeholder label
        let label = UILabel()
        label.text = placeholder
        label.font = .preferredFont(forTextStyle: .body)
        label.textColor = .placeholderText
        label.tag = 999
        label.translatesAutoresizingMaskIntoConstraints = false
        textView.addSubview(label)
        NSLayoutConstraint.activate([
            label.topAnchor.constraint(equalTo: textView.topAnchor, constant: 8),
            label.leadingAnchor.constraint(equalTo: textView.leadingAnchor, constant: 8),
        ])

        return textView
    }

    func updateUIView(_ uiView: UITextView, context: Context) {
        if uiView.attributedText != attributedText {
            uiView.attributedText = attributedText
        }

        // Update placeholder visibility
        if let label = uiView.viewWithTag(999) as? UILabel {
            label.isHidden = !uiView.text.isEmpty
        }

        // First responder management
        if isFirstResponder && !uiView.isFirstResponder {
            uiView.becomeFirstResponder()
        } else if !isFirstResponder && uiView.isFirstResponder {
            uiView.resignFirstResponder()
        }
    }

    @available(iOS 16.0, *)
    func sizeThatFits(
        _ proposal: ProposedViewSize,
        uiView: UITextView,
        context: Context
    ) -> CGSize? {
        let width = proposal.width ?? UIView.layoutFittingExpandedSize.width
        let size = uiView.sizeThatFits(CGSize(width: width, height: .greatestFiniteMagnitude))
        return CGSize(width: width, height: max(size.height, 44))
    }

    final class Coordinator: NSObject, UITextViewDelegate {
        var parent: RichTextEditor

        init(_ parent: RichTextEditor) { self.parent = parent }

        func textViewDidChange(_ textView: UITextView) {
            parent.attributedText = textView.attributedText ?? NSAttributedString()
            if let label = textView.viewWithTag(999) as? UILabel {
                label.isHidden = !textView.text.isEmpty
            }
        }

        func textViewDidBeginEditing(_ textView: UITextView) {
            parent.isFirstResponder = true
        }

        func textViewDidEndEditing(_ textView: UITextView) {
            parent.isFirstResponder = false
        }
    }
}
```

### Usage

```swift
struct NotesEditorView: View {
    @State private var text = NSAttributedString()
    @State private var isFocused = false

    var body: some View {
        RichTextEditor(
            attributedText: $text,
            placeholder: "Write something...",
            isFirstResponder: $isFocused
        )
        .frame(minHeight: 100)
    }
}
```

### Gotchas

- **`NSAttributedString` comparison.** The equality check in `updateUIView` is critical -- without it, every keystroke triggers a full re-render loop.
- **First responder management.** Avoid calling `becomeFirstResponder()` unconditionally in `updateUIView` -- it steals focus from other fields.
- **iOS 26 alternative.** `TextEditor` in iOS 26 supports `AttributedString` natively. Prefer it unless you need `NSAttributedString` or delegate-level control.

---

## 4. AVCaptureVideoPreviewLayer Wrapper

Display a live camera preview. The preview layer requires a `UIView` host.

```swift
import SwiftUI
import AVFoundation

struct CameraPreview: UIViewRepresentable {
    let session: AVCaptureSession

    func makeUIView(context: Context) -> CameraPreviewUIView {
        let view = CameraPreviewUIView()
        view.previewLayer.session = session
        view.previewLayer.videoGravity = .resizeAspectFill
        return view
    }

    func updateUIView(_ uiView: CameraPreviewUIView, context: Context) {
        // Session is reference type -- no update needed unless swapping sessions
        if uiView.previewLayer.session !== session {
            uiView.previewLayer.session = session
        }
    }
}

final class CameraPreviewUIView: UIView {
    override class var layerClass: AnyClass { AVCaptureVideoPreviewLayer.self }

    var previewLayer: AVCaptureVideoPreviewLayer {
        layer as! AVCaptureVideoPreviewLayer
    }

    override func layoutSubviews() {
        super.layoutSubviews()
        previewLayer.frame = bounds
    }
}
```

### Usage

```swift
struct CameraScreen: View {
    @State private var cameraManager = CameraManager()

    var body: some View {
        CameraPreview(session: cameraManager.session)
            .ignoresSafeArea()
            .task { await cameraManager.start() }
    }
}
```

### Gotchas

- **Use a custom UIView subclass with `layerClass`.** Overriding `layerClass` avoids adding a sublayer and ensures the preview layer resizes automatically with the view.
- **Session management belongs outside the representable.** Create and manage `AVCaptureSession` in a separate model. The representable only displays it.
- **Orientation.** Set `previewLayer.connection?.videoRotationAngle` if supporting device rotation.

---

## 5. PHPickerViewController Wrapper

Multi-select photo picker that loads selected images asynchronously.

```swift
import SwiftUI
import PhotosUI

struct PhotoPicker: UIViewControllerRepresentable {
    @Binding var selectedImages: [UIImage]
    var selectionLimit: Int = 0  // 0 = unlimited
    @Environment(\.dismiss) private var dismiss

    func makeCoordinator() -> Coordinator { Coordinator(self) }

    func makeUIViewController(context: Context) -> PHPickerViewController {
        var config = PHPickerConfiguration(photoLibrary: .shared())
        config.filter = .images
        config.selectionLimit = selectionLimit
        config.preferredAssetRepresentationMode = .current

        let picker = PHPickerViewController(configuration: config)
        picker.delegate = context.coordinator
        return picker
    }

    func updateUIViewController(_ uiViewController: PHPickerViewController, context: Context) {
        // Nothing to update -- configuration is immutable after creation
    }

    final class Coordinator: NSObject, PHPickerViewControllerDelegate {
        let parent: PhotoPicker

        init(_ parent: PhotoPicker) { self.parent = parent }

        func picker(
            _ picker: PHPickerViewController,
            didFinishPicking results: [PHPickerResult]
        ) {
            parent.dismiss()

            guard !results.isEmpty else { return }

            Task { @MainActor in
                var images: [UIImage] = []
                for result in results {
                    if let image = await loadImage(from: result.itemProvider) {
                        images.append(image)
                    }
                }
                parent.selectedImages = images
            }
        }

        private func loadImage(from provider: NSItemProvider) async -> UIImage? {
            await withCheckedContinuation { continuation in
                if provider.canLoadObject(ofClass: UIImage.self) {
                    provider.loadObject(ofClass: UIImage.self) { image, _ in
                        continuation.resume(returning: image as? UIImage)
                    }
                } else {
                    continuation.resume(returning: nil)
                }
            }
        }
    }
}
```

### Usage

```swift
struct ImagePickerDemo: View {
    @State private var images: [UIImage] = []
    @State private var showPicker = false

    var body: some View {
        VStack {
            ScrollView(.horizontal) {
                HStack {
                    ForEach(images.indices, id: \.self) { i in
                        Image(uiImage: images[i])
                            .resizable()
                            .scaledToFill()
                            .frame(width: 100, height: 100)
                            .clipShape(RoundedRectangle(cornerRadius: 8))
                    }
                }
            }
            Button("Pick Photos") { showPicker = true }
        }
        .sheet(isPresented: $showPicker) {
            PhotoPicker(selectedImages: $images, selectionLimit: 5)
        }
    }
}
```

### Gotchas

- **Always dismiss in the delegate.** `picker(_:didFinishPicking:)` is called for both selection and cancellation (with empty results). Dismiss in both cases.
- **Async image loading.** `NSItemProvider.loadObject` is completion-based. Wrap in `withCheckedContinuation` for async/await usage. Load images after dismissal to avoid blocking the picker UI.
- **iOS 17 alternative.** `PhotosUI.PhotosPicker` is a native SwiftUI view. Prefer it unless you need custom picker UI or advanced filtering.

---

## 6. MFMailComposeViewController Wrapper

Present the system email composer with pre-filled fields and handle the result.

```swift
import SwiftUI
import MessageUI

struct MailComposer: UIViewControllerRepresentable {
    let subject: String
    let recipients: [String]
    let body: String
    var isHTML: Bool = false
    var onResult: ((MFMailComposeResult) -> Void)?
    @Environment(\.dismiss) private var dismiss

    func makeCoordinator() -> Coordinator { Coordinator(self) }

    func makeUIViewController(context: Context) -> MFMailComposeViewController {
        let controller = MFMailComposeViewController()
        controller.mailComposeDelegate = context.coordinator
        controller.setSubject(subject)
        controller.setToRecipients(recipients)
        controller.setMessageBody(body, isHTML: isHTML)
        return controller
    }

    func updateUIViewController(_ uiViewController: MFMailComposeViewController, context: Context) {
        // Cannot update mail compose after presentation
    }

    final class Coordinator: NSObject, MFMailComposeViewControllerDelegate {
        let parent: MailComposer

        init(_ parent: MailComposer) { self.parent = parent }

        func mailComposeController(
            _ controller: MFMailComposeViewController,
            didFinishWith result: MFMailComposeResult,
            error: Error?
        ) {
            parent.onResult?(result)
            parent.dismiss()
        }
    }
}
```

### Usage

```swift
struct FeedbackView: View {
    @State private var showMail = false

    var body: some View {
        Button("Send Feedback") {
            guard MFMailComposeViewController.canSendMail() else { return }
            showMail = true
        }
        .sheet(isPresented: $showMail) {
            MailComposer(
                subject: "App Feedback",
                recipients: ["support@example.com"],
                body: "I have feedback about..."
            ) { result in
                print("Mail result: \(result.rawValue)")
            }
        }
    }
}
```

### Gotchas

- **Check `canSendMail()` before presenting.** The app crashes if `MFMailComposeViewController` is presented on a device with no mail account configured.
- **Cannot update after presentation.** `updateUIViewController` is intentionally empty -- the mail compose API does not support changing fields after the controller is shown.
- **The delegate protocol name is `MFMailComposeViewControllerDelegate`**, not `MFMailComposeDelegate`.

---

## 7. UIActivityViewController Wrapper (Share Sheet)

Present the system share sheet. This is a `UIViewControllerRepresentable` because `UIActivityViewController` is a controller, not a view.

```swift
import SwiftUI

struct ShareSheet: UIViewControllerRepresentable {
    let items: [Any]
    var activities: [UIActivity]? = nil
    var excludedTypes: [UIActivity.ActivityType]? = nil

    func makeUIViewController(context: Context) -> UIActivityViewController {
        let controller = UIActivityViewController(
            activityItems: items,
            applicationActivities: activities
        )
        controller.excludedActivityTypes = excludedTypes
        return controller
    }

    func updateUIViewController(_ uiViewController: UIActivityViewController, context: Context) {
        // Cannot update after presentation
    }
}
```

### Usage

```swift
struct ContentView: View {
    @State private var showShare = false

    var body: some View {
        Button("Share") { showShare = true }
            .sheet(isPresented: $showShare) {
                ShareSheet(items: ["Check out this app!", URL(string: "https://example.com")!])
                    .presentationDetents([.medium])
            }
    }
}
```

### Gotchas

- **Present via `.sheet`.** Do not try to use `UIActivityViewController` as an inline view -- it is a modal controller.
- **iPad requires `popoverPresentationController`.** When using on iPad outside of `.sheet`, set the source view/rect on the popover controller. SwiftUI's `.sheet` handles this automatically.
- **iOS 16+ alternative.** `ShareLink` is a native SwiftUI view for Transferable items. Prefer it for simple sharing.

---

## 8. UISearchBar Wrapper

Wrap `UISearchBar` with delegate-based callbacks, debounce support, and cancel button handling.

```swift
import SwiftUI
import Combine

struct SearchBar: UIViewRepresentable {
    @Binding var text: String
    var placeholder: String = "Search"
    var onSearch: ((String) -> Void)?
    var onCancel: (() -> Void)?

    func makeCoordinator() -> Coordinator { Coordinator(self) }

    func makeUIView(context: Context) -> UISearchBar {
        let searchBar = UISearchBar()
        searchBar.delegate = context.coordinator
        searchBar.placeholder = placeholder
        searchBar.searchBarStyle = .minimal
        searchBar.autocapitalizationType = .none
        return searchBar
    }

    func updateUIView(_ uiView: UISearchBar, context: Context) {
        if uiView.text != text {
            uiView.text = text
        }
    }

    final class Coordinator: NSObject, UISearchBarDelegate {
        var parent: SearchBar
        private var debounceTask: Task<Void, Never>?

        init(_ parent: SearchBar) { self.parent = parent }

        func searchBar(_ searchBar: UISearchBar, textDidChange searchText: String) {
            parent.text = searchText
            searchBar.showsCancelButton = !searchText.isEmpty

            // Debounce search
            debounceTask?.cancel()
            debounceTask = Task { @MainActor in
                try? await Task.sleep(for: .milliseconds(300))
                guard !Task.isCancelled else { return }
                parent.onSearch?(searchText)
            }
        }

        func searchBarSearchButtonClicked(_ searchBar: UISearchBar) {
            debounceTask?.cancel()
            parent.onSearch?(parent.text)
            searchBar.resignFirstResponder()
        }

        func searchBarCancelButtonClicked(_ searchBar: UISearchBar) {
            parent.text = ""
            parent.onCancel?()
            searchBar.resignFirstResponder()
            searchBar.showsCancelButton = false
        }
    }
}
```

### Usage

```swift
struct SearchableList: View {
    @State private var query = ""
    @State private var results: [String] = []

    var body: some View {
        VStack(spacing: 0) {
            SearchBar(text: $query, placeholder: "Search items") { text in
                results = performSearch(text)
            }
            List(results, id: \.self) { Text($0) }
        }
    }
}
```

### Gotchas

- **Native `.searchable` modifier.** Prefer SwiftUI's `.searchable(text:)` modifier for standard search patterns. Use this wrapper only when you need precise control over search bar appearance or delegate timing.
- **Debounce with `Task.sleep`.** Cancel the previous task before starting a new one to debounce. `Combine` is not needed.
- **Cancel button state.** Toggle `showsCancelButton` in the delegate, not in `updateUIView`, to avoid layout jumps.

---

## 9. SFSafariViewController Wrapper

Present an in-app browser using Safari's full rendering engine, reader mode, and content blocking.

```swift
import SwiftUI
import SafariServices

struct SafariView: UIViewControllerRepresentable {
    let url: URL
    var preferredBarTintColor: UIColor? = nil
    var preferredControlTintColor: UIColor? = nil
    var dismissButtonStyle: SFSafariViewController.DismissButtonStyle = .done
    @Environment(\.dismiss) private var dismiss

    func makeCoordinator() -> Coordinator { Coordinator(self) }

    func makeUIViewController(context: Context) -> SFSafariViewController {
        let config = SFSafariViewController.Configuration()
        config.entersReaderIfAvailable = false
        config.barCollapsingEnabled = true

        let safari = SFSafariViewController(url: url, configuration: config)
        safari.delegate = context.coordinator
        safari.preferredBarTintColor = preferredBarTintColor
        safari.preferredControlTintColor = preferredControlTintColor
        safari.dismissButtonStyle = dismissButtonStyle
        return safari
    }

    func updateUIViewController(_ uiViewController: SFSafariViewController, context: Context) {
        // SFSafariViewController does not support URL changes after creation.
        // To navigate to a new URL, dismiss and re-present with a new URL.
    }

    final class Coordinator: NSObject, SFSafariViewControllerDelegate {
        let parent: SafariView

        init(_ parent: SafariView) { self.parent = parent }

        func safariViewControllerDidFinish(_ controller: SFSafariViewController) {
            parent.dismiss()
        }
    }
}
```

### Usage

```swift
struct ArticleView: View {
    @State private var showSafari = false
    let articleURL = URL(string: "https://example.com/article")!

    var body: some View {
        Button("Read Full Article") { showSafari = true }
            .sheet(isPresented: $showSafari) {
                SafariView(url: articleURL)
                    .ignoresSafeArea()
            }
    }
}
```

### Gotchas

- **Cannot change URL after creation.** `SFSafariViewController` does not expose its navigation. To load a different URL, dismiss and present a new instance.
- **Must use `.sheet` or fullScreenCover.** Apple rejects apps that embed `SFSafariViewController` as a child view controller inline -- it must be presented modally.
- **The dismiss delegate is essential.** Without `safariViewControllerDidFinish`, the Done button tap does not dismiss the SwiftUI sheet, leaving the user stuck.
- **`ignoresSafeArea()`.** Safari's own chrome handles safe areas. Without this modifier, you get double safe area insets.
