# Camera Capture

Complete patterns for AVCaptureSession setup, photo capture, video recording, and camera features in SwiftUI. All patterns use a dedicated `@Observable` model that owns the session; the SwiftUI view only displays the preview and triggers actions.

---

## 1. Complete Camera Manager with Photo Capture

A full-featured camera model with photo capture using the delegate pattern.

```swift
import AVFoundation
import UIKit

@available(iOS 17.0, *)
@Observable
@MainActor
final class CameraManager: NSObject {
    let session = AVCaptureSession()

    private let photoOutput = AVCapturePhotoOutput()
    private var currentInput: AVCaptureDeviceInput?
    private var photoContinuation: CheckedContinuation<Data?, Never>?

    var isRunning = false
    var cameraPosition: AVCaptureDevice.Position = .back
    var flashMode: AVCaptureDevice.FlashMode = .auto
    var lastCapturedPhoto: Data?
    var error: String?

    // MARK: - Configuration

    func configure() async {
        guard await requestAccess() else {
            error = "Camera access denied"
            return
        }

        session.beginConfiguration()
        session.sessionPreset = .photo

        // Add camera input
        guard let device = cameraDevice(for: cameraPosition),
              let input = try? AVCaptureDeviceInput(device: device),
              session.canAddInput(input) else {
            error = "Failed to configure camera input"
            session.commitConfiguration()
            return
        }
        session.addInput(input)
        currentInput = input

        // Add photo output
        guard session.canAddOutput(photoOutput) else {
            error = "Failed to configure photo output"
            session.commitConfiguration()
            return
        }
        session.addOutput(photoOutput)

        // Enable maximum quality
        photoOutput.isHighResolutionCaptureEnabled = true
        photoOutput.maxPhotoQualityPrioritization = .quality

        session.commitConfiguration()
    }

    // MARK: - Session Control

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

    // MARK: - Photo Capture

    func capturePhoto() async -> Data? {
        let settings = AVCapturePhotoSettings()
        settings.flashMode = flashMode

        if photoOutput.availablePhotoCodecTypes.contains(.hevc) {
            settings.photoQualityPrioritization = .quality
        }

        return await withCheckedContinuation { continuation in
            photoContinuation = continuation
            photoOutput.capturePhoto(with: settings, delegate: self)
        }
    }

    // MARK: - Camera Switching

    func switchCamera() {
        let newPosition: AVCaptureDevice.Position = (cameraPosition == .back) ? .front : .back

        guard let device = cameraDevice(for: newPosition),
              let newInput = try? AVCaptureDeviceInput(device: device) else { return }

        session.beginConfiguration()
        if let currentInput {
            session.removeInput(currentInput)
        }
        if session.canAddInput(newInput) {
            session.addInput(newInput)
            currentInput = newInput
            cameraPosition = newPosition
        }
        session.commitConfiguration()
    }

    // MARK: - Helpers

    private func cameraDevice(for position: AVCaptureDevice.Position) -> AVCaptureDevice? {
        AVCaptureDevice.default(.builtInWideAngleCamera, for: .video, position: position)
    }

    private func requestAccess() async -> Bool {
        let status = AVCaptureDevice.authorizationStatus(for: .video)
        if status == .notDetermined {
            return await AVCaptureDevice.requestAccess(for: .video)
        }
        return status == .authorized
    }
}

// MARK: - AVCapturePhotoCaptureDelegate

@available(iOS 17.0, *)
extension CameraManager: AVCapturePhotoCaptureDelegate {
    nonisolated func photoOutput(
        _ output: AVCapturePhotoOutput,
        didFinishProcessingPhoto photo: AVCapturePhoto,
        error: Error?
    ) {
        let data = photo.fileDataRepresentation()
        Task { @MainActor in
            lastCapturedPhoto = data
            photoContinuation?.resume(returning: data)
            photoContinuation = nil
        }
    }
}
```

The `capturePhoto()` method bridges the delegate-based API to async/await using `CheckedContinuation`. Store only one continuation at a time -- overlapping captures are not supported.

---

