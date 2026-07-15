# AlarmKit Patterns

Complete implementation patterns for AlarmKit alarms, countdown timers,
authorization, state observation, and Live Activity integration. All patterns
target iOS 26+ / iPadOS 26+ with Swift 6.3. The alerting UI is system-managed;
countdown and paused states use a widget extension for custom Live Activity UI.

## Contents
- Complete Alarm Scheduling Flow
- Complete Countdown Timer Flow
- Authorization Manager
- State Observation with Async Sequences
- Live Activity Widget Extension for Alarms
- Recurring Alarm Patterns
- Snooze and Dismiss Handling
- Info.plist Configuration
- Error Handling
- Apple Documentation Links

## Complete Alarm Scheduling Flow

End-to-end pattern for scheduling a wake-up alarm with snooze support.

```swift
import AlarmKit

struct WakeUpMetadata: AlarmMetadata {
    var label: String
}

@MainActor
func scheduleWakeUpAlarm(
    hour: Int, minute: Int, label: String
) async throws -> Alarm {
    let manager = AlarmManager.shared
    let authState = try await manager.requestAuthorization()
    guard authState == .authorized else { throw AlarmSchedulingError.notAuthorized }

    let alert = AlarmPresentation.Alert(
        title: LocalizedStringResource(stringLiteral: label),
        secondaryButton: AlarmButton(
            text: "Snooze", textColor: .white, systemImageName: "bell.slash"
        ),
        secondaryButtonBehavior: .countdown
    )
    let presentation = AlarmPresentation(alert: alert)
    let attributes = AlarmAttributes(
        presentation: presentation,
        metadata: WakeUpMetadata(label: label),
        tintColor: .indigo
    )

    let id = UUID()
    let snooze = Alarm.CountdownDuration(preAlert: nil, postAlert: 300)
    let config = AlarmManager.AlarmConfiguration(
        countdownDuration: snooze,
        schedule: .relative(.init(
            time: .init(hour: hour, minute: minute), repeats: .never
        )),
        attributes: attributes,
        sound: .default
    )
    return try await manager.schedule(id: id, configuration: config)
}

enum AlarmSchedulingError: Error {
    case notAuthorized
}
```

## Complete Countdown Timer Flow

End-to-end pattern for a countdown timer with pause/resume support.

```swift
import AlarmKit

struct CookingTimerMetadata: AlarmMetadata {
    var recipeName: String
    var stepDescription: String
}

@MainActor
func startCookingTimer(
    durationSeconds: TimeInterval, recipeName: String, step: String
) async throws -> Alarm {
    let manager = AlarmManager.shared
    let authState = try await manager.requestAuthorization()
    guard authState == .authorized else { throw AlarmSchedulingError.notAuthorized }

    let alert = AlarmPresentation.Alert(
        title: LocalizedStringResource(stringLiteral: "\(recipeName): \(step)"),
        secondaryButton: nil, secondaryButtonBehavior: nil
    )
    let countdown = AlarmPresentation.Countdown(
        title: LocalizedStringResource(stringLiteral: recipeName),
        pauseButton: AlarmButton(
            text: "Pause", textColor: .orange, systemImageName: "pause.fill"
        )
    )
    let paused = AlarmPresentation.Paused(
        title: "Paused",
        resumeButton: AlarmButton(
            text: "Resume", textColor: .green, systemImageName: "play.fill"
        )
    )
    let presentation = AlarmPresentation(
        alert: alert, countdown: countdown, paused: paused
    )
    let attributes = AlarmAttributes(
        presentation: presentation,
        metadata: CookingTimerMetadata(recipeName: recipeName, stepDescription: step),
        tintColor: .orange
    )

    let id = UUID()
    let config = AlarmManager.AlarmConfiguration.timer(
        duration: durationSeconds,
        attributes: attributes,
        sound: .default
    )
    return try await manager.schedule(id: id, configuration: config)
}
```

## Authorization Manager

Observable pattern for centralized authorization management.

