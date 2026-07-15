---
name: pencilkit
description: "Add Apple Pencil drawing with PKCanvasView, PKToolPicker, PKDrawing serialization/export, stroke inspection, and PencilKit/PaperKit handoffs. Use when building drawing apps, annotation features, handwriting capture, signature fields, content-version-safe ink workflows, or Apple Pencil-powered experiences on iOS/iPadOS/visionOS."
---

# PencilKit

Capture Apple Pencil and finger input using `PKCanvasView`, manage drawing
tools with `PKToolPicker`, serialize drawings with `PKDrawing`, and wrap PencilKit in SwiftUI.

## Contents

- [Setup](#setup)
- [Capture-to-Export Workflow](#capture-to-export-workflow)
- [PKCanvasView Basics](#pkcanvasview-basics)
- [PKToolPicker](#pktoolpicker)
- [PKDrawing Serialization](#pkdrawing-serialization)
- [Content Version Compatibility](#content-version-compatibility)
- [Exporting to Image](#exporting-to-image)
- [Stroke Inspection](#stroke-inspection)
- [SwiftUI Integration](#swiftui-integration)
- [PaperKit Relationship](#paperkit-relationship)
- [Common Mistakes](#common-mistakes)
- [Review Checklist](#review-checklist)
- [References](#references)

## Setup

PencilKit requires no entitlements or Info.plist entries. Import `PencilKit`
and create a `PKCanvasView`.

```swift
import PencilKit
```

**Platform availability:** iOS 13+, iPadOS 13+, Mac Catalyst 13.1+, visionOS 1.0+.

## Capture-to-Export Workflow

1. **Capture:** Read `canvasView.drawing` from
   `canvasViewDrawingDidChange(_:)`; keep the previous persisted revision until
   the new revision completes the remaining checkpoints.
2. **Serialize:** Create `dataRepresentation()`, write atomically, and run the
   [decode validate/fix/retry loop](#decode-validatefixretry-loop). Do not mark
   bytes valid when `PKDrawing(data:)` still throws.
3. **Version-gate:** Apply [Content Version Compatibility](#content-version-compatibility)
   before editable sync. If the recipient cannot load the drawing, preserve the
   full-fidelity source and use an existing compatible fallback or read-only
   preview.
4. **Sync:** Send only validated, compatible data and mark the revision synced
   after acknowledgement. On transport or conflict failure, retain the pending
   revision, resolve the cause, and retry without discarding the last good copy.
5. **Export:** Validate a nonempty drawing region and intended scale before
   calling `image(from:scale:)`; skip export on invalid bounds without altering
   the serialized drawing.

## PKCanvasView Basics

`PKCanvasView` is a `UIScrollView` subclass that captures Apple Pencil and
finger input and renders strokes.

```swift
import PencilKit
import UIKit

class DrawingViewController: UIViewController, PKCanvasViewDelegate {
    let canvasView = PKCanvasView()

    override func viewDidLoad() {
        super.viewDidLoad()
        canvasView.delegate = self
        canvasView.drawingPolicy = .anyInput
        canvasView.tool = PKInkingTool(.pen, color: .black, width: 5)
        canvasView.frame = view.bounds
        canvasView.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        view.addSubview(canvasView)
    }

    func canvasViewDrawingDidChange(_ canvasView: PKCanvasView) {
        // Drawing changed -- save or process
    }
}
```

### Drawing Policies

| Policy | Behavior |
|---|---|
| `.default` | Respects `UIPencilInteraction.prefersPencilOnlyDrawing` when the tool picker is visible; otherwise Pencil-only |
| `.anyInput` | Both pencil and finger draw |
| `.pencilOnly` | Only Apple Pencil touches draw on the canvas |

```swift
canvasView.drawingPolicy = .pencilOnly
```

Use `.default` for system-standard Pencil-primary canvases when the tool
picker's drawing-policy control should follow the user's Pencil preference. Use
`.anyInput` for signature pads, whiteboards, or explicit finger-drawing modes.
Use `.pencilOnly` when finger input should never create strokes.

### Configuring the Canvas

```swift
// Set a large drawing area (scrollable)
canvasView.contentSize = CGSize(width: 2000, height: 3000)

// Enable/disable the ruler
canvasView.isRulerActive = true

// Set the current tool programmatically
canvasView.tool = PKInkingTool(.pencil, color: .blue, width: 3)
canvasView.tool = PKEraserTool(.vector)
```

## PKToolPicker

`PKToolPicker` displays a floating palette of drawing tools. The canvas
automatically adopts the selected tool.

```swift
class DrawingViewController: UIViewController {
    let canvasView = PKCanvasView()
    let toolPicker = PKToolPicker()

    override func viewDidAppear(_ animated: Bool) {
        super.viewDidAppear(animated)
        toolPicker.addObserver(canvasView)
        toolPicker.setVisible(true, forFirstResponder: canvasView)
        canvasView.becomeFirstResponder()
    }
}
```

### Custom Tool Picker Items

Create a tool picker with specific tools. `PKToolPicker(toolItems:)` and
custom tool picker item classes require iOS/iPadOS 18+, Mac Catalyst 18+, and
visionOS 2+; those item classes are available on macOS starting in macOS 26.

```swift
let toolPicker = PKToolPicker(toolItems: [
    PKToolPickerInkingItem(type: .pen, color: .black, width: 5),
    PKToolPickerInkingItem(type: .pencil, color: .gray, width: 5),
    PKToolPickerInkingItem(type: .marker, color: .yellow, width: 12),
    PKToolPickerEraserItem(type: .vector),
    PKToolPickerLassoItem(),
    PKToolPickerRulerItem()
])
```

### Ink Types

| Type | Description |
|---|---|
| `.pen` | Smooth, pressure-sensitive pen |
| `.pencil` | Textured pencil with tilt shading |
| `.marker` | Semi-transparent highlighter |
| `.monoline` | Uniform-width pen |
| `.fountainPen` | Variable-width calligraphy pen |
| `.watercolor` | Blendable watercolor brush |
| `.crayon` | Textured crayon |
| `.reed` | Reed pen (iOS/iPadOS/macOS/visionOS 26+) |

### Content Versions

Use [Content Version Compatibility](#content-version-compatibility) as the
single version map and compatibility gate for both the canvas and tool picker.

## PKDrawing Serialization

`PKDrawing` is a value type (struct) that holds all stroke data. Serialize
it to `Data` for persistence.

```swift
// Save
func saveDrawing(_ drawing: PKDrawing) throws {
    let data = drawing.dataRepresentation()
    try data.write(to: fileURL, options: .atomic)
}

// Load
func loadDrawing() throws -> PKDrawing {
    let data = try Data(contentsOf: fileURL)
    return try PKDrawing(data: data)
}
```

### Decode Validate/Fix/Retry Loop

For synced or user-provided data: **validate** with `PKDrawing(data:)`; on
failure preserve the original bytes and **fix** the cause by refetching an
intact revision or selecting a previously generated compatible copy; then
**retry** the decode. Assign the drawing only after a successful retry. If
recovery still fails, keep the source unchanged and show an error or available
read-only preview instead of suppressing the failure with `try?`.

```swift
do {
    canvasView.drawing = try PKDrawing(data: correctedData) // retry
} catch {
    showReadOnlyPreview(for: document, loadError: error)
}
```

### Combining Drawings

```swift
var drawing1 = PKDrawing()
let drawing2 = PKDrawing()
drawing1.append(drawing2)

// Non-mutating
let combined = drawing1.appending(drawing2)
```

### Transforming Drawings

```swift
let scaled = drawing.transformed(using: CGAffineTransform(scaleX: 2, y: 2))
let translated = drawing.transformed(using: CGAffineTransform(translationX: 100, y: 0))
```

## Content Version Compatibility

For sync, migration, downgrade, or cross-device editing tasks, use
`requiredContentVersion` as the compatibility gate and choose an explicit
`maximumSupportedContentVersion` when old clients must keep editing.

```swift
let targetVersion: PKContentVersion = .version1
canvasView.maximumSupportedContentVersion = targetVersion
toolPicker.maximumSupportedContentVersion = targetVersion

switch drawing.requiredContentVersion {
case .version1:
    // Older marker, pen, and pencil ink set
    syncEditable(drawing)
case .version2:
    // iPadOS 17-era inks: monoline, fountain pen, watercolor, crayon
    syncIfRecipientsSupportVersion2(drawing)
case .version3, .version4:
    // Later features such as barrel-roll data and Reed Pen
    syncEditableOnlyToCurrentClients(drawing)
@unknown default:
    showReadOnlyPreview(for: drawing)
}
```

If a drawing requires a newer version than a recipient can load, preserve the
full-fidelity `PKDrawing` for capable clients and provide a read-only preview or
separate fallback instead of silently overwriting it. See
[references/pencilkit-patterns.md](references/pencilkit-patterns.md) for the
deeper compatibility table.

## Exporting to Image

Generate a `UIImage` from a drawing.

```swift
func exportImage(from drawing: PKDrawing, scale: CGFloat = 2.0) -> UIImage {
    drawing.image(from: drawing.bounds, scale: scale)
}

// Export a specific region
let region = CGRect(x: 0, y: 0, width: 500, height: 500)
let scale = UITraitCollection.current.displayScale
let croppedImage = drawing.image(from: region, scale: scale)
```

## Stroke Inspection

Access individual strokes, their ink, and control points.

```swift
for stroke in drawing.strokes {
    let ink = stroke.ink
    print("Ink type: \(ink.inkType), color: \(ink.color)")
    print("Bounds: \(stroke.renderBounds)")

    // Access path points
    let path = stroke.path
    print("Points: \(path.count), created: \(path.creationDate)")

    // Interpolate along the path
    for point in path.interpolatedPoints(by: .distance(10)) {
        print("Location: \(point.location), force: \(point.force)")
    }
}
```

### Constructing Strokes Programmatically

Load [Constructing Strokes Programmatically](references/pencilkit-patterns.md#constructing-strokes-programmatically)
only for generated ink paths; ordinary drawing and inspection do not need the
advanced constructors.

## SwiftUI Integration

Wrap `PKCanvasView` in a `UIViewRepresentable` for SwiftUI.

```swift
import SwiftUI
import PencilKit

struct CanvasView: UIViewRepresentable {
    @Binding var drawing: PKDrawing
    @Binding var toolPickerVisible: Bool

    func makeUIView(context: Context) -> PKCanvasView {
        let canvas = PKCanvasView()
        canvas.delegate = context.coordinator
        canvas.drawingPolicy = .anyInput
        canvas.drawing = drawing
        context.coordinator.toolPicker.addObserver(canvas)
        return canvas
    }

    func updateUIView(_ canvas: PKCanvasView, context: Context) {
        if canvas.drawing != drawing {
            canvas.drawing = drawing
        }
        let toolPicker = context.coordinator.toolPicker
        toolPicker.setVisible(toolPickerVisible, forFirstResponder: canvas)
        if toolPickerVisible { canvas.becomeFirstResponder() }
    }

    func makeCoordinator() -> Coordinator { Coordinator(self) }

    class Coordinator: NSObject, PKCanvasViewDelegate {
        let parent: CanvasView
        let toolPicker = PKToolPicker()

        init(_ parent: CanvasView) {
            self.parent = parent
            super.init()
        }

        func canvasViewDrawingDidChange(_ canvasView: PKCanvasView) {
            parent.drawing = canvasView.drawing
        }
    }
}
```

For SwiftUI wrappers, set the input policy using the canonical
[Drawing Policies](#drawing-policies) table.

### Usage in SwiftUI

```swift
struct DrawingScreen: View {
    @State private var drawing = PKDrawing()
    @State private var showToolPicker = true

    var body: some View {
        CanvasView(drawing: $drawing, toolPickerVisible: $showToolPicker)
            .ignoresSafeArea()
    }
}
```

## PaperKit Relationship

PaperKit (iOS 26+) extends PencilKit with a complete markup experience
including shapes, text boxes, images, stickers, and loupes. Use the sibling
`paperkit` skill when you need structured markup rather than only freeform
drawing.

| Capability | PencilKit | PaperKit |
|---|---|---|
| Freeform drawing | Yes | Yes |
| Shapes & lines | No | Yes |
| Text boxes | No | Yes |
| Images & stickers | No | Yes |
| Loupes | No | Yes |
| Markup toolbar | No | Yes |
| Markup insertion UI | No | `MarkupEditViewController`, `MarkupToolbarViewController` |
| Data model | `PKDrawing` | `PaperMarkup` |

PaperKit uses PencilKit under the hood: `PaperMarkupViewController` accepts
`PKTool` for its `drawingTool` property, and `PaperMarkup` can append a
`PKDrawing`.

## Common Mistakes

### DON'T: Forget to call becomeFirstResponder for the tool picker

The tool picker only appears when its associated responder is first responder.

```swift
// WRONG: Tool picker never shows
toolPicker.setVisible(true, forFirstResponder: canvasView)

// CORRECT: Also become first responder
toolPicker.setVisible(true, forFirstResponder: canvasView)
canvasView.becomeFirstResponder()
```

### DON'T: Create multiple tool pickers for the same canvas

One `PKToolPicker` per canvas. Creating extras causes visual conflicts.

```swift
// WRONG
func viewDidAppear(_ animated: Bool) {
    let picker = PKToolPicker()  // New picker every appearance
    picker.setVisible(true, forFirstResponder: canvasView)
}

// CORRECT: Store picker as a property
let toolPicker = PKToolPicker()
```

### DON'T: Ignore content versions for backward compatibility

Apply the [Content Version Compatibility](#content-version-compatibility) gate
to both the canvas and tool picker before syncing editable drawings.

### DON'T: Compare drawings by data representation

`dataRepresentation()` is for persistence and interchange, not comparison.
Use `PKDrawing` equality for exact value checks, and inspect strokes or rendered
images for visual/approximate comparisons.

```swift
// WRONG
if drawing1.dataRepresentation() == drawing2.dataRepresentation() { }

// CORRECT
if drawing1 == drawing2 { }
```

## Review Checklist

- [ ] `PKCanvasView.drawingPolicy` follows the canonical policy table
- [ ] `PKToolPicker` stored as a property, not recreated each appearance
- [ ] `canvasView.becomeFirstResponder()` called to show the tool picker
- [ ] Canvas added as a `PKToolPicker` observer before showing the picker
- [ ] Drawing serialized via `dataRepresentation()` and loaded via `PKDrawing(data:)`
- [ ] `canvasViewDrawingDidChange` delegate method used to track changes
- [ ] `maximumSupportedContentVersion` set on both canvas and tool picker if backward compatibility is needed
- [ ] Custom tool picker item code guarded for iOS/iPadOS 18+ and visionOS 2+
- [ ] Exported images use appropriate scale factor for the device
- [ ] SwiftUI wrapper avoids infinite update loops by checking `drawing != binding`
- [ ] Drawing bounds checked before image export (empty drawings have `.zero` bounds)

## References

- Extended PencilKit patterns (advanced strokes, content versions, delegates): [references/pencilkit-patterns.md](references/pencilkit-patterns.md)
- [PencilKit framework](https://sosumi.ai/documentation/pencilkit)
- [PKCanvasView](https://sosumi.ai/documentation/pencilkit/pkcanvasview)
- [PKDrawing](https://sosumi.ai/documentation/pencilkit/pkdrawing-swift.struct)
- [PKToolPicker](https://sosumi.ai/documentation/pencilkit/pktoolpicker)
- [PKInkingTool](https://sosumi.ai/documentation/pencilkit/pkinkingtool-swift.struct)
- [PKStroke](https://sosumi.ai/documentation/pencilkit/pkstroke-swift.struct)
- [Drawing with PencilKit](https://sosumi.ai/documentation/pencilkit/drawing-with-pencilkit)
- [Configuring the PencilKit tool picker](https://sosumi.ai/documentation/pencilkit/configuring-the-pencilkit-tool-picker)
