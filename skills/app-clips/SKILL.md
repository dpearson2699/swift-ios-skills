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

**Validation checkpoint:** Archive both targets and inspect their archived
entitlements. If signing or validation fails, correct the three raw key/target
assignments above and rearchive until both pass.

## Invocation and Experience Routing

Read [`references/routing-and-experiences.md`](references/routing-and-experiences.md) when implementing invocation URL routing, App Store Connect experiences, Local Experiences, Safari Smart App Banners, QR/NFC/App Clip Codes, AASA, or associated domains.

App Clips receive `NSUserActivityTypeBrowsingWeb` activities. Keep the invocation router shared with the full app because, after installation, the full app replaces the App Clip and receives future invocations.

- SwiftUI: use `.onContinueUserActivity(NSUserActivityTypeBrowsingWeb)`.
- UIKit cold launch: inspect `connectionOptions.userActivities` in `scene(_:willConnectTo:options:)`.
- UIKit continuation: handle the actual `NSUserActivity` in `scene(_:continue:)`.
- `scene(_:willContinueUserActivityWithType:)` is only advance notice and does not provide the URL.

Configure the required default App Clip experience in App Store Connect. Use advanced experiences for Maps integration, location association, production App Clip Codes, per-location cards, and precise physical-place routing; demo App Clip Codes can use the short demo App Clip link.

For custom URLs, add `appclips:example.com` to Associated Domains on both the full app and App Clip targets, and host an AASA file with the App Clip app identifier. For Safari banners, use `app-id`, `app-clip-bundle-id`, and optional `app-clip-display=card`; do not rely on `app-argument` for App Clip launches.

**Validation checkpoint:** Exercise each URL with `_XCAppClipURL` and a Local
Experience, fix routing/AASA/experience mismatches, and repeat until the App
Clip and installed full app reach the same destination.

## Size and Capability Decisions

Use [Size, capabilities, and promotion](references/size-capabilities-and-promotion.md)
as the authoritative checklist for feasibility reviews, size tiers and measurement,
Background Assets, CloudKit, Live Activities, unsupported features, and full-app
promotion. Load it whenever any of those topics is in scope.

Keep product reviews at the boundary level: state the size basis, invocation and
download fit, capability exclusions, and handoff destination. Add implementation
APIs only when the user asks for implementation.

## Data, Notifications, and Location

Read [`references/data-handoff-notifications-location.md`](references/data-handoff-notifications-location.md) when implementing App Group/full-app migration, keychain or Sign in with Apple handoff, ephemeral notifications, notification relaunch routing, or physical location confirmation.

Treat App Group storage as non-secret handoff state, not a trust boundary. The
reference owns the iOS 15.4+ one-way keychain rule, Sign in with Apple
verification, ephemeral-notification permission and relaunch routing, and
physical-location confirmation—including their required raw keys and targets.

## Common Mistakes

### Exceeding the applicable App Clip size limit

Choose and measure the applicable limit using
[Size Limits](references/size-capabilities-and-promotion.md#size-limits).

### Designing a marketing-only or web-view-heavy App Clip

App Clips should let people complete a focused task or full demo without installing the app. Avoid marketing-only clips, ad-heavy flows, splash screens, launch-blocking downloads, repeated install prompts, and web-view-heavy experiences that would work better as a website.

## Review Checklist

Do not ship until every applicable gate passes; fix failures and rerun the same gate.

- [ ] Target IDs, all three raw entitlement keys, and shared-code boundaries are correct.
- [ ] Invocation works for SwiftUI/UIKit cold launch and continuation, then hands off to the full app.
- [ ] Associated domains, AASA, App Store Connect experiences, and local invocation tests pass.
- [ ] Size, capability, UX, Live Activity, and promotion decisions pass the
      [feasibility review](references/size-capabilities-and-promotion.md#feasibility-review-template).
- [ ] Data, credential, notification, and location flows pass the detailed
      [handoff checks](references/data-handoff-notifications-location.md).

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
