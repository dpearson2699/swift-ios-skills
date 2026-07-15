---
name: vision-framework
description: "Implement computer vision features including text recognition (OCR), face detection, barcode scanning, image segmentation, object tracking, and document scanning in iOS apps. Covers both the modern Swift-native Vision API (iOS 18+) and legacy VNRequest patterns, VisionKit DataScannerViewController for live camera scanning, and CoreMLRequest/VNCoreMLRequest for custom model inference. Use when adding OCR, barcode scanning, face detection, or custom Core ML model inference with Vision."
---

# Vision Framework

Detect text, faces, barcodes, objects, and body poses in images and video using
on-device computer vision. Prefer the modern iOS 18+ request APIs and load the legacy reference only when the deployment target requires it.

See [references/vision-requests.md](references/vision-requests.md) for complete code patterns and
[references/visionkit-scanner.md](references/visionkit-scanner.md) for DataScannerViewController integration.

## Contents

- [Two API Generations](#two-api-generations)
- [Request Pattern (Modern API)](#request-pattern-modern-api)
- [Text Recognition (OCR)](#text-recognition-ocr)
- [Face Detection](#face-detection)
- [Barcode Detection](#barcode-detection)
- [Document Scanning (iOS 26+)](#document-scanning-ios-26)
- [Image Segmentation](#image-segmentation)
- [Object Tracking](#object-tracking)
- [Other Request Types](#other-request-types)
- [Core ML Integration](#core-ml-integration)
- [VisionKit: DataScannerViewController](#visionkit-datascannerviewcontroller)
- [Common Mistakes](#common-mistakes)
- [Review Checklist](#review-checklist)
- [References](#references)

## Two API Generations

Vision has two distinct API layers. Prefer the modern API for new code:
Swift-native request types plus `try await request.perform(on:)`. Keep `VN*`,
`VNImageRequestHandler`, `VNSequenceRequestHandler`, completion handlers, and
legacy `CGRect` helpers inside explicit legacy fallback sections or files.

| Aspect | Modern (iOS 18+) | Legacy |
|---|---|---|
| Pattern | `let result = try await request.perform(on: image)` | `VNImageRequestHandler` + completion handler |
| Request types | Swift types — structs and classes (`RecognizeTextRequest`, `DetectFaceRectanglesRequest`) | ObjC classes (`VNRecognizeTextRequest`, `VNDetectFaceRectanglesRequest`) |
| Concurrency | Native async/await | Completion handlers or synchronous `perform` |
| Observations | Typed return values | Cast `results` from `[Any]` |
| Availability | iOS 18+ / macOS 15+ | iOS 11+ |

The modern API uses the `ImageProcessingRequest` protocol. Each request type
has a `perform(on:orientation:)` method that accepts `CGImage`, `CIImage`,
`CVPixelBuffer`, `CMSampleBuffer`, `Data`, or `URL`. Most requests are
structs; stateful requests such as `GeneratePersonSegmentationRequest`,
`TrackObjectRequest`, `TrackRectangleRequest`, and `DetectTrajectoriesRequest`
are final classes.

## Request Pattern (Modern API)

All modern Vision requests follow the same pattern: create a request, call
`perform(on:)`, and handle the typed result.

```swift
import Vision

func recognizeText(in image: CGImage) async throws -> [String] {
    var request = RecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.recognitionLanguages = [Locale.Language(identifier: "en-US")]

    let observations = try await request.perform(on: image)
    return observations.compactMap { observation in
        observation.topCandidates(1).first?.string
    }
}
```

### Legacy Pattern (Pre-iOS 18)

For pre-iOS 18 targets, use the corresponding `VNRequest` with `VNImageRequestHandler` or `VNSequenceRequestHandler`. Load [references/vision-requests.md](references/vision-requests.md) for complete legacy request and handler patterns.

## Text Recognition (OCR)

### Modern: RecognizeTextRequest (iOS 18+)

```swift
var request = RecognizeTextRequest()
request.recognitionLevel = .accurate       // .fast for real-time
request.recognitionLanguages = [
    Locale.Language(identifier: "en-US"),
    Locale.Language(identifier: "fr-FR"),
]
request.usesLanguageCorrection = true
request.customWords = ["SwiftUI", "Xcode"] // domain-specific terms

let observations = try await request.perform(on: cgImage)
for observation in observations {
    guard let candidate = observation.topCandidates(1).first else { continue }
    let text = candidate.string
    let confidence = candidate.confidence  // 0.0 ... 1.0
    let bounds = observation.boundingBox   // NormalizedRect
}
```

### Legacy: VNRecognizeTextRequest

The legacy request uses string language identifiers and the handler pattern in the reference; both generations support accurate and fast recognition levels.

## Face Detection

Detect face rectangles, landmarks (eyes, nose, mouth), and capture quality.

```swift
// Modern API
let faceRequest = DetectFaceRectanglesRequest()
let faces = try await faceRequest.perform(on: cgImage)

for face in faces {
    let boundingBox = face.boundingBox   // NormalizedRect
    let roll = face.roll                 // Measurement<UnitAngle>
    let yaw = face.yaw                  // Measurement<UnitAngle>
}

// Landmarks (eyes, nose, mouth contours)
var landmarkRequest = DetectFaceLandmarksRequest()
let landmarkFaces = try await landmarkRequest.perform(on: cgImage)
for face in landmarkFaces {
    let landmarks = face.landmarks
    let leftEye = landmarks?.leftEye.points
    let nose = landmarks?.nose.points
}
```

### Coordinate System

Vision uses a normalized coordinate system with origin at the bottom-left.
Convert to UIKit (top-left origin) before display:

```swift
import Vision

func imageRectForDisplay(_ rect: NormalizedRect, imageSize: CGSize) -> CGRect {
    rect.toImageCoordinates(imageSize, origin: .upperLeft)
}
```

## Barcode Detection

Detect 1D and 2D barcodes including QR codes.

```swift
var request = DetectBarcodesRequest()
let symbologies: [BarcodeSymbology] = [.qr, .ean13, .code128, .pdf417]
request.symbologies = symbologies

let barcodes = try await request.perform(on: cgImage)
for barcode in barcodes {
    let payload = barcode.payloadString          // decoded content
    let symbology = barcode.symbology            // .qr, .ean13, etc.
    let bounds = barcode.boundingBox             // NormalizedRect
}
```
Type annotate local values first, then assign request properties separately.

## Document Scanning (iOS 26+)

`RecognizeDocumentsRequest` provides structured document reading with layout
understanding beyond basic OCR. Returns `DocumentObservation` objects with a
nested `Container` structure for paragraphs, tables, lists, and barcodes.
Currently, Vision returns one document observation for each image.

```swift
var request = RecognizeDocumentsRequest()
let documents = try await request.perform(on: cgImage)

for observation in documents {
    let container = observation.document

    // Full text content
    let fullText = container.text

    // Structured access to paragraphs
    for paragraph in container.paragraphs {
        let paragraphText = paragraph.text
    }

    // Tables and lists
    for table in container.tables { /* structured table data */ }
    for list in container.lists { /* structured list data */ }

    // Embedded barcodes detected within the document
    for barcode in container.barcodes { /* barcode data */ }

    // Document title if detected
    if let title = container.title { print(title) }
}
```

For simpler document camera scanning, use VisionKit's
`VNDocumentCameraViewController` which provides a full-screen camera UI with
auto-capture, perspective correction, and multi-page scanning.

## Image Segmentation

### Modern: GeneratePersonSegmentationRequest (iOS 18+)

```swift
var request = GeneratePersonSegmentationRequest()
request.qualityLevel = .accurate  // .balanced, .fast

let mask = try await request.perform(on: cgImage)
// mask is a PixelBufferObservation with a pixelBuffer property
let maskBuffer = mask.pixelBuffer
// Apply mask using Core Image: CIFilter.blendWithMask()
```

### Legacy: VNGeneratePersonSegmentationRequest

For older targets, `VNGeneratePersonSegmentationRequest` exposes its mask through the first pixel-buffer observation; use the reference's handler and mask-composition recipe.

Quality levels:
- `.accurate` -- best quality, slowest (~1s), full resolution
- `.balanced` -- good quality, moderate speed (~100ms), 960x540
- `.fast` -- lowest quality, fastest (~10ms), 256x144, suitable for real-time

### Instance Segmentation (iOS 18+)

Separate masks per person for individual effects.

```swift
// Modern API (iOS 18+)
let request = GeneratePersonInstanceMaskRequest()
let observation = try await request.perform(on: cgImage)
let indices = observation.allInstances

for index in indices {
    let mask = try observation.generateMask(for: IndexSet(integer: index))
    // mask is a CVPixelBuffer with only this person visible
}
```

```swift
// Legacy API (iOS 17+)
let request = VNGeneratePersonInstanceMaskRequest()
let handler = VNImageRequestHandler(cgImage: cgImage)
try handler.perform([request])

guard let result = request.results?.first else { return }
let indices = result.allInstances
for index in indices {
    let instanceMask = try result.generateMaskedImage(
        ofInstances: IndexSet(integer: index),
        from: handler,
        croppedToInstancesExtent: false
    )
}
```

See [references/vision-requests.md](references/vision-requests.md) for mask composition and Core Image filter
integration patterns.

## Object Tracking

### Modern: TrackObjectRequest (iOS 18+)

`TrackObjectRequest` is a stateful request that maintains tracking context
across frames.

```swift
// Initialize with a detected object's bounding box
let initialObservation = DetectedObjectObservation(boundingBox: detectedBox)
let request = TrackObjectRequest(detectedObject: initialObservation)

for pixelBuffer in framePixelBuffers {
    let results = try await request.perform(on: pixelBuffer)
    if let tracked = results.first {
        let updatedBounds = tracked.boundingBox  // NormalizedRect
    }
}
```

Modern `TrackObjectRequest` has no `trackingLevel` or `qualityLevel`.

### Legacy: VNTrackObjectRequest

For older targets, use `VNTrackObjectRequest` with one retained `VNSequenceRequestHandler` and feed each result back as the next input observation. The reference contains the complete loop.

## Other Request Types

Vision provides additional requests covered in [references/vision-requests.md](references/vision-requests.md):

| Request | Purpose |
|---|---|
| `ClassifyImageRequest` | Classify scene content (outdoor, food, animal, etc.) |
| `GenerateAttentionBasedSaliencyImageRequest` | Single `SaliencyImageObservation` for where viewers focus attention |
| `GenerateObjectnessBasedSaliencyImageRequest` | Single `SaliencyImageObservation` for object-like regions |
| `GenerateForegroundInstanceMaskRequest` | Foreground object segmentation (not person-specific) |
| `DetectRectanglesRequest` | Detect rectangular shapes (documents, cards, screens) |
| `DetectHorizonRequest` | Detect horizon angle for auto-leveling photos |
| `DetectHumanBodyPoseRequest` | Detect body joints (shoulders, elbows, knees) |
| `DetectHumanBodyPose3DRequest` | 3D human body pose estimation |
| `DetectHumanHandPoseRequest` | Detect hand joints and finger positions |
| `DetectAnimalBodyPoseRequest` | Detect animal body joint positions |
| `DetectFaceCaptureQualityRequest` | Face capture quality scoring (0–1) for photo selection |
| `TrackRectangleRequest` | Track rectangular objects across video frames |
| `TrackOpticalFlowRequest` | Optical flow between video frames |
| `DetectTrajectoriesRequest` | Detect object trajectories in video |

All modern request types above are iOS 18+ / macOS 15+.

## Core ML Integration

Run custom Core ML models through Vision for automatic image preprocessing.

Vision runs already-prepared models with `CoreMLRequest` or `VNCoreMLRequest`;
hand conversion, profiling, packaging, and lifecycle decisions to `coreml`.

```swift
import CoreML
import Vision

// Modern API (iOS 18+): CoreMLRequest takes a CoreMLModelContainer.
let model = try MLModel(contentsOf: modelURL)
let container = try CoreMLModelContainer(model: model, featureProvider: nil)
let request = CoreMLRequest(model: container)
let results = try await request.perform(on: cgImage)

// Classification model
if let classification = results.first as? ClassificationObservation {
    let label = classification.identifier
    let confidence = classification.confidence
}
```
`CoreMLModelContainer` is the public iOS 18+ Vision container for
`CoreMLRequest`: load an `MLModel`, wrap it with
`CoreMLModelContainer(model:featureProvider:)`, then pass that container to
`CoreMLRequest(model:)`. State result mapping when reviewing Core ML through
Vision: classifiers produce `ClassificationObservation`, image outputs produce
`PixelBufferObservation`, and general predictors produce `CoreMLFeatureValueObservation`.

```swift
// Legacy API
let vnModel = try VNCoreMLModel(for: model)
let request = VNCoreMLRequest(model: vnModel) { request, error in
    guard let results = request.results as? [VNClassificationObservation] else { return }
    let topResult = results.first
}
let handler = VNImageRequestHandler(cgImage: cgImage)
try handler.perform([request])
```

## VisionKit: DataScannerViewController

`DataScannerViewController` provides a live camera scanner for text and
barcodes; see [references/visionkit-scanner.md](references/visionkit-scanner.md). VisionKit uses
`VNBarcodeSymbology`; modern `DetectBarcodesRequest` uses `BarcodeSymbology`.

### Quick Start

```swift
import AVFoundation
import Vision
import VisionKit

@MainActor
func presentScanner() async {
    // Add NSCameraUsageDescription before requesting camera access.
    guard await AVCaptureDevice.requestAccess(for: .video) else { return }
    guard DataScannerViewController.isSupported,
          DataScannerViewController.isAvailable else { return }

    let scannerSymbologies: [VNBarcodeSymbology] = [.qr, .ean13]
    let scanner = DataScannerViewController(
        recognizedDataTypes: [
            .text(languages: ["en"]),
            .barcode(symbologies: scannerSymbologies)
        ],
        qualityLevel: .balanced,
        recognizesMultipleItems: true,
        isHighFrameRateTrackingEnabled: true,
        isHighlightingEnabled: true
    )
    scanner.delegate = self
    present(scanner, animated: true) {
        // Start scanning after presentation, on the main actor.
        try? scanner.startScanning()
    }
}
```

### SwiftUI Integration

Wrap `DataScannerViewController` in `UIViewControllerRepresentable` and start in
`updateUIViewController` with `Task { @MainActor in try? controller.startScanning() }`; see [references/visionkit-scanner.md](references/visionkit-scanner.md).

## Common Mistakes

**DON'T:** Use the legacy `VNImageRequestHandler` API for new iOS 18+ projects.
**DO:** Use modern Swift-native requests with `perform(on:)` and async/await.
**Why:** Modern API provides type safety, better Swift concurrency support, and cleaner error handling.

**DON'T:** Forget to convert normalized coordinates before drawing bounding boxes.
**DO:** Use `NormalizedRect.toImageCoordinates(_:origin:)` for modern observations, or `VNImageRectForNormalizedRect(_:_:_:)` for legacy `CGRect` observations.
**Why:** Vision uses normalized coordinates (0...1) with bottom-left origin; UIKit uses points with top-left origin.

**DON'T:** Run Vision requests on the main thread.
**DO:** Perform requests on a background thread or use async/await from a detached task.
**Why:** Image analysis is CPU/GPU-intensive and blocks the UI if run on the main actor.

**DON'T:** Use `.accurate` recognition level for real-time camera feeds.
**DO:** Use `.fast` for live video, `.accurate` for still images or offline processing.
**Why:** Accurate recognition is too slow for 30fps video; fast recognition trades quality for speed.

**DON'T:** Treat every Vision observation as having the same properties.
**DO:** Check each observation type for its bounding box, confidence, payload, mask, or angle fields before writing shared helpers.
**Why:** Modern Vision returns strongly typed observations, and result shapes vary by request.

**DON'T:** Recreate stateful tracking requests for each video frame.
**DO:** Keep the same modern `TrackObjectRequest` instance, or use `VNSequenceRequestHandler` with legacy tracking requests.
**Why:** Tracking relies on temporal context across frames.

**DON'T:** Request all barcode symbologies when you only need QR codes.
**DO:** Specify only the symbologies you need in the request.
**Why:** Fewer symbologies means faster detection and fewer false positives.

**DON'T:** Assume `DataScannerViewController` is available on all devices.
**DO:** Check both `isSupported` (hardware) and `isAvailable` (user permissions) before presenting.
**Why:** Requires A12+ chip; `isAvailable` also checks camera access authorization.

## Review Checklist

- [ ] Uses modern Vision API (iOS 18+) unless targeting older deployments
- [ ] Vision requests run off the main thread (async/await or background queue)
- [ ] Normalized coordinates converted before UI display
- [ ] Confidence threshold applied to filter low-quality observations
- [ ] Recognition level matches use case (`.fast` for video, `.accurate` for stills)
- [ ] Language hints set for text recognition when input language is known
- [ ] Barcode symbologies limited to only those needed
- [ ] `DataScannerViewController` availability checked before presentation
- [ ] Camera usage description (`NSCameraUsageDescription`) in Info.plist for VisionKit
- [ ] VisionKit camera access requested before presentation and scanning started after presentation
- [ ] Person segmentation quality level appropriate for use case
- [ ] Stateful tracking request or `VNSequenceRequestHandler` preserved across video frames
- [ ] Error handling covers request failures and empty results

## References

- Vision request patterns: [references/vision-requests.md](references/vision-requests.md)
- VisionKit scanner integration: [references/visionkit-scanner.md](references/visionkit-scanner.md)
- Apple docs: [Vision](https://sosumi.ai/documentation/vision) |
  [VisionKit](https://sosumi.ai/documentation/visionkit) |
  [RecognizeTextRequest](https://sosumi.ai/documentation/vision/recognizetextrequest) |
  [DataScannerViewController](https://sosumi.ai/documentation/visionkit/datascannerviewcontroller) |
  [CoreMLRequest](https://sosumi.ai/documentation/vision/coremlrequest) |
  [CoreMLModelContainer](https://sosumi.ai/documentation/vision/coremlmodelcontainer)
