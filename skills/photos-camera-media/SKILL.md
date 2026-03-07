---
name: photos-camera-media
description: "Implement, review, or improve photo picking, camera capture, and media handling in iOS apps. Use when working with PhotosPicker, PHPickerViewController, camera capture sessions (AVCaptureSession), photo library access, image loading and display, video recording, or media permissions. Trigger for any task involving selecting photos from the library, taking pictures, recording video, processing images, or handling photo/camera privacy permissions in Swift apps."
---

# Photos, Camera & Media

Modern patterns for photo picking, camera capture, image loading, and media permissions targeting iOS 26+ with Swift 6.2. Patterns are backward-compatible to iOS 16 unless noted.

See `references/photospicker-patterns.md` for complete picker recipes and `references/camera-capture.md` for AVCaptureSession patterns.

## PhotosPicker (SwiftUI, iOS 16+)

`PhotosPicker` is the native SwiftUI replacement for `UIImagePickerController`. It runs out-of-process, requires no photo library permission for browsing, and supports single or multi-selection with media type filtering.

### Single Selection

```swift
import SwiftUI
import PhotosUI

struct SinglePhotoPicker: View {
    @State private var selectedItem: PhotosPickerItem?
    @State private var selectedImage: Image?

    var body: some View {
        VStack {
            if let selectedImage {
                selectedImage
                    .resizable()
                    .scaledToFit()
                    .frame(maxHeight: 300)
            }

            PhotosPicker("Select Photo", selection: $selectedItem, matching: .images)
        }
        .onChange(of: selectedItem) { _, newItem in
            Task {
                if let data = try? await newItem?.loadTransferable(type: Data.self),
                   let uiImage = UIImage(data: data) {
                    selectedImage = Image(uiImage: uiImage)
                }
            }
        }
    }
}
```

### Multi-Selection

```swift
struct MultiPhotoPicker: View {
    @State private var selectedItems: [PhotosPickerItem] = []
    @State private var selectedImages: [Image] = []

    var body: some View {
        VStack {
            ScrollView(.horizontal) {
                HStack {
                    ForEach(selectedImages.indices, id: \.self) { index in
                        selectedImages[index]
                            .resizable()
                            .scaledToFill()
                            .frame(width: 100, height: 100)
                            .clipShape(RoundedRectangle(cornerRadius: 8))
                    }
                }
            }

            PhotosPicker(
                "Select Photos",
                selection: $selectedItems,
                maxSelectionCount: 5,
                matching: .images
            )
        }
        .onChange(of: selectedItems) { _, newItems in
            Task {
                selectedImages = []
                for item in newItems {
                    if let data = try? await item.loadTransferable(type: Data.self),
                       let uiImage = UIImage(data: data) {
                        selectedImages.append(Image(uiImage: uiImage))
                    }
                }
            }
        }
    }
}
```

### Media Type Filtering

Filter with `PHPickerFilter` composites to restrict selectable media:

```swift
// Images only
PhotosPicker(selection: $items, matching: .images)

// Videos only
PhotosPicker(selection: $items, matching: .videos)

// Live Photos only
PhotosPicker(selection: $items, matching: .livePhotos)

// Screenshots only
PhotosPicker(selection: $items, matching: .screenshots)

// Images and videos combined
PhotosPicker(selection: $items, matching: .any(of: [.images, .videos]))

// Images excluding screenshots
PhotosPicker(selection: $items, matching: .all(of: [.images, .not(.screenshots)]))
```

### Loading Selected Items with Transferable

`PhotosPickerItem` loads content asynchronously via `loadTransferable(type:)`. Define a `Transferable` type for automatic decoding:

```swift
struct PickedImage: Transferable {
    let data: Data
    let image: Image

    static var transferRepresentation: some TransferRepresentation {
        DataRepresentation(importedContentType: .image) { data in
            guard let uiImage = UIImage(data: data) else {
                throw TransferError.importFailed
            }
            return PickedImage(data: data, image: Image(uiImage: uiImage))
        }
    }
}

enum TransferError: Error {
    case importFailed
}

// Usage
if let picked = try? await item.loadTransferable(type: PickedImage.self) {
    selectedImage = picked.image
}
```

