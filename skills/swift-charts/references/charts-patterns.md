# Swift Charts Patterns Reference

Extended patterns, accessibility guidance, and theming for Swift Charts on
iOS 26+. Import `Charts` in every file that uses these APIs.

```swift
import SwiftUI
import Charts
```

---

## Data Modeling

Use `@Observable` for chart data models. Pair with `@State` in views.

```swift
@Observable
class SalesModel {
    var monthlySales: [MonthlySale] = []

    func load() async {
        monthlySales = await SalesService.fetchMonthlySales()
    }
}

struct MonthlySale: Identifiable {
    let id = UUID()
    let month: Date
    let revenue: Double
    let category: String
}
```

```swift
struct SalesDashboard: View {
    @State private var model = SalesModel()

    var body: some View {
        Chart(model.monthlySales) { item in
            BarMark(
                x: .value("Month", item.month, unit: .month),
                y: .value("Revenue", item.revenue)
            )
            .foregroundStyle(by: .value("Category", item.category))
        }
        .task { await model.load() }
    }
}
```

---

## Bar Chart Patterns

### Simple vertical bars

```swift
Chart(data) { item in
    BarMark(
        x: .value("Department", item.department),
        y: .value("Revenue", item.revenue)
    )
}
```

### Stacked bars (automatic)

When multiple bars share the same x value, they stack automatically:

```swift
Chart(data) { item in
    BarMark(
        x: .value("Quarter", item.quarter),
        y: .value("Sales", item.sales)
    )
    .foregroundStyle(by: .value("Product", item.product))
}
```

### Grouped bars

Use `.position(by:)` to place bars side by side instead of stacking:

```swift
Chart(data) { item in
    BarMark(
        x: .value("Quarter", item.quarter),
        y: .value("Sales", item.sales)
    )
    .foregroundStyle(by: .value("Product", item.product))
    .position(by: .value("Product", item.product))
}
```

### Horizontal bars

Swap the x and y axes:

```swift
Chart(data) { item in
    BarMark(
        x: .value("Sales", item.sales),
        y: .value("Region", item.region)
    )
}
.chartYAxis {
    AxisMarks { _ in
        AxisValueLabel()
    }
}
```

### Normalized stacked bars (100%)

```swift
Chart(data) { item in
    BarMark(
        x: .value("Quarter", item.quarter),
        y: .value("Sales", item.sales),
        stacking: .normalized
    )
    .foregroundStyle(by: .value("Product", item.product))
}
```

### Bar with annotation

```swift
Chart(data) { item in
    BarMark(
        x: .value("Month", item.month),
        y: .value("Revenue", item.revenue)
    )
    .annotation(position: .top, alignment: .center, spacing: 4) {
        Text(item.revenue, format: .currency(code: "USD").precision(.fractionLength(0)))
            .font(.caption2)
    }
}
```

### Gantt chart (interval bars)

```swift
Chart(tasks) { task in
    BarMark(
        xStart: .value("Start", task.startDate),
        xEnd: .value("End", task.endDate),
        y: .value("Task", task.name)
    )
    .foregroundStyle(by: .value("Status", task.status))
}
```

---

## Line Chart Patterns

### Single line with points

```swift
Chart(data) { item in
    LineMark(
        x: .value("Date", item.date),
        y: .value("Price", item.price)
    )
    PointMark(
        x: .value("Date", item.date),
        y: .value("Price", item.price)
    )
    .symbolSize(30)
}
```

### Multi-series lines

```swift
Chart(temperatures) { item in
    LineMark(
        x: .value("Date", item.date),
        y: .value("Temp", item.temperature)
    )
    .foregroundStyle(by: .value("City", item.city))
    .symbol(by: .value("City", item.city))
}
```

### Line with area fill

```swift
Chart(data) { item in
    AreaMark(
        x: .value("Date", item.date),
        y: .value("Value", item.value)
    )
    .foregroundStyle(
        .linearGradient(
            colors: [.blue.opacity(0.3), .blue.opacity(0.05)],
            startPoint: .top,
            endPoint: .bottom
        )
    )
    LineMark(
        x: .value("Date", item.date),
        y: .value("Value", item.value)
    )
    .foregroundStyle(.blue)
}
```

### Interpolation methods

| Method | Use Case |
|---|---|
| `.linear` | Default; straight segments between points |
| `.monotone` | Smooth curve that preserves monotonicity |
| `.catmullRom` | Smooth general-purpose curve |
| `.cardinal` | Smooth with adjustable tension |
| `.stepStart` | Step function starting at data point |
| `.stepCenter` | Step function centered on data point |
| `.stepEnd` | Step function ending at data point |

