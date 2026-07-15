---
name: alarmkit
description: "Implement AlarmKit alarms and countdown timers for iOS and iPadOS with Lock Screen, Dynamic Island, StandBy, and paired Apple Watch system UI. Covers AlarmManager scheduling, AlarmAttributes and AlarmPresentation, AlarmButton stop and snooze actions, authorization, state observation, countdown widget-extension handoff, and Live Activity integration. Use when building wake-up alarms, countdown timers, or alarm-style alerts that need Apple's system alarm experience."
---

# AlarmKit

Schedule prominent alarms and countdown timers that surface on the Lock Screen,
Dynamic Island, StandBy, and a paired Apple Watch when the alarm fires. AlarmKit
requires iOS 26+ / iPadOS 26+. Alarms can break through Focus and Silent mode.

AlarmKit uses ActivityKit data models for its Live Activity, but the firing alert
is system-managed alarm UI, not a general custom notification UI surface. Custom
UI belongs only to countdown and paused Live Activity states rendered by a Widget
Extension with the same `AlarmAttributes<Metadata>` and
`AlarmPresentationState` used when scheduling.

See [references/alarmkit-patterns.md](references/alarmkit-patterns.md) for complete code patterns including
authorization, scheduling, countdown timers, snooze handling, and widget setup.

```swift
import AlarmKit
```

## Contents