Always load in a `Task` to avoid blocking the main thread. Handle `nil` returns and thrown errors -- the user may select a format that cannot be decoded.

## Privacy and Permissions

### Photo Library Access Levels

iOS provides two access levels for the photo library. The system automatically presents the limited-library picker when an app requests `.readWrite` access -- users choose which photos to share.

| Access Level | Description | Info.plist Key |
|-------------|-------------|----------------|
| Add-only | Write photos to the library without reading | `NSPhotoLibraryAddUsageDescription` |
| Read-write | Full or limited read access plus write | `NSPhotoLibraryUsageDescription` |

`PhotosPicker` requires no permission to browse -- it runs out-of-process and only grants access to selected items. Request explicit permission only when you need to read the full library (e.g., a custom gallery) or save photos.

### Checking and Requesting Photo Library Permission

```swift
import Photos

func requestPhotoLibraryAccess() async -> PHAuthorizationStatus {
    let status = PHPhotoLibrary.authorizationStatus(for: .readWrite)

    switch status {
    case .notDetermined:
        return await PHPhotoLibrary.requestAuthorization(for: .readWrite)
    case .authorized, .limited:
        return status
    case .denied, .restricted:
        return status
    @unknown default:
        return status
    }
}
```

### Camera Permission

Add `NSCameraUsageDescription` to Info.plist. Check and request access before configuring a capture session:

```swift
import AVFoundation

func requestCameraAccess() async -> Bool {
    let status = AVCaptureDevice.authorizationStatus(for: .video)

    switch status {
    case .notDetermined:
        return await AVCaptureDevice.requestAccess(for: .video)
    case .authorized:
        return true
    case .denied, .restricted:
        return false
    @unknown default:
        return false
    }
}
```

### Handling Denied Permissions

When the user denies access, guide them to Settings. Never repeatedly prompt or hide functionality silently.

```swift
struct PermissionDeniedView: View {
    let message: String

    var body: some View {
        ContentUnavailableView {
            Label("Access Denied", systemImage: "lock.shield")
        } description: {
            Text(message)
        } actions: {
            Button("Open Settings") {
                if let url = URL(string: UIApplication.openSettingsURLString) {
                    UIApplication.shared.open(url)
                }
            }
        }
    }
}
```

### Required Info.plist Keys

| Key | When Required |
|-----|--------------|
| `NSPhotoLibraryUsageDescription` | Reading photos from the library |
| `NSPhotoLibraryAddUsageDescription` | Saving photos/videos to the library |
| `NSCameraUsageDescription` | Accessing the camera |
| `NSMicrophoneUsageDescription` | Recording audio (video with sound) |

Omitting a required key causes a runtime crash when the permission dialog would appear.

## Camera Capture Basics

Manage camera sessions in a dedicated `@Observable` model. The representable view only displays the preview. See `references/camera-capture.md` for complete patterns.

### Minimal Camera Manager

```swift
import AVFoundation

@available(iOS 17.0, *)
@Observable
@MainActor
final class CameraManager {
    let session = AVCaptureSession()
    private let photoOutput = AVCapturePhotoOutput()
    private var currentDevice: AVCaptureDevice?

    var isRunning = false
    var capturedImage: Data?

    func configure() async {
        guard await requestCameraAccess() else { return }

        session.beginConfiguration()
        session.sessionPreset = .photo

        // Add camera input
        guard let device = AVCaptureDevice.default(.builtInWideAngleCamera,
                                                    for: .video,
                                                    position: .back) else { return }
        currentDevice = device

        guard let input = try? AVCaptureDeviceInput(device: device),
              session.canAddInput(input) else { return }
        session.addInput(input)

        // Add photo output
        guard session.canAddOutput(photoOutput) else { return }
        session.addOutput(photoOutput)

        session.commitConfiguration()
    }

    func start() {
        guard !session.isRunning else { return }
        Task.detached { [session] in
            session.startRunning()
        }
        isRunning = true
    }

    func stop() {
        guard session.isRunning else { return }
        Task.detached { [session] in
            session.stopRunning()
        }
        isRunning = false
    }

    private func requestCameraAccess() async -> Bool {
        let status = AVCaptureDevice.authorizationStatus(for: .video)
        if status == .notDetermined {
            return await AVCaptureDevice.requestAccess(for: .video)
        }
        return status == .authorized
    }
}
```

