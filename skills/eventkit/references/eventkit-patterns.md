# EventKit Extended Patterns

Overflow reference for the `eventkit` skill. Contains advanced patterns that exceed the main skill file's scope.

## Contents

- [SwiftUI Calendar Integration](#swiftui-calendar-integration)
- [Advanced Predicate Queries](#advanced-predicate-queries)
- [Batch Operations](#batch-operations)
- [Calendar Management](#calendar-management)
- [Reminder Workflows](#reminder-workflows)
- [EventKitUI in SwiftUI](#eventkitui-in-swiftui)
- [Typed Change Notifications](#typed-change-notifications)

## SwiftUI Calendar Integration

Prerequisite: pass the main skill's full-access authorization gate before using
this read/write integration. Keep the iOS 17+ request and older-system fallback
in that single authorization path.

### Observable Event Manager

```swift
import EventKit
import SwiftUI

@Observable
@MainActor
final class CalendarManager {
    let eventStore = EKEventStore()
    var events: [EKEvent] = []
    var authorizationStatus: EKAuthorizationStatus = .notDetermined

    func requestAccess() async {
        do {
            let granted = try await eventStore.requestFullAccessToEvents()
            authorizationStatus = granted ? .fullAccess : .denied
            if granted { fetchThisWeekEvents() }
        } catch {
            authorizationStatus = .denied
        }
    }

    func fetchThisWeekEvents() {
        let calendar = Calendar.current
        let start = calendar.startOfDay(for: Date())
        let end = calendar.date(byAdding: .day, value: 7, to: start)!

        let predicate = eventStore.predicateForEvents(
            withStart: start,
            end: end,
            calendars: nil
        )
        events = eventStore.events(matching: predicate)
            .sorted { $0.startDate < $1.startDate }
    }

    func observeChanges() {
        NotificationCenter.default.addObserver(
            forName: .EKEventStoreChanged,
            object: eventStore,
            queue: .main
        ) { [weak self] _ in
            self?.fetchThisWeekEvents()
        }
    }
}
```

### SwiftUI View with Calendar Events

```swift
struct CalendarEventsView: View {
    @State private var manager = CalendarManager()

    var body: some View {
        List(manager.events, id: \.eventIdentifier) { event in
            VStack(alignment: .leading) {
                Text(event.title)
                    .font(.headline)
                Text(event.startDate, style: .date)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
        .task {
            await manager.requestAccess()
            manager.observeChanges()
        }
        .overlay {
            if manager.events.isEmpty {
                ContentUnavailableView(
                    "No Events",
                    systemImage: "calendar",
                    description: Text("No events this week.")
                )
            }
        }
    }
}
```

## Advanced Predicate Queries

Event predicates search at most a four-year span. `events(matching:)` and
`enumerateEvents(matching:using:)` are synchronous and include only committed
events, so commit batched changes before querying and move large reads off the
main actor when needed.

### Events in a Specific Calendar

```swift
func fetchEvents(in calendar: EKCalendar, range: DateInterval) -> [EKEvent] {
    let predicate = eventStore.predicateForEvents(
        withStart: range.start,
        end: range.end,
        calendars: [calendar]
    )
    return eventStore.events(matching: predicate)
}
```

### Completed Reminders in a Date Range

```swift
func fetchCompletedReminders(from start: Date, to end: Date) async -> [EKReminder] {
    let predicate = eventStore.predicateForCompletedReminders(
        withCompletionDateStarting: start,
        ending: end,
        calendars: nil
    )

    return await withCheckedContinuation { continuation in
        eventStore.fetchReminders(matching: predicate) { reminders in
            continuation.resume(returning: reminders ?? [])
        }
    }
}
```

### Enumerating Events Efficiently

For large date ranges, use `enumerateEvents` to process events one at a time
without loading all into memory.

```swift
func processAllEvents(from start: Date, to end: Date) {
    let predicate = eventStore.predicateForEvents(
        withStart: start,
        end: end,
        calendars: nil
    )

    eventStore.enumerateEvents(matching: predicate) { event, stop in
        // Process each event
        if event.title.contains("Cancel") {
            stop.pointee = true // Stop enumeration early
        }
    }
}
```

## Batch Operations

### Creating Multiple Events Efficiently

Validate inputs and writable calendars first. Stage individual operations with
`commit: false`, then call the throwing `commit()` once. On any staging or commit
failure, call `reset()` to discard unsaved EventKit state and propagate the
error. `reset()` disassociates and invalidates every existing object created or
retrieved from that store, so discard all retained `EKObject` instances. Correct
the known cause, then refetch with full access or reconstruct with write-only
access before creating a new batch; do not blindly retry or require a read-back.

```swift
enum EventBatchError: Error {
    case noWritableCalendar
    case readOnlyCalendar
}

func createEvents(from entries: [(String, Date, Date)]) throws {
    guard let calendar = eventStore.defaultCalendarForNewEvents,
          calendar.allowsContentModifications else {
        throw EventBatchError.noWritableCalendar
    }

    do {
        for (title, start, end) in entries {
            let event = EKEvent(eventStore: eventStore)
            event.title = title
            event.startDate = start
            event.endDate = end
            event.calendar = calendar
            try eventStore.save(event, span: .thisEvent, commit: false)
        }
        try eventStore.commit()
    } catch {
        eventStore.reset()
        throw error
    }
}
```

### Deleting Events in Bulk

```swift
func deleteEvents(_ events: [EKEvent]) throws {
    guard events.allSatisfy({ $0.calendar.allowsContentModifications }) else {
        throw EventBatchError.readOnlyCalendar
    }

    do {
        for event in events {
            try eventStore.remove(event, span: .thisEvent, commit: false)
        }
        try eventStore.commit()
    } catch {
        eventStore.reset()
        throw error
    }
}
```

### Resetting Unsaved Changes

```swift
// Discard all uncommitted changes
eventStore.reset()
```

## Calendar Management

### Creating a Custom Calendar

```swift
func createCalendar(name: String, color: CGColor) throws -> EKCalendar {
    let calendar = EKCalendar(for: .event, eventStore: eventStore)
    calendar.title = name
    calendar.cgColor = color

    // Find a local source (iCloud, local, etc.)
    if let localSource = eventStore.sources.first(where: {
        $0.sourceType == .local
    }) {
        calendar.source = localSource
    } else if let defaultSource = eventStore.defaultCalendarForNewEvents?.source {
        calendar.source = defaultSource
    }

    try eventStore.saveCalendar(calendar, commit: true)
    return calendar
}
```

### Listing Calendars by Type

```swift
// All event calendars
let eventCalendars = eventStore.calendars(for: .event)

// All reminder calendars
let reminderCalendars = eventStore.calendars(for: .reminder)

// Only writable calendars
let writableCalendars = eventCalendars.filter { $0.allowsContentModifications }
```

## Reminder Workflows

### Reminder with Location-Based Alarm

```swift
import CoreLocation
import EventKit

enum CalendarError: Error {
    case remindersAccessRequired
    case missingDefaultReminderList
}

func createLocationReminder(
    title: String,
    latitude: Double,
    longitude: Double
) throws {
    guard EKEventStore.authorizationStatus(for: .reminder) == .fullAccess else {
        throw CalendarError.remindersAccessRequired
    }
    guard let reminderCalendar = eventStore.defaultCalendarForNewReminders() else {
        throw CalendarError.missingDefaultReminderList
    }

    let reminder = EKReminder(eventStore: eventStore)
    reminder.title = title
    reminder.calendar = reminderCalendar

    let location = EKStructuredLocation(title: "Target Location")
    location.geoLocation = CLLocation(latitude: latitude, longitude: longitude)
    location.radius = 200 // meters

    let alarm = EKAlarm(relativeOffset: 0)
    alarm.structuredLocation = location
    alarm.proximity = .enter  // .enter or .leave
    reminder.addAlarm(alarm)

    try eventStore.save(reminder, commit: true)
}
```

If the app uses the person's current location while creating location-based
reminders, add `NSLocationWhenInUseUsageDescription` and request Core Location
authorization in the location layer.

### Reminder with Priority

```swift
let reminder = EKReminder(eventStore: eventStore)
reminder.title = "Important Task"
reminder.priority = 1  // 1-4: High, 5: Medium, 6-9: Low, 0: None
reminder.calendar = eventStore.defaultCalendarForNewReminders()
```

## EventKitUI in SwiftUI

### UIViewControllerRepresentable for Event Editor

```swift
import SwiftUI
import EventKitUI

struct EventEditView: UIViewControllerRepresentable {
    let eventStore: EKEventStore
    @Binding var isPresented: Bool

    func makeUIViewController(context: Context) -> EKEventEditViewController {
        let editor = EKEventEditViewController()
        editor.eventStore = eventStore
        editor.editViewDelegate = context.coordinator
        return editor
    }

    func updateUIViewController(
        _ uiViewController: EKEventEditViewController,
        context: Context
    ) {}

    func makeCoordinator() -> Coordinator {
        Coordinator(self)
    }

    class Coordinator: NSObject, EKEventEditViewDelegate {
        let parent: EventEditView

        init(_ parent: EventEditView) {
            self.parent = parent
        }

        func eventEditViewController(
            _ controller: EKEventEditViewController,
            didCompleteWith action: EKEventEditViewAction
        ) {
            parent.isPresented = false
        }
    }
}
```

On iOS 17+, the editor can create events without app calendar authorization. It
runs out of process, so the app cannot inspect the dismissed controller to learn
what the person saved unless the app separately has full access and refetches.

### Usage in SwiftUI

```swift
struct CalendarView: View {
    @State private var showEditor = false
    let eventStore = EKEventStore()

    var body: some View {
        Button("Add Event") { showEditor = true }
            .sheet(isPresented: $showEditor) {
                EventEditView(
                    eventStore: eventStore,
                    isPresented: $showEditor
                )
            }
    }
}
```

## Typed Change Notifications

Use `.EKEventStoreChanged` for broad compatibility. On iOS 26+, the typed
notification message is available when you want Foundation's message API:

```swift
if #available(iOS 26.0, *) {
    let observation = NotificationCenter.default.addObserver(
        of: eventStore,
        for: .changed
    ) { _ in
        fetchThisWeekEvents()
    }
}
```