## 2. Camera Preview (UIViewRepresentable)

```swift
import SwiftUI
import AVFoundation

struct CameraPreview: UIViewRepresentable {
    let session: AVCaptureSession

    func makeUIView(context: Context) -> CameraPreviewView {
        let view = CameraPreviewView()
        view.previewLayer.session = session
        view.previewLayer.videoGravity = .resizeAspectFill
        return view
    }

    func updateUIView(_ uiView: CameraPreviewView, context: Context) {
        if uiView.previewLayer.session !== session {
            uiView.previewLayer.session = session
        }
    }
}

/// Custom UIView that uses AVCaptureVideoPreviewLayer as its backing layer.
/// Overriding layerClass ensures the preview layer resizes automatically with the view.
final class CameraPreviewView: UIView {
    override class var layerClass: AnyClass { AVCaptureVideoPreviewLayer.self }

    var previewLayer: AVCaptureVideoPreviewLayer {
        layer as! AVCaptureVideoPreviewLayer
    }
}
```

Never add `AVCaptureVideoPreviewLayer` as a sublayer manually. Using `layerClass` avoids manual frame management in `layoutSubviews`.

---

## 3. Complete Camera Screen in SwiftUI

```swift
import SwiftUI

@available(iOS 17.0, *)
struct CameraScreen: View {
    @State private var camera = CameraManager()
    @State private var showCapturedPhoto = false

    var body: some View {
        ZStack {
            CameraPreview(session: camera.session)
                .ignoresSafeArea()

            VStack {
                // Top controls
                HStack {
                    Button {
                        camera.switchCamera()
                    } label: {
                        Image(systemName: "camera.rotate")
                            .font(.title2)
                            .padding()
                            .background(.ultraThinMaterial, in: Circle())
                    }

                    Spacer()

                    // Flash toggle
                    Button {
                        camera.flashMode = (camera.flashMode == .off) ? .auto : .off
                    } label: {
                        Image(systemName: camera.flashMode == .off
                              ? "bolt.slash.fill" : "bolt.fill")
                            .font(.title2)
                            .padding()
                            .background(.ultraThinMaterial, in: Circle())
                    }
                }
                .padding(.horizontal)

                Spacer()

                // Bottom controls
                HStack {
                    // Thumbnail of last capture
                    if let data = camera.lastCapturedPhoto,
                       let uiImage = UIImage(data: data) {
                        Button { showCapturedPhoto = true } label: {
                            Image(uiImage: uiImage)
                                .resizable()
                                .scaledToFill()
                                .frame(width: 50, height: 50)
                                .clipShape(RoundedRectangle(cornerRadius: 8))
                        }
                    } else {
                        Color.clear.frame(width: 50, height: 50)
                    }

                    Spacer()

                    // Shutter button
                    Button {
                        Task { _ = await camera.capturePhoto() }
                    } label: {
                        ZStack {
                            Circle().fill(.white).frame(width: 72, height: 72)
                            Circle().stroke(.gray, lineWidth: 3).frame(width: 78, height: 78)
                        }
                    }

                    Spacer()

                    Color.clear.frame(width: 50, height: 50)
                }
                .padding(.horizontal, 24)
                .padding(.bottom, 32)
            }
        }
        .task {
            await camera.configure()
            camera.start()
        }
        .onDisappear {
            camera.stop()
        }
        .sheet(isPresented: $showCapturedPhoto) {
            if let data = camera.lastCapturedPhoto,
               let uiImage = UIImage(data: data) {
                Image(uiImage: uiImage)
                    .resizable()
                    .scaledToFit()
            }
        }
    }
}
```

---

## 4. Video Recording

Add `AVCaptureMovieFileOutput` for video capture. Video recording requires `NSMicrophoneUsageDescription` in Info.plist for audio.

