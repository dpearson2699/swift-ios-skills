# Swift iOS Skills for Claude Code

23 skills that teach Claude Code how to build iOS and Apple-platform apps with Swift. Each skill covers one framework or domain -- install only what you need.

Every skill is self-contained. No skill depends on another.

## Skills

| Skill | What it covers |
|-------|---------------|
| [app-intents](app-intents/) | Siri, Shortcuts, Spotlight, Apple Intelligence, AppEntity, AppShortcutsProvider |
| [app-store-review](app-store-review/) | App Review guidelines, rejection prevention, privacy manifests, ATT, HIG compliance |
| [apple-on-device-ai](apple-on-device-ai/) | Foundation Models framework, Core ML, MLX Swift, on-device LLM inference |
| [ios-accessibility](ios-accessibility/) | VoiceOver, Dynamic Type, custom rotors, accessibility focus, assistive-technology support |
| [ios-localization](ios-localization/) | String Catalogs, pluralization, FormatStyle, right-to-left layout |
| [ios-networking](ios-networking/) | URLSession async/await, REST APIs, downloads/uploads, WebSockets, pagination, retry, caching |
| [ios-security](ios-security/) | Keychain, CryptoKit, Face ID/Touch ID, Secure Enclave, ATS, certificate pinning |
| [live-activities](live-activities/) | ActivityKit, Dynamic Island, Lock Screen Live Activities |
| [mapkit-location](mapkit-location/) | MapKit, CoreLocation, annotations, geocoding, directions, geofencing |
| [photos-camera-media](photos-camera-media/) | PhotosPicker, AVCaptureSession, photo library, video recording, media permissions |
| [push-notifications](push-notifications/) | UNUserNotificationCenter, APNs, rich notifications, silent push, service extensions |
| [storekit](storekit/) | StoreKit 2 purchases, subscriptions, SubscriptionStoreView, transaction verification |
| [swift-charts](swift-charts/) | Bar, line, area, pie, donut charts, scrolling, selection, annotations |
| [swift-concurrency](swift-concurrency/) | Swift 6.2 concurrency, Sendable, actors, structured concurrency, data-race safety |
| [swift-testing](swift-testing/) | Swift Testing framework, @Test, @Suite, #expect, parameterized tests, mocking |
| [swiftdata](swiftdata/) | @Model, @Query, #Predicate, ModelContainer, migrations, CloudKit sync, @ModelActor |
| [swiftui-animation](swiftui-animation/) | Spring animations, PhaseAnimator, KeyframeAnimator, matchedGeometryEffect, SF Symbols |
| [swiftui-liquid-glass](swiftui-liquid-glass/) | iOS 26 Liquid Glass, glassEffect, GlassEffectContainer, morphing transitions |
| [swiftui-patterns](swiftui-patterns/) | @Observable, NavigationStack, view composition, sheets, TabView, MV-pattern architecture |
| [swiftui-performance](swiftui-performance/) | Rendering performance, view update optimization, layout thrash, Instruments profiling |
| [swiftui-uikit-interop](swiftui-uikit-interop/) | UIViewRepresentable, UIHostingController, Coordinator, incremental UIKit-to-SwiftUI migration |
| [tipkit](tipkit/) | Feature discovery tooltips, contextual tips, tip rules, tip events |
| [widgetkit](widgetkit/) | Home Screen/Lock Screen/StandBy widgets, Control Center controls, timeline providers |

## Install

Install a single skill:

```
claude install-skill dpearson/swift-ios-skills/storekit
```

Or clone the repo and install locally:

```
git clone https://github.com/dpearson/swift-ios-skills.git
claude install-skill ./swift-ios-skills/storekit
```

## Structure

Each skill is a directory containing:

```
skill-name/
  SKILL.md              # Main skill file (what Claude reads)
  references/           # Detailed reference material (optional)
    some-topic.md
    another-topic.md
```

`SKILL.md` contains the core guidance. The `references/` folder holds longer examples, advanced patterns, and lookup tables that the main file points to.

## License

GPLv2 -- see [LICENSE](LICENSE)