Start and stop `AVCaptureSession` on a background queue. The `startRunning()` and `stopRunning()` methods are synchronous and block the calling thread.

### Camera Preview in SwiftUI

Wrap `AVCaptureVideoPreviewLayer` in a `UIViewRepresentable`. Override `layerClass` for automatic resizing:

```swift
import SwiftUI
import AVFoundation

struct CameraPreview: UIViewRepresentable {
    let session: AVCaptureSession

    func makeUIView(context: Context) -> PreviewView {
        let view = PreviewView()
        view.previewLayer.session = session
        view.previewLayer.videoGravity = .resizeAspectFill
        return view
    }

    func updateUIView(_ uiView: PreviewView, context: Context) {
        if uiView.previewLayer.session !== session {
            uiView.previewLayer.session = session
        }
    }
}

final class PreviewView: UIView {
    override class var layerClass: AnyClass { AVCaptureVideoPreviewLayer.self }
    var previewLayer: AVCaptureVideoPreviewLayer { layer as! AVCaptureVideoPreviewLayer }
}
```

### Using the Camera in a View

```swift
struct CameraScreen: View {
    @State private var cameraManager = CameraManager()

    var body: some View {
        ZStack(alignment: .bottom) {
            CameraPreview(session: cameraManager.session)
                .ignoresSafeArea()

            Button {
                // Capture photo -- see references/camera-capture.md
            } label: {
                Circle()
                    .fill(.white)
                    .frame(width: 72, height: 72)
                    .overlay(Circle().stroke(.gray, lineWidth: 3))
            }
            .padding(.bottom, 32)
        }
        .task {
            await cameraManager.configure()
            cameraManager.start()
        }
        .onDisappear {
            cameraManager.stop()
        }
    }
}
```

Always call `stop()` in `onDisappear`. A running capture session holds the camera exclusively and drains battery.

## Image Loading and Display

### AsyncImage for Remote Images

```swift
AsyncImage(url: imageURL) { phase in
    switch phase {
    case .empty:
        ProgressView()
    case .success(let image):
        image
            .resizable()
            .scaledToFill()
    case .failure:
        Image(systemName: "photo")
            .foregroundStyle(.secondary)
    @unknown default:
        EmptyView()
    }
}
.frame(width: 200, height: 200)
.clipShape(RoundedRectangle(cornerRadius: 12))
```

`AsyncImage` does not cache images across view redraws. For production apps with many images, use a dedicated image loading library or implement `URLCache`-based caching.

### Downsampling Large Images

Load full-resolution photos from the library into a display-sized `CGImage` to avoid memory spikes. A 48MP photo can consume over 200 MB uncompressed.

```swift
import ImageIO
import UIKit

func downsample(data: Data, to pointSize: CGSize, scale: CGFloat = UIScreen.main.scale) -> UIImage? {
    let maxDimensionInPixels = max(pointSize.width, pointSize.height) * scale

    let options: [CFString: Any] = [
        kCGImageSourceCreateThumbnailFromImageAlways: true,
        kCGImageSourceShouldCacheImmediately: true,
        kCGImageSourceCreateThumbnailWithTransform: true,
        kCGImageSourceThumbnailMaxPixelSize: maxDimensionInPixels
    ]

    guard let source = CGImageSourceCreateWithData(data as CFData, nil),
          let cgImage = CGImageSourceCreateThumbnailAtIndex(source, 0, options as CFDictionary) else {
        return nil
    }

    return UIImage(cgImage: cgImage)
}
```

