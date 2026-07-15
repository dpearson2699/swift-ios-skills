---
name: paperkit
description: "Add drawings, shapes, and a consistent markup experience using PaperKit. Use when integrating PaperMarkupViewController for markup editing, adding shape recognition, working with PaperMarkup data models, embedding markup tools in document editors, or building annotation features that need the system-standard markup toolbar. New in iOS 26."
---

# PaperKit

> **Beta-sensitive.** PaperKit is new in iOS/iPadOS 26, macOS 26, and visionOS 26. API surface may change. Verify details against current Apple documentation before shipping.

PaperKit combines PencilKit drawing with structured markup elements such as shapes, text, images, and lines in a canvas managed by `PaperMarkupViewController`.

## Contents

- [Setup](#setup)
- [Workflow](#workflow)
- [PaperMarkupViewController](#papermarkupviewcontroller)
- [PaperMarkup Data Model](#papermarkup-data-model)
- [Insertion Controllers](#insertion-controllers)
- [FeatureSet Configuration](#featureset-configuration)
- [Integration with PencilKit](#integration-with-pencilkit)
- [SwiftUI Integration](#swiftui-integration)
- [Common Mistakes](#common-mistakes)
- [Review Checklist](#review-checklist)
- [References](#references)

## Workflow

1. Choose the document bounds, supported `FeatureSet`, and persistence version before constructing UI.
2. Create `PaperMarkup`, embed `PaperMarkupViewController`, and keep the controller, tool picker, and insertion controller alive for the view lifetime.
3. Use the platform-appropriate insertion surface and keep PencilKit drawing inside the PaperKit document boundary.
4. Save off the main thread, retain a thumbnail for forward-incompatible content, and test round-trip loading with the same feature set.
5. On failure, restore the original document bytes, fix the feature-set/version/controller mismatch, and rerun edit, save, relaunch, load, thumbnail fallback, and undo checks.

Load [references/paperkit-patterns.md](references/paperkit-patterns.md) for full platform setup, tool picker wiring, persistence, thumbnails, custom feature sets, programmatic construction, and migration.

## Setup

PaperKit requires no entitlements or special Info.plist entries.

```swift
import PaperKit
```

**Platform availability:** iOS 26.0+, iPadOS 26.0+, Mac Catalyst 26.0+, macOS 26.0+, visionOS 26.0+.

Three core components:

| Component | Role |
|---|---|
| `PaperMarkupViewController` | Interactive canvas for creating and displaying markup and drawing |
| `PaperMarkup` | Data model for serializing all markup elements and PencilKit drawing |
| `MarkupEditViewController` / `MarkupToolbarViewController` | Insertion UI for adding markup elements |

## PaperMarkupViewController

The primary view controller for interactive markup. Provides a scrollable canvas for freeform PencilKit drawing and structured markup elements. Conforms to `Observable` and `PKToolPickerObserver`.

### Basic UIKit Setup

```swift
import PaperKit
import PencilKit
import UIKit

class MarkupViewController: UIViewController, PaperMarkupViewController.Delegate {
    var paperVC: PaperMarkupViewController!
    var toolPicker: PKToolPicker!

    override func viewDidLoad() {
        super.viewDidLoad()

        let pageBounds = CGRect(origin: .zero, size: CGSize(width: 612, height: 792))
        let markup = PaperMarkup(bounds: pageBounds)
        let features = FeatureSet.latest

        paperVC = PaperMarkupViewController(
            markup: markup,
            supportedFeatureSet: features
        )
        paperVC.delegate = self

        addChild(paperVC)
        paperVC.view.frame = view.bounds
        paperVC.view.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        view.addSubview(paperVC.view)
        paperVC.didMove(toParent: self)

        toolPicker = PKToolPicker()
        toolPicker.addObserver(paperVC)
        paperVC.pencilKitResponderState.activeToolPicker = toolPicker
        paperVC.pencilKitResponderState.toolPickerVisibility = .visible
    }

    func paperMarkupViewControllerDidChangeMarkup(
        _ controller: PaperMarkupViewController
    ) {
        guard let markup = controller.markup else { return }
        Task { try await save(markup) }
    }
}
```

### Key Properties

| Property | Type | Description |
|---|---|---|
| `markup` | `PaperMarkup?` | The current data model |
| `selectedMarkup` | `PaperMarkup` | Currently selected content |
| `isEditable` | `Bool` | Whether the canvas accepts input |
| `isRulerActive` | `Bool` | Whether the ruler overlay is shown |
| `drawingTool` | `any PKTool` | Active PencilKit drawing tool |
| `contentView` | `UIView?` / `NSView?` | Background view rendered beneath markup |
| `zoomRange` | `ClosedRange<CGFloat>` | Min/max zoom scale |
| `supportedFeatureSet` | `FeatureSet` | Enabled PaperKit features |

### Touch Modes

`PaperMarkupViewController.TouchMode` has two cases: `.drawing` and `.selection`.

```swift
paperVC.directTouchMode = .drawing    // Finger draws
paperVC.directTouchMode = .selection  // Finger selects elements
paperVC.directTouchAutomaticallyDraws = true  // System decides based on Pencil state
```

### Content Background

Set any view beneath the markup layer for templates, document pages, or images being annotated. Keep the `PaperMarkup(bounds:)` coordinate space aligned to the background content, such as a PDF page or rendered image size, so saved annotations restore in the right place:

```swift
let pageBounds = CGRect(origin: .zero, size: pageImage.size)
let imageView = UIImageView(image: pageImage)
imageView.frame = pageBounds

let markup = PaperMarkup(bounds: pageBounds)
paperVC = PaperMarkupViewController(markup: markup, supportedFeatureSet: features)
paperVC.contentView = imageView
```

### Delegate Callbacks

| Method | Called when |
|---|---|
| `paperMarkupViewControllerDidChangeMarkup(_:)` | Markup content changes |
| `paperMarkupViewControllerDidBeginDrawing(_:)` | User starts drawing |
| `paperMarkupViewControllerDidChangeSelection(_:)` | Selection changes |
| `paperMarkupViewControllerDidChangeContentVisibleFrame(_:)` | Visible frame changes |

## PaperMarkup Data Model

`PaperMarkup` is a `Sendable` struct that stores all markup elements and PencilKit drawing data.

### Creating and Persisting

```swift
// New empty model. Bounds define the saved document coordinate space.
let markup = PaperMarkup(bounds: CGRect(x: 0, y: 0, width: 612, height: 792))

// Load from saved data
let markup = try PaperMarkup(dataRepresentation: savedData)

// Save — dataRepresentation() is async throws
func save(_ markup: PaperMarkup) async throws {
    let data = try await markup.dataRepresentation()
    try data.write(to: fileURL)
}
```

### Inserting Content Programmatically

```swift
// Text box
markup.insertNewTextbox(
    attributedText: AttributedString("Annotation"),
    frame: CGRect(x: 50, y: 100, width: 200, height: 40),
    rotation: 0
)

// Image
markup.insertNewImage(cgImage, frame: CGRect(x: 50, y: 200, width: 300, height: 200), rotation: 0)

// Shape
let shapeConfig = ShapeConfiguration(
    type: .rectangle,
    fillColor: UIColor.systemBlue.withAlphaComponent(0.2).cgColor,
    strokeColor: UIColor.systemBlue.cgColor,
    lineWidth: 2
)
markup.insertNewShape(configuration: shapeConfig, frame: CGRect(x: 50, y: 420, width: 200, height: 100), rotation: 0)

// Line with arrow end marker
let lineConfig = ShapeConfiguration(type: .line, fillColor: nil, strokeColor: UIColor.red.cgColor, lineWidth: 3)
markup.insertNewLine(
    configuration: lineConfig,
    from: CGPoint(x: 50, y: 550), to: CGPoint(x: 250, y: 550),
    startMarker: false, endMarker: true
)
```

Shape types: `.rectangle`, `.roundedRectangle`, `.ellipse`, `.line`, `.arrowShape`, `.star`, `.chatBubble`, `.regularPolygon`.

### Other Operations

```swift
markup.append(contentsOf: otherMarkup)       // Merge another PaperMarkup
markup.append(contentsOf: pkDrawing)          // Merge a PKDrawing
markup.transformContent(CGAffineTransform(...)) // Apply affine transform
markup.removeContentUnsupported(by: featureSet) // Strip unsupported elements
```

| Property | Description |
|---|---|
| `bounds` | Coordinate space of the markup |
| `contentsRenderFrame` | Tight bounding box of all content |
| `featureSet` | Features used by this data model's content |
| `indexableContent` | Extractable text for search indexing |

Use `suggestedFrameForInserting(contentInFrame:)` on the view controller to get a frame that avoids overlapping existing content.

## Insertion Controllers

### MarkupEditViewController (iOS, iPadOS, Mac Catalyst, visionOS)

Presents a popover menu for inserting shapes, text boxes, lines, and other elements.

```swift
func showInsertionMenu(from barButtonItem: UIBarButtonItem) {
    let editVC = MarkupEditViewController(
        supportedFeatureSet: paperVC.supportedFeatureSet,
        additionalActions: []
    )
    editVC.delegate = paperVC  // PaperMarkupViewController conforms to the delegate
    editVC.modalPresentationStyle = .popover
    editVC.popoverPresentationController?.barButtonItem = barButtonItem
    present(editVC, animated: true)
}
```

### MarkupToolbarViewController (macOS, Mac Catalyst)

Provides a toolbar with drawing tools and insertion buttons. Use it for native macOS and for Mac Catalyst toolbar-style UI; Catalyst apps that want a UIKit popover can use `MarkupEditViewController`.

```swift
let toolbar = MarkupToolbarViewController(supportedFeatureSet: paperVC.supportedFeatureSet)
toolbar.delegate = paperVC
addChild(toolbar)
toolbar.view.frame = toolbarContainerView.bounds
toolbarContainerView.addSubview(toolbar.view)
toolbar.didMove(toParent: self)
```

Both controllers must use the same `FeatureSet` as the `PaperMarkupViewController`.

## FeatureSet Configuration

`FeatureSet` controls which markup capabilities are available.

| Preset | Description |
|---|---|
| `.latest` | All current features — recommended starting point |
| `.version1` | Features from version 1 |
| `.empty` | No features enabled |

### Customizing

```swift
var features = FeatureSet.latest
features.remove(.stickers)
features.remove(.images)

// Or build up from empty
var features = FeatureSet.empty
features.insert(.drawing)
features.insert(.text)
features.insert(.shapeStrokes)
```

### Available Features

| Feature | Description |
|---|---|
| `.drawing` | Freeform PencilKit drawing |
| `.text` | Text box insertion |
| `.images` | Image insertion |
| `.stickers` | Sticker insertion |
| `.links` | Link annotations |
| `.loupes` | Loupe/magnifier elements |
| `.shapeStrokes` | Shape outlines |
| `.shapeFills` | Shape fills |
| `.shapeOpacity` | Shape opacity control |

### HDR Support

Set `colorMaximumLinearExposure` above `1.0` on both the `FeatureSet` and `PKToolPicker`:

```swift
var features = FeatureSet.latest
features.colorMaximumLinearExposure = 4.0
toolPicker.colorMaximumLinearExposure = features.colorMaximumLinearExposure
```

Use `view.window?.windowScene?.screen.potentialEDRHeadroom` to match the device screen's capability. Use `1.0` for SDR-only.

### Shapes, Inks, and Line Markers

```swift
features.shapes = [.rectangle, .ellipse, .arrowShape, .line]
features.inks = [.pen, .pencil, .marker]
features.lineMarkerPositions = .all  // .single, .double, .plain, or .all
```

## Integration with PencilKit

PaperKit accepts `PKTool` for drawing and can append `PKDrawing` content.

PaperKit is not a drop-in replacement for a low-level `PKCanvasView` when the app depends on custom brush behavior, raw `PKDrawing` / `PKStroke` analytics, or custom lasso-centric editing. Keep those workflows owned by PencilKit, and add PaperKit beside them for structured review markup such as callouts, arrows, text boxes, labels, image stamps, and system-standard insertion UI. Migrate or duplicate existing drawings into a PaperKit annotation layer with `PaperMarkup.append(contentsOf: PKDrawing)` only when the low-level editing path no longer needs to own that content.

```swift
import PencilKit

// Set drawing tool
paperVC.drawingTool = PKInkingTool(.pen, color: .black, width: 3)

// Merge existing PKDrawing into markup
markup.append(contentsOf: existingPKDrawing)
```

### Tool Picker Setup

```swift
let toolPicker = PKToolPicker()
toolPicker.addObserver(paperVC)
paperVC.pencilKitResponderState.activeToolPicker = toolPicker
paperVC.pencilKitResponderState.toolPickerVisibility = .visible
```

Setting `toolPickerVisibility` to `.hidden` keeps the picker functional (responds to Pencil gestures) but not visible, enabling the mini tool picker experience.

### Content Version Compatibility

`FeatureSet.ContentVersion` maps to `PKContentVersion`:

```swift
let pkVersion = features.contentVersion.pencilKitContentVersion
```

## SwiftUI Integration

Wrap `PaperMarkupViewController` in `UIViewControllerRepresentable`:

```swift
struct MarkupView: UIViewControllerRepresentable {
    @Binding var markup: PaperMarkup
    let features: FeatureSet

    func makeUIViewController(context: Context) -> PaperMarkupViewController {
        let vc = PaperMarkupViewController(markup: markup, supportedFeatureSet: features)
        vc.delegate = context.coordinator
        let toolPicker = PKToolPicker()
        toolPicker.addObserver(vc)
        vc.pencilKitResponderState.activeToolPicker = toolPicker
        vc.pencilKitResponderState.toolPickerVisibility = .visible
        context.coordinator.toolPicker = toolPicker
        return vc
    }

    func updateUIViewController(_ vc: PaperMarkupViewController, context: Context) {
        if vc.markup != markup { vc.markup = markup }
    }

    func makeCoordinator() -> Coordinator { Coordinator(parent: self) }

    class Coordinator: NSObject, PaperMarkupViewController.Delegate {
        let parent: MarkupView
        var toolPicker: PKToolPicker?
        init(parent: MarkupView) { self.parent = parent }

        func paperMarkupViewControllerDidChangeMarkup(
            _ controller: PaperMarkupViewController
        ) {
            if let markup = controller.markup { parent.markup = markup }
        }
    }
}
```

Initialize the bound `PaperMarkup` from the document or page size before creating the SwiftUI bridge:

```swift
struct DocumentMarkupScreen: View {
    let pageSize: CGSize
    @State private var markup: PaperMarkup
    private let features = FeatureSet.latest

    init(pageSize: CGSize) {
        self.pageSize = pageSize
        _markup = State(
            initialValue: PaperMarkup(
                bounds: CGRect(origin: .zero, size: pageSize)
            )
        )
    }

    var body: some View {
        MarkupView(markup: $markup, features: features)
    }
}
```

## Common Mistakes

| Mistake | Fix |
|---|---|
| View, insertion UI, and saved document use mismatched feature sets | Choose one supported `FeatureSet` and use it across the editing session. |
| Loaded content is assigned without a version check | Verify `markup.featureSet.isSubset(of: supportedFeatureSet)` or show the saved thumbnail/fallback. |
| Serialization blocks UI or overlaps unsafely | Await `dataRepresentation()` off the interaction path and debounce autosaves. |
| Tool picker is a local variable | Retain it for the controller/view lifetime. |
| Wrong insertion surface for the platform | Use `MarkupToolbarViewController` on macOS; use `MarkupEditViewController` on UIKit, with Catalyst supporting either presentation. |

## Review Checklist

- [ ] `import PaperKit` present; deployment target is iOS 26+ / macOS 26+ / visionOS 26+
- [ ] `PaperMarkup` initialized with bounds matching content size
- [ ] Same `FeatureSet` used for `PaperMarkupViewController` and insertion controller
- [ ] `dataRepresentation()` called in async context
- [ ] `PKToolPicker` retained as a stored property
- [ ] Delegate set on `PaperMarkupViewController` for change callbacks
- [ ] Content version checked when loading saved data
- [ ] Correct insertion controller per platform (`MarkupToolbarViewController` for macOS/Catalyst toolbar UI; `MarkupEditViewController` for UIKit/Catalyst popovers)
- [ ] `MarkupError` cases handled on deserialization
- [ ] HDR: `colorMaximumLinearExposure` set on `FeatureSet` and `PKToolPicker.colorMaximumLinearExposure`

## References

- [PaperKit documentation](https://sosumi.ai/documentation/paperkit)
- [Integrating PaperKit into your app](https://sosumi.ai/documentation/paperkit/getting-started-with-paperkit)
- [Meet PaperKit — WWDC25](https://sosumi.ai/videos/play/wwdc2025/285/)
- The `pencilkit` skill covers PencilKit drawing, tool pickers, and PKDrawing serialization
- [references/paperkit-patterns.md](references/paperkit-patterns.md) — data persistence, rendering, multi-platform setup, custom feature sets
