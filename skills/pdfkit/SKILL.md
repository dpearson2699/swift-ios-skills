---
name: pdfkit
description: "Display and manipulate PDF documents using PDFKit. Use when embedding PDFView to show PDF files, creating or modifying PDFDocument instances, adding annotations (highlights, notes, signature widgets), extracting text with PDFSelection, navigating pages, generating thumbnails, filling PDF forms, or wrapping PDFView in SwiftUI."
---

# PDFKit

Display, navigate, search, annotate, and manipulate PDF documents with `PDFView`, `PDFDocument`, `PDFPage`, `PDFAnnotation`, and `PDFSelection`.

## Contents

- [Setup](#setup)
- [Displaying PDFs](#displaying-pdfs)
- [Loading Documents](#loading-documents)
- [Page Navigation](#page-navigation)
- [Text Search and Selection](#text-search-and-selection)
- [Annotations](#annotations)
- [Thumbnails](#thumbnails)
- [SwiftUI Integration](#swiftui-integration)
- [Common Mistakes](#common-mistakes)
- [Review Checklist](#review-checklist)
- [References](#references)

## Setup

PDFKit requires no entitlements or Info.plist entries.

```swift
import PDFKit
```

| API | Availability |
|---|---|
| PDFKit framework | iOS/iPadOS/tvOS 11+, Mac Catalyst 13.1+, macOS 10.4+, visionOS 1.0+ |
| Find interaction and page overlays | iOS/iPadOS 16+ |

## Displaying PDFs

`PDFView` renders PDF content and handles zoom, scrolling, text selection, and page navigation.

```swift
import PDFKit
import UIKit

class PDFViewController: UIViewController {
    let pdfView = PDFView()

    override func viewDidLoad() {
        super.viewDidLoad()
        pdfView.frame = view.bounds
        pdfView.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        view.addSubview(pdfView)

        pdfView.autoScales = true
        pdfView.displayMode = .singlePageContinuous
        pdfView.displayDirection = .vertical

        if let url = Bundle.main.url(forResource: "sample", withExtension: "pdf") {
            pdfView.document = PDFDocument(url: url)
        }
    }
}
```

### Display Modes

| Mode | Behavior |
|---|---|
| `.singlePage` | One page at a time |
| `.singlePageContinuous` | Pages stacked vertically, scrollable |
| `.twoUp` | Two pages side by side |
| `.twoUpContinuous` | Two-up with continuous scrolling |

### Scaling and Appearance

```swift
pdfView.autoScales = true
pdfView.minScaleFactor = pdfView.scaleFactorForSizeToFit
pdfView.maxScaleFactor = 4.0

pdfView.displaysPageBreaks = true
pdfView.pageShadowsEnabled = true
pdfView.interpolationQuality = .high
```

## Loading Documents

`PDFDocument` loads from a URL, `Data`, or can be created empty.

```swift
let fileDoc = PDFDocument(url: fileURL)
let dataDoc = PDFDocument(data: pdfData)
let emptyDoc = PDFDocument()
```

### Password-Protected PDFs

```swift
guard let document = PDFDocument(url: url) else { return }
if document.isLocked {
    if !document.unlock(withPassword: userPassword) {
        // Show password prompt
    }
}
```

### Saving and Page Manipulation

```swift
document.write(to: outputURL)
document.write(to: outputURL, withOptions: [
    .ownerPasswordOption: "ownerPass", .userPasswordOption: "userPass"
])
let data = document.dataRepresentation()

// Pages are zero-based. Validate indices; out-of-range calls raise exceptions.
let count = document.pageCount
document.insert(PDFPage(), at: count)
if document.pageCount > 2 {
    document.removePage(at: 2)
}
if document.pageCount > 3 {
    document.exchangePage(at: 0, withPageAt: 3)
}
```

## Page Navigation

`PDFView` provides built-in navigation with history tracking.

```swift
// Go to a specific page
let pageIndex = 5
if let document = pdfView.document,
   pageIndex >= 0,
   pageIndex < document.pageCount,
   let page = document.page(at: pageIndex) {
    pdfView.go(to: page)
}

// Sequential navigation
pdfView.goToNextPage(nil)
pdfView.goToPreviousPage(nil)
pdfView.goToFirstPage(nil)
pdfView.goToLastPage(nil)

// Check navigation state
if pdfView.canGoToNextPage { /* ... */ }

// History navigation
if pdfView.canGoBack { pdfView.goBack(nil) }

// Go to a specific point on the current page
if let page = pdfView.currentPage {
    let destination = PDFDestination(page: page, at: CGPoint(x: 0, y: 500))
    pdfView.go(to: destination)
}
```

### Observing Page Changes

```swift
NotificationCenter.default.addObserver(
    self, selector: #selector(pageChanged),
    name: .PDFViewPageChanged, object: pdfView
)

@objc func pageChanged(_ notification: Notification) {
    guard let page = pdfView.currentPage,
          let doc = pdfView.document else { return }
    let index = doc.index(for: page)
    pageLabel.text = "Page \(index + 1) of \(doc.pageCount)"
}
```

## Text Search and Selection

### Synchronous Search

```swift
let results: [PDFSelection] = document.findString(
    "search term", withOptions: [.caseInsensitive]
)
```

### Asynchronous Search

Use `PDFDocumentDelegate` for background searches on large documents.
Implement `didMatchString(_:)` to receive each match and
`documentDidEndDocumentFind(_:)` for completion.

### Incremental Search and Find Interaction

```swift
// Find next match from current selection
let next = document.findString("term", fromSelection: current, withOptions: [.caseInsensitive])

// System find bar; apply the Setup availability gate
pdfView.isFindInteractionEnabled = true
```

### Text Extraction

```swift
let fullText = document.string                          // Entire document
let firstPage = document.pageCount > 0 ? document.page(at: 0) : nil
let pageText = firstPage?.string                        // Single page
let attributed = firstPage?.attributedString            // With formatting

// Region-based extraction
if let page = firstPage {
    let selection = page.selection(for: CGRect(x: 50, y: 50, width: 400, height: 200))
    let text = selection?.string
}
```

### Highlighting Search Results

```swift
let results = document.findString("important", withOptions: [.caseInsensitive])
for selection in results { selection.color = .yellow }
pdfView.highlightedSelections = results

if let first = results.first {
    pdfView.setCurrentSelection(first, animate: true)
    pdfView.go(to: first)
}
```

## Annotations

Annotations are created with `PDFAnnotation(bounds:forType:withProperties:)`
and added to a `PDFPage`.

### Highlight Annotation

```swift
func addHighlight(to page: PDFPage, selection: PDFSelection) {
    let highlight = PDFAnnotation(
        bounds: selection.bounds(for: page),
        forType: .highlight, withProperties: nil
    )
    highlight.color = UIColor.yellow.withAlphaComponent(0.5)
    page.addAnnotation(highlight)
}
```

### Text Note Annotation

```swift
let note = PDFAnnotation(
    bounds: CGRect(x: 100, y: 700, width: 30, height: 30),
    forType: .text, withProperties: nil
)
note.contents = "This is a sticky note."
note.color = .systemYellow
note.iconType = .comment
page.addAnnotation(note)
```

### Free Text Annotation

```swift
let freeText = PDFAnnotation(
    bounds: CGRect(x: 50, y: 600, width: 300, height: 40),
    forType: .freeText, withProperties: nil
)
freeText.contents = "Added commentary"
freeText.font = UIFont.systemFont(ofSize: 14)
freeText.fontColor = .darkGray
page.addAnnotation(freeText)
```

### Link Annotation

```swift
let link = PDFAnnotation(
    bounds: CGRect(x: 50, y: 500, width: 200, height: 20),
    forType: .link, withProperties: nil
)
link.url = URL(string: "https://example.com")
page.addAnnotation(link)

// Internal page link
link.destination = PDFDestination(page: targetPage, at: .zero)
```

### Removing Annotations

```swift
for annotation in page.annotations {
    page.removeAnnotation(annotation)
}
```

Common subtypes include `.highlight`, `.underline`, `.strikeOut`, `.text`,
`.freeText`, `.ink`, `.link`, `.line`, `.square`, `.circle`, `.stamp`, and
`.widget`.

## Thumbnails

### PDFThumbnailView

`PDFThumbnailView` shows a strip of page thumbnails linked to a `PDFView`.

```swift
let thumbnailView = PDFThumbnailView()
thumbnailView.pdfView = pdfView
thumbnailView.thumbnailSize = CGSize(width: 60, height: 80)
thumbnailView.layoutMode = .vertical
thumbnailView.translatesAutoresizingMaskIntoConstraints = false
view.addSubview(thumbnailView)
```

### Generating Thumbnails Programmatically

```swift
let thumbnail = page.thumbnail(of: CGSize(width: 120, height: 160), for: .mediaBox)

// All pages
let thumbnails = (0..<document.pageCount).compactMap {
    document.page(at: $0)?.thumbnail(of: CGSize(width: 120, height: 160), for: .mediaBox)
}
```

## SwiftUI Integration

Wrap `PDFView` in a `UIViewRepresentable` for SwiftUI. PDF-specific wrappers
that configure `PDFView`, pages, annotations, search, thumbnails, or overlays
belong in this skill; route only generic representable lifecycle, layout, or SwiftUI state architecture questions to SwiftUI/UIKit interop guidance.

```swift
import SwiftUI
import PDFKit

struct PDFKitView: UIViewRepresentable {
    let document: PDFDocument

    func makeUIView(context: Context) -> PDFView {
        let pdfView = PDFView()
        pdfView.autoScales = true
        pdfView.displayMode = .singlePageContinuous
        pdfView.document = document
        return pdfView
    }

    func updateUIView(_ pdfView: PDFView, context: Context) {
        if pdfView.document !== document {
            pdfView.document = document
        }
    }
}
```

### Usage

```swift
struct DocumentScreen: View {
    let url: URL

    var body: some View {
        if let document = PDFDocument(url: url) {
            PDFKitView(document: document)
                .ignoresSafeArea()
        } else {
            ContentUnavailableView("Unable to load PDF", systemImage: "doc.questionmark")
        }
    }
}
```

For interactive wrappers with page tracking, annotation hit detection, and
coordinator patterns, see [references/pdfkit-patterns.md](references/pdfkit-patterns.md).

### Page Overlays

`PDFPageOverlayViewProvider` places UIKit views on top of individual pages
for interactive controls or custom rendering beyond standard annotations.

```swift
class OverlayProvider: NSObject, PDFPageOverlayViewProvider {
    func pdfView(_ view: PDFView, overlayViewFor page: PDFPage) -> UIView? {
        let overlay = UIView()
        // Add custom subviews
        return overlay
    }
}

class PDFOverlayController: UIViewController {
    let pdfView = PDFView()
    private let overlayProvider = OverlayProvider()

    override func viewDidLoad() {
        super.viewDidLoad()
        pdfView.pageOverlayViewProvider = overlayProvider
    }
}
```

`pageOverlayViewProvider` is weak, so keep the provider strongly owned. For overlay lifecycle and save handling, read [references/pdfkit-patterns.md](references/pdfkit-patterns.md).

## Common Mistakes

### DON'T: Force-unwrap PDFDocument init

`PDFDocument(url:)` and `PDFDocument(data:)` are failable initializers.

```swift
// WRONG
let document = PDFDocument(url: url)!

// CORRECT
guard let document = PDFDocument(url: url) else { return }
```

### DON'T: Forget autoScales on PDFView

Without `autoScales`, the PDF renders at its native resolution.

```swift
// WRONG
pdfView.document = document

// CORRECT
pdfView.autoScales = true
pdfView.document = document
```

### DON'T: Ignore PDF coordinate system in annotations

PDF page coordinates have origin at the bottom-left with Y increasing
upward -- opposite of UIKit.

```swift
// WRONG: UIKit coordinates
let bounds = CGRect(x: 50, y: 50, width: 200, height: 30)

// CORRECT: PDF coordinates (origin bottom-left)
let pageBounds = page.bounds(for: .mediaBox)
let pdfY = pageBounds.height - 50 - 30
let bounds = CGRect(x: 50, y: pdfY, width: 200, height: 30)
```

### DON'T: Modify annotations on a background thread

PDFKit classes are not thread-safe.

```swift
// WRONG
DispatchQueue.global().async { page.addAnnotation(annotation) }

// CORRECT
DispatchQueue.main.async { page.addAnnotation(annotation) }
```

### DON'T: Compare PDFDocument with == in UIViewRepresentable

`PDFDocument` is a reference type. Use identity (`!==`).

```swift
// WRONG: Always replaces document
func updateUIView(_ pdfView: PDFView, context: Context) {
    pdfView.document = document
}

// CORRECT
func updateUIView(_ pdfView: PDFView, context: Context) {
    if pdfView.document !== document {
        pdfView.document = document
    }
}
```

## Review Checklist

- [ ] `PDFDocument` init uses optional binding, not force-unwrap
- [ ] `pdfView.autoScales = true` set for proper initial display
- [ ] Page indices checked against `pageCount` before access
- [ ] `displayMode` and `displayDirection` configured to match design
- [ ] Annotations use PDF coordinate space (origin bottom-left, Y up)
- [ ] All PDFKit mutations happen on the main thread
- [ ] Password-protected PDFs handled with `isLocked` / `unlock(withPassword:)`
- [ ] SwiftUI wrapper uses `!==` identity check in `updateUIView`
- [ ] `PDFViewPageChanged` notification observed for page tracking
- [ ] `PDFThumbnailView.pdfView` linked to the main `PDFView`
- [ ] Large-document search uses async `beginFindString` with delegate
- [ ] Saved documents use `write(to:withOptions:)` when encryption needed

## References

- Extended patterns (forms, watermarks, merging, printing, overlays, outlines, custom drawing): [references/pdfkit-patterns.md](references/pdfkit-patterns.md)
- [PDFKit framework](https://sosumi.ai/documentation/pdfkit)
- [PDFView](https://sosumi.ai/documentation/pdfkit/pdfview)
- [PDFDocument](https://sosumi.ai/documentation/pdfkit/pdfdocument)
- [PDFPage](https://sosumi.ai/documentation/pdfkit/pdfpage), [PDFAnnotation](https://sosumi.ai/documentation/pdfkit/pdfannotation), [PDFSelection](https://sosumi.ai/documentation/pdfkit/pdfselection), [PDFThumbnailView](https://sosumi.ai/documentation/pdfkit/pdfthumbnailview)
- [PDFPageOverlayViewProvider](https://sosumi.ai/documentation/pdfkit/pdfpageoverlayviewprovider)
- [Adding Widgets to a PDF Document](https://sosumi.ai/documentation/pdfkit/adding-widgets-to-a-pdf-document)
- [Adding Custom Graphics to a PDF](https://sosumi.ai/documentation/pdfkit/adding-custom-graphics-to-a-pdf)