```swift
import AVFoundation

@available(iOS 17.0, *)
@Observable
@MainActor
final class VideoRecorder: NSObject {
    let session = AVCaptureSession()

    private let movieOutput = AVCaptureMovieFileOutput()
    private var videoContinuation: CheckedContinuation<URL?, Never>?

    var isRecording = false
    var recordedVideoURL: URL?
    var error: String?

    func configure() async {
        guard await requestAccess() else {
            error = "Camera access denied"
            return
        }

        session.beginConfiguration()
        session.sessionPreset = .high

        // Video input
        guard let videoDevice = AVCaptureDevice.default(.builtInWideAngleCamera,
                                                         for: .video, position: .back),
              let videoInput = try? AVCaptureDeviceInput(device: videoDevice),
              session.canAddInput(videoInput) else {
            session.commitConfiguration()
            return
        }
        session.addInput(videoInput)

        // Audio input
        if let audioDevice = AVCaptureDevice.default(for: .audio),
           let audioInput = try? AVCaptureDeviceInput(device: audioDevice),
           session.canAddInput(audioInput) {
            session.addInput(audioInput)
        }

        // Movie output
        guard session.canAddOutput(movieOutput) else {
            session.commitConfiguration()
            return
        }
        session.addOutput(movieOutput)

        session.commitConfiguration()
    }

    func startRecording() {
        guard !isRecording else { return }

        let outputURL = FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString)
            .appendingPathExtension("mov")

        movieOutput.startRecording(to: outputURL, recordingDelegate: self)
        isRecording = true
    }

    func stopRecording() async -> URL? {
        guard isRecording else { return nil }

        return await withCheckedContinuation { continuation in
            videoContinuation = continuation
            movieOutput.stopRecording()
        }
    }

    func start() {
        Task.detached { [session] in session.startRunning() }
    }

    func stop() {
        Task.detached { [session] in session.stopRunning() }
    }

    private func requestAccess() async -> Bool {
        let videoStatus = AVCaptureDevice.authorizationStatus(for: .video)
        let videoGranted: Bool
        if videoStatus == .notDetermined {
            videoGranted = await AVCaptureDevice.requestAccess(for: .video)
        } else {
            videoGranted = videoStatus == .authorized
        }

        // Also request audio for video recording
        let audioStatus = AVCaptureDevice.authorizationStatus(for: .audio)
        if audioStatus == .notDetermined {
            _ = await AVCaptureDevice.requestAccess(for: .audio)
        }

        return videoGranted
    }
}

@available(iOS 17.0, *)
extension VideoRecorder: AVCaptureFileOutputRecordingDelegate {
    nonisolated func fileOutput(
        _ output: AVCaptureFileOutput,
        didFinishRecordingTo outputFileURL: URL,
        from connections: [AVCaptureConnection],
        error: Error?
    ) {
        Task { @MainActor in
            isRecording = false
            recordedVideoURL = error == nil ? outputFileURL : nil
            videoContinuation?.resume(returning: error == nil ? outputFileURL : nil)
            videoContinuation = nil
        }
    }
}
```

Clean up temporary video files when they are no longer needed. Recorded videos can be large and the temporary directory is not automatically cleaned during the app's lifetime.

---

## 5. Flash and Torch Control

Flash applies to photo capture settings. Torch provides continuous illumination for video or preview.

```swift
import AVFoundation

func toggleTorch(on device: AVCaptureDevice, enabled: Bool) throws {
    guard device.hasTorch, device.isTorchAvailable else { return }

    try device.lockForConfiguration()
    device.torchMode = enabled ? .on : .off
    if enabled {
        try device.setTorchModeOn(level: AVCaptureDevice.maxAvailableTorchLevel)
    }
    device.unlockForConfiguration()
}
```

Always wrap device configuration in `lockForConfiguration()` / `unlockForConfiguration()`. Multiple clients may attempt to configure the device simultaneously.

---

## 6. Focus and Exposure

Implement tap-to-focus by converting a SwiftUI tap location to the camera coordinate system.