```swift
import AlarmKit
import Observation

@Observable
@MainActor
final class AlarmAuthorizationManager {
    private let manager = AlarmManager.shared
    private(set) var isAuthorized = false
    private(set) var authState: AlarmManager.AuthorizationState = .notDetermined

    init() {
        authState = manager.authorizationState
        isAuthorized = authState == .authorized
    }

    func requestIfNeeded() async throws -> Bool {
        guard authState == .notDetermined else { return isAuthorized }
        let state = try await manager.requestAuthorization()
        authState = state
        isAuthorized = state == .authorized
        return isAuthorized
    }

    func observeAuthorizationChanges() async {
        for await state in manager.authorizationUpdates {
            authState = state
            isAuthorized = state == .authorized
        }
    }
}

// Usage in SwiftUI
struct AlarmSettingsView: View {
    @State private var authManager = AlarmAuthorizationManager()

    var body: some View {
        Group {
            if authManager.isAuthorized {
                Text("Alarms are enabled")
            } else if authManager.authState == .denied {
                ContentUnavailableView(
                    "Alarms Disabled", systemImage: "alarm.waves.left.and.right",
                    description: Text("Enable in Settings > Your App > Alarms & Timers.")
                )
            } else {
                Button("Enable Alarms") {
                    Task { try? await authManager.requestIfNeeded() }
                }
            }
        }
        .task { await authManager.observeAuthorizationChanges() }
    }
}
```

## State Observation with Async Sequences

Pattern for tracking all alarms and reacting to state changes.

```swift
import AlarmKit
import Observation

@Observable
@MainActor
final class AlarmStore {
    private let manager = AlarmManager.shared
    private(set) var alarms: [Alarm] = []

    func refreshAlarms() throws {
        alarms = try manager.alarms
    }

    func startObserving() async {
        for await updatedAlarms in manager.alarmUpdates {
            alarms = updatedAlarms
        }
    }

    func alarm(for id: UUID) -> Alarm? { alarms.first { $0.id == id } }
    func alarms(in state: Alarm.State) -> [Alarm] { alarms.filter { $0.state == state } }

    func cancel(_ id: Alarm.ID) throws { try manager.cancel(id: id) }
    func pause(_ id: Alarm.ID) throws { try manager.pause(id: id) }
    func resume(_ id: Alarm.ID) throws { try manager.resume(id: id) }
    func stop(_ id: Alarm.ID) throws { try manager.stop(id: id) }
    func snooze(_ id: Alarm.ID) throws { try manager.countdown(id: id) }
}

// Usage in SwiftUI
struct AlarmListView: View {
    @State private var store = AlarmStore()

    var body: some View {
        List(store.alarms, id: \.id) { alarm in
            HStack {
                Text(alarm.id.uuidString.prefix(8)).font(.headline)
                Spacer()
                switch alarm.state {
                case .scheduled:
                    Button("Cancel", role: .destructive) { try? store.cancel(alarm.id) }
                case .countdown:
                    Button("Pause") { try? store.pause(alarm.id) }
                case .paused:
                    Button("Resume") { try? store.resume(alarm.id) }
                case .alerting:
                    Button("Stop") { try? store.stop(alarm.id) }
                @unknown default:
                    EmptyView()
                }
            }
        }
        .task {
            try? store.refreshAlarms()
            await store.startObserving()
        }
    }
}
```

## Live Activity Widget Extension for Alarms

Widget extension that renders countdown and paused states. AlarmKit expects this
when your alarm uses countdown presentation; the system fallback countdown UI is
limited to cases such as after restart before first unlock.

