# Changelog

## Unreleased

## v3.7.0

### Repository

- Bump the Tessl plugin and Claude Code marketplace metadata to 3.7.0.
- Add focused local Agent Skills eval coverage and promoted Tessl scenarios for SwiftUI view decomposition, preview isolation, and scroll-driven reveal surfaces.

### Skill updates

- Expand `swiftui-patterns` with concrete view-decomposition signals, focused value/action interfaces for narrowing Observation dependencies, and an explicit distinction between file organization and dedicated `View` boundaries.
- Add isolated preview-construction guidance covering deterministic loaded, loading, empty, and error states; complete required dependency installation; in-memory persistence; and avoidance of live services, authentication, production data, keychain state, and global singletons.
- Route advanced cancellation, debounce, clocks, `AsyncSequence`, and actor-isolation details from `swiftui-patterns` to `swift-concurrency`.
- Add paged primary/detail reveal guidance to `swiftui-layout-components` using `ScrollPosition`, normalized `onScrollGeometryChange` progress, shared continuous effects, discrete settled-state callbacks, scroll arbitration during zoom or crop, and safeguards against geometry feedback loops and broad per-frame invalidation.

## v3.6.1

### Skill updates

- Fix the `core-bluetooth` SwiftUI BLE reference sample so it compiles under Swift 6.3 strict concurrency by keeping delegate callbacks on the `@MainActor` view model when using Core Bluetooth's main-queue `queue: nil` delivery, avoiding `nonisolated` delegate methods that capture non-Sendable Core Bluetooth objects inside `Task { @MainActor }`.

## v3.6.0

### Repository

- Migrate Tessl packaging from deprecated root `tile.json` to `.tessl-plugin/plugin.json`; keep the same 84-skill bundle via explicit skill paths and retain `README.md` as the external public catalog.
- Update the release workflow to publish the Tessl plugin package instead of the deprecated tile package, and verify an already-created registry version when the Tessl publish client times out after the server accepts the upload.
- Bump Tessl plugin and Claude Code marketplace metadata to 3.6.0.
- Promote 248 reviewed Tessl scenarios into the root `evals/` suite for full-project public eval coverage.
- Keep generated Agent Skills workspaces and skill-local generated scenario staging ignored while retaining committed source eval definitions and promoted root scenarios.

### Skill updates

