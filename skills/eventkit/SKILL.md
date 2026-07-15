---
name: eventkit
description: "Create, read, and manage calendar events and reminders using EventKit and EventKitUI. Use when adding events to the user's calendar, creating reminders, setting recurrence rules, requesting calendar or reminders access, presenting event editors, choosing calendars, handling alarms, observing calendar changes, or working with EKEventStore, EKEvent, EKReminder, EKCalendar, EKRecurrenceRule, EKEventEditViewController, EKCalendarChooser, or EventKitUI views."
---

# EventKit

Use EventKit for calendar and reminder authorization, CRUD, recurrence, alarms,
and system editors.

## Contents

- [Availability](#availability)
- [Setup](#setup)
- [Authorization](#authorization)
- [Creating Events](#creating-events)
- [Fetching Events](#fetching-events)
- [Reminders](#reminders)
- [Recurrence Rules](#recurrence-rules)
- [Alarms](#alarms)
- [EventKitUI Controllers](#eventkitui-controllers)
- [Observing Changes](#observing-changes)
- [Common Mistakes](#common-mistakes)
- [Review Checklist](#review-checklist)
- [References](#references)

## Availability

- **iOS 17+:** Use granular full/write-only request methods; legacy
  `requestAccess(to:)` no longer prompts and throws. The system event editor can
  create an event without app calendar access. For iOS 10–16, guard those APIs,
  use the legacy request plus `NSCalendarsUsageDescription` /
  `NSRemindersUsageDescription`; EventKitUI may also need
  `NSContactsUsageDescription`.
- **iOS 26+:** The typed `EKEventStore.EventStoreChanged` / `.changed` message is
  available behind a guard. Keep `EKEventStoreChanged` for earlier systems.

## Setup

### Info.plist Keys

Add the usage description for the access path selected in
[Authorization](#authorization). Do not request broader access merely to simplify
the setup path.

The authorization-free system editor path needs no calendar usage string.
Direct writes need write-only or full access; reads need full access. Reminders
have only full access.

### Event Store

Create a single `EKEventStore` instance and reuse it. Do not mix objects from
different event stores.

```swift
import EventKit

let eventStore = EKEventStore()
```

## Authorization

Request the narrowest access that matches the feature. Apply the versioned
request path in [Availability](#availability).

| Key | Access Level |
|---|---|
| `NSCalendarsFullAccessUsageDescription` | Read + write events |
| `NSCalendarsWriteOnlyAccessUsageDescription` | Direct write-only event creation |
| `NSRemindersFullAccessUsageDescription` | Read + write reminders |

### Full Access to Events

Call `try await eventStore.requestFullAccessToEvents()` when the app needs to
read, edit, delete, or fetch calendar events.

### Write-Only Access to Events

Use when your app only creates events (e.g., saving a booking) and does not
need to read existing events.

Call `try await eventStore.requestWriteOnlyAccessToEvents()` before direct
EventKit writes that do not use `EKEventEditViewController`.

Write-only access can create events but cannot fetch calendars or events,
including app-created events. Use full access for later query, verification,
modification, or sync.

### Full Access to Reminders

Call `try await eventStore.requestFullAccessToReminders()` before reading,
creating, editing, or deleting reminders.

### Checking Authorization Status

Use `EKEventStore.authorizationStatus(for: .event)` or `.reminder` before work.
Handle `.notDetermined`, `.fullAccess`, `.writeOnly`, `.restricted`, `.denied`,
and `@unknown default`; only `.fullAccess` supports event/reminder reads.

## Creating Events

```swift
func createEvent(
    title: String,
    startDate: Date,
    endDate: Date,
    calendar: EKCalendar? = nil
) throws {
    let event = EKEvent(eventStore: eventStore)
    event.title = title
    event.startDate = startDate
    event.endDate = endDate
    event.calendar = calendar ?? eventStore.defaultCalendarForNewEvents

    try eventStore.save(event, span: .thisEvent)
}
```

### Setting a Specific Calendar

```swift
// List writable calendars
let calendars = eventStore.calendars(for: .event)
    .filter { $0.allowsContentModifications }

// Use the first writable calendar, or the default
let targetCalendar = calendars.first ?? eventStore.defaultCalendarForNewEvents
event.calendar = targetCalendar
```

### Adding Structured Location

```swift
import CoreLocation

let location = EKStructuredLocation(title: "Apple Park")
location.geoLocation = CLLocation(latitude: 37.3349, longitude: -122.0090)
event.structuredLocation = location
```

## Fetching Events

After the full-access gate in [Authorization](#authorization), use a date-range
predicate to query events. The `events(matching:)` method returns occurrences of
recurring events expanded within the range. Event predicates are capped to a
four-year span, and `events(matching:)` /
`enumerateEvents(matching:using:)` are synchronous and return only committed
events.

```swift
func fetchEvents(from start: Date, to end: Date) -> [EKEvent] {
    let predicate = eventStore.predicateForEvents(
        withStart: start,
        end: end,
        calendars: nil  // nil = all calendars
    )
    return eventStore.events(matching: predicate)
        .sorted { $0.startDate < $1.startDate }
}
```

### Fetching a Single Event by Identifier

```swift
if let event = eventStore.event(withIdentifier: savedEventID) {
    print(event.title ?? "No title")
}
```

## Reminders

### Creating a Reminder

```swift
func createReminder(title: String, dueDate: Date) throws {
    let reminder = EKReminder(eventStore: eventStore)
    reminder.title = title
    reminder.calendar = eventStore.defaultCalendarForNewReminders()

    let dueDateComponents = Calendar.current.dateComponents(
        [.year, .month, .day, .hour, .minute],
        from: dueDate
    )
    reminder.dueDateComponents = dueDateComponents

    try eventStore.save(reminder, commit: true)
}
```

### Fetching Reminders

Reminder fetches are asynchronous and return through a completion handler.

```swift
func fetchIncompleteReminders() async -> [EKReminder] {
    let predicate = eventStore.predicateForIncompleteReminders(
        withDueDateStarting: nil,
        ending: nil,
        calendars: nil
    )

    return await withCheckedContinuation { continuation in
        eventStore.fetchReminders(matching: predicate) { reminders in
            continuation.resume(returning: reminders ?? [])
        }
    }
}
```

### Completing a Reminder

```swift
func completeReminder(_ reminder: EKReminder) throws {
    reminder.isCompleted = true
    try eventStore.save(reminder, commit: true)
}
```

## Recurrence Rules

Use `EKRecurrenceRule` to create repeating events or reminders.

### Simple Recurrence

```swift
// Every week, indefinitely
let weeklyRule = EKRecurrenceRule(
    recurrenceWith: .weekly,
    interval: 1,
    end: nil
)
event.addRecurrenceRule(weeklyRule)

// Every 2 weeks, ending after 10 occurrences
let biweeklyRule = EKRecurrenceRule(
    recurrenceWith: .weekly,
    interval: 2,
    end: EKRecurrenceEnd(occurrenceCount: 10)
)

// Monthly, ending on a specific date
let monthlyRule = EKRecurrenceRule(
    recurrenceWith: .monthly,
    interval: 1,
    end: EKRecurrenceEnd(end: endDate)
)
```

### Complex Recurrence

```swift
// Every Monday and Wednesday
let days = [
    EKRecurrenceDayOfWeek(.monday),
    EKRecurrenceDayOfWeek(.wednesday)
]

let complexRule = EKRecurrenceRule(
    recurrenceWith: .weekly,
    interval: 1,
    daysOfTheWeek: days,
    daysOfTheMonth: nil,
    monthsOfTheYear: nil,
    weeksOfTheYear: nil,
    daysOfTheYear: nil,
    setPositions: nil,
    end: nil
)
event.addRecurrenceRule(complexRule)
```

### Editing Recurring Events

When saving changes to a recurring event, specify the span:

```swift
// Change only this occurrence
try eventStore.save(event, span: .thisEvent)

// Change this and all future occurrences
try eventStore.save(event, span: .futureEvents)
```

## Alarms

Attach alarms to events or reminders to trigger notifications.

```swift
// 15 minutes before
let alarm = EKAlarm(relativeOffset: -15 * 60)
event.addAlarm(alarm)

// At an absolute date
let absoluteAlarm = EKAlarm(absoluteDate: alertDate)
event.addAlarm(absoluteAlarm)
```

For reminder geofences, put an `EKStructuredLocation` and `.enter` / `.leave`
proximity on an `EKAlarm`, then add it to the reminder. See
[references/eventkit-patterns.md](references/eventkit-patterns.md) for the full
location-based reminder pattern.

## EventKitUI Controllers

### EKEventEditViewController — Create/Edit Events

Present the system event editor for creating or editing events.

On the authorization-free path in [Availability](#availability), the editor runs
out of process with its own calendar access. Do not inspect the dismissed
controller to learn what was saved; refetch only with separate full access.

```swift
import EventKitUI

class EventEditorCoordinator: NSObject, EKEventEditViewDelegate {
    let eventStore = EKEventStore()

    func presentEditor(from viewController: UIViewController) {
        let editor = EKEventEditViewController()
        editor.eventStore = eventStore
        editor.editViewDelegate = self
        viewController.present(editor, animated: true)
    }

    func eventEditViewController(
        _ controller: EKEventEditViewController,
        didCompleteWith action: EKEventEditViewAction
    ) {
        switch action {
        case .saved:
            // Event saved
            break
        case .canceled:
            break
        case .deleted:
            break
        @unknown default:
            break
        }
        controller.dismiss(animated: true)
    }
}
```

### EKEventViewController — View an Event

```swift
import EventKitUI

let viewer = EKEventViewController()
viewer.event = existingEvent
viewer.allowsEditing = true
navigationController?.pushViewController(viewer, animated: true)
```

### EKCalendarChooser — Select Calendars

`EKCalendarChooser` requires write-only or full calendar access. In write-only
apps, the chooser behaves as writable-calendars-only and only allows a single
writable calendar selection.

```swift
let chooser = EKCalendarChooser(
    selectionStyle: .multiple,
    displayStyle: .allCalendars,
    entityType: .event,
    eventStore: eventStore
)
chooser.showsDoneButton = true
chooser.showsCancelButton = true
chooser.delegate = self
present(UINavigationController(rootViewController: chooser), animated: true)
```

## Observing Changes

Register for `EKEventStoreChanged` notifications to keep your UI in sync when
events are modified outside your app (e.g., by the Calendar app or a sync).

```swift
NotificationCenter.default.addObserver(
    forName: .EKEventStoreChanged,
    object: eventStore,
    queue: .main
) { [weak self] _ in
    self?.refreshEvents()
}
```

Always re-fetch events after receiving this notification. Previously fetched
`EKEvent`, `EKReminder`, and `EKCalendar` objects may be stale. The notification
is posted on the main actor.

## Common Mistakes

### DON'T: Use legacy requestAccess(to:) on current systems

```swift
// WRONG: Legacy request API on current systems
eventStore.requestAccess(to: .event) { granted, error in }

// CORRECT: Use the granular async methods
let granted = try await eventStore.requestFullAccessToEvents()
```

Keep it only in the compatibility fallback from [Availability](#availability).

### DON'T: Save events to a read-only calendar

```swift
// WRONG: No check -- will throw if calendar is read-only
event.calendar = someCalendar
try eventStore.save(event, span: .thisEvent)

// CORRECT: Verify the calendar allows modifications
guard someCalendar.allowsContentModifications else {
    event.calendar = eventStore.defaultCalendarForNewEvents
    return
}
event.calendar = someCalendar
try eventStore.save(event, span: .thisEvent)
```

### DON'T: Ignore timezone when creating events

```swift
// WRONG: Event appears at wrong time for traveling users
event.startDate = Date()
event.endDate = Date().addingTimeInterval(3600)

// CORRECT: Set the timezone explicitly for location-specific events
event.timeZone = TimeZone(identifier: "America/New_York")
event.startDate = startDate
event.endDate = endDate
```

### DON'T: Forget to commit batched saves

```swift
// WRONG: Changes never persisted
try eventStore.save(event1, span: .thisEvent, commit: false)
try eventStore.save(event2, span: .thisEvent, commit: false)
// Missing commit!

// CORRECT: Commit after batching
try eventStore.save(event1, span: .thisEvent, commit: false)
try eventStore.save(event2, span: .thisEvent, commit: false)
try eventStore.commit()
```

### DON'T: Mix EKObjects from different event stores

```swift
// WRONG: Event fetched from storeA, saved to storeB
let event = storeA.event(withIdentifier: id)!
try storeB.save(event, span: .thisEvent) // Undefined behavior

// CORRECT: Use the same store throughout
let event = eventStore.event(withIdentifier: id)!
try eventStore.save(event, span: .thisEvent)
```

## Review Checklist

- [ ] Correct `Info.plist` usage description keys added for calendars and/or reminders
- [ ] Authorization follows the version split in [Availability](#availability)
- [ ] Write-only calendar access used only for direct event creation, not event/calendar reads
- [ ] Authorization status checked before fetching or saving
- [ ] Full access required before any event or reminder fetch
- [ ] Single `EKEventStore` instance reused across the app
- [ ] Events saved to a writable calendar (`allowsContentModifications` checked)
- [ ] Recurring event saves specify correct `EKSpan` (`.thisEvent` vs `.futureEvents`)
- [ ] Batched saves validate writable calendars, stage with `commit: false`,
      call throwing `commit()`, and on failure `reset()` unsaved state, discard
      every invalidated `EKObject`, then refetch or reconstruct before retry
- [ ] `EKEventStoreChanged` notification observed to refresh stale data
- [ ] Change observation uses the classic notification or guarded typed message per [Availability](#availability)
- [ ] Timezone set explicitly for location-specific events
- [ ] EKObjects not shared across different event store instances
- [ ] EventKitUI delegates dismiss controllers in completion callbacks

## References

- Extended patterns (SwiftUI wrappers, predicate queries, batch operations): [references/eventkit-patterns.md](references/eventkit-patterns.md)
- [EventKit framework](https://sosumi.ai/documentation/eventkit)
- [EKEventStore](https://sosumi.ai/documentation/eventkit/ekeventstore)
- [EKEvent](https://sosumi.ai/documentation/eventkit/ekevent)
- [EKReminder](https://sosumi.ai/documentation/eventkit/ekreminder)
- [EKRecurrenceRule](https://sosumi.ai/documentation/eventkit/ekrecurrencerule)
- [EKCalendar](https://sosumi.ai/documentation/eventkit/ekcalendar)
- [EventKit UI](https://sosumi.ai/documentation/eventkitui)
- [EKEventEditViewController](https://sosumi.ai/documentation/eventkitui/ekeventeditviewcontroller)
- [EKCalendarChooser](https://sosumi.ai/documentation/eventkitui/ekcalendarchooser)
- [Accessing the event store](https://sosumi.ai/documentation/eventkit/accessing-the-event-store)
- [Creating a recurring event](https://sosumi.ai/documentation/eventkit/creating-a-recurring-event)
