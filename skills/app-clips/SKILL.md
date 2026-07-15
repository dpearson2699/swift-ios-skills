---
name: app-clips
description: "Build iOS App Clips with invocation URLs, App Clip Codes, NFC, QR codes, Safari banners, Maps, Messages, target setup, App Store Connect experiences, size/capability constraints, NSUserActivity routing, SKOverlay promotion, App Group/keychain handoff, ephemeral notifications, location confirmation, and full-app migration. Use when creating App Clips or wiring App Clip invocation, experience configuration, or full-app handoff."
---

# App Clips

Build lightweight, instantly available versions of an iOS app for focused in-the-moment experiences or demos.

## Contents

- [App Clip Target Setup](#app-clip-target-setup)
- [Invocation and Experience Routing](#invocation-and-experience-routing)
- [Size and Capability Decisions](#size-and-capability-decisions)
- [Data, Notifications, and Location](#data-notifications-and-location)
- [Common Mistakes](#common-mistakes)
- [Review Checklist](#review-checklist)
- [References](#references)

## App Clip Target Setup

An App Clip is a **separate target** in the same Xcode project as your full app:

1. **File → New → Target → App Clip** — Xcode creates the App Clip target, adds the **Embed App Clip** build phase to the full app target, and wires the association entitlements.
2. The App Clip bundle ID **must** be prefixed by the full app's bundle ID: `com.example.MyApp.Clip`.
3. Verify raw entitlement keys when diagnosing archive, signing, or App Store Connect failures:
   - App Clip target: `com.apple.developer.on-demand-install-capable`
   - App Clip target parent app link: `com.apple.developer.parent-application-identifiers`
   - Full app target associated App Clip link: `com.apple.developer.associated-appclip-app-identifiers`

Use Swift packages or shared source files for code needed by both targets. Add App Clip-specific compile branches with the `APPCLIP` active compilation condition, and avoid linking full-app-only frameworks into the App Clip target.

## Invocation and Experience Routing

Read [`references/routing-and-experiences.md`](references/routing-and-experiences.md) when implementing invocation URL routing, App Store Connect experiences, Local Experiences, Safari Smart App Banners, QR/NFC/App Clip Codes, AASA, or associated domains.

App Clips receive `NSUserActivityTypeBrowsingWeb` activities. Keep the invocation router shared with the full app because, after installation, the full app replaces the App Clip and receives future invocations.

- SwiftUI: use `.onContinueUserActivity(NSUserActivityTypeBrowsingWeb)`.
- UIKit cold launch: inspect `connectionOptions.userActivities` in `scene(_:willConnectTo:options:)`.
- UIKit continuation: handle the actual `NSUserActivity` in `scene(_:continue:)`.
- `scene(_:willContinueUserActivityWithType:)` is only advance notice and does not provide the URL.

Configure the required default App Clip experience in App Store Connect. Use advanced experiences for Maps integration, location association, production App Clip Codes, per-location cards, and precise physical-place routing; demo App Clip Codes can use the short demo App Clip link.

For custom URLs, add `appclips:example.com` to Associated Domains on both the full app and App Clip targets, and host an AASA file with the App Clip app identifier. For Safari banners, use `app-id`, `app-clip-bundle-id`, and optional `app-clip-display=card`; do not rely on `app-argument` for App Clip launches.

## Size and Capability Decisions

Read [`references/size-capabilities-and-promotion.md`](references/size-capabilities-and-promotion.md) before feasibility reviews or capability audits, and when checking size budgets, measurement, Background Assets, SKOverlay, Live Activities App Clip extension constraints, CloudKit limits, or unsupported capabilities.

Always measure App Clip size with the App Thinning Size Report. In feasibility reviews, explicitly choose the size limit from deployment target, invocation support, and connectivity: the larger iOS 17+ limit applies to digital-only App Clips where reliable internet is likely; physical invocation or iOS 16 support uses a smaller budget; demo links can use the current 100 MB limit while supporting NFC/QR test invocations, and demo App Clip Codes require the short demo link. Apple has changed App Clip size policy over time, so re-check current App Store Connect and App Clip documentation before release-blocking size decisions.

Use Background Assets only for content that can arrive after launch without blocking the in-the-moment task, and do not mark App Clip background asset downloads as essential. Large bundled media, ML models, catalogs, or downloads that must finish before useful work are poor App Clip fits; state that required pre-task downloads are not acceptable for in-the-moment App Clips, and check download size plus whether any required download blocks useful work. Move those flows to streaming/server-backed content, post-task assets, or the full app. Show `SKOverlay.AppClipConfiguration` or SwiftUI `appStoreOverlay` only after task completion, never as a gate.

App Clips can use CloudKit public database reads on iOS 16+ with `CloudKit-Anonymous`, but cannot write the public database or use iCloud Documents, key-value storage, private containers, or shared containers. App Clips can offer Live Activities through an App Clip-only widget extension starting in iOS 16. That extension can include only Live Activities and needs the App Clip Extension capability; always include the raw entitlement key `com.apple.developer.on-demand-install-capable` when reviewing this boundary.

In feasibility reviews, explicitly name unsupported App Clip runtime features instead of summarizing them generically. Always list `SKAdNetwork`, `App Tracking Transparency`, and custom URL schemes when discussing excluded runtime features, alongside App Intents, Background Tasks, background URL sessions, in-app purchases, durable persistent local state, and background/persistent assumptions. Route detailed ActivityKit/WidgetKit Live Activity work, StoreKit purchase/full-app monetization, BackgroundTasks processing, CloudKit schema or sync beyond public reads, durable credentials, and long-term state to sibling or full-app domains without implementation detail. For product/PM feasibility reviews, stay at the App Clip boundary level: capability fit, size basis, invocation constraints, and handoff destinations. Describe location confirmation, install promotion, App Group/keychain handoff, and Live Activities conceptually. Do not add Swift package decomposition, API symbols such as `APActivationPayload`, `CLCircularRegion`, or `SKOverlay.AppClipConfiguration`, App Group/keychain implementation recipes, or other API-level implementation guidance unless the user asks for implementation.

## Data, Notifications, and Location

Read [`references/data-handoff-notifications-location.md`](references/data-handoff-notifications-location.md) when implementing App Group/full-app migration, keychain or Sign in with Apple handoff, ephemeral notifications, notification relaunch routing, or physical location confirmation.

Use App Groups/shared containers for non-secret handoff data only. Any target provisioned with the App Group entitlement can read and write the shared container/defaults suite, so it is not a trust boundary. Do not put passwords, refresh tokens, payment credentials, or other secrets there.

Starting in iOS 15.4, the full app can access keychain items created by its corresponding App Clip only when the App Clip and full app have the correct association entitlements, including the full app's `com.apple.developer.associated-appclip-app-identifiers`. The App Clip cannot read keychain items created by the full app.

For Sign in with Apple handoff, store the `ASAuthorizationAppleIDCredential.user` identifier and have the full app verify `ASAuthorizationAppleIDProvider.getCredentialState(forUserID:) == .authorized`.

For ephemeral notifications, set `NSAppClipRequestEphemeralUserNotification` under the App Clip target's `NSAppClip` `Info.plist` dictionary. Authorization can last up to 8 hours after each launch, but users can disable it on the App Clip card, so check notification settings for `.ephemeral` before scheduling. Notification taps relaunch without the original invocation URL, so route multi-experience notifications with APNs `target-content-id` for remote notifications or `UNNotificationContent.targetContentIdentifier` for local notifications. Use a URL matching the relevant App Store Connect advanced App Clip experience, not an arbitrary opaque ID.

For physical-location confirmation, use `NSUserActivity.appClipActivationPayload` / `APActivationPayload.confirmAcquired(in:)` with a `CLCircularRegion` radius up to 500 meters, and set `NSAppClipRequestLocationConfirmation` under the App Clip target's `NSAppClip` `Info.plist` dictionary, not the full app's. This confirms eligible physical invocations without granting continuous location access.

## Common Mistakes

### Exceeding the applicable App Clip size limit

Choose the limit based on deployment target and invocation support. A physically invoked App Clip that supports iOS 16 has a much smaller budget than an iOS 17+ digital-only App Clip. Measure with the App Thinning Size Report after meaningful target changes.

### Mixing up App Clip entitlement names

```text
App Clip target:
com.apple.developer.on-demand-install-capable
com.apple.developer.parent-application-identifiers

Full app target:
com.apple.developer.associated-appclip-app-identifiers
```

Display names in Xcode differ from raw entitlement keys; use raw keys when debugging signing output or archived entitlements.

### Treating UIKit continuation notification as URL handling

`scene(_:willContinueUserActivityWithType:)` does not include the `NSUserActivity`. Handle the URL in `scene(_:willConnectTo:options:)` for cold launch and `scene(_:continue:)` for activity continuation.

### Not testing invocation URLs locally

A direct Xcode launch can skip the invocation path and hide routing bugs. Use the `_XCAppClipURL` scheme environment variable or register a Local Experience in Settings → Developer → Local Experiences.

### Not handling the full app replacing the App Clip

Share invocation routing with the full app. After install, all future invocations go to the full app.

### Storing secrets in App Group storage

Use App Groups for non-secret handoff state only. Use keychain or server-side verification for credentials.

### Designing a marketing-only or web-view-heavy App Clip

App Clips should let people complete a focused task or full demo without installing the app. Avoid marketing-only clips, ad-heavy flows, splash screens, launch-blocking downloads, repeated install prompts, and web-view-heavy experiences that would work better as a website.

### Missing associated domains configuration

Add `appclips:example.com` to Associated Domains on both the full app and App Clip targets, and host `/.well-known/apple-app-site-association` with the App Clip app identifier for custom URL invocations and advanced experiences.

## Review Checklist

- [ ] App Clip target bundle ID is prefixed by the full app's bundle ID.
- [ ] App Clip target has `com.apple.developer.on-demand-install-capable`.
- [ ] App Clip target has `com.apple.developer.parent-application-identifiers`.
- [ ] Full app target has `com.apple.developer.associated-appclip-app-identifiers`.
- [ ] Shared code uses Swift packages or compilation conditions (`APPCLIP`).
- [ ] SwiftUI uses `.onContinueUserActivity(NSUserActivityTypeBrowsingWeb)` for invocation routing.
- [ ] UIKit cold launch checks `connectionOptions.userActivities` and continuation handles `scene(_:continue:)`.
- [ ] Full app handles every invocation URL the App Clip supports.
- [ ] App Thinning Size Report confirms the binary is within the limit for deployment target and invocation support; size reviews name the 10 MB, 15 MB, and current 100 MB tiers when size is at issue.
- [ ] Associated Domains entitlement includes `appclips:yourdomain.com` on both full app and App Clip targets when using custom URLs.
- [ ] AASA file is hosted at `/.well-known/apple-app-site-association` when using custom URLs.
- [ ] Default App Clip experience is configured in App Store Connect.
- [ ] Production App Clip Codes, Maps, or per-location cards use advanced experiences; demo App Clip Codes use the short demo link.
- [ ] Live Activities, when mentioned, are limited to an App Clip-only widget extension with only Live Activities and the raw `com.apple.developer.on-demand-install-capable` entitlement.
- [ ] Shared App Group storage contains only non-secret data the full app needs, never credentials or payment secrets.
- [ ] Keychain handoff states the one-way rule: the full app can read App Clip-created items on iOS 15.4+ with correct association entitlements, but the App Clip cannot read full-app keychain items.
- [ ] Sign in with Apple migration verifies credential state in the full app.
- [ ] `SKOverlay` / `appStoreOverlay` appears after task completion, never as a gate.
- [ ] `NSAppClipRequestLocationConfirmation` is set only in the App Clip target if using location confirmation.
- [ ] Ephemeral notification code checks for `.ephemeral` authorization before scheduling because the card permission can be disabled.
- [ ] Ephemeral notification routing handles relaunch without an invocation URL.
- [ ] HIG review rejects marketing-only, ad-heavy, web-view-heavy, install-gated, or launch-blocking App Clip designs.
- [ ] Unsupported runtime features are named explicitly, including durable persistent local state and background/persistent assumptions, not just unavailable frameworks.
- [ ] No reliance on background processing, restricted frameworks, custom URL schemes, in-app purchases, or persistent local storage.
- [ ] Sibling handoff is boundary-only, with no ActivityKit, StoreKit, BackgroundTasks, CloudKit, Swift package, App Group/keychain recipe, location-confirmation API symbol, `SKOverlay`, or framework-snippet implementation detail in App Clip feasibility answers.
- [ ] Tested with Local Experiences and `_XCAppClipURL`.

## References

- [Routing and experiences](references/routing-and-experiences.md)
- [Data handoff, notifications, and location](references/data-handoff-notifications-location.md)
- [Size, capabilities, and promotion](references/size-capabilities-and-promotion.md)
- [App Clips framework](https://sosumi.ai/documentation/appclip/)
- [Creating an App Clip with Xcode](https://sosumi.ai/documentation/appclip/creating-an-app-clip-with-xcode/)
- [Configuring App Clip experiences](https://sosumi.ai/documentation/appclip/configuring-the-launch-experience-of-your-app-clip/)
- [Responding to invocations](https://sosumi.ai/documentation/appclip/responding-to-invocations/)
- [Choosing the right functionality](https://sosumi.ai/documentation/appclip/choosing-the-right-functionality-for-your-app-clip/)
- [Confirming a person's physical location](https://sosumi.ai/documentation/appclip/confirming-a-person-s-physical-location/)
- [Sharing data between App Clip and full app](https://sosumi.ai/documentation/appclip/sharing-data-between-your-app-clip-and-your-full-app/)
- [Enabling notifications in App Clips](https://sosumi.ai/documentation/appclip/enabling-notifications-in-app-clips/)
- [Supporting invocations from your website and the Messages app](https://sosumi.ai/documentation/appclip/supporting-invocations-from-your-website-and-the-messages-app/)
- [Offering Live Activities with your App Clip](https://sosumi.ai/documentation/appclip/offering-live-activities-with-your-app-clip/)
- [Recommending your app to App Clip users](https://sosumi.ai/documentation/appclip/recommending-your-app-to-app-clip-users/)
- [APActivationPayload](https://sosumi.ai/documentation/appclip/apactivationpayload/)
- [SKOverlay.AppClipConfiguration](https://sosumi.ai/documentation/storekit/skoverlay/appclipconfiguration/)
- [NSUserActivityTypeBrowsingWeb](https://sosumi.ai/documentation/foundation/nsuseractivitytypebrowsingweb/)
- [Creating App Clip Codes](https://sosumi.ai/documentation/appclip/creating-app-clip-codes/)
- [Distributing your App Clip](https://sosumi.ai/documentation/appclip/distributing-your-app-clip/)
- [App Clips HIG](https://sosumi.ai/design/human-interface-guidelines/app-clips/)
