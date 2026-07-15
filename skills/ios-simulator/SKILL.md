---
name: ios-simulator
description: "Manages iOS Simulator devices and app tests with xcrun simctl: lifecycle, install/launch, push and location simulation, privacy permissions, deep links, status-bar overrides, screenshots/video, log streaming, app containers, and targetEnvironment(simulator). Use when scripting Simulator workflows, debugging CoreSimulator boot failures, or deciding which hardware, performance, networking, memory-pressure, and security behaviors require a physical device."
---

# iOS Simulator

Load [the simctl command reference](references/simctl-commands.md) when you need
complete command tables, JSON parsing, privacy/status-bar values, Logger filter
setup, or boot recovery commands.

## Contents

- [Device Lifecycle](#device-lifecycle)
- [App Install and Launch](#app-install-and-launch)
- [Testing Workflows](#testing-workflows)
- [Screenshot and Video Recording](#screenshot-and-video-recording)
- [Log Streaming](#log-streaming)
- [Compile-Time Simulator Detection](#compile-time-simulator-detection)
- [Simulator Limitations](#simulator-limitations)
- [Common Mistakes](#common-mistakes)
- [Review Checklist](#review-checklist)
- [References](#references)

## Device Lifecycle

### Listing Devices and Runtimes

```bash
# List all available simulators grouped by runtime
xcrun simctl list devices available

# List installed runtimes
xcrun simctl list runtimes

# List only booted devices
xcrun simctl list devices booted

# JSON output for scripting
xcrun simctl list -j devices available
```

Parse JSON output to find a specific device programmatically. See [references/simctl-commands.md](references/simctl-commands.md) for `jq` parsing examples.

### Creating a Device

```bash
# Find available device types and runtimes
xcrun simctl list devicetypes
xcrun simctl list runtimes

# Create a device — returns the new UDID
xcrun simctl create "My Test Phone" "iPhone 16 Pro" "com.apple.CoreSimulator.SimRuntime.iOS-18-4"
```

Device types and runtime identifiers in examples throughout this skill are illustrative. Run `simctl list devicetypes` and `simctl list runtimes` to find the identifiers available on your system.

Use the returned UDID for subsequent commands.

### Boot, Shutdown, Erase, Delete

```bash
# Boot a specific device
xcrun simctl boot <UDID>

# Boot if needed and wait until the device is ready
xcrun simctl bootstatus <UDID> -b

# Shutdown a running device
xcrun simctl shutdown <UDID>

# Factory reset — wipes all data, keeps the device
xcrun simctl erase <UDID>

# Delete a specific device
xcrun simctl delete <UDID>

# Delete all devices not available in the current Xcode
xcrun simctl delete unavailable

# Shutdown everything
xcrun simctl shutdown all
```

Use `booted` as a UDID shorthand when exactly one simulator is running:

```bash
xcrun simctl shutdown booted
```

If multiple simulators are booted, `booted` picks one of them non-deterministically. Prefer explicit UDIDs when running parallel simulators.

In scripts and CI, `xcrun simctl bootstatus <UDID> -b` is the canonical
boot-and-readiness gate before install, launch, push, or location commands.

## App Install and Launch

### Installing an App

```bash
# Build for simulator first
xcodebuild build \
    -scheme MyApp \
    -destination 'platform=iOS Simulator,name=iPhone 16 Pro' \
    -derivedDataPath build/

# Boot and wait for SpringBoard/services before install
xcrun simctl bootstatus <UDID> -b

# Install the .app bundle
xcrun simctl install <UDID> build/Build/Products/Debug-iphonesimulator/MyApp.app
```

The path must point to a `.app` directory built for the simulator architecture, not a `.ipa` file.

### Launching and Terminating

```bash
# Launch by bundle ID
xcrun simctl launch booted com.example.MyApp

# Launch and stream stdout/stderr to the terminal
xcrun simctl launch --console booted com.example.MyApp

# Pass launch arguments
xcrun simctl launch booted com.example.MyApp --reset-onboarding -AppleLanguages "(fr)"

# Terminate a running app
xcrun simctl terminate booted com.example.MyApp
```

`--console` is useful for debugging — it shows `print()` and `os_log` output directly in the terminal.

### App Container Paths

```bash
# App bundle location
xcrun simctl get_app_container booted com.example.MyApp app

# Data container (Documents, Library, tmp)
xcrun simctl get_app_container booted com.example.MyApp data

# Shared app group container
xcrun simctl get_app_container booted com.example.MyApp group.com.example.shared
```

## Testing Workflows

### Push Notification Simulation

Create a JSON payload file:

```json
{
    "aps": {
        "alert": {
            "title": "New Message",
            "body": "You have a new message from Alice"
        },
        "badge": 3,
        "sound": "default"
    },
    "customKey": "customValue"
}
```

Send it to the Simulator:

```bash
# Send push payload from file
xcrun simctl push booted com.example.MyApp payload.json

# Pipe payload from stdin
echo '{"aps":{"alert":"Quick test"}}' | xcrun simctl push booted com.example.MyApp -
```

This tests local payload handling and notification UI, not APNs delivery.

### Location Simulation

```bash
# Set a fixed coordinate (latitude, longitude)
xcrun simctl location booted set 37.3349,-122.0090

# List available predefined scenarios
xcrun simctl location booted list

# Run a predefined scenario
xcrun simctl location booted run "City Run"

# Follow custom command-line waypoints
xcrun simctl location booted start --speed=15 --interval=1 \
    37.3349,-122.0090 37.3317,-122.0307

# Read waypoints from stdin, one "lat,lon" pair per line
printf "37.3349,-122.0090\n37.3317,-122.0307\n" | \
    xcrun simctl location booted start --distance=100 -

# Clear the simulated location
xcrun simctl location booted clear
```

Use `set` for one coordinate, `run` for predefined scenario names, and `start` for custom waypoint routes. The command boundary matters: `simctl location run` accepts built-in scenario names (e.g., "City Run", "Freeway Drive"), not GPX file paths; `simctl location start` is the command-line path for custom coordinate waypoints. Use Xcode's Debug > Simulate Location menu for GPX-based routes.

Location simulation affects all apps using Core Location on the booted device. Clear the location when done to avoid unexpected test results.

### Privacy Permissions

```bash
# Grant a permission
xcrun simctl privacy booted grant photos com.example.MyApp

# Revoke a permission
xcrun simctl privacy booted revoke microphone com.example.MyApp

# Reset all permissions for the app
xcrun simctl privacy booted reset all com.example.MyApp
```

Common service names: `photos`, `microphone`, `contacts`, `calendar`, `reminders`, `location`, `location-always`, `motion`, `siri`. See [references/simctl-commands.md](references/simctl-commands.md) for the full list.

Pre-granting permissions in CI avoids system permission dialogs that block automated test runs, but it can mask missing usage description keys. Keep the required Info.plist privacy strings in place and still test the normal prompt flow.

### Deep Links and URLs

```bash
# Open a URL (triggers universal links or custom URL schemes)
xcrun simctl openurl booted "https://example.com/product/123"

# Custom URL scheme
xcrun simctl openurl booted "myapp://settings/notifications"
```

For universal links, the app's associated domains entitlement must be configured. The Simulator uses the `apple-app-site-association` file from the domain.

### Status Bar Overrides

```bash
# Set a clean status bar for screenshots
xcrun simctl status_bar booted override \
    --time "9:41" \
    --batteryState charged \
    --batteryLevel 100 \
    --cellularMode active \
    --cellularBars 4 \
    --wifiBars 3 \
    --operatorName ""

# Clear all overrides
xcrun simctl status_bar booted clear
```

Use status bar overrides to produce consistent App Store screenshots. Always clear overrides after capturing to avoid confusing other testing.

## Screenshot and Video Recording

```bash
# Capture a screenshot
xcrun simctl io booted screenshot screenshot.png

# Record video (press Ctrl+C to stop)
xcrun simctl io booted recordVideo recording.mov

# Screenshot with specific display mask
xcrun simctl io booted screenshot --mask black screenshot.png
```

`--mask` options: `ignored` (default, no mask), `alpha` (transparent corners), `black` (black corners). Use `alpha` or `black` when capturing screenshots that show the device shape. The `alpha` mask is only supported for screenshots — video recording falls back to `black`.

Video recording continues until the process receives SIGINT (Ctrl+C). The recording is saved only after stopping — killing the process with SIGKILL loses the file.

## Log Streaming

### Basic Log Stream

```bash
# Stream all logs at debug level and above
xcrun simctl spawn booted log stream --level debug

# Filter by subsystem
xcrun simctl spawn booted log stream --level debug \
    --predicate 'subsystem == "com.example.app"'

# Filter by subsystem and category
xcrun simctl spawn booted log stream --level debug \
    --predicate 'subsystem == "com.example.app" AND category == "networking"'

# Filter by process name
xcrun simctl spawn booted log stream \
    --predicate 'process == "MyApp"'
```

Load [Logger and Filtered Streaming](references/simctl-commands.md#logger-and-filtered-streaming)
when defining `Logger` subsystems/categories and matching `log stream`
predicates.

## Compile-Time Simulator Detection

Use `#if targetEnvironment(simulator)` to exclude code that cannot run in the Simulator:

```swift
func registerForPush() {
    #if targetEnvironment(simulator)
    logger.info("Skipping APNs registration — running in Simulator")
    #else
    UIApplication.shared.registerForRemoteNotifications()
    #endif
}
```

Runtime detection via environment variables:

```swift
var isSimulator: Bool {
    ProcessInfo.processInfo.environment["SIMULATOR_DEVICE_NAME"] != nil
}
```

Prefer compile-time checks (`#if targetEnvironment(simulator)`) over runtime checks. The compiler strips excluded code entirely, preventing linker errors from unavailable symbols.

## Simulator Limitations

Use this table as the authoritative classification. A supported trigger or proxy
does not establish real-device fidelity.

| Capability | Simulator Support |
|-----------|------------------|
| APNs push delivery | No — use `simctl push` for local simulation |
| Performance fidelity | Relative only — Simulator is not accurate for CPU/processing performance, networking speed, graphics/Metal, memory bandwidth, frame timing, memory pressure, Jetsam, shader correctness, or thermal behavior; verify performance-sensitive work on hardware |
| Metal GPU family parity | Partial — Simulator uses the host Mac GPU, not the device GPU; some shaders and limits differ |
| Camera hardware | No — use photo library injection or mock `AVCaptureSession` |
| Audio input / microphone | No general app audio input; Siri can be activated from Simulator menus |
| Secure Enclave | No — `kSecAttrTokenIDSecureEnclave` operations fail |
| App Attest (DCAppAttestService) | No — `isSupported` returns `false` |
| DockKit motor control | No — no physical accessory connection |
| Accelerometer / Gyroscope | No motion sensor support; use real devices for motion-dependent behavior |
| Barometer | No |
| NFC (Core NFC) | No |
| Bluetooth (Core Bluetooth) | No — use a real device for BLE testing |
| CarPlay display simulation | Supported through Simulator's external display/CarPlay option; still verify in vehicle or device setups |
| Face ID / Touch ID hardware | No hardware — use Features > Face ID / Touch ID menu in Simulator |
| Memory warnings, location changes, manual iCloud sync trigger | Supported through Simulator menus or `simctl`; manual sync can test app callback handling |
| Automatic iCloud propagation and conflicts | Hardware required for real accounts/devices, notification-triggered sync, background delivery, conflicts, and account/device state differences |
| Cellular network conditions | No — use Network Link Conditioner on Mac |

## Common Mistakes

### DON'T: Hardcode simulator UDIDs in scripts

UDIDs change when simulators are deleted and recreated. Hardcoded values break on other machines and CI.

```bash
# WRONG — hardcoded UDID
xcrun simctl boot "A1B2C3D4-E5F6-7890-ABCD-EF1234567890"

# CORRECT — look up by name and runtime
UDID=$(xcrun simctl list -j devices available | \
    jq -r '.devices["com.apple.CoreSimulator.SimRuntime.iOS-18-4"][] | select(.name == "iPhone 16 Pro") | .udid')
xcrun simctl boot "$UDID"

# CORRECT — use "booted" when one simulator is running
xcrun simctl install booted MyApp.app
```

### DON'T: Install or launch on a shutdown simulator

`simctl install` and `simctl launch` require a booted device. They fail silently or with an unhelpful error on a shutdown device.

```bash
# WRONG — device is not booted
xcrun simctl install <UDID> MyApp.app  # fails

# CORRECT — boot if needed and wait for readiness, then install
xcrun simctl bootstatus <UDID> -b
xcrun simctl install <UDID> MyApp.app
xcrun simctl launch <UDID> com.example.MyApp
```

### DON'T: Leave zombie simulators running in CI

Each booted simulator consumes memory and CPU. CI pipelines that create simulators without cleanup accumulate zombie devices.

```bash
# WRONG — CI script creates and boots but never cleans up
xcrun simctl create "CI Phone" "iPhone 16 Pro" "com.apple.CoreSimulator.SimRuntime.iOS-18-4"
xcrun simctl boot "$UDID"
# ... tests run, pipeline exits ...

# CORRECT — always clean up in CI teardown
cleanup() {
    xcrun simctl shutdown all
    xcrun simctl delete "$UDID"
}
trap cleanup EXIT
```

### DON'T: Keep retrying boot on a stuck simulator

A simulator stuck in the "Booting" state will not recover by retrying `boot`. The underlying CoreSimulator state is corrupted.

```bash
# WRONG — retry loop on a stuck device
xcrun simctl boot "$UDID"  # "Unable to boot device in current state: Booting"
xcrun simctl boot "$UDID"  # same error, forever

# CORRECT — shut down, erase, and retry
xcrun simctl shutdown "$UDID"
xcrun simctl erase "$UDID"
xcrun simctl boot "$UDID"

# If that fails, reset CoreSimulator entirely
xcrun simctl shutdown all
xcrun simctl erase all
# Last resort: rm -rf ~/Library/Developer/CoreSimulator/Caches
```

## Review Checklist

- [ ] Simulator devices created with explicit device type and runtime identifiers
- [ ] Scripts use `booted` or parsed UDID from JSON output, not hardcoded values
- [ ] Push notification payloads tested via `simctl push` during development
- [ ] Push notification delivery verified on a real device before release
- [ ] Location simulation tested with fixed coordinates, predefined scenarios, and custom waypoints when needed
- [ ] Privacy permissions pre-granted in CI to avoid blocking dialogs
- [ ] `#if targetEnvironment(simulator)` guards around APIs unavailable in Simulator
- [ ] Status bar overrides cleared after capturing screenshots
- [ ] CI pipelines shut down and delete simulators in teardown
- [ ] Log streaming configured with subsystem/category predicates for focused debugging
- [ ] App container paths used for inspecting sandboxed data during debugging

## References

- [Running your app in Simulator or on a device](https://sosumi.ai/documentation/xcode/running-your-app-in-simulator-or-on-a-device)
- [Downloading and installing additional Xcode components](https://sosumi.ai/documentation/xcode/installing-additional-simulator-runtimes)
- [Testing in Simulator versus testing on hardware devices](https://sosumi.ai/documentation/xcode/testing-in-simulator-versus-testing-on-hardware-devices)
- [Testing complex hardware device scenarios in Simulator](https://sosumi.ai/documentation/xcode/testing-complex-hardware-device-scenarios-in-simulator)
- [Simulating an external display or CarPlay](https://sosumi.ai/documentation/xcode/simulating-an-external-display-or-carplay)
- simctl command reference: [references/simctl-commands.md](references/simctl-commands.md)