```swift
import WidgetKit
import SwiftUI
import AlarmKit

// MARK: - Widget bundle

struct AlarmWidgetBundle: WidgetBundle {
    var body: some Widget {
        AlarmLiveActivityWidget()
    }
}

// MARK: - Live Activity configuration

struct AlarmLiveActivityWidget: Widget {
    var body: some WidgetConfiguration {
        ActivityConfiguration(for: AlarmAttributes<CookingTimerMetadata>.self) { context in
            AlarmLockScreenView(context: context)
        } dynamicIsland: { context in
            DynamicIsland {
                DynamicIslandExpandedRegion(.leading) {
                    Image(systemName: "alarm.fill")
                        .font(.title2)
                        .foregroundStyle(context.attributes.tintColor)
                }
                DynamicIslandExpandedRegion(.trailing) {
                    AlarmCountdownText(state: context.state)
                        .font(.title3.monospacedDigit())
                }
                DynamicIslandExpandedRegion(.center) {
                    Text(context.attributes.metadata?.recipeName ?? "Timer")
                        .font(.headline)
                }
                DynamicIslandExpandedRegion(.bottom) {
                    if let step = context.attributes.metadata?.stepDescription {
                        Text(step).font(.subheadline).foregroundStyle(.secondary)
                    }
                }
            } compactLeading: {
                Image(systemName: "alarm.fill").foregroundStyle(context.attributes.tintColor)
            } compactTrailing: {
                AlarmCountdownText(state: context.state)
                    .frame(width: 44).monospacedDigit()
            } minimal: {
                Image(systemName: "alarm.fill").foregroundStyle(context.attributes.tintColor)
            }
            .keylineTint(context.attributes.tintColor)
        }
    }
}

// MARK: - Lock Screen view

struct AlarmLockScreenView: View {
    let context: ActivityViewContext<AlarmAttributes<CookingTimerMetadata>>

    var body: some View {
        VStack(alignment: .leading) {
            HStack {
                Image(systemName: "alarm.fill")
                    .foregroundStyle(context.attributes.tintColor)
                Text(context.attributes.metadata?.recipeName ?? "Timer")
                    .font(.headline)
                Spacer()
                AlarmCountdownText(state: context.state)
                    .font(.title3.monospacedDigit().bold())
            }

            switch context.state.mode {
            case .countdown(let info):
                ProgressView(
                    value: info.previouslyElapsedDuration,
                    total: info.totalCountdownDuration
                )
                .tint(context.attributes.tintColor)
            case .paused:
                Label("Paused", systemImage: "pause.fill")
                    .font(.subheadline).foregroundStyle(.secondary)
            case .alert:
                EmptyView()  // System handles alerting UI
            @unknown default:
                EmptyView()
            }
        }
        .padding()
    }
}

// MARK: - Helper views

struct AlarmCountdownText: View {
    let state: AlarmPresentationState

    var body: some View {
        switch state.mode {
        case .countdown(let info):
            Text(info.fireDate, style: .timer)
        case .paused(let info):
            let remaining = info.totalCountdownDuration - info.previouslyElapsedDuration
            Text(Duration.seconds(remaining), format: .time(pattern: .minuteSecond))
        case .alert(let info):
            Text("\(info.time.hour):\(String(format: "%02d", info.time.minute))")
        @unknown default:
            Text("--:--")
        }
    }
}
```

## Recurring Alarm Patterns

```swift
// Daily alarm (every day)
let dailySchedule = Alarm.Schedule.relative(.init(
    time: .init(hour: 7, minute: 0),
    repeats: .weekly([.sunday, .monday, .tuesday, .wednesday,
                      .thursday, .friday, .saturday])
))

// Weekday-only alarm
let weekdaySchedule = Alarm.Schedule.relative(.init(
    time: .init(hour: 6, minute: 30),
    repeats: .weekly([.monday, .tuesday, .wednesday, .thursday, .friday])
))

// Weekend alarm
let weekendSchedule = Alarm.Schedule.relative(.init(
    time: .init(hour: 9, minute: 0),
    repeats: .weekly([.saturday, .sunday])
))

// One-time alarm at a specific Date
let targetDate = Calendar.current.date(
    from: DateComponents(year: 2026, month: 6, day: 15, hour: 14, minute: 30)
)!
let fixedSchedule = Alarm.Schedule.fixed(targetDate)
```

## Snooze and Dismiss Handling

Pattern for alarm with snooze (countdown behavior) and custom secondary action.

### Snooze with countdown restart

```swift
func scheduleAlarmWithSnooze(
    hour: Int, minute: Int, snoozeDurationSeconds: TimeInterval
) async throws -> Alarm {
    let id = UUID()
    let alert = AlarmPresentation.Alert(
        title: "Good Morning",
        secondaryButton: AlarmButton(
            text: "Snooze 5 min", textColor: .white, systemImageName: "zzz"
        ),
        secondaryButtonBehavior: .countdown  // tapping Snooze restarts countdown
    )
    // postAlert defines the snooze duration
    let countdown = Alarm.CountdownDuration(
        preAlert: nil, postAlert: snoozeDurationSeconds
    )
    let countdownPresentation = AlarmPresentation.Countdown(
        title: "Snoozing...", pauseButton: nil
    )
    let presentation = AlarmPresentation(
        alert: alert, countdown: countdownPresentation
    )
    let attributes = AlarmAttributes(
        presentation: presentation,
        metadata: nil as WakeUpMetadata?,
        tintColor: .purple
    )
    let config = AlarmManager.AlarmConfiguration(
        countdownDuration: countdown,
        schedule: .relative(.init(
            time: .init(hour: hour, minute: minute), repeats: .never
        )),
        attributes: attributes,
        sound: .default
    )
    return try await AlarmManager.shared.schedule(id: id, configuration: config)
}
```