```swift
LineMark(x: .value("X", item.x), y: .value("Y", item.y))
    .interpolationMethod(.monotone)
```

### Sparkline (minimal inline chart)

```swift
Chart(recentData) { item in
    LineMark(
        x: .value("Time", item.time),
        y: .value("Value", item.value)
    )
    .interpolationMethod(.catmullRom)
}
.chartXAxis(.hidden)
.chartYAxis(.hidden)
.chartLegend(.hidden)
.frame(width: 80, height: 30)
```

---

## Pie and Donut Chart Patterns (SectorMark, iOS 17+)

### Basic pie chart

```swift
Chart(products, id: \.name) { item in
    SectorMark(angle: .value("Sales", item.sales))
        .foregroundStyle(by: .value("Product", item.name))
}
```

### Donut chart with golden ratio inner radius

```swift
Chart(products, id: \.name) { item in
    SectorMark(
        angle: .value("Sales", item.sales),
        innerRadius: .ratio(0.618),
        outerRadius: .inset(10),
        angularInset: 1
    )
    .cornerRadius(4)
    .foregroundStyle(by: .value("Product", item.name))
}
```

### Donut chart with center label

```swift
Chart(products, id: \.name) { item in
    SectorMark(
        angle: .value("Sales", item.sales),
        innerRadius: .ratio(0.618),
        angularInset: 1
    )
    .cornerRadius(4)
    .foregroundStyle(by: .value("Product", item.name))
}
.chartBackground { _ in
    VStack {
        Text("Total")
            .font(.caption)
            .foregroundStyle(.secondary)
        Text("\(totalSales, format: .number)")
            .font(.title2.bold())
    }
}
```

### Angular selection on donut

```swift
@State private var selectedProduct: String?

Chart(products, id: \.name) { item in
    SectorMark(
        angle: .value("Sales", item.sales),
        innerRadius: .ratio(0.618),
        angularInset: 1
    )
    .cornerRadius(4)
    .foregroundStyle(by: .value("Product", item.name))
    .opacity(selectedProduct == nil || selectedProduct == item.name ? 1.0 : 0.4)
}
.chartAngleSelection(value: $selectedProduct)
```

### Grouping small slices

Limit pie/donut charts to 5-7 sectors. Group the rest into "Other":

```swift
func groupSmallSlices(_ data: [CategorySales], topN: Int = 5) -> [CategorySales] {
    let sorted = data.sorted { $0.sales > $1.sales }
    let top = Array(sorted.prefix(topN))
    let otherTotal = sorted.dropFirst(topN).reduce(0) { $0 + $1.sales }
    guard otherTotal > 0 else { return top }
    return top + [CategorySales(name: "Other", sales: otherTotal)]
}
```

---

## Combined Chart Patterns

### Line + area (trend with fill)

```swift
Chart(data) { item in
    AreaMark(
        x: .value("Date", item.date),
        yStart: .value("Min", item.low),
        yEnd: .value("Max", item.high)
    )
    .foregroundStyle(.blue.opacity(0.15))

    LineMark(
        x: .value("Date", item.date),
        y: .value("Average", item.average)
    )
    .foregroundStyle(.blue)
    .lineStyle(StrokeStyle(lineWidth: 2))
}
```

### Bar + threshold rule

```swift
Chart {
    ForEach(data) { item in
        BarMark(
            x: .value("Month", item.month),
            y: .value("Revenue", item.revenue)
        )
    }
    RuleMark(y: .value("Target", targetRevenue))
        .foregroundStyle(.red)
        .lineStyle(StrokeStyle(lineWidth: 1, dash: [5, 3]))
        .annotation(position: .top, alignment: .leading) {
            Text("Target: \(targetRevenue, format: .number)")
                .font(.caption)
                .foregroundStyle(.red)
        }
}
```

### Scatter + trend line

```swift
Chart {
    ForEach(data) { item in
        PointMark(
            x: .value("Experience", item.yearsExperience),
            y: .value("Salary", item.salary)
        )
        .opacity(0.6)
    }
    LinePlot(x: "Experience", y: "Salary", domain: 0...20) { x in
        baseSalary + x * salaryPerYear  // linear trend
    }
    .foregroundStyle(.red)
    .lineStyle(StrokeStyle(lineWidth: 1.5, dash: [4, 2]))
}
```

---

## Chart Selection with Overlay Annotation

Show a tooltip at the selected position using `chartOverlay`:

