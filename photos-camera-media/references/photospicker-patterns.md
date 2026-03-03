# PhotosPicker Patterns

Complete recipes for photo and video selection, loading, saving, and processing. All patterns target iOS 16+ with SwiftUI and async/await.

---

## 1. Single Photo Selection with Loading State

Handle the full lifecycle: idle, loading, loaded, and error.

```swift
import SwiftUI
import PhotosUI

struct ProfilePhotoPicker: View {
    @State private var selectedItem: PhotosPickerItem?
    @State private var loadState: LoadState = .idle

    enum LoadState {
        case idle, loading, loaded(Image), error(String)
    }

    var body: some View {
        VStack {
            switch loadState {
            case .idle:
                Image(systemName: "person.crop.circle.fill")
                    .resizable()
                    .frame(width: 120, height: 120)
                    .foregroundStyle(.secondary)
            case .loading:
                ProgressView()
                    .frame(width: 120, height: 120)
            case .loaded(let image):
                image
                    .resizable()
                    .scaledToFill()
                    .frame(width: 120, height: 120)
                    .clipShape(Circle())
            case .error(let message):
                ContentUnavailableView(message, systemImage: "exclamationmark.triangle")
            }

            PhotosPicker("Choose Photo", selection: $selectedItem, matching: .images)
                .buttonStyle(.borderedProminent)
        }
        .onChange(of: selectedItem) { _, newItem in
            guard let newItem else {
                loadState = .idle
                return
            }
            loadState = .loading
            Task {
                do {
                    if let data = try await newItem.loadTransferable(type: Data.self),
                       let uiImage = UIImage(data: data) {
                        loadState = .loaded(Image(uiImage: uiImage))
                    } else {
                        loadState = .error("Unable to load image")
                    }
                } catch {
                    loadState = .error(error.localizedDescription)
                }
            }
        }
    }
}
```

---

## 2. Multi-Selection with Progress Tracking

Load multiple images sequentially and report progress back to the UI.

```swift
import SwiftUI
import PhotosUI

struct MultiPhotoLoader: View {
    @State private var selectedItems: [PhotosPickerItem] = []
    @State private var loadedImages: [UIImage] = []
    @State private var loadProgress: Double = 0
    @State private var isLoading = false

    var body: some View {
        VStack {
            if isLoading {
                ProgressView(value: loadProgress)
                    .padding()
            }

            ScrollView(.horizontal) {
                LazyHStack(spacing: 8) {
                    ForEach(loadedImages.indices, id: \.self) { index in
                        Image(uiImage: loadedImages[index])
                            .resizable()
                            .scaledToFill()
                            .frame(width: 100, height: 100)
                            .clipShape(RoundedRectangle(cornerRadius: 8))
                    }
                }
                .padding(.horizontal)
            }
            .frame(height: loadedImages.isEmpty ? 0 : 116)

            PhotosPicker(
                "Select Photos",
                selection: $selectedItems,
                maxSelectionCount: 10,
                matching: .images
            )
        }
        .onChange(of: selectedItems) { _, newItems in
            Task { await loadImages(from: newItems) }
        }
    }

    private func loadImages(from items: [PhotosPickerItem]) async {
        isLoading = true
        loadProgress = 0
        var images: [UIImage] = []

        for (index, item) in items.enumerated() {
            if let data = try? await item.loadTransferable(type: Data.self),
               let uiImage = UIImage(data: data) {
                images.append(uiImage)
            }
            loadProgress = Double(index + 1) / Double(items.count)
        }

        loadedImages = images
        isLoading = false
    }
}
```

Load sequentially rather than concurrently to control memory usage. Each full-resolution image can be large; loading ten simultaneously risks memory termination.

---

## 3. Loading Videos from PhotosPicker

Use a `Transferable` wrapper that writes video data to a temporary file, since videos are too large to hold in memory as `Data`.

```swift
import SwiftUI
import PhotosUI
import AVKit

struct PickedMovie: Transferable {
    let url: URL

    static var transferRepresentation: some TransferRepresentation {
        FileRepresentation(contentType: .movie) { movie in
            SentTransferredFile(movie.url)
        } importing: { received in
            // Copy to a temporary location the app controls
            let tempURL = FileManager.default.temporaryDirectory
                .appendingPathComponent(UUID().uuidString)
                .appendingPathExtension("mov")
            try FileManager.default.copyItem(at: received.file, to: tempURL)
            return PickedMovie(url: tempURL)
        }
    }
}

struct VideoPickerView: View {
    @State private var selectedItem: PhotosPickerItem?
    @State private var player: AVPlayer?

    var body: some View {
        VStack {
            if let player {
                VideoPlayer(player: player)
                    .frame(height: 300)
            }

            PhotosPicker("Select Video", selection: $selectedItem, matching: .videos)
        }
        .onChange(of: selectedItem) { _, newItem in
            Task {
                if let movie = try? await newItem?.loadTransferable(type: PickedMovie.self) {
                    player = AVPlayer(url: movie.url)
                }
            }
        }
    }
}
```

Always copy the received file to a temporary directory you control. The system may delete the original transfer file at any time.