- Complete the post-3.5.0 audit sweep across 83 shipped skills, excluding only unchanged `photokit`; refresh `SKILL.md`, references, local `skills/<skill>/evals/evals.json`, and promoted root Tessl scenarios where applicable.
- Refresh Apple framework and app-experience skills: `accessorysetupkit`, `activitykit`, `adattributionkit`, `alarmkit`, `app-clips`, `app-intents`, `app-store-optimization`, `app-store-review`, `appmigrationkit`, `audioaccessorykit`, `avkit`, `background-processing`, `browserenginekit`, `callkit`, `carplay`, `cloudkit`, `contacts-framework`, `core-bluetooth`, `core-data`, `core-motion`, `core-nfc`, `cryptotokenkit`, `device-integrity`, `dockkit`, `energykit`, `eventkit`, `financekit`, `gamekit`, `healthkit`, `homekit`, `ios-networking`, `ios-simulator`, `mapkit`, `metrickit`, `musickit`, `paperkit`, `passkit`, `pdfkit`, `pencilkit`, `permissionkit`, `push-notifications`, `relevancekit`, `sensorkit`, `shareplay-activities`, `storekit`, `tabletopkit`, `tipkit`, `weatherkit`, and `widgetkit`.
- Refresh Swift, SwiftUI, tooling, AI, media, and architecture skills: `apple-on-device-ai`, `authentication`, `coreml`, `cryptokit`, `debugging-instruments`, `focus-engine`, `ios-accessibility`, `ios-localization`, `natural-language`, `realitykit`, `scenekit`, `speech-recognition`, `spritekit`, `swift-api-design-guidelines`, `swift-architecture`, `swift-charts`, `swift-codable`, `swift-concurrency`, `swift-formatstyle`, `swift-language`, `swift-security`, `swift-testing`, `swiftdata`, `swiftlint`, `swiftui-animation`, `swiftui-gestures`, `swiftui-layout-components`, `swiftui-liquid-glass`, `swiftui-navigation`, `swiftui-patterns`, `swiftui-performance`, `swiftui-uikit-interop`, `swiftui-webkit`, and `vision-framework`.
- Add or expand progressive-disclosure references for App Clips routing/data handoff/size limits, Authentication passkeys, SpeechAnalyzer workflows, SwiftData/Core Data coexistence, Swift concurrency synchronization primitives, Swift Security keychain and CryptoKit material, SwiftUI performance WWDC sources, and Vision request/scanner guidance.
- Correct and tighten fast-moving API guidance across audited skills, including AccessorySetupKit discovery and migration, ActivityKit scheduled and transient Live Activity semantics, ADAttributionKit custom-rendered ads and postbacks, App Intents Spotlight and Visual Intelligence boundaries, BrowserEngineKit distribution boundaries, DeviceCheck/App Attest flows, DockKit camera control, EnergyKit event modeling, MapKit iOS 26 place lookup, PermissionKit availability, RelevanceKit relevance providers, SpeechAnalyzer/SpeechTranscriber usage, TabletopKit availability/back-deployment, WeatherKit context/statistics APIs, and WidgetKit controls/push reload behavior.
- Update Swift and SwiftUI guidance for current toolchains and platform APIs, including Swift 6.4 cleanup/build settings and synchronization primitives, `FormatStyle` parsing and URL formatting, Swift language interop attributes, Swift Testing migration and availability boundaries, SwiftLint plugin and baseline rollout, Swift Charts 3D/angle selection, SwiftUI Liquid Glass layering/status/tool-palette guidance, navigation sheet dismissal and typed routes, gesture precedence and availability, animation phase/keyframe behavior, list/scroll target behavior, performance diagnostics, UIKit interop observation/coordinator boundaries, and WebKit JavaScript/navigation boundaries.
- Strengthen sibling-boundary routing across skills so agents choose the correct skill for adjacent topics such as AccessorySetupKit vs CoreBluetooth, PaperKit vs PencilKit, SwiftData vs Core Data, StoreKit vs App Store Review, WidgetKit vs RelevanceKit, SwiftUI layout/navigation/animation/performance/patterns, and framework-specific security or networking handoffs.
- Add or refresh local Agent Skills eval definitions for the 83 audited skills and root Tessl scenarios covering setup flows, API-correction reviews, sibling-boundary routing, stale-claim detection, availability checks, and implementation-plan reviews.

## v3.5.0

### Repository

- Add a GitHub Actions workflow to publish the Tessl tile to the registry from release tags or manual dispatch.
- Add Tessl project metadata and MCP configuration for supported coding agents.
- Update Tessl tile and Claude Code plugin metadata for the 3.5.0 release.

## v3.4.1

### Repository

- Add Tessl tile configuration for the Swift iOS skills collection.
- Include README and changelog as Tessl tile documentation content.
- Format Swift `@` symbols in prose as inline code so Tessl and GitHub do not treat them as missing references or user mentions.

## v3.4.0

### New skills

- `swiftlint` — SwiftLint setup and enforcement: build tool plugin via SimplyDanny/SwiftLintPlugins, `.swiftlint.yml` configuration, rule selection strategy, `disabled_rules`/`opt_in_rules`/`only_rules`, baselines for incremental adoption, inline suppressions, autocorrect, CI integration with SARIF/GitHub Actions reporters, multiple configurations, regex custom rules, `swiftlint analyze`, multi-toolchain guidance

### Bundle changes

- Add `swiftlint` to `ios-engineering-skills` and `all-ios-skills` bundles.
- Update `all-ios-skills` count from 83 to 84.
- Update `ios-engineering-skills` description and keywords to include linting coverage.

### Repository

- Update README catalog, bundle table, install count, and skill listings for new skill.

## v3.3.0

### New skills

- `core-data` — Core Data persistence: NSPersistentContainer stack setup, NSFetchedResultsController, batch operations, persistent history tracking, staged migration (iOS 17+), composite attributes, testing patterns
- `swift-architecture` — Architecture pattern selection: MV (@Observable), MVVM, MVI, TCA, Clean Architecture, Coordinator pattern, decision framework, migration guidance
- `swift-formatstyle` — FormatStyle protocol and all concrete types: numbers, currency, percentages, dates, durations, measurements, person names, lists, byte counts, URLs, custom FormatStyle
- `focus-engine` — SwiftUI and UIKit focus behavior including `@FocusState`, `defaultFocus`, `focusedSceneValue`, `focusSection()`, focus restoration, and `UIFocusGuide`