```swift
@State private var selectedDate: Date?

var body: some View {
    Chart(data) { item in
        LineMark(
            x: .value("Date", item.date),
            y: .value("Value", item.value)
        )
        if let selectedDate,
           let match = data.first(where: { Calendar.current.isDate($0.date, inSameDayAs: selectedDate) }) {
            RuleMark(x: .value("Selected", match.date))
                .foregroundStyle(.secondary)
            PointMark(
                x: .value("Date", match.date),
                y: .value("Value", match.value)
            )
            .symbolSize(60)
            .annotation(position: .top) {
                Text("\(match.value, format: .number)")
                    .font(.caption)
                    .padding(4)
                    .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 4))
            }
        }
    }
    .chartXSelection(value: $selectedDate)
}
```

---

## Scrollable Chart with Visible Domain

```swift
@State private var scrollPosition: Date?

var body: some View {
    Chart(dailySteps) { item in
        BarMark(
            x: .value("Date", item.date, unit: .day),
            y: .value("Steps", item.steps)
        )
    }
    .chartScrollableAxes(.horizontal)
    .chartXVisibleDomain(length: 3600 * 24 * 7) // 7 days
    .chartScrollPosition(x: $scrollPosition)
    .chartScrollTargetBehavior(
        .valueAligned(matching: DateComponents(hour: 0), majorAlignment: .page)
    )
    .chartXAxis {
        AxisMarks(values: .stride(by: .day)) { value in
            AxisGridLine()
            AxisValueLabel(format: .dateTime.weekday(.abbreviated))
        }
    }
}
```

---

## Function Plotting (LinePlot, iOS 18+)

### Standard function y = f(x)

```swift
Chart {
    LinePlot(x: "x", y: "y", domain: -2 * .pi ... 2 * .pi) { x in
        sin(x)
    }
    .foregroundStyle(.blue)
}
.chartYScale(domain: -1.5...1.5)
```

### Parametric function (x, y) = f(t)

```swift
Chart {
    LinePlot(x: "x", y: "y", t: "t", domain: 0 ... 2 * .pi) { t in
        (x: cos(t), y: sin(t))
    }
}
.chartXScale(domain: -1.5...1.5)
.chartYScale(domain: -1.5...1.5)
```

### Range area function

```swift
Chart {
    AreaPlot(x: "x", yStart: "min", yEnd: "max", domain: 0...10) { x in
        (yStart: sin(x) - 0.5, yEnd: sin(x) + 0.5)
    }
    .foregroundStyle(.blue.opacity(0.2))
}
```

---

## Accessibility

### Automatic VoiceOver support

Swift Charts provides automatic VoiceOver descriptions for chart elements. The
framework reads axis labels and values to visually impaired users without
additional code. Ensure `.value("Label", ...)` strings are descriptive.

### Custom accessibility labels

```swift
Chart(data) { item in
    BarMark(
        x: .value("Month", item.month),
        y: .value("Sales", item.sales)
    )
    .accessibilityLabel("Sales for \(item.month)")
    .accessibilityValue("\(item.sales) units sold")
}
```

### Accessibility on vectorized plots (KeyPath-based)

```swift
BarPlot(data, x: .value("Month", \.month), y: .value("Sales", \.sales))
    .accessibilityLabel(\.accessibilityDescription)
    .accessibilityValue(\.formattedSales)
```

### Audio graphs

The system automatically generates audio representations of chart data for
VoiceOver users. Use clear, consistent data labels to ensure audio graphs
convey meaningful patterns.

### Best practices

- Use descriptive strings in `.value("Label", ...)` -- these become VoiceOver labels.
- Add `.accessibilityLabel` and `.accessibilityValue` for context beyond raw numbers.
- Test with VoiceOver enabled: navigate the chart and verify each element is announced.
- Avoid `.accessibilityHidden(true)` on data-bearing marks.

---

## Dynamic Type and Color Considerations

### Dynamic Type

Charts automatically adjust axis label sizes with Dynamic Type. Avoid fixed
frame heights that clip labels at larger text sizes.

```swift
// WRONG -- clips at large text sizes
Chart(data) { ... }
    .frame(height: 200)

// CORRECT -- adaptive height
Chart(data) { ... }
    .frame(minHeight: 200)
    .frame(maxHeight: 400)
```

Test charts at the "Accessibility Extra Extra Extra Large" text size to verify
axis labels, annotations, and legends remain readable.

### Color

- Avoid encoding meaning solely in color. Pair `.foregroundStyle(by:)` with
  `.symbol(by:)` or `.lineStyle(by:)` for distinguishability.
