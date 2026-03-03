# Swift iOS Skills — Agent Skills for iOS 26+ & Apple-Platform Development

[![License: GPLv2](https://img.shields.io/badge/License-GPLv2-blue.svg)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/dpearson2699/swift-ios-skills)](https://github.com/dpearson2699/swift-ios-skills/stargazers)
[![Swift 6.2](https://img.shields.io/badge/Swift-6.2-F05138.svg)](https://swift.org)
[![iOS 26+](https://img.shields.io/badge/iOS-26%2B-000000.svg?logo=apple)](https://developer.apple.com)
[![macOS](https://img.shields.io/badge/macOS-supported-000000.svg?logo=apple)](https://developer.apple.com)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-compatible-blueviolet.svg?logo=anthropic)](https://claude.ai/code)
[![OpenAI Codex](https://img.shields.io/badge/OpenAI%20Codex-compatible-412991.svg?logo=openai)](https://developers.openai.com/codex)
[![Cursor](https://img.shields.io/badge/Cursor-compatible-00A4DC.svg)](https://cursor.com)
[![GitHub Copilot](https://img.shields.io/badge/GitHub%20Copilot-compatible-000000.svg?logo=github)](https://github.com/features/copilot)
[![Windsurf](https://img.shields.io/badge/Windsurf-compatible-06B6D4.svg)](https://codeium.com/windsurf)
[![Roo Code](https://img.shields.io/badge/Roo%20Code-compatible-F97316.svg)](https://roocode.com)
[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-standard-green.svg)](https://agentskills.io)

23 agent skills optimized for **iOS 26+** development with Swift 6.2 and modern Apple frameworks. All code examples, patterns, and guidance target the latest APIs -- Liquid Glass, Swift 6.2 approachable concurrency, Foundation Models, StoreKit 2, SwiftData, async/await URLSession, and more. No deprecated patterns.

Compatible with [Claude Code](https://claude.ai/code), [OpenAI Codex](https://developers.openai.com/codex), [Cursor](https://cursor.com), [GitHub Copilot](https://github.com/features/copilot), and [40+ other agents](https://skills.sh). Follows the open [Agent Skills](https://agentskills.io) standard.

Every skill is self-contained. No skill depends on another. Install only what you need.

## Install

### Any agent (via [skills CLI](https://github.com/vercel-labs/skills))

Install a single skill:

```
npx skills add dpearson2699/swift-ios-skills@<skill-name>
```

Install all skills from this repo:

```
npx skills add dpearson2699/swift-ios-skills
```

### Claude Code (via plugin marketplace)

Add the marketplace (one-time):

```
/plugin marketplace add dpearson2699/swift-ios-skills
```

Install everything:

```
/plugin install all-ios-skills@swift-ios-skills
```

Or install a themed bundle:

```
/plugin install swiftui-skills@swift-ios-skills
/plugin install swift-core-skills@swift-ios-skills
/plugin install ios-framework-skills@swift-ios-skills
/plugin install ios-engineering-skills@swift-ios-skills
```

### OpenAI Codex

```
$skill-installer install https://github.com/dpearson2699/swift-ios-skills/tree/main/skills/<skill-name>
```

## Plugin Bundles (Claude Code)

| Plugin | Skills included |
|--------|----------------|
| **all-ios-skills** | All 23 skills |
| **swiftui-skills** | swiftui-patterns, swiftui-animation, swiftui-liquid-glass, swiftui-performance, swiftui-uikit-interop |
| **swift-core-skills** | swift-concurrency, swift-testing, swiftdata, swift-charts |
| **ios-framework-skills** | app-intents, storekit, widgetkit, live-activities, mapkit-location, tipkit, push-notifications, photos-camera-media |
| **ios-engineering-skills** | ios-networking, ios-security, ios-accessibility, ios-localization, app-store-review, apple-on-device-ai |

## Skills

### SwiftUI

| Skill | What it covers |
|-------|---------------|
| [swiftui-patterns](skills/swiftui-patterns/) | @Observable, NavigationStack, view composition, sheets, TabView, MV-pattern architecture |
| [swiftui-animation](skills/swiftui-animation/) | Spring animations, PhaseAnimator, KeyframeAnimator, matchedGeometryEffect, SF Symbols |
| [swiftui-liquid-glass](skills/swiftui-liquid-glass/) | iOS 26 Liquid Glass, glassEffect, GlassEffectContainer, morphing transitions |
| [swiftui-performance](skills/swiftui-performance/) | Rendering performance, view update optimization, layout thrash, Instruments profiling |
| [swiftui-uikit-interop](skills/swiftui-uikit-interop/) | UIViewRepresentable, UIHostingController, Coordinator, incremental UIKit-to-SwiftUI migration |

### Core Swift

| Skill | What it covers |
|-------|---------------|
| [swift-concurrency](skills/swift-concurrency/) | Swift 6.2 concurrency, Sendable, actors, structured concurrency, data-race safety |
| [swift-testing](skills/swift-testing/) | Swift Testing framework, @Test, @Suite, #expect, parameterized tests, mocking |
| [swiftdata](skills/swiftdata/) | @Model, @Query, #Predicate, ModelContainer, migrations, CloudKit sync, @ModelActor |
| [swift-charts](skills/swift-charts/) | Bar, line, area, pie, donut charts, scrolling, selection, annotations |

### iOS Frameworks

| Skill | What it covers |
|-------|---------------|
| [app-intents](skills/app-intents/) | Siri, Shortcuts, Spotlight, Apple Intelligence, AppEntity, AppShortcutsProvider |
| [storekit](skills/storekit/) | StoreKit 2 purchases, subscriptions, SubscriptionStoreView, transaction verification |
| [widgetkit](skills/widgetkit/) | Home Screen, Lock Screen, and StandBy widgets, Control Center controls, timeline providers |
| [live-activities](skills/live-activities/) | ActivityKit, Dynamic Island, Lock Screen Live Activities |
| [mapkit-location](skills/mapkit-location/) | MapKit, CoreLocation, annotations, geocoding, directions, geofencing |
| [tipkit](skills/tipkit/) | Feature discovery tooltips, contextual tips, tip rules, tip events |
| [push-notifications](skills/push-notifications/) | UNUserNotificationCenter, APNs, rich notifications, silent push, service extensions |
| [photos-camera-media](skills/photos-camera-media/) | PhotosPicker, AVCaptureSession, photo library, video recording, media permissions |

### iOS Engineering

| Skill | What it covers |
|-------|---------------|
| [ios-networking](skills/ios-networking/) | URLSession async/await, REST APIs, downloads/uploads, WebSockets, pagination, retry, caching |
| [ios-security](skills/ios-security/) | Keychain, CryptoKit, Face ID/Touch ID, Secure Enclave, ATS, certificate pinning |
| [ios-accessibility](skills/ios-accessibility/) | VoiceOver, Dynamic Type, custom rotors, accessibility focus, assistive-technology support |
| [ios-localization](skills/ios-localization/) | String Catalogs, pluralization, FormatStyle, right-to-left layout |
| [app-store-review](skills/app-store-review/) | App Review guidelines, rejection prevention, privacy manifests, ATT, HIG compliance |
| [apple-on-device-ai](skills/apple-on-device-ai/) | Foundation Models framework, Core ML, MLX Swift, on-device LLM inference |

## Structure

Each skill follows the open [Agent Skills](https://agentskills.io) standard:

```
skills/
  skill-name/
    SKILL.md              # Required — instructions and metadata
    references/           # Optional — detailed reference material
      some-topic.md
```

`SKILL.md` contains YAML frontmatter (`name`, `description`) and markdown instructions. The `references/` folder holds longer examples, advanced patterns, and lookup tables that the main file points to.

## Compatibility

These skills work with any agent that supports the [Agent Skills standard](https://agentskills.io), including:

- [Claude Code](https://claude.ai/code) (Anthropic)
- [OpenAI Codex](https://developers.openai.com/codex)
- [Cursor](https://cursor.com)
- [GitHub Copilot](https://github.com/features/copilot)
- [Windsurf](https://codeium.com/windsurf)
- [Roo Code](https://roocode.com)
- And [many more](https://skills.sh)

## License

GPLv2 -- see [LICENSE](LICENSE)
