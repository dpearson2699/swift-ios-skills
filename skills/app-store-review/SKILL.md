---
name: app-store-review
description: "Audits App Store submission readiness and rejection risk across current review guidelines, PrivacyInfo.xcprivacy and required-reason APIs, privacy labels, ATT, StoreKit payments, metadata, entitlements, widgets, and Live Activities. Use when preparing a submission, responding to rejection, reconciling privacy evidence, or separating upload blockers from cleanup."
---

# App Store Review Preparation

Catch App Store rejection risks before submission. Treat policy, SDK, privacy, entitlement, payment, and metadata checks as current release evidence rather than durable facts.

## Contents

- [Top Rejection Reasons and How to Avoid Them](#top-rejection-reasons-and-how-to-avoid-them)
- [PrivacyInfo.xcprivacy -- Privacy Manifest Requirements](#privacyinfoxcprivacy-privacy-manifest-requirements)
- [Data Use, Sharing, and Privacy Policy (Guideline 5.1.2)](#data-use-sharing-and-privacy-policy-guideline-512)
- [In-App Purchase and StoreKit Rules (Guideline 3.1.1)](#in-app-purchase-and-storekit-rules-guideline-311)
- [HIG Compliance Checklist](#hig-compliance-checklist)
- [App Tracking Transparency (ATT)](#app-tracking-transparency-att)
- [EU Digital Markets Act (DMA) Considerations](#eu-digital-markets-act-dma-considerations)
- [Entitlements and Capabilities](#entitlements-and-capabilities)
- [Submission Workflow](#submission-workflow)
- [Metadata Best Practices](#metadata-best-practices)
- [Appeal Process](#appeal-process)
- [Common Mistakes](#common-mistakes)
- [Review Checklist](#review-checklist)
- [References](#references)

Start every audit by fetching the current App Review Guidelines, Upcoming Requirements, screenshot specifications, required-reason API documentation, and applicable storefront/entitlement payment rules. Record the checked date and source beside each release blocker. Then archive-build and validate the exact submission, separate blockers from cleanup, fix one class of evidence mismatch, and rerun the same checks against the rebuilt archive.

For prompts about keywords, screenshot captions, product-page metadata, or metadata rejection risk, answer from a compliance angle and explicitly defer keyword research, ranking strategy, conversion optimization, screenshot ordering, and A/B testing to `app-store-optimization`. Keep App Review metadata guidance limited to accuracy, field limits, misleading-content risk, and screenshot compliance. Load the dated format, screenshot, and toolchain facts from [Current Release Requirements](references/review-checklists.md#current-release-requirements).

For full submission readiness audits, separate blocking upload/review issues from ordinary cleanup. Cross-check privacy manifests, App Store privacy nutrition labels, privacy policy, ATT state, runtime network behavior, and SDK behavior against each other; the declarations and observed behavior must align.

### Blocking Submission Checks

Escalate these as blockers before ordinary cleanup:

- The archive misses the current Xcode or platform SDK upload floor
- Unresolved privacy evidence mismatches; reconcile them with the [PrivacyInfo.xcprivacy requirements](#privacyinfoxcprivacy-privacy-manifest-requirements)
- Payment paths that fail the [StoreKit rules](#in-app-purchase-and-storekit-rules-guideline-311)
- Missing screenshot sets required by the current App Store Connect specification
- Review access that fails the Guideline 2.1 completeness evidence below

## Top Rejection Reasons and How to Avoid Them

| Guideline risk | Release evidence |
|---|---|
| 2.1 completeness | No placeholders, broken/empty flows, inaccessible hardware-only features, or login gates without working demo credentials and review notes. |
| 2.3 metadata | App name, category, description, keywords, and screenshots accurately represent the submitted binary and actual UI. |
| 4.2 minimum functionality | The app provides meaningful app-specific value beyond a thin website or trivial duplication of system behavior. |
| 2.5.1 software requirements | Archive uses public APIs and does not download code that changes reviewed functionality outside documented exceptions. |

Verify these against the current guidelines and the exact archive; do not carry version or screenshot requirements forward from an older release checklist.

## PrivacyInfo.xcprivacy -- Privacy Manifest Requirements

A privacy manifest is required when your app code, an executable, a dynamic library, or a third-party SDK uses Apple's required-reason API categories or declares collected data/tracking behavior.

**See:** [references/privacy-manifest.md](references/privacy-manifest.md) for the full structure, reason codes, and checklists.

### Summary

- Required-reason API categories are file timestamps, system boot time, disk space, active keyboards, and UserDefaults; each requires an approved reason code when used.
- Before final submission, re-check Apple's current required-reason API documentation and do not choose broad, convenient, or invented reason codes.
- Required-reason API declarations belong in the bundle that contains the code using the API; every app target, executable, dynamic library, framework, or SDK bundle containing manifest-relevant code needs the matching manifest declarations.
- Each SDK, executable, or dynamic library that collects data, uses required-reason APIs, enables data collection/tracking, or contacts tracking domains needs manifest attention in the bundle containing that code; SDK code cannot rely on the host app's manifest to report the SDK's own usage.
- Manifest declarations must match App Store privacy nutrition labels, SDK behavior, and the app's presented functionality.

## Data Use, Sharing, and Privacy Policy (Guideline 5.1.2)

- A privacy policy URL must be set in App Store Connect AND accessible within the app
- The privacy policy must accurately describe what data you collect, how you use it, and who you share it with
- App Store privacy nutrition labels must match your actual data collection practices
- Privacy labels, privacy manifests, SDK disclosures, and runtime behavior should tell the same story

## In-App Purchase and StoreKit Rules (Guideline 3.1.1)

Digital goods, features, subscriptions, virtual currency, ad removal, and digital tips generally require IAP unless a current guideline exception, storefront rule, or approved entitlement applies. Physical goods and real-world services use their ordinary payment flow. Before purchase, show price, duration, renewal/trial terms, billing frequency, and cancellation terms; verify product classification, restoration, entitlement verification, deferred/interrupted purchases, and Ask to Buy. Load `storekit` for implementation and re-check current regional/external-link rules before labeling a path compliant.

## HIG Compliance Checklist

Load the full HIG checks for navigation, modals, widgets, system features,
launch screens, and empty states from [review-checklists.md](references/review-checklists.md).

## App Tracking Transparency (ATT)

### When ATT Is Required

If your app tracks users across other companies' apps or websites, you must:

1. Request permission via `ATTrackingManager.requestTrackingAuthorization` before any cross-app or cross-website tracking occurs, including tracking-capable SDK behavior
2. Respect the user's choice -- disable cross-app and cross-website tracking if the user denies permission
3. Not gate app functionality behind tracking consent ("Accept tracking or you cannot use this app" is rejected)
4. Provide a clear purpose string in `NSUserTrackingUsageDescription` explaining what tracking is used for

### When ATT Is NOT Required

If you do not track users across apps or websites, do not show the ATT prompt. Apple rejects unnecessary ATT prompts.

### ATT Implementation

```swift
import AppTrackingTransparency

@MainActor
func requestTrackingPermission() async {
    let status = await ATTrackingManager.requestTrackingAuthorization()
    switch status {
    case .authorized:
        // Enable tracking, initialize ad SDKs with tracking
        break
    case .denied, .restricted:
        // Use non-personalized ads and disable cross-app/cross-website tracking
        break
    case .notDetermined:
        // Should not happen after request, handle gracefully
        break
    @unknown default:
        break
    }
}
```

**Timing:** Request ATT permission after the app is active and the user has context for why tracking is being requested. Do not show the prompt immediately on first launch or stack it with another system permission prompt.

## EU Digital Markets Act (DMA) Considerations

Alternative distribution, browser-engine, notarization, and external-payment
paths are region- and entitlement-specific. Re-check the current storefront
rules and treat an unsupported route as a blocker.

## Entitlements and Capabilities

Every entitlement needs an active feature, a specific usage description when
applicable, and matching archive behavior. Use the table and valid property-list
examples in [Entitlements and Usage Descriptions](references/review-checklists.md#entitlements-and-usage-descriptions).

## Submission Workflow

### Pre-Submission Steps

1. **Archive in Xcode.** Product > Archive (requires a Distribution signing identity). Verify the archive builds clean with zero warnings in Release configuration.
2. **Upload to App Store Connect.** Use the Organizer window (Distribute App > App Store Connect) or `xcodebuild -exportArchive`. Automated uploads via `altool` or Transporter also work.
3. **TestFlight internal testing.** The build is available to internal testers (your team) within minutes of processing. Walk through every screen and flow on at least two device sizes.
4. **TestFlight external testing.** External groups require Beta App Review before first external distribution. Use this to validate with real users before full submission.
5. **Submit for App Review.** In App Store Connect, select the build, fill in all metadata fields, attach screenshots, and click Submit for Review. Review timing varies; allow buffer for rejections, appeals, and metadata fixes.

### Expedited Review Requests

Request expedited review only for Apple-documented critical or time-sensitive
cases, using a concise factual justification in App Store Connect's Contact Us
form.

### Phased Release

Use [Phased Release Schedule](references/review-checklists.md#phased-release-schedule)
for the rollout percentages and App Store Connect controls.

## Metadata Best Practices

Keep the name, subtitle, keywords, screenshots, and previews accurate to the
submitted binary and actual UI. Do not use prices, competitor terms, or
misleading claims. Apply field limits and media rules from the
[Metadata Compliance Checklist](references/review-checklists.md#metadata-compliance-checklist),
and route research, ranking, conversion, screenshot ordering, and A/B testing
to `app-store-optimization`.

## Appeal Process

Respond in App Store Connect's Resolution Center with a concise evidence trail:

- [ ] Map the rejection to the cited guideline and exact submitted behavior.
- [ ] If fixed, identify the precise change and resubmit; if disputed, explain how
      the submission satisfies each relevant requirement.
- [ ] Attach the evidence needed to reproduce compliance, such as working demo
      credentials, screenshots, or a focused video walkthrough.
- [ ] If the exchange remains unresolved, request App Review Board escalation
      through the Resolution Center or App Store Contact form (App Review >
      Appeal), including the full submission history and supporting evidence.

The Board's decision is final for that submission; modifying the app and
resubmitting remains available.

## Common Mistakes

1. **Vague usage descriptions.** Name the specific feature that uses the data.
2. **Treating code quality as review compliance.** Concurrency and transaction correctness do not replace privacy, payment, metadata, and entitlement evidence.

## Review Checklist

Quick-check before every submission (full version in [references/review-checklists.md](references/review-checklists.md)):

- [ ] Guideline 2.1 completeness and review access pass [Blocking Submission Checks](#blocking-submission-checks)
- [ ] App name and screenshots match the binary and current release requirements
- [ ] Privacy evidence passes the [PrivacyInfo.xcprivacy requirements](#privacyinfoxcprivacy-privacy-manifest-requirements)
- [ ] Privacy policy URL set and accessible in-app
- [ ] Payment paths pass the [StoreKit rules](#in-app-purchase-and-storekit-rules-guideline-311)
- [ ] Dark Mode and Dynamic Type supported; standard navigation patterns
- [ ] Archive and entitlements pass [Blocking Submission Checks](#blocking-submission-checks)
- [ ] ATT behavior passes the [ATT criteria](#app-tracking-transparency-att)

## References

- Review checklists: [references/review-checklists.md](references/review-checklists.md)
- Privacy manifest guide: [references/privacy-manifest.md](references/privacy-manifest.md)
- Apple App Review Guidelines: https://developer.apple.com/app-store/review/guidelines/
- Apple upcoming SDK requirements: https://developer.apple.com/news/upcoming-requirements/
- App Store Connect screenshot specifications: https://developer.apple.com/help/app-store-connect/reference/app-information/screenshot-specifications/
- Sosumi required-reason API docs: https://sosumi.ai/documentation/bundleresources/describing-use-of-required-reason-api