```swift
import AVFoundation

func setFocusAndExposure(
    at point: CGPoint,
    in previewLayer: AVCaptureVideoPreviewLayer,
    device: AVCaptureDevice
) throws {
    let devicePoint = previewLayer.captureDevicePointConverted(fromLayerPoint: point)

    try device.lockForConfiguration()

    if device.isFocusPointOfInterestSupported {
        device.focusPointOfInterest = devicePoint
        device.focusMode = .autoFocus
    }

    if device.isExposurePointOfInterestSupported {
        device.exposurePointOfInterest = devicePoint
        device.exposureMode = .autoExpose
    }

    device.unlockForConfiguration()
}
```

### Integrating Tap-to-Focus in SwiftUI

```swift
struct FocusableCameraPreview: UIViewRepresentable {
    let session: AVCaptureSession
    var onTapToFocus: ((CGPoint, AVCaptureVideoPreviewLayer) -> Void)?

    func makeUIView(context: Context) -> CameraPreviewView {
        let view = CameraPreviewView()
        view.previewLayer.session = session
        view.previewLayer.videoGravity = .resizeAspectFill

        let tap = UITapGestureRecognizer(
            target: context.coordinator,
            action: #selector(Coordinator.handleTap(_:))
        )
        view.addGestureRecognizer(tap)

        return view
    }

    func updateUIView(_ uiView: CameraPreviewView, context: Context) {}

    func makeCoordinator() -> Coordinator { Coordinator(self) }

    final class Coordinator: NSObject {
        var parent: FocusableCameraPreview

        init(_ parent: FocusableCameraPreview) { self.parent = parent }

        @objc func handleTap(_ gesture: UITapGestureRecognizer) {
            guard let view = gesture.view as? CameraPreviewView else { return }
            let point = gesture.location(in: view)
            parent.onTapToFocus?(point, view.previewLayer)
        }
    }
}
```

---

## 7. Barcode and QR Code Scanning

Use `AVCaptureMetadataOutput` to detect barcodes and QR codes from the camera feed.

```swift
import AVFoundation

@available(iOS 17.0, *)
@Observable
@MainActor
final class QRCodeScanner: NSObject {
    let session = AVCaptureSession()

    private let metadataOutput = AVCaptureMetadataOutput()

    var scannedCode: String?
    var isScanning = false

    func configure() async {
        guard await requestAccess() else { return }

        session.beginConfiguration()

        guard let device = AVCaptureDevice.default(.builtInWideAngleCamera,
                                                    for: .video, position: .back),
              let input = try? AVCaptureDeviceInput(device: device),
              session.canAddInput(input) else {
            session.commitConfiguration()
            return
        }
        session.addInput(input)

        guard session.canAddOutput(metadataOutput) else {
            session.commitConfiguration()
            return
        }
        session.addOutput(metadataOutput)

        // Set metadata types AFTER adding to session -- available types depend on session config
        metadataOutput.metadataObjectTypes = [.qr, .ean8, .ean13, .code128, .code39]
        metadataOutput.setMetadataObjectsDelegate(self, queue: .main)

        session.commitConfiguration()
    }

    func start() {
        scannedCode = nil
        isScanning = true
        Task.detached { [session] in session.startRunning() }
    }

    func stop() {
        isScanning = false
        Task.detached { [session] in session.stopRunning() }
    }

    private func requestAccess() async -> Bool {
        let status = AVCaptureDevice.authorizationStatus(for: .video)
        if status == .notDetermined {
            return await AVCaptureDevice.requestAccess(for: .video)
        }
        return status == .authorized
    }
}

@available(iOS 17.0, *)
extension QRCodeScanner: AVCaptureMetadataOutputObjectsDelegate {
    nonisolated func metadataOutput(
        _ output: AVCaptureMetadataOutput,
        didOutput metadataObjects: [AVMetadataObject],
        from connection: AVCaptureConnection
    ) {
        guard let object = metadataObjects.first as? AVMetadataMachineReadableCodeObject,
              let value = object.stringValue else { return }

        Task { @MainActor in
            scannedCode = value
            stop()
        }
    }
}
```

### Scanner View