---

## 4. Loading Live Photos

```swift
import SwiftUI
import PhotosUI

@available(iOS 17.0, *)
struct LivePhotoPickerView: View {
    @State private var selectedItem: PhotosPickerItem?
    @State private var livePhoto: PHLivePhoto?

    var body: some View {
        VStack {
            if let livePhoto {
                LivePhotoView(livePhoto: livePhoto)
                    .frame(height: 300)
            }

            PhotosPicker(
                "Select Live Photo",
                selection: $selectedItem,
                matching: .livePhotos
            )
        }
        .onChange(of: selectedItem) { _, newItem in
            Task {
                livePhoto = try? await newItem?.loadTransferable(type: PHLivePhoto.self)
            }
        }
    }
}
```

`PHLivePhoto` conforms to `Transferable` on iOS 17+. On iOS 16, load the Live Photo components manually using `PHAsset`.

---

## 5. PHPickerViewController Wrapping (UIKit Interop)

Use `PHPickerViewController` when you need UIKit-level control or are integrating into an existing UIKit codebase. Prefer `PhotosPicker` for pure SwiftUI apps.

```swift
import SwiftUI
import PhotosUI

struct PHPickerWrapper: UIViewControllerRepresentable {
    @Binding var selectedImages: [UIImage]
    var selectionLimit: Int = 0
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
        // Configuration is immutable after creation
    }

    final class Coordinator: NSObject, PHPickerViewControllerDelegate {
        let parent: PHPickerWrapper

        init(_ parent: PHPickerWrapper) { self.parent = parent }

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

Always call `parent.dismiss()` in `picker(_:didFinishPicking:)` -- this delegate method fires for both selection and cancellation (with empty results).

---

## 6. Saving Images to Photo Library

Saving requires `NSPhotoLibraryAddUsageDescription` in Info.plist. Use `PHPhotoLibrary` for saving with metadata, or `UIImageWriteToSavedPhotosAlbum` for simple saves.

### Using PHPhotoLibrary (Preferred)

```swift
import Photos

func saveImageToLibrary(_ image: UIImage) async throws {
    try await PHPhotoLibrary.shared().performChanges {
        let request = PHAssetCreationRequest.forAsset()
        request.addResource(with: .photo, data: image.jpegData(compressionQuality: 0.9)!, options: nil)
    }
}

func saveImageDataToLibrary(_ data: Data) async throws {
    try await PHPhotoLibrary.shared().performChanges {
        let request = PHAssetCreationRequest.forAsset()
        let options = PHAssetResourceCreationOptions()
        request.addResource(with: .photo, data: data, options: options)
    }
}
```

### Saving to a Specific Album

```swift
import Photos

func saveToAlbum(image: UIImage, albumName: String) async throws {
    let album = try await findOrCreateAlbum(named: albumName)

    try await PHPhotoLibrary.shared().performChanges {
        let assetRequest = PHAssetCreationRequest.forAsset()
        assetRequest.addResource(
            with: .photo,
            data: image.jpegData(compressionQuality: 0.9)!,
            options: nil
        )

        guard let placeholder = assetRequest.placeholderForCreatedAsset,
              let albumChangeRequest = PHAssetCollectionChangeRequest(for: album) else { return }
        albumChangeRequest.addAssets([placeholder] as NSArray)
    }
}

private func findOrCreateAlbum(named name: String) async throws -> PHAssetCollection {
    let fetchOptions = PHFetchOptions()
    fetchOptions.predicate = NSPredicate(format: "title = %@", name)
    let result = PHAssetCollection.fetchAssetCollections(with: .album, subtype: .any, options: fetchOptions)

    if let existing = result.firstObject {
        return existing
    }

    // Create the album
    var placeholder: PHObjectPlaceholder?
    try await PHPhotoLibrary.shared().performChanges {
        let request = PHAssetCollectionChangeRequest.creationRequestForAssetCollection(withTitle: name)
        placeholder = request.placeholderForCreatedAssetCollection
    }

    guard let placeholder,
          let collection = PHAssetCollection.fetchAssetCollections(
              withLocalIdentifiers: [placeholder.localIdentifier],
              options: nil
          ).firstObject else {
        throw PhotoLibraryError.albumCreationFailed
    }

    return collection
}

enum PhotoLibraryError: Error {
    case albumCreationFailed
}
```

---

## 7. Thumbnail Generation with ImageIO Downsampling

Generate thumbnails efficiently without decoding the full image into memory. This is critical for grids and lists displaying many photos.

```swift
import ImageIO
import UIKit

/// Downsample image data to a target display size.
/// Use this instead of UIImage(data:) followed by resizing, which decodes the full image.
func downsample(
    data: Data,
    to pointSize: CGSize,
    scale: CGFloat = UIScreen.main.scale
) -> UIImage? {
    let maxDimension = max(pointSize.width, pointSize.height) * scale

    let options: [CFString: Any] = [
        kCGImageSourceCreateThumbnailFromImageAlways: true,
        kCGImageSourceShouldCacheImmediately: true,
        kCGImageSourceCreateThumbnailWithTransform: true,
        kCGImageSourceThumbnailMaxPixelSize: maxDimension
    ]

    guard let source = CGImageSourceCreateWithData(data as CFData, nil),
          let cgImage = CGImageSourceCreateThumbnailAtIndex(source, 0, options as CFDictionary) else {
        return nil
    }

    return UIImage(cgImage: cgImage)
}