Use this whenever displaying user-selected photos in lists, grids, or thumbnails. Pass the raw `Data` from `PhotosPickerItem` directly to the downsampler before creating a `UIImage`.

### Image Rendering Modes

```swift
// Original: display the image as-is with its original colors
Image("photo")
    .renderingMode(.original)

// Template: treat the image as a mask, colored by foregroundStyle
Image(systemName: "heart.fill")
    .renderingMode(.template)
    .foregroundStyle(.red)
```

Use `.original` for photos and artwork. Use `.template` for icons that should adopt the current tint color.

## Common Mistakes

**DON'T:** Use `UIImagePickerController` for photo picking.
**DO:** Use `PhotosPicker` (SwiftUI) or `PHPickerViewController` (UIKit).
*Why:* `UIImagePickerController` is legacy API with limited functionality. `PhotosPicker` runs out-of-process, supports multi-selection, and requires no library permission for browsing.

**DON'T:** Request full photo library access when you only need the user to pick photos.
**DO:** Use `PhotosPicker` which requires no permission, or request `.readWrite` and let the system handle limited access.
*Why:* Full access is unnecessary for most pick-and-use workflows. The system's limited-library picker respects user privacy and still grants access to selected items.

**DON'T:** Load full-resolution images into memory for thumbnails.
**DO:** Use `CGImageSource` with `kCGImageSourceThumbnailMaxPixelSize` to downsample.
*Why:* A 48MP image occupies over 200 MB uncompressed. Loading multiple at full resolution causes memory pressure warnings and termination.

**DON'T:** Block the main thread loading `PhotosPickerItem` data.
**DO:** Use `async loadTransferable(type:)` in a `Task`.
*Why:* Photo data loading involves disk I/O and potential format conversion. Blocking the main thread causes UI hangs and watchdog kills.

**DON'T:** Forget to stop `AVCaptureSession` when the view disappears.
**DO:** Call `session.stopRunning()` in `onDisappear` or `dismantleUIView`.
*Why:* A running session holds the camera exclusively, preventing other apps from using it, and drains battery continuously.

**DON'T:** Assume camera access is granted without checking.
**DO:** Check `AVCaptureDevice.authorizationStatus(for: .video)` and handle `.denied` and `.restricted` with appropriate UI.
*Why:* Attempting to add a camera input without authorization silently fails. The user sees a blank preview with no explanation.

**DON'T:** Call `session.startRunning()` on the main thread.
**DO:** Dispatch to a background thread with `Task.detached` or a dedicated serial queue.
*Why:* `startRunning()` is a synchronous blocking call that can take hundreds of milliseconds while the hardware initializes.

**DON'T:** Create `AVCaptureSession` inside a `UIViewRepresentable`.
**DO:** Own the session in a separate `@Observable` model and pass it to the representable.
*Why:* `updateUIView` runs on every state change. Creating a session there destroys and recreates the capture pipeline repeatedly.

## Review Checklist

- [ ] `PhotosPicker` used instead of deprecated `UIImagePickerController`
- [ ] Privacy description strings set in Info.plist for camera and/or photo library
- [ ] Loading states handled for async image/video loading from `PhotosPickerItem`
- [ ] Large images downsampled with `CGImageSource` before display
- [ ] Camera session properly started on background thread and stopped in `onDisappear`
- [ ] Permission denial handled with Settings deep link and `ContentUnavailableView`
- [ ] Memory pressure considered for multi-photo selection (sequential loading, downsampling)
- [ ] `AVCaptureSession` owned by a model, not created inside `UIViewRepresentable`
- [ ] Camera preview uses `layerClass` override for automatic resizing
- [ ] `NSMicrophoneUsageDescription` included if recording video with audio
- [ ] Media asset types and picker results are `Sendable` when passed across concurrency boundaries

## References

- `references/photospicker-patterns.md` — Picker patterns, media loading, thumbnail generation, HEIC handling.
- `references/camera-capture.md` — AVCaptureSession setup, photo/video capture, QR scanning, orientation.
