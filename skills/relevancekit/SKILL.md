---
name: relevancekit
description: "Increase widget visibility on Apple Watch using RelevanceKit. Use when providing contextual relevance signals for watchOS widgets, declaring time-based or location-based relevance, combining multiple relevance providers, helping the system surface the right widget at the right time on watchOS 26, or routing mixed RelevanceKit/WidgetKit/HealthKit/MapKit Smart Stack scope."
---

# RelevanceKit

Provide on-device contextual clues that increase a widget's visibility in the
Apple Watch Smart Stack. RelevanceKit tells the system *when* a widget is
relevant by time, location, fitness state, sleep schedule, or connected hardware.
Targets Swift 6.3 / watchOS 26+.

> **Beta-sensitive.** Re-check Apple documentation before making strong RelevanceKit availability or behavior claims.

See [references/relevancekit-patterns.md](references/relevancekit-patterns.md) for complete relevant-widget, timeline provider, grouping, preview, and permission patterns.

## Contents

- [Overview](#overview)
- [Setup](#setup)
- [Relevance Providers](#relevance-providers)
- [Boundary Routing](#boundary-routing)
- [Time-Based Relevance](#time-based-relevance)
- [Location-Based Relevance](#location-based-relevance)
- [Fitness and Sleep Relevance](#fitness-and-sleep-relevance)
- [Hardware Relevance](#hardware-relevance)
- [Combining Signals](#combining-signals)
- [Widget Integration](#widget-integration)
- [Common Mistakes](#common-mistakes)
- [Review Checklist](#review-checklist)
- [References](#references)

## Overview

watchOS uses two mechanisms to determine widget relevance in the Smart Stack:

1. **Timeline provider relevance** -- implement `relevance()` on an existing
   `AppIntentTimelineProvider` to attach `RelevantContext` clues to timeline
   entries. Available across platforms; only watchOS acts on the data.
2. **Relevant widget** -- use `RelevanceConfiguration` with a
   `RelevanceEntriesProvider` to build a widget driven entirely by relevance
   clues. The system creates individual Smart Stack cards per relevant entry.
   watchOS 26+ only.

Choose a timeline provider when the widget always has data to show and relevance
is supplementary. Choose a relevant widget when the widget should *only* appear
when conditions match, or when multiple cards should appear simultaneously (e.g.,
several upcoming calendar events).

### Key Types

| Type | Module | Role |
|---|---|---|
| `RelevantContext` | RelevanceKit | A contextual clue (date, location, fitness, sleep, hardware) |
| `WidgetRelevance` | WidgetKit | Collection of relevance attributes for a widget kind |
| `WidgetRelevanceAttribute` | WidgetKit | Pairs a widget configuration with a `RelevantContext` |
| `WidgetRelevanceGroup` | WidgetKit | Controls grouping behavior in the Smart Stack |
| `RelevanceConfiguration` | WidgetKit | Widget configuration driven by relevance clues (watchOS 26+) |
| `RelevanceEntriesProvider` | WidgetKit | Provides entries for a relevance-configured widget (watchOS 26+) |
| `RelevanceEntry` | WidgetKit | Data needed to render one relevant widget card (watchOS 26+) |

`RelevanceConfiguration`, `RelevanceEntriesProvider`, and `RelevanceEntry` are
WidgetKit APIs. Keep them in this skill's scope only when they are part of the
watchOS relevant-widget workflow that exposes RelevanceKit clues.

## Setup

### Import

```swift
import RelevanceKit
import WidgetKit
```

### Platform Availability

`RelevantContext` is declared across platforms (iOS 17+, watchOS 10+), but
**RelevanceKit functionality only takes effect on watchOS**. Calling the API on
other platforms has no effect. Timeline-provider `relevance()` is available on
iOS 18+, macOS 15+, visionOS 26+, and watchOS 11+ for shared provider code.
`RelevanceConfiguration`, `RelevanceEntriesProvider`, and `RelevanceEntry` are
watchOS 26+ only.

### Permissions

Certain relevance clues require authorization or target setup:

| Clue | Required Permission |
|---|---|
| `.location(inferred:)` | Containing app requests location access; widget extension declares `NSWidgetWantsLocation` |
| `.location(_:)` (CLRegion) | Containing app requests location access; widget extension declares `NSWidgetWantsLocation` |
| `.location(category:)` | Containing app requests location access; widget extension declares `NSWidgetWantsLocation` |
| `.fitness(.workoutActive)` | HealthKit access to `HKWorkoutType` |
| `.fitness(.activityRingsIncomplete)` | HealthKit access to `appleExerciseTime`, `appleMoveTime`, and `appleStandTime` |
| `.sleep(_:)` | HealthKit `sleepAnalysis` permission |
| `.hardware(headphones:)` | None |
| `.date(...)` | None |

Add location purpose strings to the containing app's `Info.plist`, not only the
widget extension. In widget code, check `CLLocationManager.isAuthorizedForWidgetUpdates`
before relying on location clues. For fitness and sleep clues, enable HealthKit
and request the exact read types in the app and widget extension target that
provides relevance.

## Relevance Providers

### Option 1: Timeline Provider with Relevance

Add a `relevance()` method to an existing `AppIntentTimelineProvider`. This
approach shares code across iOS and watchOS while adding watchOS Smart Stack
intelligence.

```swift
struct MyProvider: AppIntentTimelineProvider {
    // ... snapshot, timeline, placeholder ...

    func relevance() async -> WidgetRelevance<MyWidgetIntent> {
        let attributes = events.map { event in
            let context = RelevantContext.date(
                from: event.startDate,
                to: event.endDate
            )
            return WidgetRelevanceAttribute(
                configuration: MyWidgetIntent(event: event),
                context: context
            )
        }
        return WidgetRelevance(attributes)
    }
}
```

### Option 2: RelevanceEntriesProvider (watchOS 26+)

Build a widget that only appears when conditions match. The system calls
`relevance()` to learn *when* the widget matters, then calls `entry()` with
the matching configuration to get render data.

```swift
@available(watchOS 26.0, *)
struct MyRelevanceProvider: RelevanceEntriesProvider {
    func relevance() async -> WidgetRelevance<MyWidgetIntent> {
        let attributes = events.map { event in
            WidgetRelevanceAttribute(
                configuration: MyWidgetIntent(event: event),
                context: RelevantContext.date(event.date, kind: .scheduled)
            )
        }
        return WidgetRelevance(attributes)
    }

    func entry(
        configuration: MyWidgetIntent,
        context: Context
    ) async throws -> MyRelevanceEntry {
        if context.isPreview {
            return .preview
        }
        return MyRelevanceEntry(event: configuration.event)
    }

    func placeholder(context: Context) -> MyRelevanceEntry {
        .placeholder
    }
}
```

## Boundary Routing

When a feature mixes widgets, location, workouts, and Smart Stack relevance,
keep RelevanceKit focused on `RelevantContext`, `WidgetRelevanceAttribute`,
provider `relevance()`, `RelevantIntentManager`, relevant-widget handoffs, and
permissions for relevance clues. Route timelines, reload budgets, families,
rendering, APNs widget pushes, Live Activities, and widget Controls to
WidgetKit; `HKWorkoutSession`, `HKLiveWorkoutBuilder`, `HKWorkoutRoute`,
queries, activity-ring/sleep data, and authorization UX to HealthKit; and
`MKLocalSearch`, `MKLocalSearchCompleter`, `MKDirections`, geocoding,
authorization, regions, geofencing, and place data to MapKit/CoreLocation.

## Time-Based Relevance

Time clues tell the system a widget matters at or around a specific moment.

### Single Date

```swift
RelevantContext.date(eventDate)
```

### Date with Kind

`DateKind` provides an additional hint about the nature of the time relevance:

| Kind | Use |
|---|---|
| `.default` | General time relevance |
| `.scheduled` | A scheduled event (meeting, flight) |
| `.informational` | Information relevant around a time (weather forecast) |

```swift
RelevantContext.date(meetingStart, kind: .scheduled)
```

### Date Range

```swift
// Using from/to
RelevantContext.date(from: startDate, to: endDate)

// Using DateInterval
RelevantContext.date(interval: dateInterval, kind: .scheduled)

// Using ClosedRange
RelevantContext.date(range: startDate...endDate, kind: .default)
```

## Location-Based Relevance

### Inferred Locations

The system infers certain locations from a person's routine. No coordinates
needed.

```swift
RelevantContext.location(inferred: .home)
RelevantContext.location(inferred: .work)
RelevantContext.location(inferred: .school)
RelevantContext.location(inferred: .commute)
```

Apply the location row in the [Permissions](#permissions) table and check
`CLLocationManager.isAuthorizedForWidgetUpdates` before returning clues.

### Specific Region

```swift
import CoreLocation

let region = CLCircularRegion(
    center: CLLocationCoordinate2D(latitude: 37.3349, longitude: -122.0090),
    radius: 500,
    identifier: "apple-park"
)
RelevantContext.location(region)
```

### Point-of-Interest Category (26.0+ SDKs)

Indicate relevance near any location of a given category. Returns `nil` if the
category is unsupported. The factory is SDK-available on Apple platforms 26.0+,
but RelevanceKit clues still only affect Smart Stack behavior on watchOS.

```swift
import MapKit

if let context = RelevantContext.location(category: .beach) {
    // Widget is relevant whenever the person is near a beach
}
```

## Fitness and Sleep Relevance

### Fitness

```swift
// Relevant when activity rings are incomplete
RelevantContext.fitness(.activityRingsIncomplete)

// Relevant during an active workout
RelevantContext.fitness(.workoutActive)
```

Apply the exact fitness mapping in [Permissions](#permissions).

### Sleep

```swift
// Relevant around bedtime
RelevantContext.sleep(.bedtime)

// Relevant around wakeup
RelevantContext.sleep(.wakeup)
```

Apply the sleep mapping in [Permissions](#permissions).

## Hardware Relevance

```swift
// Relevant when headphones are connected
RelevantContext.hardware(headphones: .connected)
```

No special permission required.

## Combining Signals

Return multiple `WidgetRelevanceAttribute` values in the `WidgetRelevance`
array to make a widget relevant under several different conditions.

```swift
func relevance() async -> WidgetRelevance<MyIntent> {
    var attributes: [WidgetRelevanceAttribute<MyIntent>] = []

    // Relevant during morning commute
    attributes.append(
        WidgetRelevanceAttribute(
            configuration: MyIntent(mode: .commute),
            context: .location(inferred: .commute)
        )
    )

    // Relevant at work
    attributes.append(
        WidgetRelevanceAttribute(
            configuration: MyIntent(mode: .work),
            context: .location(inferred: .work)
        )
    )

    // Relevant around a scheduled event
    for event in upcomingEvents {
        attributes.append(
            WidgetRelevanceAttribute(
                configuration: MyIntent(eventID: event.id),
                context: .date(event.date, kind: .scheduled)
            )
        )
    }

    return WidgetRelevance(attributes)
}
```

**Order matters.** Return relevance attributes ordered by priority. The system
may use only a subset of the provided relevances.

## Widget Integration

### Relevant Widget with RelevanceConfiguration

```swift
@available(watchOS 26, *)
struct MyRelevantWidget: Widget {
    var body: some WidgetConfiguration {
        RelevanceConfiguration(
            kind: "com.example.relevant-events",
            provider: MyRelevanceProvider()
        ) { entry in
            EventWidgetView(entry: entry)
        }
        .configurationDisplayName("Events")
        .description("Shows upcoming events when relevant")
    }
}
```

### Associating with a Timeline Widget

When both a timeline widget and a relevant widget show the same data, use
`associatedKind` to prevent duplicate cards. The system replaces the timeline
widget card with relevant widget cards when they are suggested.

```swift
RelevanceConfiguration(
    kind: "com.example.relevant-events",
    provider: MyRelevanceProvider()
) { entry in
    EventWidgetView(entry: entry)
}
.associatedKind("com.example.timeline-events")
```

### Grouping

`WidgetRelevanceGroup` controls how the system groups widgets in the Smart Stack.

```swift
// Opt out of default per-app grouping so each card appears independently
WidgetRelevanceAttribute(
    configuration: intent,
    group: .ungrouped
)

// Named group -- only one widget from the group appears at a time
WidgetRelevanceAttribute(
    configuration: intent,
    group: .named("weather-alerts")
)

// Default system grouping
WidgetRelevanceAttribute(
    configuration: intent,
    group: .automatic
)
```

### RelevantIntent (Timeline Provider Path)

When using a timeline provider, also update `RelevantIntentManager` so the
system has relevance data between timeline refreshes.

```swift
import AppIntents

func updateRelevantIntents() async {
    let intents = events.map { event in
        RelevantIntent(
            MyWidgetIntent(event: event),
            widgetKind: "com.example.events",
            relevance: RelevantContext.date(from: event.start, to: event.end)
        )
    }
    try? await RelevantIntentManager.shared.updateRelevantIntents(intents)
}
```

Call this whenever relevance data changes -- not only during timeline refreshes.

### Previewing Relevant Widgets

Use the entry, relevance-configuration, and full-provider recipes in
[Preview Recipes](references/relevancekit-patterns.md#preview-recipes). Enable
WidgetKit Developer Mode on the watch, test permissions granted and denied, and
finish on a physical Apple Watch; see
[Testing Tips](references/relevancekit-patterns.md#testing-tips).

## Common Mistakes

- **Using RelevanceKit API expecting iOS behavior.** The API compiles on all
  platforms but only has effect on watchOS.
- **Duplicate Smart Stack cards.** When offering both a timeline widget and a
  relevant widget for the same data, use `.associatedKind(_:)` to prevent
  duplication.
- **Not calling `updateRelevantIntents`.** When using timeline providers,
  calling this only inside `timeline()` means the system has stale relevance
  data between refreshes. Update whenever data changes.
- **Ignoring nil from `location(category:)`.** This factory returns an optional.
  Not all `MKPointOfInterestCategory` values are supported.

## Review Checklist

- [ ] Routing: RelevanceKit is watchOS-effect-only, and WidgetKit,
      HealthKit, MapKit, and CoreLocation implementation remains in sibling scope.
- [ ] Signals: contexts match the data model, attributes are priority-ordered,
      and every clue uses the exact Permissions-table setup.
- [ ] Providers: entry, placeholder, relevance, and preview paths are present;
      location category optionals and widget-update authorization are handled.
- [ ] Coordination: `.associatedKind(_:)` prevents duplicate cards, and
      `updateRelevantIntents` runs whenever timeline-provider data changes.
- [ ] Testing: Developer Mode is enabled and previews cover display sizes plus
      granted and denied permission states.

## References

- [references/relevancekit-patterns.md](references/relevancekit-patterns.md) -- extended patterns, full provider
  implementations, permission handling, and grouping strategies
- [RelevanceKit documentation](https://sosumi.ai/documentation/relevancekit)
- [RelevantContext](https://sosumi.ai/documentation/relevancekit/relevantcontext)
- [Increasing the visibility of widgets in Smart Stacks](https://sosumi.ai/documentation/widgetkit/widget-suggestions-in-smart-stacks)
- [RelevanceConfiguration](https://sosumi.ai/documentation/widgetkit/relevanceconfiguration)
- [RelevanceEntriesProvider](https://sosumi.ai/documentation/widgetkit/relevanceentriesprovider)
- [What's new in watchOS 26 (WWDC25 session 334)](https://sosumi.ai/videos/play/wwdc2025/334/)
