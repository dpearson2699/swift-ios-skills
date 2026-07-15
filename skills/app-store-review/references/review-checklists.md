# App Store Review Checklists

## Contents
- Current Release Requirements
- Entitlements and Usage Descriptions
- Phased Release Schedule
- App Review Information Checklist
- Privacy Manifest Checklist
- In-App Purchase Checklist
- Metadata Compliance Checklist
- HIG Compliance Checklist
- Pre-Submission Checklist

## Current Release Requirements

Treat this table as a dated release snapshot, not a durable policy source.
Re-check the linked current Apple requirements at the start of every audit and
record the checked date beside each blocker.

| Requirement | Current release evidence |
|---|---|
| Upload toolchain | Uploads after April 28, 2026 require Xcode 26+ and the relevant platform SDK 26+. |
| iPhone screenshots | As of May 2026, 6.9-inch screenshots are the primary accepted set; provide 6.5-inch only when the 6.9-inch set is absent or intentionally optimized as a fallback. |
| iPad screenshots | Provide 13-inch screenshots when the app runs on iPad. |
| Metadata limits | App name: 30 characters; subtitle: 30 characters; keyword field: up to 100 UTF-8 bytes, with comma-separated terms longer than two characters and no spaces after commas. |

Sources: [Upcoming requirements](https://developer.apple.com/news/upcoming-requirements/)
and [Screenshot specifications](https://developer.apple.com/help/app-store-connect/reference/app-information/screenshot-specifications/).

## Entitlements and Usage Descriptions

Every entitlement must be justified by an active feature and its release
evidence:

| Entitlement | Review evidence |
|---|---|
| Camera | Specific `NSCameraUsageDescription` tied to a visible feature |
| Location (Always) | Clear user-facing reason for background location |
| Push Notifications | Marketing notifications require user opt-in |
| HealthKit | Meaningful use of the requested health data |
| Background Modes | Every enabled mode is justified and exercised |
| App Groups | Shared data and participating targets are documented |
| Associated Domains | Universal links resolve and function |

Use valid property-list entries with specific user-facing purposes:

```xml
<key>NSLocationWhenInUseUsageDescription</key>
<string>Your location is used to show nearby restaurants on the map.</string>
<key>NSCameraUsageDescription</key>
<string>The camera is used to scan barcodes for price comparison.</string>
```

Vague strings such as “This app needs your location” do not explain the feature
or why the data is needed.

## Phased Release Schedule

After approval, an automatic phased release uses this seven-day schedule:

| Day | Percentage of Users |
|---|---|
| 1 | 1% |
| 2 | 2% |
| 3 | 5% |
| 4 | 10% |
| 5 | 20% |
| 6 | 50% |
| 7 | 100% |

Users who manually request the update receive it immediately. App Store Connect
can pause, resume, or complete the rollout.

## App Review Information Checklist

Use this to avoid Guideline 2.1 rejections:

- [ ] Demo credentials provided in App Review Information notes (if login required)
- [ ] Demo mode available if credentials are impractical or account state is hard to reproduce
- [ ] Demo account works and has access to all features
- [ ] App Review notes explain login-gated, role-gated, region-gated, hardware-gated, or otherwise non-obvious features
- [ ] All screens have real content (no placeholders or Lorem Ipsum)
- [ ] No broken links or dead-end flows
- [ ] All hardware-required features have fallback or reviewer instructions

## Privacy Manifest Checklist

Verify PrivacyInfo.xcprivacy completeness:

- [ ] `PrivacyInfo.xcprivacy` exists where app code, SDK code, executables, or dynamic libraries need it
- [ ] All required-reason API categories in app and bundled SDK code are declared with approved reason codes
- [ ] `NSPrivacyTracking` is true only if tracking occurs
- [ ] Third-party SDK manifests present and up to date when SDKs collect data, use required-reason APIs, enable data collection, or contact tracking domains
- [ ] Privacy nutrition labels match actual data collection
- [ ] Audit runtime network traffic and SDK transmissions; observed behavior must match privacy labels, manifests, privacy policy, and ATT state

## In-App Purchase Checklist

- [ ] Digital goods and subscriptions use StoreKit IAP unless current storefront rules or approved entitlements allow otherwise
- [ ] Subscription price, duration, billing frequency, auto-renewal terms, and any trial duration/post-trial price shown before purchase
- [ ] Restore purchases button present and functional
- [ ] No external purchase path, link, button, or call to action for digital goods unless current rules or approved entitlements allow it
- [ ] Ask-to-buy and interrupted purchases handled
- [ ] Transaction verification uses StoreKit 2 or server-side verification

## Metadata Compliance Checklist

Keep this checklist about App Review compliance. Route keyword research,
ranking, conversion optimization, screenshot ordering, and A/B testing to
`app-store-optimization`.

### App Name and Subtitle

- [ ] Name and subtitle meet the limits in Current Release Requirements
- [ ] Name is unique and not only a generic category term
- [ ] Name and subtitle omit prices, competitor names, and trademarks you do not own

### Screenshots

- [ ] 1-10 screenshots are uploaded for each required platform and localization
- [ ] iPhone and iPad sets match Current Release Requirements
- [ ] Screenshots show localized, actual app UI and no unavailable features
- [ ] Overlays and marketing frames do not obscure or misrepresent the interface

### Keywords

- [ ] Keyword field meets the limit and delimiter format in Current Release Requirements
- [ ] Terms do not duplicate the app name or subtitle
- [ ] Terms use either singular or plural, not both
- [ ] Terms omit competitors, trademarks, and irrelevant words

### App Previews

- [ ] Up to three previews per localization, each no longer than 30 seconds
- [ ] Footage shows the actual app; framing and effects do not misrepresent it
- [ ] Optional audio or narration complies with rights and metadata claims
- [ ] The first frame works as the product-page poster frame

## HIG Compliance Checklist

### Navigation
- [ ] `NavigationStack` used (not `NavigationView`)
- [ ] System back chevron used; no custom back icons
- [ ] Tab bar uses <= 5 tabs; use More tab if needed
- [ ] Avoid hamburger menus

### Modals and Sheets
- [ ] Sheets have a visible dismiss control
- [ ] Full-screen modals have close/done button
- [ ] Alerts use system alert styles

### System Feature Support
- [ ] Dark Mode renders correctly
- [ ] Dynamic Type supported throughout
- [ ] iPad multitasking supported (Slide Over, Split View)
- [ ] Dynamic Island / Live Activities render correctly when used
- [ ] System gestures not disabled

### Widgets and Live Activities
- [ ] Widgets show real content (not placeholders)
- [ ] Timelines update meaningfully
- [ ] Live Activities show time-sensitive info
- [ ] Lock Screen widgets are legible at small sizes

## Pre-Submission Checklist

### Completeness
- [ ] No placeholder or test content
- [ ] All features functional without special hardware
- [ ] Demo credentials or demo mode provided, with App Review notes for gated or non-obvious features
- [ ] No dead-end screens

### Metadata
- [ ] App name matches functionality
- [ ] Screenshots are real app screenshots using the sets in Current Release Requirements
- [ ] Description contains no prices or competitor mentions
- [ ] Category is correct

### Privacy
- [ ] Privacy manifest present where required, with approved reason codes
- [ ] Third-party SDK manifests verified
- [ ] Privacy policy URL present and accessible
- [ ] Audit runtime network traffic and SDK transmissions; nutrition labels, privacy manifest declarations, privacy policy, and observed behavior match actual data collection
- [ ] ATT prompt only if tracking occurs

### Payments
- [ ] Digital content uses StoreKit IAP unless current rules or approved entitlements allow otherwise
- [ ] Subscription price, duration, billing frequency, auto-renewal terms, and any trial duration/post-trial price visible before purchase
- [ ] No external purchase paths, payment links, buttons, or calls to action unless current storefront rules or approved entitlements allow them
- [ ] Free trial terms clear
- [ ] Restore purchases implemented

### Design
- [ ] Standard navigation patterns used
- [ ] Dark Mode supported
- [ ] Dynamic Type supported
- [ ] No custom alerts mimicking system alerts
- [ ] Launch screen not an ad
- [ ] Empty states provide guidance

### Technical
- [ ] Archive meets the upload toolchain floor in Current Release Requirements
- [ ] No private API usage
- [ ] No dynamic code execution
- [ ] Entitlements justified with usage descriptions
- [ ] Background modes justified and used
- [ ] Deployment target is intentionally chosen and tested