### Custom secondary action (open app)

Use `.custom` behavior to trigger the `secondaryIntent` instead of restarting
a countdown. The intent opens the app or performs custom logic.

```swift
struct OpenAppIntent: LiveActivityIntent {
    static var title: LocalizedStringResource = "Open App"
    func perform() async throws -> some IntentResult { .result() }
}

func scheduleAlarmWithOpenAction(hour: Int, minute: Int) async throws -> Alarm {
    let id = UUID()
    let alert = AlarmPresentation.Alert(
        title: "Medication Reminder",
        secondaryButton: AlarmButton(
            text: "Open", textColor: .blue, systemImageName: "pill.fill"
        ),
        secondaryButtonBehavior: .custom  // triggers secondaryIntent
    )
    let presentation = AlarmPresentation(alert: alert)
    let attributes = AlarmAttributes<WakeUpMetadata>(
        presentation: presentation, metadata: nil, tintColor: .blue
    )
    let config = AlarmManager.AlarmConfiguration.alarm(
        schedule: .relative(.init(
            time: .init(hour: hour, minute: minute), repeats: .never
        )),
        attributes: attributes,
        secondaryIntent: OpenAppIntent(),
        sound: .default
    )
    return try await AlarmManager.shared.schedule(id: id, configuration: config)
}
```

## Info.plist Configuration

### Required key

```xml
<key>NSAlarmKitUsageDescription</key>
<string>We schedule alerts for alarms and timers you create.</string>
```

This key is **mandatory**. If missing or empty, `schedule(id:configuration:)`
will fail and no alarms can be created by the app.

### Countdown UI setup

If you support countdown presentation, add a widget extension target for the
custom Live Activity UI. Keep `NSAlarmKitUsageDescription` in the host app's
Info.plist; Apple does not document `NSSupportsLiveActivities` as an AlarmKit
setup key.

## Error Handling

```swift
import AlarmKit

func scheduleAlarmSafely<Metadata: AlarmMetadata>(
    id: UUID,
    configuration: AlarmManager.AlarmConfiguration<Metadata>
) async {
    guard AlarmManager.shared.authorizationState == .authorized else {
        print("Not authorized -- request authorization first")
        return
    }
    do {
        let alarm = try await AlarmManager.shared.schedule(
            id: id, configuration: configuration
        )
        print("Scheduled alarm: \(alarm.id), state: \(alarm.state)")
    } catch let error as AlarmManager.AlarmError {
        switch error {
        case .maximumLimitReached:
            print("Too many alarms -- cancel an existing one first")
        @unknown default:
            print("AlarmKit error: \(error)")
        }
    } catch {
        print("Unexpected error: \(error)")
    }
}

// State transition helpers -- each throws if alarm is in wrong state
func cancelAlarmSafely(id: Alarm.ID) {
    do { try AlarmManager.shared.cancel(id: id) }
    catch { print("Failed to cancel: \(error)") }
}

func pauseAlarmSafely(id: Alarm.ID) {
    // Only valid when alarm is in .countdown state
    do { try AlarmManager.shared.pause(id: id) }
    catch { print("Cannot pause: \(error)") }
}
```

## Apple Documentation Links

- [AlarmKit](https://sosumi.ai/documentation/alarmkit)
- [AlarmManager](https://sosumi.ai/documentation/alarmkit/alarmmanager)
- [AlarmAttributes](https://sosumi.ai/documentation/alarmkit/alarmattributes)
- [AlarmPresentation](https://sosumi.ai/documentation/alarmkit/alarmpresentation)
- [AlarmPresentationState](https://sosumi.ai/documentation/alarmkit/alarmpresentationstate)
- [AlarmButton](https://sosumi.ai/documentation/alarmkit/alarmbutton)
- [Alarm](https://sosumi.ai/documentation/alarmkit/alarm)
- [Alarm.Schedule](https://sosumi.ai/documentation/alarmkit/alarm/schedule-swift.enum)
- [Alarm.CountdownDuration](https://sosumi.ai/documentation/alarmkit/alarm/countdownduration-swift.struct)
- [Scheduling an alarm with AlarmKit](https://sosumi.ai/documentation/alarmkit/scheduling-an-alarm-with-alarmkit)
