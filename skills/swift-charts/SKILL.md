---
name: swift-charts
description: "Implement, review, or improve data visualizations using Swift Charts. Use when building bar, line, area, point, pie, donut, or iOS 26 3D charts; when adding chart selection, scrolling, annotations, axes, scales, legends, or foregroundStyle grouping; when plotting functions with BarPlot, LinePlot, AreaPlot, PointPlot, Chart3D, or SurfacePlot; or when creating heat maps, Gantt charts, grouped bars, sparklines, threshold lines, or spatial visualizations."
---

# Swift Charts

Build data visualizations with Swift Charts targeting iOS 26+. Compose marks
inside `Chart` or `Chart3D`, configure axes and scales with view modifiers, and
use vectorized plots or 3D plots when the data calls for them.

See [references/charts-patterns.md](references/charts-patterns.md) for extended patterns, 3D charts, accessibility, and theming guidance.

## Contents

- [Workflow](#workflow)
- [Chart Container](#chart-container)
- [Mark Types](#mark-types)
- [Axis Customization](#axis-customization)
- [Scale Configuration](#scale-configuration)
- [Foreground Style and Encoding](#foreground-style-and-encoding)
- [Selection (iOS 17+)](#selection-ios-17)
- [Scrollable Charts (iOS 17+)](#scrollable-charts-ios-17)
- [Annotations](#annotations)
- [Legend](#legend)
- [Vectorized Plots (iOS 18+)](#vectorized-plots-ios-18)
- [3D Charts (iOS 26+)](#3d-charts-ios-26)
- [Common Mistakes](#common-mistakes)
- [Review Checklist](#review-checklist)
- [References](#references)

## Workflow

### 1. Build a new chart

1. Define data as an `Identifiable` struct or use `id:` key path.
2. Choose mark type(s): `BarMark`, `LineMark`, `PointMark`, `AreaMark`,
   `RuleMark`, `RectangleMark`, `SectorMark`, or `SurfacePlot`.
3. Wrap 2D marks in `Chart`; use `Chart3D` only for real spatial or surface data.
4. Encode visual channels: `.foregroundStyle(by:)`, `.symbol(by:)`, `.lineStyle(by:)`.
5. Configure axes with `.chartXAxis` / `.chartYAxis`.
6. Set scale domains with `.chartXScale(domain:)` / `.chartYScale(domain:)`.
7. Add selection, scrolling, or annotations as needed.
8. For 1000+ 2D data points, use vectorized plots (`BarPlot`, `LinePlot`, etc.).
9. Render representative empty, typical, dense, large-text, high-contrast, and VoiceOver states; exercise selection and scrolling when present.
10. If an encoding, axis, selection, or accessibility check fails, restore the data fixture, fix one layer, and rerun the same matrix before adding decoration.

### 2. Review existing chart code

Identify the data semantics before judging mark choice. Then trace every value through mark, scale, axis, style, selection, and accessibility output; run the same validation matrix used for new charts.

## Chart Container

```swift
Chart(sales) { item in
    BarMark(x: .value("Month", item.month), y: .value("Revenue", item.revenue))
}
```

Use the data-driven initializer for a single collection. Use the content closure for mixed marks or multiple series, and pass `id:` when elements are not `Identifiable`. Load [references/charts-patterns.md](references/charts-patterns.md) for complete mixed-series, theming, accessibility, and 3D recipes.

## Mark Types

### BarMark (iOS 16+)

```swift
// Vertical bar
BarMark(x: .value("Month", item.month), y: .value("Sales", item.sales))

// Stacked by category (automatic when same x maps to multiple bars)
BarMark(x: .value("Month", item.month), y: .value("Sales", item.sales))
    .foregroundStyle(by: .value("Product", item.product))

// Horizontal bar
BarMark(x: .value("Sales", item.sales), y: .value("Month", item.month))

// Interval bar (Gantt chart)
BarMark(
    xStart: .value("Start", item.start),
    xEnd: .value("End", item.end),
    y: .value("Task", item.task)
)
```

### LineMark (iOS 16+)

```swift
// Single line
LineMark(x: .value("Date", item.date), y: .value("Price", item.price))

// Multi-series via foregroundStyle encoding
LineMark(x: .value("Date", item.date), y: .value("Temp", item.temp))
    .foregroundStyle(by: .value("City", item.city))
    .interpolationMethod(.catmullRom)

// Multi-series with explicit series parameter
LineMark(
    x: .value("Date", item.date),
    y: .value("Price", item.price),
    series: .value("Ticker", item.ticker)
)
```

### PointMark (iOS 16+)

```swift
PointMark(x: .value("Height", item.height), y: .value("Weight", item.weight))
    .foregroundStyle(by: .value("Species", item.species))
    .symbol(by: .value("Species", item.species))
    .symbolSize(100)
```

### AreaMark (iOS 16+)

```swift
// Stacked area
AreaMark(x: .value("Date", item.date), y: .value("Sales", item.sales))
    .foregroundStyle(by: .value("Category", item.category))

// Range band
AreaMark(
    x: .value("Date", item.date),
    yStart: .value("Min", item.min),
    yEnd: .value("Max", item.max)
)
.opacity(0.3)
```

### RuleMark (iOS 16+)

```swift
RuleMark(y: .value("Target", 9000))
    .foregroundStyle(.red)
    .lineStyle(StrokeStyle(dash: [5, 3]))
    .annotation(position: .top, alignment: .leading) {
        Text("Target").font(.caption).foregroundStyle(.red)
    }
```

### RectangleMark (iOS 16+)

```swift
RectangleMark(x: .value("Hour", item.hour), y: .value("Day", item.day))
    .foregroundStyle(by: .value("Intensity", item.intensity))
```

### SectorMark (iOS 17+)
Use `SectorMark` for strictly positive values; filter, aggregate, or explain zero/negative values outside the pie or donut.
```swift
// Pie chart
Chart(data, id: \.name) { item in
    SectorMark(angle: .value("Sales", item.sales))
        .foregroundStyle(by: .value("Category", item.name))
}

// Donut chart
Chart(data, id: \.name) { item in
    SectorMark(
        angle: .value("Sales", item.sales),
        innerRadius: .ratio(0.618),
        outerRadius: .inset(10),
        angularInset: 1
    )
    .cornerRadius(4)
    .foregroundStyle(by: .value("Category", item.name))
}
```

## Axis Customization

```swift
// Hide axes
.chartXAxis(.hidden)
.chartYAxis(.hidden)

// Custom axis content
.chartXAxis {
    AxisMarks(values: .stride(by: .month)) { value in
        AxisGridLine()
        AxisTick()
        AxisValueLabel(format: .dateTime.month(.abbreviated))
    }
}

// Multiple AxisMarks compositions (different intervals for grid vs. labels)
.chartXAxis {
    AxisMarks(values: .stride(by: .day)) { _ in AxisGridLine() }
    AxisMarks(values: .stride(by: .week)) { _ in
        AxisTick()
        AxisValueLabel(format: .dateTime.week())
    }
}

// Axis labels (titles)
.chartXAxisLabel("Time", position: .bottom, alignment: .center)
.chartYAxisLabel("Revenue ($)", position: .leading, alignment: .center)
```

## Scale Configuration

```swift
.chartYScale(domain: 0...100)                          // Explicit numeric domain
.chartYScale(domain: .automatic(includesZero: true))   // Include zero
.chartYScale(domain: 1...10000, type: .log)            // Logarithmic scale
.chartXScale(domain: ["Mon", "Tue", "Wed", "Thu"])     // Categorical ordering
```

## Foreground Style and Encoding

```swift
BarMark(...).foregroundStyle(.blue)                                    // Static color
BarMark(...).foregroundStyle(by: .value("Category", item.category))   // Data encoding
AreaMark(...).foregroundStyle(                                         // Gradient
    .linearGradient(colors: [.blue, .cyan], startPoint: .bottom, endPoint: .top)
)
```

## Selection (iOS 17+)

```swift
@State private var selectedDate: Date?
@State private var selectedRange: ClosedRange<Date>?
@State private var selectedAngle: Double?

// Point selection
Chart(data) { item in
    LineMark(x: .value("Date", item.date), y: .value("Value", item.value))
}
.chartXSelection(value: $selectedDate)

// Range selection
.chartXSelection(range: $selectedRange)

// Angular selection binds the plottable angle value; derive the category from ranges.
.chartAngleSelection(value: $selectedAngle)
```

## Scrollable Charts (iOS 17+)

```swift
Chart(dailyData) { item in
    BarMark(x: .value("Date", item.date, unit: .day), y: .value("Steps", item.steps))
}
.chartScrollableAxes(.horizontal)
.chartXVisibleDomain(length: 3600 * 24 * 7) // 7 days visible
.chartScrollPosition(initialX: latestDate)
.chartScrollTargetBehavior(
    .valueAligned(matching: DateComponents(hour: 0), majorAlignment: .page)
)
```

## Annotations

```swift
BarMark(x: .value("Month", item.month), y: .value("Sales", item.sales))
    .annotation(position: .top, alignment: .center, spacing: 4) {
        Text("\(item.sales, format: .number)").font(.caption2)
    }

// Overflow resolution
.annotation(
    position: .top,
    overflowResolution: .init(x: .fit(to: .chart), y: .padScale)
) { Text("Label") }
```

## Legend

```swift
.chartLegend(.hidden)                                           // Hide
.chartLegend(position: .bottom, alignment: .center, spacing: 10) // Position
.chartLegend(position: .bottom) {                                // Custom
    HStack {
        ForEach(categories, id: \.self) { cat in
            Label(cat, systemImage: "circle.fill").font(.caption)
        }
    }
}
```

## Vectorized Plots (iOS 18+)

Use for large datasets (1000+ points). Accept entire collections or functions.

```swift
// Data-driven
Chart {
    BarPlot(sales, x: .value("Month", \.month), y: .value("Revenue", \.revenue))
        .foregroundStyle(\.barColor)
}

// Function plotting: y = f(x)
Chart {
    LinePlot(x: "x", y: "y", domain: -5...5) { x in sin(x) }
}

// Parametric: (x, y) = f(t)
Chart {
    LinePlot(x: "x", y: "y", t: "t", domain: 0...(2 * .pi)) { t in
        (x: cos(t), y: sin(t))
    }
}
```

Apply KeyPath-based modifiers before simple-value modifiers:

```swift
BarPlot(data, x: .value("X", \.x), y: .value("Y", \.y))
    .foregroundStyle(\.color)    // KeyPath first
    .opacity(0.8)                // Value modifier second
```

## 3D Charts (iOS 26+)

Use `Chart3D` for spatial data or bivariate surfaces, not as a decorative
replacement for ordinary 2D categorical or time-series charts. `Chart3D`
accepts `SurfacePlot` plus 3D initializers of `PointMark`, `RuleMark`, and
`RectangleMark`.

```swift
@State private var pose: Chart3DPose = .default

Chart3D {
    SurfacePlot(x: "x", y: "y", z: "z") { x, z in
        sin(2 * x) * cos(2 * z)
    }
    .foregroundStyle(.heightBased)
}
.chartXScale(domain: -2...2)
.chartYScale(domain: -1...1)
.chartZScale(domain: -2...2)
.chart3DPose($pose)
```

## Common Mistakes

### 1. Missing series parameter for multi-line charts

```swift
// WRONG -- all points connect into one line
Chart {
    ForEach(allCities) { item in
        LineMark(x: .value("Date", item.date), y: .value("Temp", item.temp))
    }
}

// CORRECT -- separate lines per city
Chart {
    ForEach(allCities) { item in
        LineMark(x: .value("Date", item.date), y: .value("Temp", item.temp))
            .foregroundStyle(by: .value("City", item.city))
    }
}
```

### 2. Too many SectorMark slices

```swift
// WRONG -- 20 tiny sectors are unreadable
Chart(twentyCategories, id: \.name) { item in
    SectorMark(angle: .value("Value", item.value))
}

// CORRECT -- group into top 5 + "Other"
Chart(groupedData, id: \.name) { item in
    SectorMark(angle: .value("Value", item.value))
        .foregroundStyle(by: .value("Category", item.name))
}
```

### 3. Missing scale domain when zero-baseline matters

```swift
// WRONG -- axis starts at ~95; small changes look dramatic
Chart(data) {
    LineMark(x: .value("Day", $0.day), y: .value("Score", $0.score))
}

// CORRECT -- explicit domain for honest representation
Chart(data) {
    LineMark(x: .value("Day", $0.day), y: .value("Score", $0.score))
}
.chartYScale(domain: 0...100)
```

### 4. Static foregroundStyle overriding data encoding

```swift
// WRONG -- static color overrides by-value encoding
BarMark(x: .value("X", item.x), y: .value("Y", item.y))
    .foregroundStyle(by: .value("Category", item.category))
    .foregroundStyle(.blue)

// CORRECT -- use only the data encoding
BarMark(x: .value("X", item.x), y: .value("Y", item.y))
    .foregroundStyle(by: .value("Category", item.category))
```

### 5. Individual marks for 10,000+ data points

```swift
// WRONG -- creates 10,000 mark views; slow
Chart(largeDataset) { item in
    PointMark(x: .value("X", item.x), y: .value("Y", item.y))
}

// CORRECT -- vectorized plot (iOS 18+)
Chart {
    PointPlot(largeDataset, x: .value("X", \.x), y: .value("Y", \.y))
}
```

### 6. Fixed chart height breaking Dynamic Type

```swift
// WRONG -- clips axis labels at large text sizes
Chart(data) { ... }
    .frame(height: 200)

// CORRECT -- adaptive sizing
Chart(data) { ... }
    .frame(minHeight: 200, maxHeight: 400)
```

### 7. KeyPath modifier after value modifier on vectorized plots

```swift
// WRONG -- compiler error
BarPlot(data, x: .value("X", \.x), y: .value("Y", \.y))
    .opacity(0.8)
    .foregroundStyle(\.color)

// CORRECT -- KeyPath modifiers first
BarPlot(data, x: .value("X", \.x), y: .value("Y", \.y))
    .foregroundStyle(\.color)
    .opacity(0.8)
```

### 8. Missing accessibility labels

```swift
// WRONG -- VoiceOver users get no context
Chart(data) {
    BarMark(x: .value("Month", $0.month), y: .value("Sales", $0.sales))
}

// CORRECT -- add per-mark accessibility
Chart(data) { item in
    BarMark(x: .value("Month", item.month), y: .value("Sales", item.sales))
        .accessibilityLabel("\(item.month)")
        .accessibilityValue("\(item.sales) units sold")
}
```

### 9. Treating angle selection as category selection

`chartAngleSelection(value:)` binds the selected plottable angle value. For
pie and donut charts, map that numeric value through cumulative sector ranges
before comparing it to a category label.

## Review Checklist

- [ ] Data model uses `Identifiable` or chart uses `id:` key path
- [ ] Mark type matches goal (bar=comparison, line=trend, sector=proportion)
- [ ] Multi-series lines use `series:` parameter or `.foregroundStyle(by:)`
- [ ] Axes configured with appropriate labels, ticks, and grid lines
- [ ] Scale domain set explicitly when zero-baseline matters
- [ ] Pie/donut uses positive values, 5-7 sectors, and "Other" grouping
- [ ] Selection binding type matches axis data type (`Date?` for date axis)
- [ ] Pie/donut angle selection maps numeric angle values back to categories
- [ ] Scrollable charts set `.chartXVisibleDomain(length:)` for viewport
- [ ] Vectorized plots used for datasets exceeding 1000 points
- [ ] KeyPath modifiers applied before value modifiers on vectorized plots
- [ ] `Chart3D` used only for real 3D data or surfaces, with z scale and pose reviewed
- [ ] Accessibility labels added to marks for VoiceOver
- [ ] Chart tested with Dynamic Type and Dark Mode
- [ ] Legend visible and positioned, or intentionally hidden
- [ ] Ensure chart data model types are Sendable; update chart data on @MainActor

## References

- Extended patterns: [references/charts-patterns.md](references/charts-patterns.md)
- Apple docs: [Swift Charts](https://sosumi.ai/documentation/charts)
- Apple docs: [Creating a chart using Swift Charts](https://sosumi.ai/documentation/charts/Creating-a-chart-using-Swift-Charts)
- Apple docs: [Swift Charts updates](https://sosumi.ai/documentation/updates/swiftcharts)
- Apple docs: [Chart3D](https://sosumi.ai/documentation/charts/Chart3D)
- Apple docs: [SurfacePlot](https://sosumi.ai/documentation/charts/SurfacePlot)