- Use system colors that adapt to both light and dark modes.
- Test with color blindness simulations in the Accessibility Inspector.

```swift
LineMark(x: .value("Date", item.date), y: .value("Value", item.value))
    .foregroundStyle(by: .value("Category", item.category))
    .symbol(by: .value("Category", item.category))
    .lineStyle(by: .value("Category", item.category))
```

---

## Performance: Vectorized Plots for Large Datasets

For datasets exceeding 1000 data points, use vectorized plot types instead of
individual marks. Vectorized plots accept entire collections and render
efficiently.

### When to use vectorized plots

| Data Points | Recommended Approach |
|---|---|
| < 100 | Individual marks (`BarMark`, `LineMark`, etc.) |
| 100 - 1000 | Either approach; profile if performance matters |
| > 1000 | Vectorized plots (`BarPlot`, `LinePlot`, etc.) |

### Data-driven vectorized plot

```swift
struct SensorReading: Identifiable {
    let id: Int
    let timestamp: Date
    let temperature: Double
    var color: Color { temperature > 30 ? .red : .blue }
    var accessibilityDescription: Text {
        Text("\(timestamp.formatted(.dateTime.hour().minute())): \(temperature, specifier: "%.1f") degrees")
    }
}

Chart {
    LinePlot(
        readings,
        x: .value("Time", \.timestamp),
        y: .value("Temperature", \.temperature)
    )
    .foregroundStyle(.blue)
}
```

### KeyPath modifier ordering

Apply KeyPath-based modifiers before simple-value modifiers:

```swift
// WRONG
BarPlot(data, x: .value("X", \.x), y: .value("Y", \.y))
    .opacity(0.8)                // value modifier
    .foregroundStyle(\.color)    // KeyPath -- compiler error

// CORRECT
BarPlot(data, x: .value("X", \.x), y: .value("Y", \.y))
    .foregroundStyle(\.color)    // KeyPath first
    .opacity(0.8)                // value modifier second
```

### Available vectorized plot types

| Plot Type | Mark Equivalent | Available From |
|---|---|---|
| `BarPlot` | `BarMark` | iOS 18+ |
| `LinePlot` | `LineMark` | iOS 18+ |
| `PointPlot` | `PointMark` | iOS 18+ |
| `AreaPlot` | `AreaMark` | iOS 18+ |
| `RulePlot` | `RuleMark` | iOS 18+ |
| `RectanglePlot` | `RectangleMark` | iOS 18+ |
| `SectorPlot` | `SectorMark` | iOS 18+ |

---

## Dark Mode and Theming

### Automatic adaptation

Swift Charts inherits the current color scheme automatically. System colors
(`.blue`, `.orange`, `.green`) adapt to light and dark modes without extra code.

### Custom color palettes

Use `.chartForegroundStyleScale` to define a consistent palette:

```swift
Chart(data) { item in
    BarMark(
        x: .value("Category", item.category),
        y: .value("Value", item.value)
    )
    .foregroundStyle(by: .value("Category", item.category))
}
.chartForegroundStyleScale([
    "Electronics": .blue,
    "Clothing": .purple,
    "Food": .orange,
    "Books": .green,
    "Other": .gray
])
```

### Background and plot area styling

```swift
Chart(data) { ... }
.chartPlotStyle { plotArea in
    plotArea
        .background(.quaternary.opacity(0.3))
        .border(.quaternary, width: 0.5)
}
```

### Axis styling

```swift
.chartXAxisStyle { axis in
    axis.background(.blue.opacity(0.05))
}
```

### Testing dark mode

Always preview charts in both light and dark color schemes. In Xcode previews:

```swift
#Preview {
    ChartView()
        .preferredColorScheme(.dark)
}
```

Verify:
- Axis labels and grid lines are readable.
- Data colors maintain sufficient contrast.
- Annotations and legend text adapt properly.

---

## Heat Map Pattern

```swift
Chart(heatMapData) { item in
    RectangleMark(
        x: .value("Hour", item.hour),
        y: .value("Day", item.day)
    )
    .foregroundStyle(by: .value("Count", item.count))
}
.chartForegroundStyleScale(range: Gradient(colors: [.blue, .yellow, .red]))
```

---

## Stacking Methods

| Method | Behavior |
|---|---|
| `.standard` | Default. Regions stack on top showing absolute values. |
| `.normalized` | Scales to 0-100% proportional view. |
| `.center` | Baseline centered (streamgraph). |
| `.unstacked` | Overlapping; no stacking. |