### Skill updates

- `focus-engine` — Expand description to cover tvOS, watchOS, visionOS, macOS. Add references/multi-platform-focus.md (tvOS geometric model, watchOS Digital Crown, visionOS gaze/hover, macOS key view loop) and references/focus-debugging.md (UIFocusDebugger LLDB commands, anti-patterns)
- `ios-accessibility` — Add AppKit accessibility coverage for `NSAccessibilityProtocol`, `NSAccessibilityElement`, and AppKit accessibility notifications. Clarify that keyboard and directional focus belong in `focus-engine`. Add references/nutrition-labels.md (all 9 App Store Accessibility Nutrition Labels with pass/fail criteria) and references/media-accessibility.md (captions, audio descriptions, AVMediaCharacteristic, SDH)
- `swift-testing` — Add explicit execution-model guidance for default parallel execution, shared-state hazards, and `.serialized` scope semantics. Add CustomTestStringConvertible and @available-conditional test patterns to testing-patterns.md reference
- `swift-concurrency` — Add references/bridging-interop.md (checked continuations, delegate bridging, GCD migration table), references/diagnostics.md (compiler diagnostic → fix reference, strict concurrency adoption), references/async-algorithms.md (swift-async-algorithms: debounce, throttle, merge, combineLatest, chunks)
- `swiftdata` — Add references/predicate-pitfalls.md (#Predicate runtime crashes and unsupported expressions) and references/indexing.md (#Index macro, compound indexes, when to index)
- `swiftui-performance` — Add ternary-modifier pattern for preserving structural identity (avoid _ConditionalContent when toggling modifiers)
- `swiftui-patterns` — Replace primary custom environment example with modern `@Entry` guidance. Update design-polish haptics guidance to prefer SwiftUI `sensoryFeedback(_:trigger:)` and narrow the focus section to form-focus basics. Expand deprecated-migration.md with cornerRadius → clipShape, tabItem → Tab (iOS 18+), scrollIndicators(.hidden)

### Bundle changes

- Add `focus-engine` to `swiftui-skills` and `all-ios-skills` bundles.
- Add `core-data`, `swift-architecture`, `swift-formatstyle` to `swift-core-skills` and `all-ios-skills` bundles.
- Update `all-ios-skills` count from 79 to 83.
- Update `swiftui-skills` bundle description to include focus coverage.

### Repository

- Add AGENTS.md with repo-level agent instructions for skill authoring
- Update README catalog, bundle table, install count, and skill listings for new skills.

## v3.2.0

### New skills

- `app-store-optimization` -- ASO keyword strategy, title/subtitle optimization, description writing, screenshot captions, Custom Product Pages, in-app events, product page A/B testing
- `ios-simulator` -- xcrun simctl device lifecycle, push/location/permission simulation, log streaming, status bar overrides, screenshot/video capture, compile-time simulator detection, simulator limitations
- `swift-api-design-guidelines` -- Swift API Design Guidelines for argument labels, mutating/nonmutating pairs, side-effect naming, documentation comments, O(1) complexity rule, conventions

### Skill updates

- `ios-security` -- Replaced with `swift-security`, vendored from [ivan-magda/swift-security-skill](https://github.com/ivan-magda/swift-security-skill) by [Ivan Magda](https://github.com/ivan-magda). Deeper coverage of Keychain, CryptoKit, biometrics, Secure Enclave, OWASP compliance (14 reference files). Local fixes: corrected SHA-3 availability (iOS 26, not iOS 18), fixed `isValidSignature` parameter labels, fixed `evaluatedPolicyDomainState` typo, added `## Contents` section, converted references to markdown links, promoted Common Mistakes to H2. Migrated ATS and file storage content to `ios-networking`.
- `ios-accessibility` -- Add Voice Control, Switch Control, and Full Keyboard Access patterns to SKILL.md and a11y-patterns.md reference.
- `ios-localization` -- Add legacy formatter migration table to formatstyle-locale.md reference. Add "Generated Localizable Symbols (Xcode 26+)" section to SKILL.md and string-catalogs.md. Update description frontmatter. Improve stable key naming guidance for preventing silent localization breaks.
- `ios-networking` -- Add "App Transport Security (ATS)" section migrated from ios-security.
- `swiftui-patterns`, `swiftui-layout-components` -- Add "prefer adaptive spacing" rule to Common Mistakes and Review Checklist. Add HIG alignment guidance to prefer omitting `spacing:` on stacks (uses platform-adaptive default). Update design-polish.md spacing section with introductory guidance.
- `swiftui-patterns` -- Add "When a New ViewModel Is Justified" and "Environment vs. Initializer Injection" sections to architecture-patterns.md. Add modern `@Observable` ViewModel example with `@State` owner and `@Bindable` child pattern.
- `swiftui-patterns` -- Add `foregroundColor(_:)` to `foregroundStyle(_:)` migration entry in deprecated-migration.md with before/after examples.
- `swiftui-gestures` -- Add Common Mistake #6: `onTapGesture` for actions that should use `Button`. Add corresponding Review Checklist item.
- `widgetkit` -- Add "Design Patterns" section to SKILL.md and widgetkit-advanced.md: prefer `Gauge` for value indicators, `containerBackground(_:for: .widget)` for backgrounds, `Canvas` for dense visualizations, match timeline refresh to data granularity. Consolidate widget families table. Simplify Live Activity example.
- `device-integrity` -- Fix App Attest retry logic: guard final-attempt sleep, use modern `Task.sleep(for:)` API.
- `energykit` -- Remove unnecessary `MainActor.run` wrapping in energykit-patterns.md (already on MainActor), modernize retry loop and use `Task.sleep(for:)` API.

### Code example improvements

- Remove ~50 unnecessary hard-coded `spacing:` and `.padding(.direction, N)` values from code examples across 34 skill files. Examples now model the best practice of omitting spacing for adaptive platform defaults. Justified values retained: `spacing: 0` (zero-gap), tight grid gutters (2–4pt), chart API parameters, glass container API, and localization RTL demos.
- Replace `onTapGesture` with `Button` + `.buttonStyle(.plain)` for single-tap actions across natural-language, swiftui-animation, core-animation-bridge, and deprecated-migration code examples. Improves VoiceOver, Voice Control, Switch Control, and keyboard accessibility.
- Modernize `.clipShape(RoundedRectangle(cornerRadius:))` to `.clipShape(.rect(cornerRadius:))` shorthand across core-animation-bridge, hosting-migration, representable-recipes, and image-loading-caching.

### Bundle changes

- Add `app-store-optimization` to `ios-engineering-skills` and `all-ios-skills` bundles.
- Add `ios-simulator` to `ios-engineering-skills` and `all-ios-skills` bundles.
- Add `swift-api-design-guidelines` to `swift-core-skills` and `all-ios-skills` bundles.
- Update `all-ios-skills` count from 76 to 79.
- Replace `ios-security` with `swift-security` in `ios-engineering-skills` and `all-ios-skills` bundles.

### Repository

- Add issue templates for skill requests, content bugs, and enhancements.
- Add scripts for syncing and validating issue template dropdowns against marketplace.json.
- Add auto-assign workflow for newly opened issues.
- Update `actions/checkout` to v5 in CI workflows.
- Add GitHub Sponsors support section to README.
- Update skills CLI upgrade command in README.
- Update platform badge in README.

## v3.1.0

### Swift 6.3 update

- Bump all skills from Swift 6.2 to Swift 6.3 targeting.
- Add `async defer` (SE-0493) and clock epochs (SE-0473) to `swift-concurrency`.
- Add `@c` (SE-0495), `@specialized` (SE-0460), `@inline(always)` guarantee (SE-0496), `@export` (SE-0497), `@section`/`@used` (SE-0492), and module selectors (SE-0491) to `swift-language`.
- Add warning-severity issues (ST-0013), programmatic test cancellation (ST-0016), exit test value capturing (ST-0012), and image attachments (ST-0014) to `swift-testing`.
- Integrate Swift 6.3 features into existing topical sections instead of version-siloed sections.
- Rename version-based reference files to topic-based names (`swift-6-2-concurrency.md` → `concurrency-patterns.md`, `swift-6-3-features.md` → `swift-attributes-interop.md`, `swift-6-3-testing.md` → `testing-advanced.md`).
- Update README badge and description for Swift 6.3.
- Bump marketplace bundle versions to 3.1.0.

## v3.0.0

### Skill renames

12 existing skills renamed to use Apple Kit framework names for consistency:

- `live-activities` -> `activitykit`
- `mapkit-location` -> `mapkit`
- `photos-camera-media` -> `photokit`
- `homekit-matter` -> `homekit`
- `callkit-voip` -> `callkit`
- `metrickit-diagnostics` -> `metrickit`
- `pencilkit-drawing` -> `pencilkit`
- `passkit-wallet` -> `passkit`
- `musickit-audio` -> `musickit`
- `cloudkit-sync` -> `cloudkit`
- `eventkit-calendar` -> `eventkit`
- `realitykit-ar` -> `realitykit`

### New skills

19 new Apple Kit framework skills, all grounded in official Apple documentation:

- `avkit` -- AVPlayerViewController, VideoPlayer, Picture-in-Picture, AirPlay, subtitles
- `gamekit` -- Game Center, leaderboards, achievements, real-time and turn-based multiplayer
- `cryptokit` -- SHA256, HMAC, AES-GCM, ChaChaPoly, P256/Curve25519 signing, Secure Enclave
- `pdfkit` -- PDFView, PDFDocument, annotations, text search, form filling, thumbnails
- `paperkit` -- PaperMarkupViewController, markup editing, drawing, shapes (iOS 26)
- `spritekit` -- SKScene, SKSpriteNode, SKAction, physics, particles, SpriteView
- `scenekit` -- SCNView, SCNScene, 3D geometry, materials, lighting, physics, SceneView
- `financekit` -- Apple Card, Apple Cash, Wallet orders, transactions, account balances
- `accessorysetupkit` -- Privacy-preserving BLE/Wi-Fi accessory discovery, picker UI
- `adattributionkit` -- Privacy-preserving ad attribution, postbacks, conversion values
- `carplay` -- CarPlay templates, navigation, audio, communication, EV charging apps
- `appmigrationkit` -- Cross-platform data transfer, export/import extensions (iOS 26)
- `browserenginekit` -- Alternative browser engines (EU), process management, web content
- `dockkit` -- DockAccessoryManager, camera subject tracking, motor control, framing
- `sensorkit` -- Research-grade sensor data, ambient light, keyboard metrics (approved studies)
- `tabletopkit` -- Multiplayer spatial board games, pieces, cards, dice (visionOS)
- `relevancekit` -- Widget relevance signals, time/location-based providers (watchOS 26)
- `audioaccessorykit` -- Audio accessory features, automatic switching (iOS 26.4)
- `cryptotokenkit` -- TKTokenDriver, TKSmartCard, iOS 26 NFC smart cards, certificate-based auth

### Bundle changes

- Add `apple-kit-skills` bundle containing 39 skills spanning Apple Kit frameworks plus CarPlay.
- Add `ios-gaming-skills` bundle containing `gamekit`, `spritekit`, `scenekit`, `tabletopkit`.
- Distribute new skills into existing themed bundles.
- Update `all-ios-skills` count from 57 to 76.
- Fix all renamed skill paths across all existing bundles.

### Other changes

- Remove PaperKit content from `pencilkit` (now standalone `paperkit` skill).
- Update README catalog, descriptions, counts, install commands, and upgrade guidance.
- Bump Claude marketplace bundle versions to 3.0.0.

### API accuracy fixes

- Fix 15+ incorrect deprecation claims across skills (RotationGesture, .tabItem, .navigationBarLeading/Trailing, IntentTimelineProvider, original StoreKit APIs were not deprecated).
- Correct API usage in activitykit, background-processing, cloudkit, debugging-instruments, energykit, shareplay-activities, swift-concurrency, and swift-testing.
- Clarify BrowserEngineKit EU/Japan distribution requirements.

### Structural improvements

- Add missing scope statements to debugging-instruments, swiftui-liquid-glass, and swiftui-performance.
- Trim photokit SKILL.md to under 500-line limit.
- Refactor metrickit and device-integrity to extract deep detail into reference files.
- Expand thin reference files in swiftui-layout-components, swiftui-performance, and swiftui-webkit.
- Add Contents sections to reference files in background-processing, swiftui-gestures, and swiftui-navigation.
- Convert all reference paths from backtick to markdown link syntax across all 76 skills.

### Link and cross-reference fixes

- Normalize all Sosumi documentation paths to lowercase.
- Repair broken self-anchor links across skills.
- Replace stale pre-rename skill names in reference file intros.
- Remove broken reference to background-websocket.md in ios-networking.
- Fix malformed key-path syntax in swiftui-performance reference.
- Clarify themed bundle purpose in README (context window management, not disk savings).
- Update apple-kit-skills description to include CarPlay.

## v2.2.0

- Add `swiftui-webkit`, a new SwiftUI skill for native WebKit-for-SwiftUI APIs including `WebView`, `WebPage`, navigation policies, JavaScript calls, observable page state, and custom URL schemes.
- Narrow `swiftui-uikit-interop` back to generic interop guidance by removing `WKWebView` and `SFSafariViewController` recipes from its representable reference file and demoting web-content ownership.
- Update the README catalog and marketplace metadata to include `swiftui-webkit`, add it to the `swiftui-skills` and `all-ios-skills` bundles, and raise the total skill count from 56 to 57.
- Bump Claude marketplace bundle versions to 2.2.0.

## v2.1.1

- Consolidate repeated sibling-skill cross-references in `swiftui-patterns` into a single scope-boundary note; remove redundant redirect sections and sibling-skill routing from frontmatter description.
- Consolidate repeated `apple-on-device-ai` cross-references in `coreml` and remove cross-skill file paths that violated self-containment.
- Bump Claude marketplace bundle versions to 2.1.1.

## v2.1.0

- Rename `codable-patterns` to `swift-codable` to improve discoverability and align it with the repo's `swift-*` core-language taxonomy.
- Tighten discovery wording for `swift-codable`, `alarmkit`, `app-clips`, and `app-intents` in skill metadata and the README catalog.
- Clarify installation guidance in `README.md`, including skills CLI usage and the direct install command for all skills.
- Remove stale MCP appendix/tool-note sections from `swiftui-liquid-glass`, `swift-testing`, and `swiftui-performance`; keep Release-build and real-device profiling guidance inline in the performance skill.
- Add `firebase-debug.log` to `.gitignore`.
- Bump Claude marketplace bundle versions to 2.1.0.

## v2.0.1

- Update `swiftui-animation` to cover `.animation(_:body:)` alongside `.animation(_:value:)`, and tighten wording around bare `.animation(_:)` and scoped transactions to match Apple docs.
- Switch the repository license to PolyForm Perimeter 1.0.0 and update the README badge/license text.
- Add `.playwright-mcp` and `tmp` to `.gitignore`.
- Bump Claude marketplace bundle versions to 2.0.1.

## v2.0.0

### New skills (33 added)

**SwiftUI (3)**
- `swiftui-gestures` — Tap, drag, magnify, rotate, long press, simultaneous and sequential gestures
- `swiftui-layout-components` — Grid, LazyVGrid, Layout protocol, ViewThatFits, custom layouts
- `swiftui-navigation` — NavigationStack, NavigationSplitView, programmatic navigation, deep linking

**Core Swift (1)**
- `swift-language` — Swift 6.2 features, macros, result builders, property wrappers

**App Experience Frameworks (3)**
- `alarmkit` — AlarmKit alarms and countdown timers, Live Activity integration, AlarmAttributes, AlarmButton
- `app-clips` — App Clip experiences, invocation, size limits, shared data
- `photos-camera-media` — PhotosPicker, AVCaptureSession, photo library, video recording, media permissions

**Data & Service Frameworks (7)**
- `cloudkit-sync` — CKContainer, CKRecord, subscriptions, sharing, NSPersistentCloudKitContainer
- `contacts-framework` — CNContactStore, fetch requests, key descriptors, CNContactPickerViewController, save requests
- `eventkit-calendar` — EKEventStore, EKEvent, EKReminder, recurrence rules, EventKitUI editors and choosers
- `healthkit` — HKHealthStore, queries, statistics, workout sessions, background delivery
- `musickit-audio` — MusicKit authorization, catalog search, ApplicationMusicPlayer, MPRemoteCommandCenter
- `passkit-wallet` — Apple Pay, PKPaymentRequest, PKPaymentAuthorizationController, Wallet passes
- `weatherkit` — WeatherService, current/hourly/daily forecasts, alerts, attribution requirements

**AI & Machine Learning (3)**
- `coreml` — Core ML model loading, prediction, MLTensor, compute unit configuration, VNCoreMLRequest, MLComputePlan
- `natural-language` — NLTokenizer, NLTagger, sentiment analysis, language identification, embeddings, Translation
- `speech-recognition` — SFSpeechRecognizer, on-device recognition, audio buffer processing

**iOS Engineering (5)**
- `authentication` — Sign in with Apple, ASAuthorizationController, passkeys, biometric auth (LAContext), credential management
- `background-processing` — BGTaskScheduler, background refresh, URLSession background transfers
- `device-integrity` — DeviceCheck (DCDevice per-device bits), App Attest (DCAppAttestService attestation and assertion flows)
- `metrickit-diagnostics` — MXMetricManager, hang diagnostics, crash reports, power metrics
- `ios-localization` — String Catalogs, pluralization, FormatStyle, right-to-left layout

**Hardware & Device Integration (4)**
- `core-motion` — CMMotionManager, CMPedometer, accelerometer, gyroscope, activity recognition, altitude
- `core-nfc` — NFCNDEFReaderSession, NFCTagReaderSession, NDEF reading/writing, background tag reading
- `pencilkit-drawing` — PKCanvasView, PKDrawing, PKToolPicker, Apple Pencil, PaperKit integration
- `realitykit-ar` — RealityView, entities, anchors, ARKit world tracking, raycasting, scene understanding

**Platform Integration (7)**
- `callkit-voip` — CXProvider, CXCallController, PushKit VoIP registration, call directory extensions
- `energykit` — ElectricityGuidance, EnergyVenue, grid forecasts, load event submission, electricity insights
- `homekit-matter` — HMHomeManager, accessories, rooms, actions, triggers, MatterSupport commissioning
- `mapkit-location` — MapKit, CoreLocation, annotations, geocoding, directions, geofencing
- `permissionkit` — AskCenter, PermissionQuestion, child communication safety, CommunicationLimits
- `shareplay-activities` — GroupActivity, GroupSession, GroupSessionMessenger, coordinated media playback
- `apple-on-device-ai` — Foundation Models framework, Core ML, MLX Swift, on-device LLM inference

### Skill refactors

- **swiftui-patterns** split into `swiftui-patterns`, `swiftui-navigation`, and `swiftui-layout-components` — each is now self-contained with no cross-references.
- **ios-security** split into `ios-security`, `authentication`, and `device-integrity` — each owns a clear domain boundary. `ios-security` covers Keychain/CryptoKit/data protection. `authentication` covers Sign in with Apple, passkeys, and biometric sign-in. `device-integrity` covers DeviceCheck and App Attest.
- All skills now self-contained with 4 or fewer reference files. No skill references another skill's files.

### Bundle restructure

v1.x had 6 themed bundles + 1 all-skills bundle. v2.0 has 8 themed bundles + 1 all-skills bundle.

Changes:
- `ios-framework-skills` (17 skills) split into `ios-app-framework-skills` (10) and `ios-data-framework-skills` (7).
- New `ios-ai-ml-skills` bundle created with `apple-on-device-ai`, `coreml`, `natural-language`, `speech-recognition`, `vision-framework`.
- AI/ML skills removed from `ios-engineering-skills` and `ios-platform-skills`.
- `ios-platform-skills` trimmed to 5 specialized platform integrations (HomeKit, SharePlay, CallKit, PermissionKit, EnergyKit).
- `ios-engineering-skills` refocused on 10 core engineering skills (networking, security, auth, accessibility, localization, debugging, diagnostics, background processing, device integrity, App Store review).

### Metadata improvements

- All 56 skill descriptions aligned with Agent Skills best practices.
- Bundle descriptions shortened and focused on user intent.
- Missing keywords added for major frameworks (Sendable, async-await, Foundation Models, BLE, Matter, etc.).
- All iOS 26 API claims verified against Apple documentation.

### Beta framework caveats

Three skills reference iOS 26 beta-only frameworks that may change before GM:
- `permissionkit` — PermissionKit (AskCenter, PermissionQuestion, CommunicationLimits)
- `energykit` — EnergyKit (ElectricityGuidance, EnergyVenue)
- `pencilkit-drawing` — references PaperKit integration

### Migration notes

- **Bundle name change**: `ios-framework-skills` no longer exists. Reinstall as `ios-app-framework-skills` and/or `ios-data-framework-skills`.
- **Skill file paths changed**: `swiftui-patterns/references/` files were reorganized during the split into three skills. Tools or scripts referencing old paths will need updating.
- **No breaking API changes**: All skills remain independently installable via `npx skills add` or `/plugin install`.

## v1.1.0

- Remove apple-docs MCP server references from skills.
- Fix npx skills CLI install commands in README.
- Bump plugin versions to 1.1.0.

## v1.0.0

- Initial release with 23 iOS and Swift development skills.
- 6 themed Claude Code plugin bundles + 1 all-skills bundle.
