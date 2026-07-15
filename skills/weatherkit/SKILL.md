---
name: weatherkit
description: "Fetch WeatherKit current, minute, hourly, and daily forecasts; weather alerts; iOS 18+ changes, historical comparisons, summaries, and statistics; and required Apple Weather attribution. Use when integrating weather data, showing forecasts or alerts, caching WeatherKit responses, displaying attribution, or reviewing WeatherKit query limits in iOS apps."
---

# WeatherKit

Fetch current conditions, hourly and daily forecasts, weather alerts, and
historical statistics using `WeatherService`. Display required Apple Weather attribution.

## Contents

- [Setup](#setup)
- [Fetching Current Weather](#fetching-current-weather)
- [Forecasts](#forecasts)
- [Weather Alerts](#weather-alerts)
- [Selective Queries](#selective-queries)
- [Context Queries](#context-queries)
- [Attribution](#attribution)
- [Availability](#availability)
- [Common Mistakes](#common-mistakes)
- [Review Checklist](#review-checklist)
- [References](#references)

## Setup

### Project Configuration

1. Enable the **WeatherKit** capability in Xcode (adds the entitlement)
2. Enable WeatherKit for your App ID in the Apple Developer portal
3. Add `NSLocationWhenInUseUsageDescription` to Info.plist if using device location
4. WeatherKit requires an active Apple Developer Program membership

### Import

```swift
import WeatherKit
import CoreLocation
```

### Creating the Service

Use the shared singleton or create an instance. `WeatherService` conforms to
`Sendable`; keep app cache and UI state isolated separately.

```swift
let weatherService = WeatherService.shared
// or
let weatherService = WeatherService()
```

## Fetching Current Weather

Fetch current conditions for a location. Returns a `Weather` object with all
available datasets.

WeatherKit temperatures are `Measurement<UnitTemperature>` values; display them
with `.formatted()` so units and number formatting follow the user's locale.

```swift
func fetchCurrentWeather(for location: CLLocation) async throws -> CurrentWeather {
    let weather = try await weatherService.weather(for: location)
    return weather.currentWeather
}

// Using the result
func displayCurrent(_ current: CurrentWeather) {
    let temp = current.temperature  // Measurement<UnitTemperature>
    let condition = current.condition  // WeatherCondition enum
    let symbol = current.symbolName  // SF Symbol name
    let humidity = current.humidity  // Double (0-1)
    let wind = current.wind  // Wind (speed, direction, gust)
    let uvIndex = current.uvIndex  // UVIndex

    print("\(condition): \(temp.formatted())")
}
```

## Forecasts

### Hourly Forecast

Returns 25 contiguous hours starting from the current hour by default.

```swift
func fetchHourlyForecast(for location: CLLocation) async throws -> Forecast<HourWeather> {
    let weather = try await weatherService.weather(for: location)
    return weather.hourlyForecast
}

// Iterate hours
for hour in hourlyForecast {
    print("\(hour.date): \(hour.temperature.formatted()), \(hour.condition)")
}
```

### Daily Forecast

Returns 10 contiguous days starting from the current day by default.

```swift
func fetchDailyForecast(for location: CLLocation) async throws -> Forecast<DayWeather> {
    let weather = try await weatherService.weather(for: location)
    return weather.dailyForecast
}

// Iterate days
for day in dailyForecast {
    print("\(day.date): \(day.lowTemperature.formatted()) - \(day.highTemperature.formatted())")
    print("  Condition: \(day.condition), Precipitation: \(day.precipitationChance)")
}
```

### Custom Date Range

Request forecasts for specific date ranges using `WeatherQuery`.

Daily and hourly date-range queries use an inclusive `startDate` and exclusive
`endDate`. They can include historical data from August 1, 2021. Forecasts are
available up to 10 days in the future; each request returns at most 10 daily
forecast days or about 240 hourly forecast hours.

```swift
func fetchExtendedForecast(for location: CLLocation) async throws -> Forecast<DayWeather> {
    let startDate = Date.now
    let endDate = Calendar.current.date(byAdding: .day, value: 10, to: startDate)!

    let forecast = try await weatherService.weather(
        for: location,
        including: .daily(startDate: startDate, endDate: endDate)
    )
    return forecast
}
```

For tomorrow-specific guidance, request the local tomorrow day interval rather
than using minute forecasts:

```swift
func fetchTomorrowForecast(for location: CLLocation) async throws -> Forecast<DayWeather> {
    let calendar = Calendar.current
    let tomorrow = calendar.startOfDay(
        for: calendar.date(byAdding: .day, value: 1, to: .now)!
    )
    let dayAfterTomorrow = calendar.date(byAdding: .day, value: 1, to: tomorrow)!

    return try await weatherService.weather(
        for: location,
        including: .daily(startDate: tomorrow, endDate: dayAfterTomorrow)
    )
}
```

## Weather Alerts

Fetch active weather alerts for a location. Alerts include severity, summary,
and affected regions.

```swift
func fetchAlerts(for location: CLLocation) async throws -> [WeatherAlert]? {
    let weather = try await weatherService.weather(for: location)
    return weather.weatherAlerts
}

// Process alerts
if let alerts = weatherAlerts {
    for alert in alerts {
        print("Alert: \(alert.summary)")
        print("Severity: \(alert.severity)")
        print("Region: \(alert.region ?? "Unknown region")")
        print("Details: \(alert.detailsURL)") // Non-optional and required for attribution
    }
}
```

For alert dashboards, name `WeatherAvailability` explicitly when discussing
support checks: it exposes `alertAvailability` and `minuteAvailability` only,
not a broad availability matrix for current, hourly, or daily weather.

## Selective Queries

Fetch only the datasets you need to minimize API usage and response size. Each
`WeatherQuery` type maps to one dataset.

### Single Dataset

```swift
let current = try await weatherService.weather(
    for: location,
    including: .current
)
// current is CurrentWeather
```

### Multiple Datasets

```swift
let (current, hourly, daily) = try await weatherService.weather(
    for: location,
    including: .current, .hourly, .daily
)
// current: CurrentWeather, hourly: Forecast<HourWeather>, daily: Forecast<DayWeather>
```

### Minute Forecast

Available in limited regions. Returns precipitation forecasts at minute
granularity for the next hour.

```swift
let minuteForecast = try await weatherService.weather(
    for: location,
    including: .minute
)
// minuteForecast: Forecast<MinuteWeather>?  (nil if unavailable)
```

### Available Query Types

| Query | Return Type | Description |
|---|---|---|
| `.current` | `CurrentWeather` | Current observed conditions |
| `.hourly` | `Forecast<HourWeather>` | 25 hours from current hour |
| `.daily` | `Forecast<DayWeather>` | 10 days from today |
| `.minute` | `Forecast<MinuteWeather>?` | Next-hour precipitation (limited regions) |
| `.alerts` | `[WeatherAlert]?` | Active weather alerts |
| `.availability` | `WeatherAvailability` | Alert and minute forecast availability only |
| `.changes` | `WeatherChanges?` | Significant upcoming weather changes (iOS 18+) |
| `.historicalComparisons` | `HistoricalComparisons?` | Current weather compared to historical averages (iOS 18+) |

## Context Queries

For "unusual tomorrow" or "what is changing?" features on iOS 18+, request the
optional `.changes` and `.historicalComparisons` results together: the first
reports significant upcoming changes and the second provides historical context.

```swift
let (changes, comparisons) = try await weatherService.weather(
    for: location,
    including: .changes, .historicalComparisons
)
```

Historical summaries and statistics use `WeatherService` methods rather than
`WeatherQuery`. Load [references/weatherkit-patterns.md](references/weatherkit-patterns.md)
for their tuple ordering, APIs, and statistics-specific properties.

## Attribution

Apple requires apps using WeatherKit to display attribution. This is a
legal requirement.

### Fetching Attribution

```swift
func fetchAttribution() async throws -> WeatherAttribution {
    return try await weatherService.attribution
}
```

Load [references/weatherkit-patterns.md](references/weatherkit-patterns.md) for the complete SwiftUI attribution view and cache integration.

### Attribution Properties

| Property | Use |
|---|---|
| `combinedMarkLightURL` | Apple Weather mark for light backgrounds |
| `combinedMarkDarkURL` | Apple Weather mark for dark backgrounds |
| `squareMarkURL` | Square Apple Weather logo |
| `legalPageURL` | URL to the legal attribution web page |
| `legalAttributionText` | Text alternative when a web view is not feasible |
| `serviceName` | Weather data provider name |

## Availability

Check whether weather alerts or minute forecast data are available for a
location. `WeatherAvailability` reports only alert and minute availability;
other datasets, such as current weather, are expected to be supported for
geographic locations.

```swift
func checkAvailability(for location: CLLocation) async throws {
    let availability = try await weatherService.weather(
        for: location,
        including: .availability
    )

    // Check specific dataset availability
    if availability.alertAvailability == .available {
        // Safe to fetch alerts
    }

    if availability.minuteAvailability == .available {
        // Minute forecast available for this region
    }
}
```

## Common Mistakes

### DON'T: Ship without Apple Weather attribution

Display the appropriate Apple Weather mark and link `legalPageURL` wherever WeatherKit data appears; use `legalAttributionText` only when the legal page cannot be shown.

### DON'T: Fetch all datasets when you only need current conditions

Each dataset query counts against your API quota. Use the selective query shown
in [Selective Queries](#selective-queries) and fetch only what the UI displays.

### DON'T: Ignore minute forecast unavailability

Minute forecasts are optional in unsupported regions. Check availability and
handle the `nil` result instead of force-unwrapping it.

### DON'T: Forget the WeatherKit entitlement

Without the capability enabled, `WeatherService` calls throw at runtime.

```swift
// WRONG: No WeatherKit capability configured
let weather = try await weatherService.weather(for: location) // Throws

// CORRECT: Enable WeatherKit in Xcode Signing & Capabilities
// and in the Apple Developer portal for your App ID
```

### DON'T: Make repeated requests without caching

WeatherKit models include `metadata.expirationDate`. Cache responses until that
expiration instead of inventing a fixed interval or fetching on every view
appearance. Let a model or cache own `loadIfNeeded`; the complete actor pattern
is in [references/weatherkit-patterns.md](references/weatherkit-patterns.md#caching-strategy).

## Review Checklist

- [ ] WeatherKit capability enabled in Xcode and Apple Developer portal
- [ ] Active Apple Developer Program membership (required for WeatherKit)
- [ ] Apple Weather attribution displayed wherever weather data appears
- [ ] Attribution mark uses correct color scheme variant (light/dark)
- [ ] Legal attribution page linked or `legalAttributionText` displayed
- [ ] Only needed `WeatherQuery` datasets fetched (not full `weather(for:)` when unnecessary)
- [ ] Minute forecast handled as optional (nil in unsupported regions)
- [ ] Weather alerts checked for nil before iteration
- [ ] Alert detail links use non-optional `detailsURL`; optional `region` is nil-safe
- [ ] Responses cached until each model's `metadata.expirationDate`
- [ ] `WeatherAvailability` used for alert/minute availability, not as a broad support matrix
- [ ] Location permission requested before passing `CLLocation` to service
- [ ] Temperature and measurements formatted with `Measurement.formatted()` for locale

## References

- Extended patterns (SwiftUI dashboard, charts integration, historical statistics): [references/weatherkit-patterns.md](references/weatherkit-patterns.md)
- [WeatherKit framework](https://sosumi.ai/documentation/weatherkit)
- [WeatherService](https://sosumi.ai/documentation/weatherkit/weatherservice)
- [WeatherAttribution](https://sosumi.ai/documentation/weatherkit/weatherattribution)
- [WeatherQuery](https://sosumi.ai/documentation/weatherkit/weatherquery)
- [WeatherQuery.daily(startDate:endDate:)](https://sosumi.ai/documentation/weatherkit/weatherquery/daily(startdate:enddate:))
- [WeatherQuery.hourly(startDate:endDate:)](https://sosumi.ai/documentation/weatherkit/weatherquery/hourly(startdate:enddate:))
- [CurrentWeather](https://sosumi.ai/documentation/weatherkit/currentweather)
- [CurrentWeather.temperature](https://sosumi.ai/documentation/weatherkit/currentweather/temperature)
- [Measurement.formatted()](https://sosumi.ai/documentation/foundation/measurement/formatted())
- [Forecast](https://sosumi.ai/documentation/weatherkit/forecast)
- [HourWeather](https://sosumi.ai/documentation/weatherkit/hourweather)
- [DayWeather](https://sosumi.ai/documentation/weatherkit/dayweather)
- [WeatherAlert](https://sosumi.ai/documentation/weatherkit/weatheralert)
- [WeatherAvailability](https://sosumi.ai/documentation/weatherkit/weatheravailability)
- [WeatherMetadata.expirationDate](https://sosumi.ai/documentation/weatherkit/weathermetadata/expirationdate)
- [WeatherQuery.changes](https://sosumi.ai/documentation/weatherkit/weatherquery/changes)
- [WeatherQuery.historicalComparisons](https://sosumi.ai/documentation/weatherkit/weatherquery/historicalcomparisons)
- [WeatherKit updates](https://sosumi.ai/documentation/updates/weatherkit)
- [Bring context to today's weather](https://sosumi.ai/videos/play/wwdc2024/10067)
- [Fetching weather forecasts with WeatherKit](https://sosumi.ai/documentation/weatherkit/fetching_weather_forecasts_with_weatherkit)
