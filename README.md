# Swift iOS Skills for Claude Code

23 skills that teach Claude Code how to build iOS and Apple-platform apps with Swift. Each skill covers one framework or domain -- install only what you need.

Every skill is self-contained. No skill depends on another.

## Install

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

## Plugin Bundles

| Plugin | Skills included |
|--------|----------------|
| **all-ios-skills** | All 23 skills |
| **swiftui-skills** | swiftui-patterns, swiftui-animation, swiftui-liquid-glass, swiftui-performance, swiftui-uikit-interop |
| **swift-core-skills** | swift-concurrency, swift-testing, swiftdata, swift-charts |
| **ios-framework-skills** | app-intents, storekit, widgetkit, live-activities, mapkit-location, tipkit, push-notifications, photos-camera-media |
| **ios-engineering-skills** | ios-networking, ios-security, ios-accessibility, ios-localization, app-store-review, apple-on-device-ai |

## Skills

| Skill | What it covers |
|-------|---------------|
| [app-intents](skills/app-intents/) | Siri, Shortcuts, Spotlight, Apple Intelligence, AppEntity, AppShortcutsProvider |
| [app-store-review](skills/app-store-review/) | App Review guidelines, rejection prevention, privacy manifests, ATT, HIG compliance |
| [apple-on-device-ai](skills/apple-on-device-ai/) | Foundation Models framework, Core ML, MLX Swift, on-device LLM inference |
| [ios-accessibility](skills/ios-accessibility/) | VoiceOver, Dynamic Type, custom rotors, accessibility focus, assistive-technology support |
| [ios-localization](skills/ios-localization/) | String Catalogs, pluralization, FormatStyle, right-to-left layout |
| [ios-networking](skills/ios-networking/) | URLSession async/await, REST APIs, downloads/uploads, WebSockets, pagination, retry, caching |
| [ios-security](skills/ios-security/) | Keychain, CryptoKit, Face ID/Touch ID, Secure Enclave, ATS, certificate pinning |
| [live-activities](skills/live-activities/) | ActivityKit, Dynamic Island, Lock Screen Live Activities |
| [mapkit-location](skills/mapkit-location/) | MapKit, CoreLocation, annotations, geocoding, directions, geofencing |
| [photos-camera-media](skills/photos-camera-media/) | PhotosPicker, AVCaptureSession, photo library, video recording, media permissions |
| [push-notifications](skills/push-notifications/) | UNUserNotificationCenter, APNs, rich notifications, silent push, service extensions |
| [storekit](skills/storekit/) | StoreKit 2 purchases, subscriptions, SubscriptionStoreView, transaction verification |
| [swift-charts](skills/swift-charts/) | Bar, line, area, pie, donut charts, scrolling, selection, annotations |
| [swift-concurrency](skills/swift-concurrency/) | Swift 6.2 concurrency, Sendable, actors, structured concurrency, data-race safety |
| [swift-testing](skills/swift-testing/) | Swift Testing framework, @Test, @Suite, #expect, parameterized tests, mocking |
| [swiftdata](skills/swiftdata/) | @Model, @Query, #Predicate, ModelContainer, migrations, CloudKit sync, @ModelActor |
| [swiftui-animation](skills/swiftui-animation/) | Spring animations, PhaseAnimator, KeyframeAnimator, matchedGeometryEffect, SF Symbols |
| [swiftui-liquid-glass](skills/swiftui-liquid-glass/) | iOS 26 Liquid Glass, glassEffect, GlassEffectContainer, morphing transitions |
| [swiftui-patterns](skills/swiftui-patterns/) | @Observable, NavigationStack, view composition, sheets, TabView, MV-pattern architecture |
| [swiftui-performance](skills/swiftui-performance/) | Rendering performance, view update optimization, layout thrash, Instruments profiling |
| [swiftui-uikit-interop](skills/swiftui-uikit-interop/) | UIViewRepresentable, UIHostingController, Coordinator, incremental UIKit-to-SwiftUI migration |
| [tipkit](skills/tipkit/) | Feature discovery tooltips, contextual tips, tip rules, tip events |
| [widgetkit](skills/widgetkit/) | Home Screen/Lock Screen/StandBy widgets, Control Center controls, timeline providers |

## Structure

```
skills/
  skill-name/
    SKILL.md              # Main skill file (what Claude reads)
    references/           # Detailed reference material (optional)
      some-topic.md
```

`SKILL.md` contains the core guidance. The `references/` folder holds longer examples, advanced patterns, and lookup tables that the main file points to.

## License

GPLv2 -- see [LICENSE](LICENSE)
