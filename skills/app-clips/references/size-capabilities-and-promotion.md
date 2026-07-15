# App Clip Size, Capabilities, and Promotion

Use this before App Clip feasibility reviews or capability audits, and when checking size budgets, measurement, Background Assets, SKOverlay, Live Activities App Clip extension constraints, CloudKit limits, or unsupported capabilities.

## Contents

- [Feasibility Review Template](#feasibility-review-template)
- [Size Limits](#size-limits)
- [Background Assets](#background-assets)
- [SKOverlay for Full App Promotion](#skoverlay-for-full-app-promotion)
- [Capabilities and Limitations](#capabilities-and-limitations)
- [Additional Restrictions](#additional-restrictions)
- [Release Review Checklist](#release-review-checklist)

## Feasibility Review Template

For capability reviews, explicitly cover:

- Size basis: deployment target, physical versus digital invocation, reliable-internet expectation, App Thinning Size Report, and demo-link/App Clip Code constraints.
- Download fit: large bundled media, ML models, catalogs, or required pre-task downloads should move to streaming/server-backed content, post-task assets, or the full app.
- UX fit: reject marketing-only, ad-heavy, web-view-heavy, install-gated, or launch-blocking App Clip designs.
- CloudKit boundary: App Clips can read the public database on iOS 16+ with `CloudKit-Anonymous`; do not plan public writes, iCloud Documents, key-value storage, private/shared containers, full CloudKit sync, or durable offline state in the App Clip.
- Live Activities boundary: App Clip-only widget extension, Live Activities only, App Clip Extension capability, and exact raw entitlement key `com.apple.developer.on-demand-install-capable`; hand implementation details to ActivityKit/WidgetKit.
- Unsupported runtime features: name App Intents, Background Tasks, background URL sessions, custom URL schemes, in-app purchases, durable persistent local state, SKAdNetwork, and App Tracking Transparency when relevant.
- Sibling handoff: keep this skill at feasibility and App Clip boundary level; route StoreKit purchases, BackgroundTasks, CloudKit schema/sync, detailed ActivityKit/WidgetKit work, durable credentials, and long-term state to sibling or full-app domains.
- Depth control: for product/PM feasibility reviews, stop at capability fit, size basis, invocation constraints, and handoff destinations. Describe location confirmation, install promotion, App Group/keychain handoff, and Live Activities conceptually. Do not add Swift package decomposition, API symbols such as `APActivationPayload`, `CLCircularRegion`, or `SKOverlay.AppClipConfiguration`, App Group/keychain implementation recipes, or other API-level implementation guidance unless the user asks for implementation.

## Size Limits

App Clip binaries must stay within strict uncompressed size limits, measured with the App Thinning Size Report:

| Deployment / Invocation Support | Maximum Uncompressed Size |
|---|---|
| iOS 15 and earlier | 10 MB |
| iOS 16 and earlier | 15 MB |
| iOS 17 and later | 100 MB |

The larger iOS 17+ limit is for digital invocations where a reliable internet connection is likely, when the App Clip does not support physical invocations and does not support iOS 16 or earlier. Physical invocation or iOS 16 support uses a smaller budget. App Store Connect demo links can use the larger limit while supporting NFC tags and QR codes for testing; demo App Clip Codes require the short demo link. Apple has changed App Clip size policy over time, so re-check the current App Store Connect and App Clip documentation before making release-blocking decisions.

**Measure size:** Archive the app → Distribute → Export as Ad Hoc/Development with App Thinning → check `App Thinning Size Report.txt`.

For feasibility reviews, name the size basis explicitly: deployment target, physical versus digital invocation, reliable-internet expectation, and whether demo links or App Clip Codes are in scope.

## Background Assets

Use Background Assets only for content that can arrive after launch without blocking the in-the-moment task. App Clips cannot set a background asset download's priority to essential with `isEssential`. They are a poor fit for large bundled media, ML models, catalogs, or downloads that must finish before useful work. Move those flows to streaming/server-backed content, post-task assets, or the full app.

## SKOverlay for Full App Promotion

Display an overlay recommending the full app from within the App Clip.

### SwiftUI

```swift
struct OrderCompleteView: View {
    @State private var showOverlay = false

    var body: some View {
        VStack {
            Text("Order placed!")
            Button("Get the full app") { showOverlay = true }
        }
        .appStoreOverlay(isPresented: $showOverlay) {
            SKOverlay.AppClipConfiguration(position: .bottom)
        }
    }
}
```

### UIKit

```swift
func displayOverlay() {
    guard let scene = view.window?.windowScene else { return }

    let config = SKOverlay.AppClipConfiguration(position: .bottom)
    let overlay = SKOverlay(configuration: config)
    overlay.delegate = self
    overlay.present(in: scene)
}
```

`SKOverlay.AppClipConfiguration` resolves to the App Clip's corresponding full app. Available iOS 14.0+.

**Never** block the user's task to force installation — show the overlay after task completion.

## Capabilities and Limitations

### Available to App Clips

SwiftUI, UIKit, Core Location (when-in-use), Sign in with Apple, Apple Pay, CloudKit public database reads only with `CloudKit-Anonymous` (iOS 16+), Background Assets, StoreKit `SKOverlay`, Keychain, App Groups, ephemeral notifications, and Live Activities through an App Clip-only widget extension.

### Live Activities

Starting in iOS 16, an App Clip can offer a Live Activity through a widget extension that belongs only to the App Clip. That extension can include only Live Activities, not ordinary widgets, and it needs the App Clip Extension capability. When reviewing this boundary, always name the exact raw entitlement key: `com.apple.developer.on-demand-install-capable`. Keep detailed ActivityKit and WidgetKit implementation guidance in those sibling skills.

### Not available / no runtime functionality

In feasibility reviews, explicitly name restricted or unsupported App Clip runtime features instead of summarizing them generically: App Intents, Background Tasks, background URL sessions, custom URL schemes, in-app purchases, durable persistent local state, SKAdNetwork, App Tracking Transparency, CallKit, Contacts, CoreMotion, EventKit, HealthKit, HomeKit, MediaPlayer, Messages, NearbyInteraction, PhotoKit, SensorKit, and Speech.

## Additional Restrictions

- No background URL sessions.
- No background Bluetooth.
- No multiple scenes on iPad.
- No on-demand resources.
- No custom URL schemes.
- No in-app purchases; reserve purchase flows for the full app and StoreKit sibling guidance.
- No durable local-state guarantee; migrate important non-secret state to a server or full-app handoff.
- No CloudKit public writes, iCloud Documents, iCloud key-value storage, private containers, or shared containers.
- No App Clip design that requires install, marketing exposure, web-view navigation, or blocking downloads before the user gets value.
- Hand off detailed ActivityKit/WidgetKit Live Activity implementation, StoreKit purchase/full-app monetization, BackgroundTasks processing, CloudKit schema or sync beyond public reads, durable credentials, and long-term state to sibling or full-app domains without adding implementation detail here.
- In feasibility answers, avoid implementation-level Swift package routing, App Group/keychain recipes, location-confirmation API symbols, `SKOverlay` API calls, or framework snippets unless the user explicitly asks for implementation.
- `UIDevice.name` and `identifierForVendor` return empty strings.

## Release Review Checklist

- [ ] App Clip target bundle ID is prefixed by the full app's bundle ID.
- [ ] All three raw App Clip association/installation entitlement keys are on the correct targets.
- [ ] Shared code uses Swift packages or the `APPCLIP` compilation condition.
- [ ] SwiftUI and UIKit cold-launch/continuation routes handle every supported invocation URL in both the App Clip and full app.
- [ ] Associated domains and AASA are correct for every custom invocation domain.
- [ ] The default experience exists; production codes, Maps, and per-location cards use advanced experiences where required.
- [ ] The App Thinning Size Report passes the applicable deployment/invocation limit.
- [ ] Unsupported capabilities and launch-blocking downloads are absent or handed to the full app.
- [ ] App Group data is non-secret; keychain and Sign in with Apple handoff follow the documented one-way and credential-state checks.
- [ ] Ephemeral notification permission and relaunch routing handle disabled access and missing invocation URLs.
- [ ] Location confirmation keys are on the App Clip target only.
- [ ] The design completes a focused task and rejects marketing-only, ad-heavy, web-view-heavy, or install-gated flows.
- [ ] Local Experiences and `_XCAppClipURL` invocation tests pass.
