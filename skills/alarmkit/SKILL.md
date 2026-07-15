---
name: alarmkit
description: "Implement AlarmKit alarms and countdown timers for iOS and iPadOS with Lock Screen, Dynamic Island, StandBy, and paired Apple Watch system UI. Covers AlarmManager scheduling, AlarmAttributes and AlarmPresentation, system Stop and AlarmButton secondary actions, authorization, state observation, countdown widget-extension handoff, and Live Activity integration. Use when building wake-up alarms, countdown timers, or alarm-style alerts that need Apple's system alarm experience."
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
8. Observe `alarmManager.alarmUpdates` and confirm the scheduled ID reaches the expected state.
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

Use `.fixed(date)` for a one-time absolute date or `.relative` for a local clock
time with `.never` or `.weekly` repetition. Load
[Recurring Alarm Patterns](references/alarmkit-patterns.md#recurring-alarm-patterns)
for daily, weekday, weekend, and fixed-date variants.

### Schedule and Configure

```swift
let id = UUID()

let alert = AlarmPresentation.Alert(
    title: "Wake Up",
    secondaryButton: AlarmButton(
        text: "Snooze", textColor: .white, systemImageName: "bell.slash"
    ),
    secondaryButtonBehavior: .countdown
)
let presentation = AlarmPresentation(alert: alert)
struct EmptyAlarmMetadata: AlarmMetadata {}
let attributes = AlarmAttributes<EmptyAlarmMetadata>(
    presentation: presentation,
    metadata: nil,
    tintColor: .indigo
)

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

For an authorization-gated function and metadata-bearing variant, load
[Complete Alarm Scheduling Flow](references/alarmkit-patterns.md#complete-alarm-scheduling-flow).

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

### CountdownDuration

`Alarm.CountdownDuration` controls the visible countdown phases:

- `preAlert` -- seconds to count down before the alarm fires (the main countdown)
- `postAlert` -- seconds for a repeat/snooze countdown after the alarm fires

Load [Complete Countdown Timer Flow](references/alarmkit-patterns.md#complete-countdown-timer-flow)
for the timer factory, pause/resume presentation, metadata, and scheduling gate.

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

Observe `alarmUpdates` rather than maintaining an independent lifecycle. Load
[State Observation with Async Sequences](references/alarmkit-patterns.md#state-observation-with-async-sequences)
for the complete store and refresh loop.

An alarm that disappears from `alarmUpdates` is no longer scheduled with
AlarmKit. Compare against app-persisted IDs when you need to distinguish fired,
cancelled, and rescheduled alarms.

## AlarmAttributes and AlarmPresentation

`AlarmAttributes` conforms to `ActivityAttributes` and defines the static
data for the alarm's Live Activity. It is generic over a `Metadata` type
conforming to `AlarmMetadata`, which inherits `Decodable`, `Encodable`,
`Hashable`, and `Sendable`. The `metadata` value itself is optional and defaults
to `nil`.

`AlarmPresentation` supplies the required alerting content and optional
countdown/paused content. The system renders alerting UI; a widget extension can
customize countdown and paused Live Activity views with the same attributes and
presentation state. Keep metadata lightweight, use `nil` when it is unnecessary,
and share its type with the widget extension.

### AlarmPresentationState

`AlarmPresentationState` is the system-managed `ContentState` of the alarm
Live Activity. It contains the alarm ID and a `Mode` enum:

- `.alert(Alert)` -- alarm is firing, includes the scheduled time
- `.countdown(Countdown)` -- actively counting down, includes fire date and durations
- `.paused(Paused)` -- countdown paused, includes elapsed and total durations

The widget extension reads `AlarmPresentationState.mode` to decide which UI to
render in the Dynamic Island and Lock Screen for non-alerting states.

## AlarmButton

`AlarmButton` defines the text, color, and symbol for an alarm action. The
representative scheduling example above shows a standard Snooze button.

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

| Work | Owner |
|---|---|
| Authorization, scheduling/state, presentation, sound, system alarm actions | AlarmKit |
| Home Screen/Smart Stack widgets, families, timelines, reloads | `widgetkit` |
| Non-alarm Live Activity lifecycle, tokens, remote content state | `activitykit` |
| APNs, notification categories/actions, custom notification UI | `push-notifications` |

AlarmKit's alert is system-rendered on Lock Screen, Dynamic Island, StandBy, and
paired Apple Watch; only countdown/paused states use the widget extension.

For setup, name Apple-documented `NSAlarmKitUsageDescription` and `AlarmManager`
authorization. Do not require unsupported AlarmKit setup keys or
`com.apple.developer.alarmkit` unless a current Apple source documents them.
Load [Live Activity Widget Extension for Alarms](references/alarmkit-patterns.md#live-activity-widget-extension-for-alarms)
for the complete shared-attributes widget implementation.

## Common Mistakes

| Mistake | Correction |
|---|---|
| Missing usage string or authorization gate | Add `NSAlarmKitUsageDescription`; handle denial before scheduling |
| Timer used for recurrence | Use an alarm with `.weekly([...])` |
| App-owned state replaces `alarmUpdates` | Observe the system sequence and reconcile by ID |
| Intents added for standard Stop/Snooze | Omit them unless cleanup/custom behavior requires one |
| Large `AlarmMetadata` payload | Keep lightweight metadata or reference app data by ID |
| Deprecated `stopButton` initializer | Use `init(title:secondaryButton:secondaryButtonBehavior:)` |

## Review Checklist

- [ ] Setup and authorization gates pass without unsupported entitlement keys
- [ ] Alarm/timer choice, presentation, metadata, intents, snooze duration, and tint are valid
- [ ] Scheduled IDs are retained and reconciled through `alarmUpdates`; operation errors are handled
- [ ] Countdown uses the shared Widget Extension attributes and presentation state
- [ ] System-managed alert UI and adjacent-skill ownership follow the routing table
- [ ] Sound, vibration, Stop/Snooze, and state changes pass on-device testing

## References

- Patterns and code: [references/alarmkit-patterns.md](references/alarmkit-patterns.md)
- Apple docs: [AlarmKit](https://sosumi.ai/documentation/alarmkit) |
  [AlarmManager](https://sosumi.ai/documentation/alarmkit/alarmmanager) |
  [AlarmAttributes](https://sosumi.ai/documentation/alarmkit/alarmattributes) |
  [Scheduling an alarm](https://sosumi.ai/documentation/alarmkit/scheduling-an-alarm-with-alarmkit)