- [Workflow](#workflow)
- [Authorization](#authorization)
- [Alarm vs Timer Decision](#alarm-vs-timer-decision)
- [Scheduling Alarms](#scheduling-alarms)
- [Countdown Timers](#countdown-timers)
- [Alarm States](#alarm-states)
- [AlarmAttributes and AlarmPresentation](#alarmattributes-and-alarmpresentation)
- [AlarmButton](#alarmbutton)
- [Live Activity Integration](#live-activity-integration)
- [Common Mistakes](#common-mistakes)
- [Review Checklist](#review-checklist)
- [References](#references)

## Workflow

### 1. Create a new alarm or timer

1. Add `NSAlarmKitUsageDescription` to Info.plist with a user-facing string.
2. Request authorization with `AlarmManager.shared.requestAuthorization()` when the app can explain the value, or handle the first-schedule system prompt.
3. If authorization is `.denied` or not `.authorized`, show recovery UI instead of scheduling.
4. Configure `AlarmPresentation` (alert, countdown, paused states).
5. Create `AlarmAttributes` with the presentation, optional metadata, and tint color.
6. Build an `AlarmManager.AlarmConfiguration` (.alarm or .timer).
7. Schedule with `AlarmManager.shared.schedule(id:configuration:)`.
8. Observe state changes via `alarmManager.alarmUpdates`.
9. If using countdown, add a Widget Extension target with an `ActivityConfiguration` for the same `AlarmAttributes<Metadata>` type.

### 2. Review existing alarm code

Run through the Review Checklist at the end of this document.

## Authorization

AlarmKit requires user authorization. Request early when the app can explain the
value, or let AlarmKit prompt automatically on first schedule. If authorization
is not granted after the explicit or automatic prompt, alarms are not scheduled
and will not alert.

```swift
let manager = AlarmManager.shared

// Request authorization explicitly
let state = try await manager.requestAuthorization()
guard state == .authorized else { return }

// Check current state synchronously
let current = manager.authorizationState // .authorized, .denied, .notDetermined

// Observe authorization changes
for await state in manager.authorizationUpdates {
    switch state {
    case .authorized: print("Alarms enabled")
    case .denied:     print("Alarms disabled")
    case .notDetermined: break
    @unknown default: break
    }
}
```

## Alarm vs Timer Decision

| Feature | Alarm (`.alarm`) | Timer (`.timer`) |
|---|---|---|
| Fires at | Specific time (schedule) | After duration elapses |
| Countdown UI | Optional | Always shown |
| Recurring | Yes (weekly days) | No |
| Use case | Wake-up, scheduled reminders | Cooking, workout intervals |

Use `.alarm(schedule:...)` when firing at a clock time. Use `.timer(duration:...)`
when firing after a duration from now.

## Scheduling Alarms

### Alarm.Schedule

Alarms use `Alarm.Schedule` to define when they fire.

```swift
// Fixed: fire at an exact Date (one-time only)
let fixed: Alarm.Schedule = .fixed(myDate)

// Relative one-time: fire at 7:30 AM in device time zone, no repeat
let oneTime: Alarm.Schedule = .relative(.init(
    time: .init(hour: 7, minute: 30),
    repeats: .never
))

// Recurring: fire at 6:00 AM on weekdays
let weekday: Alarm.Schedule = .relative(.init(
    time: .init(hour: 6, minute: 0),
    repeats: .weekly([.monday, .tuesday, .wednesday, .thursday, .friday])
))
```

### Schedule and Configure

```swift
let id = UUID()

let snooze = Alarm.CountdownDuration(preAlert: nil, postAlert: 300)
let configuration = AlarmManager.AlarmConfiguration(
    countdownDuration: snooze,
    schedule: .relative(.init(
        time: .init(hour: 7, minute: 0),
        repeats: .never
    )),
    attributes: attributes,
    sound: .default
)

let alarm = try await AlarmManager.shared.schedule(
    id: id,
    configuration: configuration
)
```

`stopIntent` and `secondaryIntent` default to `nil`. Omit `stopIntent` for
AlarmKit's standard system Stop behavior; provide it only when Stop must run app
cleanup, custom stop behavior, or other side effects. Omit `secondaryIntent` for
ordinary Snooze/Repeat with `secondaryButtonBehavior: .countdown` and
`Alarm.CountdownDuration.postAlert`; provide it only for `.custom` secondary
behavior or app cleanup/custom behavior.

### Alarm State Transitions

```text
cancel(id:)
    |
scheduled --> countdown --> alerting
    |             |             |
    |         pause(id:)    stop(id:) / countdown(id:)
    |             |
    |         paused ----> countdown (via resume(id:))
    |
cancel(id:) removes from system entirely
```

- `cancel(id:)` -- remove the alarm completely, including repeating alarms
- `pause(id:)` -- pause a counting-down alarm; throws from other states
- `resume(id:)` -- resume a paused alarm; throws from other states
- `stop(id:)` -- stop the alarm; one-shot alarms are removed, repeating alarms reschedule
- `countdown(id:)` -- restart countdown from alerting state (snooze); throws from other states

## Countdown Timers

Timers fire after a duration and always show a countdown UI. Use
`Alarm.CountdownDuration` to control pre-alert and post-alert durations.

```swift
// Simple timer: 5-minute countdown, no snooze
let timerConfig = AlarmManager.AlarmConfiguration.timer(
    duration: 300,
    attributes: attributes,
    stopIntent: StopTimerIntent(timerID: id.uuidString),
    sound: .default
)

let alarm = try await AlarmManager.shared.schedule(
    id: UUID(),
    configuration: timerConfig
)
```

### CountdownDuration

`Alarm.CountdownDuration` controls the visible countdown phases:

- `preAlert` -- seconds to count down before the alarm fires (the main countdown)
- `postAlert` -- seconds for a repeat/snooze countdown after the alarm fires

```swift
let countdown = Alarm.CountdownDuration(
    preAlert: 600,   // 10-minute countdown before alert
    postAlert: 300   // 5-minute snooze countdown if user taps Repeat
)

let config = AlarmManager.AlarmConfiguration(
    countdownDuration: countdown,
    schedule: .relative(.init(
        time: .init(hour: 8, minute: 0),
        repeats: .never
    )),
    attributes: attributes,
    sound: .default
)
```

## Alarm States

Each `Alarm` has a `state` property reflecting its current lifecycle position.

| State | Meaning |
|---|---|
| `.scheduled` | Scheduled and ready to alert at the appropriate time |
| `.countdown` | Actively counting down (timer or pre-alert phase) |
| `.paused` | Countdown paused by user or app |
| `.alerting` | Alarm is firing -- sound playing, UI prominent |

### Observing State Changes

`AlarmManager.shared.alarms` is a throwing getter for the current daemon
snapshot. Use `try`, and either propagate the error or wrap launch refresh in
`do/catch` before relying on the snapshot.

```swift
let manager = AlarmManager.shared

// Get all current alarms
let alarms = try manager.alarms

// Observe changes as an async sequence
for await updatedAlarms in manager.alarmUpdates {
    for alarm in updatedAlarms {
        switch alarm.state {
        case .scheduled:  print("\(alarm.id) waiting")
        case .countdown:  print("\(alarm.id) counting down")
        case .paused:     print("\(alarm.id) paused")
        case .alerting:   print("\(alarm.id) alerting!")
        @unknown default: break
        }
    }
}
```

An alarm that disappears from `alarmUpdates` is no longer scheduled with
AlarmKit. Compare against app-persisted IDs when you need to distinguish fired,
cancelled, and rescheduled alarms.

## AlarmAttributes and AlarmPresentation

`AlarmAttributes` conforms to `ActivityAttributes` and defines the static
data for the alarm's Live Activity. It is generic over a `Metadata` type
conforming to `AlarmMetadata`, which inherits `Decodable`, `Encodable`,
`Hashable`, and `Sendable`. The `metadata` value itself is optional and defaults
to `nil`.

### AlarmPresentation

Defines the UI content for each alarm state. The system renders the alerting UI,
while a widget extension can customize countdown and paused Live Activity views
with the same attributes and presentation state.

```swift
// Alert state (required) -- shown when alarm is firing
let alert = AlarmPresentation.Alert(
    title: "Wake Up",
    secondaryButton: AlarmButton(
        text: "Snooze",
        textColor: .white,
        systemImageName: "bell.slash"
    ),
    secondaryButtonBehavior: .countdown  // snooze restarts countdown
)

// Countdown state (optional) -- shown during pre-alert countdown
let countdown = AlarmPresentation.Countdown(
    title: "Morning Alarm",
    pauseButton: AlarmButton(
        text: "Pause",
        textColor: .orange,
        systemImageName: "pause.fill"
    )
)

// Paused state (optional) -- shown when countdown is paused
let paused = AlarmPresentation.Paused(
    title: "Paused",
    resumeButton: AlarmButton(
        text: "Resume",
        textColor: .green,
        systemImageName: "play.fill"
    )
)

let presentation = AlarmPresentation(
    alert: alert,
    countdown: countdown,
    paused: paused
)
```

### AlarmAttributes

```swift
struct CookingMetadata: AlarmMetadata {
    var recipeName: String
    var stepNumber: Int
}

let attributes = AlarmAttributes(
    presentation: presentation,
    metadata: CookingMetadata(recipeName: "Pasta", stepNumber: 3),
    tintColor: .blue
)

let attributesWithoutMetadata = AlarmAttributes<EmptyAlarmMetadata>(
    presentation: presentation,
    metadata: nil,
    tintColor: .blue
)

struct EmptyAlarmMetadata: AlarmMetadata {}
```

### AlarmPresentationState

`AlarmPresentationState` is the system-managed `ContentState` of the alarm
Live Activity. It contains the alarm ID and a `Mode` enum:

- `.alert(Alert)` -- alarm is firing, includes the scheduled time
- `.countdown(Countdown)` -- actively counting down, includes fire date and durations
- `.paused(Paused)` -- countdown paused, includes elapsed and total durations

The widget extension reads `AlarmPresentationState.mode` to decide which UI to
render in the Dynamic Island and Lock Screen for non-alerting states.

## AlarmButton

`AlarmButton` defines the appearance of action buttons in the alarm UI.

```swift
let stopButton = AlarmButton(
    text: "Stop",
    textColor: .red,
    systemImageName: "stop.fill"
)

let snoozeButton = AlarmButton(
    text: "Snooze",
    textColor: .white,
    systemImageName: "bell.slash"
)
```

### Secondary Button Behavior

The secondary button on the alert UI has two behaviors:

| Behavior | Effect |
|---|---|
| `.countdown` | Restarts a countdown using `postAlert` duration (snooze) |
| `.custom` | Triggers the `secondaryIntent` (e.g., open app) |

## Live Activity Integration

AlarmKit alarms appear as Live Activities on the Lock Screen, Dynamic Island,
StandBy, and on a paired Apple Watch when the alarm fires. The system manages
the alerting UI. For countdown and paused states, add a Widget Extension target
whose `ActivityConfiguration` uses the same `AlarmAttributes<Metadata>` type
used when scheduling the alarm.

A widget extension is expected if your alarm uses countdown presentation. Keep
that lightweight metadata type available to both the app and widget extension.
Without the extension, alarms may be dismissed unexpectedly or fail to alert,
though the system can still show a fallback countdown UI in limited cases such
as after a device restart before first unlock.

AlarmKit owns authorization, `AlarmManager` scheduling/state, alarm attributes and presentation, sound, and system Stop/Repeat/Open App actions. The firing alert is system-rendered; only countdown and paused states use the widget extension's `ActivityConfiguration`. Supported alarm surfaces are Lock Screen, Dynamic Island, StandBy, and paired Apple Watch—not Smart Stack.

Route ordinary Home Screen or Smart Stack widgets, `WidgetFamily` layout choices,
widget timelines, and `WidgetCenter` reload policy to `widgetkit`. Route non-alarm
Live Activity lifecycle (`Activity.request`, `update`, `end`), push-to-start
tokens, per-activity update tokens, and remote Live Activity `content-state`
payload contracts to `activitykit`. Route generic APNs, `UNUserNotificationCenter`,
notification categories/actions, and custom notification UI to `push-notifications`
unless app code ultimately calls `AlarmManager`.

For setup, name Apple-documented `NSAlarmKitUsageDescription` and `AlarmManager`
authorization. Do not require unsupported AlarmKit setup keys or
`com.apple.developer.alarmkit` unless a current Apple source documents them.

```swift
struct AlarmWidgetBundle: WidgetBundle {
    var body: some Widget {
        AlarmActivityWidget()
    }
}

struct AlarmActivityWidget: Widget {
    var body: some WidgetConfiguration {
        ActivityConfiguration(for: AlarmAttributes<CookingMetadata>.self) { context in
            // Lock Screen presentation for countdown/paused states
            AlarmLockScreenView(context: context)
        } dynamicIsland: { context in
            DynamicIsland {
                DynamicIslandExpandedRegion(.center) {
                    Text(context.attributes.presentation.alert.title)
                }
                DynamicIslandExpandedRegion(.bottom) {
                    // Show countdown or paused info based on mode
                    AlarmExpandedView(state: context.state)
                }
            } compactLeading: {
                Image(systemName: "alarm.fill")
            } compactTrailing: {
                AlarmCompactTrailing(state: context.state)
            } minimal: {
                Image(systemName: "alarm.fill")
            }
        }
    }
}
```

## Common Mistakes

**DON'T:** Forget `NSAlarmKitUsageDescription` in Info.plist.
**DO:** Add a descriptive usage string. Without it, AlarmKit cannot schedule alarms at all.

**DON'T:** Skip authorization and assume alarms will schedule.
**DO:** Call `requestAuthorization()` early and handle `.denied` gracefully.

**DON'T:** Use `.timer` when you need a recurring schedule.
**DO:** Use `.alarm` with `.weekly([...])` for recurring alarms. Timers are one-shot.

**DON'T:** Omit the widget extension when using countdown presentation.
**DO:** Add a widget extension target for countdown/paused Live Activity UI.
**Why:** Without a widget extension, alarms may be dismissed before they alert; the system fallback is limited.

**DON'T:** Ignore `alarmUpdates` and track alarm state manually.
**DO:** Observe `alarmManager.alarmUpdates` to stay synchronized with the system.
**Why:** Alarm state can change while your app is backgrounded.

**DON'T:** Treat `stopIntent` and `secondaryIntent` as mandatory for every alarm.
**DO:** Omit them for standard system Stop/Snooze; provide intents only for app cleanup or custom behavior.

**DON'T:** Fold ordinary widgets, generic Live Activities, or push/local notification behavior into AlarmKit.
**DO:** Route Home Screen/Smart Stack widgets, `WidgetFamily`, timelines, and `WidgetCenter` reloads to `widgetkit`; route non-alarm `Activity.request`/`update`/`end`, push-to-start, update tokens, and remote `content-state` payloads to `activitykit`; route generic APNs, `UNUserNotificationCenter`, and notification categories/actions to `push-notifications` unless app code ultimately calls `AlarmManager`.

**DON'T:** Store large data in `AlarmMetadata`.
**DO:** Keep metadata lightweight or pass `nil`. Store large data in your app and reference by ID.

**DON'T:** Use deprecated `stopButton` parameter on `AlarmPresentation.Alert`.
**DO:** Use the current `init(title:secondaryButton:secondaryButtonBehavior:)` initializer.

## Review Checklist

- [ ] `NSAlarmKitUsageDescription` present in Info.plist with non-empty string
- [ ] Authorization requested and `.denied` state handled in UI
- [ ] `AlarmPresentation` covers all relevant states (alert, countdown, paused)
- [ ] Widget Extension target uses `ActivityConfiguration` for the same `AlarmAttributes<Metadata>` type if countdown presentation is used
- [ ] `AlarmAttributes` metadata is lightweight, optional when unused, and conforms to `AlarmMetadata`
- [ ] Alarm ID stored for later cancel/pause/resume/stop operations
- [ ] `alarmUpdates` async sequence observed to track state changes
- [ ] `stopIntent` and `secondaryIntent` omitted for standard system Stop/Snooze and provided only for cleanup/custom behavior
- [ ] `postAlert` duration set on `CountdownDuration` if snooze (`.countdown` behavior) is used
- [ ] AlarmKit ownership is limited to authorization, `AlarmManager` scheduling/state, `AlarmAttributes`, `AlarmPresentation`, `AlarmPresentationState`, sound, and alarm actions
- [ ] Alerting UI is described as system-managed alarm UI, not a general custom notification UI surface
- [ ] Custom countdown/paused UI is routed to a Widget Extension `ActivityConfiguration` using the same `AlarmAttributes<Metadata>` and `AlarmPresentationState`
- [ ] Boundary routing is explicit: Home Screen/Smart Stack widgets, `WidgetFamily`, timelines, and `WidgetCenter` reloads go to `widgetkit`; non-alarm `Activity.request`/`update`/`end`, push-to-start/update tokens, and remote `content-state` payloads go to `activitykit`; generic APNs/`UNUserNotificationCenter` goes to `push-notifications`
- [ ] Setup is source-grounded: `NSAlarmKitUsageDescription` and authorization are named; unsupported keys such as `com.apple.developer.alarmkit` are not required unless Apple documents them
- [ ] Tint color set on `AlarmAttributes` to differentiate from other apps
- [ ] Error handling for `AlarmManager.AlarmError.maximumLimitReached`
- [ ] Tested on device (alarm sound/vibration differs from Simulator)

## References

- Patterns and code: [references/alarmkit-patterns.md](references/alarmkit-patterns.md)
- Apple docs: [AlarmKit](https://sosumi.ai/documentation/alarmkit) |
  [AlarmManager](https://sosumi.ai/documentation/alarmkit/alarmmanager) |
  [AlarmAttributes](https://sosumi.ai/documentation/alarmkit/alarmattributes) |
  [Scheduling an alarm](https://sosumi.ai/documentation/alarmkit/scheduling-an-alarm-with-alarmkit)