/// Downsample from a file URL (avoids loading full data into memory).
func downsample(
    url: URL,
    to pointSize: CGSize,
    scale: CGFloat = UIScreen.main.scale
) -> UIImage? {
    let maxDimension = max(pointSize.width, pointSize.height) * scale

    let sourceOptions: [CFString: Any] = [kCGImageSourceShouldCache: false]
    guard let source = CGImageSourceCreateWithURL(url as CFURL, sourceOptions as CFDictionary) else {
        return nil
    }

    let downsampleOptions: [CFString: Any] = [
        kCGImageSourceCreateThumbnailFromImageAlways: true,
        kCGImageSourceShouldCacheImmediately: true,
        kCGImageSourceCreateThumbnailWithTransform: true,
        kCGImageSourceThumbnailMaxPixelSize: maxDimension
    ]

    guard let cgImage = CGImageSourceCreateThumbnailAtIndex(source, 0, downsampleOptions as CFDictionary) else {
        return nil
    }

    return UIImage(cgImage: cgImage)
}
```

### Usage in a Photo Grid

```swift
struct PhotoGridItem: View {
    let imageData: Data
    let thumbnailSize = CGSize(width: 100, height: 100)

    @State private var thumbnail: UIImage?

    var body: some View {
        Group {
            if let thumbnail {
                Image(uiImage: thumbnail)
                    .resizable()
                    .scaledToFill()
            } else {
                Rectangle()
                    .fill(.quaternary)
                    .overlay(ProgressView())
            }
        }
        .frame(width: 100, height: 100)
        .clipShape(RoundedRectangle(cornerRadius: 6))
        .task {
            thumbnail = downsample(data: imageData, to: thumbnailSize)
        }
    }
}
```

---

## 8. HEIC/HEIF Handling

Modern iPhones capture photos in HEIC format by default. Handle both HEIC and JPEG transparently.

### Checking Image Format

```swift
import UniformTypeIdentifiers

func imageContentType(data: Data) -> UTType? {
    guard let source = CGImageSourceCreateWithData(data as CFData, nil),
          let uti = CGImageSourceGetType(source) as? String else {
        return nil
    }
    return UTType(uti)
}
```

### Converting HEIC to JPEG

```swift
import UIKit

func convertToJPEG(heicData: Data, compressionQuality: CGFloat = 0.9) -> Data? {
    guard let image = UIImage(data: heicData) else { return nil }
    return image.jpegData(compressionQuality: compressionQuality)
}
```

### Preserving HEIC When Possible

When saving or uploading, prefer keeping the original HEIC format to preserve quality and reduce file size. Convert to JPEG only when the destination requires it (e.g., a server that rejects HEIC).

```swift
import PhotosUI

// Request the current representation to avoid transcoding
var config = PHPickerConfiguration(photoLibrary: .shared())
config.preferredAssetRepresentationMode = .current  // Keeps HEIC as-is
// vs .compatible which transcodes to JPEG
```

---

## 9. Custom PhotosPicker Appearance

Customize the picker trigger with any SwiftUI view using the label closure:

```swift
PhotosPicker(selection: $selectedItems, maxSelectionCount: 3, matching: .images) {
    Label("Add Photos", systemImage: "photo.on.rectangle.angled")
        .font(.headline)
        .padding()
        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 12))
}
```

### Inline PhotosPicker (iOS 17+)

Display the picker inline rather than as a sheet:

```swift
@available(iOS 17.0, *)
PhotosPicker(
    selection: $selectedItems,
    maxSelectionCount: 5,
    matching: .images
)
.photosPickerStyle(.inline)
.frame(height: 300)
```

### Photos Picker Access Behavior (iOS 17+)

Control how the picker interacts with limited library access:

```swift
@available(iOS 17.0, *)
PhotosPicker(selection: $selectedItems, matching: .images)
    .photosPickerAccessBehavior(.limited)  // Only show user-approved photos
    // .automatic (default) -- system decides
    // .limited -- only previously approved photos
```

---

## 10. Image Cropping Pattern

A basic square crop using Core Graphics after selecting a photo:

```swift
import UIKit

func cropToSquare(_ image: UIImage) -> UIImage? {
    guard let cgImage = image.cgImage else { return nil }

    let side = min(cgImage.width, cgImage.height)
    let x = (cgImage.width - side) / 2
    let y = (cgImage.height - side) / 2
    let cropRect = CGRect(x: x, y: y, width: side, height: side)

    guard let cropped = cgImage.cropping(to: cropRect) else { return nil }
    return UIImage(cgImage: cropped, scale: image.scale, orientation: image.imageOrientation)
}
```

For interactive cropping, consider wrapping a third-party crop view or building a gesture-based crop overlay in SwiftUI. The system does not provide a built-in crop controller.