```swift
@available(iOS 17.0, *)
struct QRScannerView: View {
    @State private var scanner = QRCodeScanner()

    var body: some View {
        ZStack {
            CameraPreview(session: scanner.session)
                .ignoresSafeArea()

            // Scanning overlay
            RoundedRectangle(cornerRadius: 12)
                .stroke(.white, lineWidth: 2)
                .frame(width: 250, height: 250)

            if let code = scanner.scannedCode {
                VStack {
                    Spacer()
                    Text(code)
                        .font(.headline)
                        .padding()
                        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 12))
                        .padding(.bottom, 60)
                }
            }
        }
        .task {
            await scanner.configure()
            scanner.start()
        }
        .onDisappear {
            scanner.stop()
        }
    }
}
```

Set `metadataObjectTypes` after adding the output to the session. Setting types before causes a runtime crash because the available types are not yet determined.

---

## 8. Camera Preview Orientation

Handle device rotation so the preview and captured photos have correct orientation.

### Preview Layer Rotation

```swift
import AVFoundation
import UIKit

func updatePreviewOrientation(
    _ previewLayer: AVCaptureVideoPreviewLayer,
    for interfaceOrientation: UIInterfaceOrientation
) {
    guard let connection = previewLayer.connection else { return }

    // iOS 17+: use videoRotationAngle
    if #available(iOS 17.0, *) {
        let angle: CGFloat
        switch interfaceOrientation {
        case .portrait: angle = 90
        case .portraitUpsideDown: angle = 270
        case .landscapeLeft: angle = 180
        case .landscapeRight: angle = 0
        default: angle = 90
        }
        if connection.isVideoRotationAngleSupported(angle) {
            connection.videoRotationAngle = angle
        }
    }
}
```

### Photo Output Orientation

Set the rotation angle on the photo output connection before each capture to ensure the captured image matches the device orientation:

```swift
func capturePhotoWithOrientation() {
    if let connection = photoOutput.connection(with: .video) {
        // iOS 17+
        if #available(iOS 17.0, *) {
            let angle = currentVideoRotationAngle()
            if connection.isVideoRotationAngleSupported(angle) {
                connection.videoRotationAngle = angle
            }
        }
    }

    let settings = AVCapturePhotoSettings()
    photoOutput.capturePhoto(with: settings, delegate: self)
}

private func currentVideoRotationAngle() -> CGFloat {
    guard let scene = UIApplication.shared.connectedScenes.first as? UIWindowScene else {
        return 90
    }
    switch scene.interfaceOrientation {
    case .portrait: return 90
    case .portraitUpsideDown: return 270
    case .landscapeLeft: return 180
    case .landscapeRight: return 0
    default: return 90
    }
}
```

Use `videoRotationAngle` (iOS 17+) instead of the deprecated `videoOrientation` property. The angle is measured in degrees clockwise from landscape-right (the natural sensor orientation).

---

## 9. Dual Camera and Device Discovery

Select specific camera hardware using `AVCaptureDevice.DiscoverySession`.

```swift
import AVFoundation

func availableCameras() -> [AVCaptureDevice] {
    let discoverySession = AVCaptureDevice.DiscoverySession(
        deviceTypes: [
            .builtInWideAngleCamera,
            .builtInUltraWideCamera,
            .builtInTelephotoCamera,
            .builtInDualCamera,
            .builtInTripleCamera
        ],
        mediaType: .video,
        position: .unspecified
    )
    return discoverySession.devices
}

func preferredBackCamera() -> AVCaptureDevice? {
    // Prefer triple > dual > wide angle
    let session = AVCaptureDevice.DiscoverySession(
        deviceTypes: [.builtInTripleCamera, .builtInDualCamera, .builtInWideAngleCamera],
        mediaType: .video,
        position: .back
    )
    return session.devices.first
}
```

---

## 10. Restricting Scan Region

Limit the metadata detection area to improve performance and UX:

```swift
// Restrict detection to center 60% of the preview
metadataOutput.rectOfInterest = CGRect(x: 0.2, y: 0.2, width: 0.6, height: 0.6)
```

Note that `rectOfInterest` uses the camera coordinate system (landscape, origin top-left). Convert from preview coordinates using `previewLayer.metadataOutputRectConverted(fromLayerRect:)`.
