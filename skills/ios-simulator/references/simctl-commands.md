# simctl Command Reference

Common `xcrun simctl` subcommands with syntax, flags, and examples. For workflows and patterns, see the main [SKILL.md](../SKILL.md).

## Contents

- [Device Management Commands](#device-management-commands)
- [App Lifecycle Commands](#app-lifecycle-commands)
- [Logger and Filtered Streaming](#logger-and-filtered-streaming)
- [Testing and Simulation Commands](#testing-and-simulation-commands)
- [Media and IO Commands](#media-and-io-commands)
- [JSON Output Parsing](#json-output-parsing)
- [Privacy Service Names](#privacy-service-names)
- [Status Bar Override Flags](#status-bar-override-flags)
- [Troubleshooting](#troubleshooting)

## Device Management Commands

| Command | Synopsis | Notes |
|---------|----------|-------|
| `list` | `simctl list [devices\|devicetypes\|runtimes\|pairs] [search-term]` | Add `-j` for JSON. Add `available` to filter to usable devices. |
| `create` | `simctl create <name> <device-type-id> [<runtime-id>]` | Returns the new UDID. Omitting runtime selects the newest compatible one. |
| `clone` | `simctl clone <UDID> <new-name>` | Copies device state including installed apps. |
| `delete` | `simctl delete <UDID\|unavailable\|all>` | `unavailable` removes devices whose runtime is missing. |
| `rename` | `simctl rename <UDID> <new-name>` | |
| `erase` | `simctl erase <UDID\|all>` | Factory reset — wipes apps and data, keeps the device. |
| `boot` | `simctl boot <UDID>` | Starts the device runtime. |
| `bootstatus` | `simctl bootstatus <UDID> [-b]` | Waits until the device finishes booting. Use `-b` in scripts to boot if needed and block until ready. |
| `shutdown` | `simctl shutdown <UDID\|all>` | Stops the device runtime. |
| `upgrade` | `simctl upgrade <UDID> <runtime-id>` | Upgrades device to a newer runtime. |
| `pair` | `simctl pair <watch-UDID> <phone-UDID>` | Pairs a watchOS simulator with an iOS simulator. |
| `unpair` | `simctl unpair <pair-UDID>` | Removes a watch/phone pairing. |

### Device Type and Runtime IDs

```bash
# List all device types — use the identifier column
xcrun simctl list devicetypes

# Example output line:
# iPhone 16 Pro (com.apple.CoreSimulator.SimDeviceType.iPhone-16-Pro)

# List all runtimes
xcrun simctl list runtimes

# Example output line:
# iOS 18.4 - com.apple.CoreSimulator.SimRuntime.iOS-18-4
```

Use the identifier strings (e.g., `com.apple.CoreSimulator.SimDeviceType.iPhone-16-Pro`) in `create` and `upgrade` commands.

## App Lifecycle Commands

| Command | Synopsis | Notes |
|---------|----------|-------|
| `install` | `simctl install <UDID> <path-to-.app>` | Device must be booted. Path is a `.app` directory, not `.ipa`. |
| `uninstall` | `simctl uninstall <UDID> <bundle-id>` | Removes app and its data. |
| `launch` | `simctl launch [--console] [--terminate-running-process] <UDID> <bundle-id> [args...]` | `--console` streams stdout/stderr. `--terminate-running-process` kills existing instance first. |
| `terminate` | `simctl terminate <UDID> <bundle-id>` | Sends SIGTERM to the running app. |
| `spawn` | `simctl spawn <UDID> <path-to-binary> [args...]` | Runs an arbitrary binary inside the simulator. Used for `log stream`. |
| `get_app_container` | `simctl get_app_container <UDID> <bundle-id> [app\|data\|groups\|<group-id>]` | Returns the filesystem path to the container. `groups` lists all App Group containers. |
| `appinfo` | `simctl appinfo <UDID> <bundle-id>` | Prints Info.plist-derived information as JSON. |

For scripts that boot a simulator before installing, prefer:

```bash
xcrun simctl bootstatus <UDID> -b
xcrun simctl install <UDID> build/Build/Products/Debug-iphonesimulator/MyApp.app
```

`bootstatus -b` safely boots if needed and waits until the simulator finishes booting. If you call `simctl boot` separately, follow it with `xcrun simctl bootstatus <UDID>` before `install`, `launch`, `push`, or `location`.

### Launch Arguments and Environment

```bash
# Pass launch arguments (received as CommandLine.arguments)
xcrun simctl launch booted com.example.MyApp --reset-onboarding --debug-mode

# Override language and locale
xcrun simctl launch booted com.example.MyApp -AppleLanguages "(ja)" -AppleLocale "ja_JP"

# Set environment variables for the launched app
SIMCTL_CHILD_MY_VAR=value xcrun simctl launch booted com.example.MyApp
```

Use the `SIMCTL_CHILD_` prefix for environment variables passed to `simctl launch`. Use `simctl spawn` for arbitrary processes inside the simulator, such as `log stream`, not as the default way to launch an installed app with environment.

## Logger and Filtered Streaming

Design Logger subsystems and categories to match the predicates used by
`simctl spawn ... log stream`:

```swift
import Foundation
import os

let networkLogger = Logger(
    subsystem: "com.example.app",
    category: "networking"
)

func fetchData() async throws -> Data {
    networkLogger.debug("Starting request to /api/data")
    let (data, response) = try await URLSession.shared.data(from: url)
    let status = (response as? HTTPURLResponse)?.statusCode ?? 0
    networkLogger.info("Received \(data.count) bytes, status: \(status)")
    return data
}
```

```bash
xcrun simctl spawn booted log stream --level debug \
    --predicate 'subsystem == "com.example.app" AND category == "networking"'
```

## Testing and Simulation Commands

| Command | Synopsis | Notes |
|---------|----------|-------|
| `push` | `simctl push <UDID> [<bundle-id>] <payload.json\|->` | Simulates local push delivery. Use `-` for stdin. Bundle ID is optional when the payload contains `Simulator Target Bundle`. |
| `openurl` | `simctl openurl <UDID> <URL>` | Triggers universal links or custom URL schemes. |
| `location` | `simctl location <UDID> <set\|clear\|list\|run\|start> [args]` | `set <lat,lon>`, `run <scenario>`, `list`, `start`, or `clear`. |
| `privacy` | `simctl privacy <UDID> <grant\|revoke\|reset> <service> <bundle-id>` | See [Privacy Service Names](#privacy-service-names) for service values. |
| `keychain` | `simctl keychain <UDID> <add-root-cert\|add-cert\|reset> [cert-path]` | Manages trusted certificates in the simulator keychain. |
| `status_bar` | `simctl status_bar <UDID> <override\|clear> [flags]` | See [Status Bar Override Flags](#status-bar-override-flags). |

### Push Payload Format

The JSON payload mirrors the APNs payload format. The `Simulator Target Bundle` key is optional — when provided, the bundle ID argument can be omitted:

```json
{
    "Simulator Target Bundle": "com.example.MyApp",
    "aps": {
        "alert": {
            "title": "Order Update",
            "subtitle": "Order #1234",
            "body": "Your order has been shipped"
        },
        "badge": 1,
        "sound": "default",
        "category": "ORDER_STATUS",
        "thread-id": "order-1234",
        "interruption-level": "time-sensitive"
    },
    "orderID": "1234"
}
```

The payload must be a top-level JSON object, include a valid `aps` dictionary, and be 4096 bytes or less. `simctl push` supports only application remote push notifications; it does not support VoIP, Complication, File Provider, or other push types.

### Location Scenarios

The `run` subcommand accepts predefined scenario names, not GPX file paths:

```bash
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

# Set a fixed coordinate
xcrun simctl location booted set 37.3349,-122.0090

# Clear the simulated location
xcrun simctl location booted clear
```

Available scenarios include "City Run", "City Bicycle Ride", "Freeway Drive", and "Apple" (stationary at Apple Park). Use `list` to see all options on your system.

Use `start` for command-line waypoint routes. It accepts at least two latitude/longitude pairs, optional speed, and either distance- or interval-based update cadence. The command boundary matters: `simctl location run` accepts built-in scenario names, not GPX file paths; for custom routes already stored as GPX files, use Xcode's Debug > Simulate Location menu instead.

## Media and IO Commands

| Command | Synopsis | Notes |
|---------|----------|-------|
| `io screenshot` | `simctl io <UDID> screenshot [--type png\|jpeg\|tiff\|bmp\|gif] [--mask ignored\|alpha\|black] <path>` | Default type is png. |
| `io recordVideo` | `simctl io <UDID> recordVideo [--codec h264\|hevc] [--mask ignored\|alpha\|black] [--force] <path>` | Ctrl+C to stop. `--force` overwrites existing files. |
| `addmedia` | `simctl addmedia <UDID> <path> [path...]` | Adds photos, live photos, videos, or contacts to the device. Supports PNG, JPEG, GIF, MOV, MP4, and vCard. |

### Mask Options

| Value | Effect |
|-------|--------|
| `ignored` | No mask applied (default). Full rectangular capture. |
| `alpha` | Transparent pixels where the device bezel would be. Produces PNG with alpha channel. Not supported for video recording — falls back to `black`. |
| `black` | Black pixels where the device bezel would be. Works with JPEG. |

## JSON Output Parsing

### Find a Booted Device UDID

```bash
xcrun simctl list -j devices booted | \
    jq -r '[.devices[][] | select(.state == "Booted")] | first | .udid'
```

### Find a Device by Name and Runtime

```bash
RUNTIME="com.apple.CoreSimulator.SimRuntime.iOS-18-4"
xcrun simctl list -j devices available | \
    jq -r --arg rt "$RUNTIME" \
    '.devices[$rt][] | select(.name == "iPhone 16 Pro") | .udid'
```

### List All Available Runtimes

```bash
xcrun simctl list -j runtimes | \
    jq -r '.runtimes[] | select(.isAvailable == true) | "\(.name) — \(.identifier)"'
```

### Get Device State

```bash
xcrun simctl list -j devices | \
    jq -r --arg udid "$UDID" \
    '[.devices[][] | select(.udid == $udid)] | first | .state'
```

## Privacy Service Names

Service names accepted by `simctl privacy grant|revoke|reset`:

| Service | Description |
|---------|-------------|
| `all` | All services. `grant` and `revoke` require a bundle identifier; `reset` may omit it. |
| `calendar` | EventKit calendar access |
| `contacts-limited` | Limited contacts access |
| `contacts` | Full contacts access |
| `location` | When-in-use location access |
| `location-always` | Always location access |
| `photos-add` | Add-only photo library access |
| `photos` | Full photo library access |
| `media-library` | Apple Music / media library |
| `microphone` | Microphone access |
| `motion` | Core Motion activity data |
| `reminders` | EventKit reminders access |
| `siri` | Siri integration |

## Status Bar Override Flags

All flags for `simctl status_bar <UDID> override`:

| Flag | Type | Example |
|------|------|---------|
| `--time` | String | `"9:41"` |
| `--dataNetwork` | String | `hide`, `wifi`, `3g`, `4g`, `lte`, `lte-a`, `lte+`, `5g`, `5g+`, `5g-uc`, `5g-uwb` |
| `--wifiMode` | String | `searching`, `failed`, `active` |
| `--wifiBars` | Integer | `0`–`3` |
| `--cellularMode` | String | `notSupported`, `searching`, `failed`, `active` |
| `--cellularBars` | Integer | `0`–`4` |
| `--operatorName` | String | `""` (empty for clean screenshots) |
| `--batteryState` | String | `charging`, `charged`, `discharging` |
| `--batteryLevel` | Integer | `0`–`100` |

### App Store Screenshot Preset

```bash
xcrun simctl status_bar booted override \
    --time "9:41" \
    --batteryState charged \
    --batteryLevel 100 \
    --cellularMode active \
    --cellularBars 4 \
    --wifiMode active \
    --wifiBars 3 \
    --dataNetwork wifi \
    --operatorName ""
```

## Troubleshooting

### Stuck "Booting" State

The device shows state "Booting" and `simctl boot` returns "Unable to boot device in current state: Booting."

```bash
# Step 1: force shutdown
xcrun simctl shutdown <UDID>

# Step 2: erase the device
xcrun simctl erase <UDID>

# Step 3: boot again
xcrun simctl boot <UDID>
```

If erasing does not resolve it, delete and recreate the device. As a last resort, clear the CoreSimulator caches:

```bash
xcrun simctl shutdown all
rm -rf ~/Library/Developer/CoreSimulator/Caches
```

### Runtime Not Installed

`simctl create` or `simctl boot` fails with "Invalid runtime" or the runtime does not appear in `simctl list runtimes`.

```bash
# Check what's installed
xcrun simctl list runtimes

# Download a runtime via xcodebuild
xcodebuild -downloadPlatform iOS

# Or download via Xcode > Settings > Platforms
```

Runtime downloads can be large (5+ GB). In CI, pre-install runtimes in the base image.

### CoreSimulator Cache Corruption

Symptoms: devices fail to boot, `simctl list` shows stale data, or "Unable to determine simulator device status."

```bash
# Nuclear option — reset everything
xcrun simctl shutdown all
xcrun simctl erase all
rm -rf ~/Library/Developer/CoreSimulator/Caches
# Restart CoreSimulatorService
launchctl kickstart -k gui/$(id -u)/com.apple.CoreSimulator.CoreSimulatorService 2>/dev/null || true
```

After clearing caches, you may need to re-create custom devices. Default devices are recreated automatically by Xcode.

### "Unable to boot device in current state: Shutdown"

This usually means the required runtime is not fully installed or is corrupted. Verify the runtime is available and re-download if needed:

```bash
xcrun simctl list runtimes
# If the runtime shows (unavailable), re-download it
xcodebuild -downloadPlatform iOS
```