```swift
AreaMark(
    x: .value("Date", item.date),
    y: .value("Revenue", item.revenue),
    stacking: .normalized
)
.foregroundStyle(by: .value("Category", item.category))
```

---

## MarkDimension Options

| Dimension | Description |
|---|---|
| `.automatic` | Framework decides |
| `.fixed(CGFloat)` | Exact pixel size |
| `.inset(CGFloat)` | Inset from available space |
| `.ratio(CGFloat)` | Proportion of available space (0...1) |

Use for `width`, `height` on `BarMark` and `innerRadius`, `outerRadius` on `SectorMark`.

---

## Symbol Configuration

### Built-in shapes

`circle`, `square`, `triangle`, `diamond`, `pentagon`, `plus`, `cross`, `asterisk`

```swift
PointMark(x: .value("X", item.x), y: .value("Y", item.y))
    .symbol(.diamond)
    .symbolSize(80)
```

### Data-driven symbol encoding

```swift
PointMark(x: .value("X", item.x), y: .value("Y", item.y))
    .symbol(by: .value("Category", item.category))
```

### Custom symbol view

```swift
PointMark(x: .value("X", item.x), y: .value("Y", item.y))
    .symbol {
        Image(systemName: "star.fill")
            .font(.caption2)
    }
```

---

## ChartProxy and Coordinate Conversion

Use `chartOverlay` or `chartBackground` to access `ChartProxy`:

```swift
.chartOverlay { proxy in
    GeometryReader { geometry in
        Rectangle()
            .fill(.clear)
            .contentShape(Rectangle())
            .gesture(
                DragGesture()
                    .onChanged { value in
                        let origin = geometry[proxy.plotAreaFrame].origin
                        let location = CGPoint(
                            x: value.location.x - origin.x,
                            y: value.location.y - origin.y
                        )
                        if let date: Date = proxy.value(atX: location.x) {
                            selectedDate = date
                        }
                    }
            )
    }
}
```

### Key ChartProxy methods

| Method | Purpose |
|---|---|
| `position(forX:)` | Data value to screen x-coordinate |
| `position(forY:)` | Data value to screen y-coordinate |
| `value(atX:as:)` | Screen x-coordinate to data value |
| `value(atY:as:)` | Screen y-coordinate to data value |
| `plotAreaSize` | Size of the plot area |
| `plotAreaFrame` | Anchor for the plot area frame |

---

## Quick Reference: Chart View Modifiers

### Axes
- `chartXAxis(_:)` / `chartXAxis(content:)`
- `chartYAxis(_:)` / `chartYAxis(content:)`
- `chartXAxisLabel(...)` / `chartYAxisLabel(...)`
- `chartXAxisStyle(content:)` / `chartYAxisStyle(content:)`

### Scales
- `chartXScale(domain:range:type:)` and variants
- `chartYScale(domain:range:type:)` and variants
- `chartForegroundStyleScale(_:)` -- custom color mapping

### Legend
- `chartLegend(_:)` -- visibility
- `chartLegend(position:alignment:spacing:)` -- positioning
- `chartLegend(position:alignment:spacing:content:)` -- custom content

### Selection (iOS 17+)
- `chartXSelection(value:)` / `chartXSelection(range:)`
- `chartYSelection(value:)` / `chartYSelection(range:)`
- `chartAngleSelection(value:)` -- for `SectorMark`

### Scrolling (iOS 17+)
- `chartScrollableAxes(_:)`
- `chartXVisibleDomain(length:)` / `chartYVisibleDomain(length:)`
- `chartScrollPosition(initialX:)` / `chartScrollPosition(x:)`
- `chartScrollTargetBehavior(_:)`

### Overlay and Background
- `chartOverlay(alignment:content:)` -- with `ChartProxy`
- `chartBackground(alignment:content:)` -- with `ChartProxy`
- `chartPlotStyle(content:)` -- plot area styling

---

## Apple Documentation Links

- [Swift Charts](https://sosumi.ai/documentation/Charts)
- [Creating a chart using Swift Charts](https://sosumi.ai/documentation/Charts/Creating-a-chart-using-Swift-Charts)
- [BarMark](https://sosumi.ai/documentation/Charts/BarMark)
- [LineMark](https://sosumi.ai/documentation/Charts/LineMark)
- [SectorMark](https://sosumi.ai/documentation/Charts/SectorMark)
- [LinePlot](https://sosumi.ai/documentation/Charts/LinePlot)
- [AxisMarks](https://sosumi.ai/documentation/Charts/AxisMarks)
