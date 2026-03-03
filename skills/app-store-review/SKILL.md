---
name: app-store-review
description: "App Store review preparation and rejection prevention. Covers App Store review guidelines, app rejection reasons, PrivacyInfo.xcprivacy privacy manifest requirements, required API reason codes, in-app purchase IAP and StoreKit rules, App Store Guidelines compliance, ATT App Tracking Transparency, EU DMA Digital Markets Act, HIG compliance checklist, app submission preparation, review preparation, metadata requirements, entitlements, widgets, and Live Activities review rules. Use when preparing for App Store submission, fixing rejection reasons, auditing privacy manifests, implementing ATT consent flow, configuring StoreKit IAP, or checking HIG compliance."
---

# App Store Review Preparation

Guidance for catching App Store rejection risks before submission. Apple reviewed 7.7 million submissions in 2024 and rejected 1.9 million. Most rejections are preventable with proper preparation.

## Top Rejection Reasons and How to Avoid Them

### Guideline 2.1 -- App Completeness

The app must be fully functional when reviewed. Apple rejects for:

- Placeholder content, lorem ipsum, or test data visible anywhere
- Broken links or empty screens
- Features behind logins without demo credentials provided in App Review notes
- Features that require hardware Apple does not have access to

**Prevention:**
- Provide demo account credentials in the App Review Information notes field in App Store Connect
- Walk through every screen and verify real content is present
- Test all flows end-to-end, including edge cases like empty states and error conditions

### Guideline 2.3 -- Accurate Metadata

- App name must match what the app actually does
- Screenshots must show the actual app UI, not marketing renders or mockups
- Description must not contain prices (they vary by region)
- No references to other platforms ("Also available on Android")
- Keywords must be relevant -- no competitor names or unrelated terms
- Category must match the app's primary function

### Guideline 4.2 -- Minimum Functionality

Apple rejects apps that are too simple or are just websites in a wrapper:

- WKWebView-only apps are rejected unless they add meaningful native functionality
- Single-feature apps may be rejected if the feature is better suited as part of another app
- Apps that duplicate built-in iOS functionality without significant improvement are rejected

### Guideline 2.5.1 -- Software Requirements

- Must use public APIs only -- private API usage is an instant rejection
- Must be built with the current Xcode GM release or later
- Must support the latest two major iOS versions (guideline, not strict rule)
- Must not download or execute code dynamically (except JavaScript in WKWebView)

## PrivacyInfo.xcprivacy -- Privacy Manifest Requirements

This is the fastest-growing rejection category (Guideline 5.1.1). A privacy manifest is **required** if your app or any of its dependencies uses certain categories of APIs.

### When a Privacy Manifest Is Required

A `PrivacyInfo.xcprivacy` file must be present if your app uses ANY of these API categories:

- **File timestamp APIs** (`NSPrivacyAccessedAPICategoryFileTimestamp`)
- **System boot time APIs** (`NSPrivacyAccessedAPICategorySystemBootTime`)
- **Disk space APIs** (`NSPrivacyAccessedAPICategoryDiskSpace`)
- **User defaults** (`NSPrivacyAccessedAPICategoryUserDefaults`) -- if storing user-identifiable data
- **Active keyboard APIs** (`NSPrivacyAccessedAPICategoryActiveKeyboards`)

### Privacy Manifest Structure

```xml
<!-- PrivacyInfo.xcprivacy -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>NSPrivacyTracking</key>
    <false/>
    <key>NSPrivacyTrackingDomains</key>
    <array/>
    <key>NSPrivacyCollectedDataTypes</key>
    <array>
        <!-- Declare every data type you collect -->
    </array>
    <key>NSPrivacyAccessedAPITypes</key>
    <array>
        <dict>
            <key>NSPrivacyAccessedAPIType</key>
            <string>NSPrivacyAccessedAPICategoryUserDefaults</string>
            <key>NSPrivacyAccessedAPITypeReasons</key>
            <array>
                <string>CA92.1</string>
            </array>
        </dict>
    </array>
</dict>
</plist>
```

### Required API Reason Codes

Each API category requires one or more reason codes explaining why the API is accessed:

| API Category | Code | Reason |
|---|---|---|
| FileTimestamp | `C617.1` | Access files inside app container |
| FileTimestamp | `3B52.1` | Access user-selected files |
| FileTimestamp | `0A2A.1` | Third-party SDK accessed on behalf of user |
| SystemBootTime | `35F9.1` | Measure elapsed time between events |
| DiskSpace | `E174.1` | Check available space before writes |
| UserDefaults | `CA92.1` | Access within your own app |
| UserDefaults | `1C8F.1` | Access within same app group |
| ActiveKeyboards | `3EC4.1` | Customize UI based on active keyboards |

### Privacy Manifest Keys Reference

| Key | Type | Purpose |
|---|---|---|
| `NSPrivacyTracking` | Boolean | Whether the app tracks users (triggers ATT requirement) |
| `NSPrivacyTrackingDomains` | Array of strings | Domains used for tracking (connected only after ATT consent) |
| `NSPrivacyCollectedDataTypes` | Array of dicts | Each data type collected, its purpose, and whether it is linked to identity |
| `NSPrivacyAccessedAPITypes` | Array of dicts | Each required-reason API used and the justification codes |

### Third-Party SDK Privacy Manifests

Every third-party SDK must include its own privacy manifest. Apple specifically audits these categories of SDKs:

- Analytics SDKs (Firebase Analytics, Mixpanel, Amplitude)
- Advertising SDKs (AdMob, Meta Ads SDK)
- Crash reporting SDKs (Crashlytics, Sentry)
- Social SDKs (Facebook SDK, Google Sign-In)

**Verification steps:**
1. Check each dependency for a `PrivacyInfo.xcprivacy` in its bundle
2. Confirm the SDK's declared API reasons match your actual usage
3. Update SDKs to versions that include privacy manifests -- older versions may lack them

### Collected Data Types Declaration

When declaring `NSPrivacyCollectedDataTypes`, each entry must specify:

- `NSPrivacyCollectedDataType` -- the category (e.g., `NSPrivacyCollectedDataTypeName`)
- `NSPrivacyCollectedDataTypeLinked` -- whether linked to user identity
- `NSPrivacyCollectedDataTypeTracking` -- whether used for tracking
- `NSPrivacyCollectedDataTypePurposes` -- array of purposes (e.g., `NSPrivacyCollectedDataTypePurposeAnalytics`)

Apple compares your privacy manifest declarations against your App Store privacy nutrition labels and actual network traffic. Mismatches cause rejection.

## Data Use, Sharing, and Privacy Policy (Guideline 5.1.2)

- A privacy policy URL must be set in App Store Connect AND accessible within the app
- The privacy policy must accurately describe what data you collect, how you use it, and who you share it with
- App Store privacy nutrition labels must match your actual data collection practices
- Apple cross-references your privacy manifest, nutrition labels, and observed network traffic

## In-App Purchase and StoreKit Rules (Guideline 3.1.1)

IAP rules are strict and heavily enforced.

### What Requires Apple IAP

All digital content and services must use Apple's In-App Purchase system:

- Premium features or content unlocks
- Subscriptions to app functionality
- Virtual currency, coins, gems
- Ad removal
- Digital tips or donations

### What Does NOT Require IAP

- Physical products (e-commerce)
- Ride-sharing, food delivery, real-world services
- One-to-one services (tutoring, consulting booked through the app)
- Enterprise/B2B apps distributed through Apple Business Manager

### Subscription Display Requirements

- Price, duration, and auto-renewal terms must be clearly displayed before purchase
- Free trials must state what happens when they end (price, billing frequency)
- No links, buttons, or language directing users to purchase outside the app
- "Reader" apps (Netflix, Spotify) may link to external sign-up but cannot offer IAP bypass

### StoreKit Implementation Checklist

- Consumables, non-consumables, and subscriptions must be correctly categorized in App Store Connect
- Restore purchases functionality must be present and working
- Transaction verification should use StoreKit 2 `Transaction.currentEntitlements` or server-side validation
- Handle interrupted purchases, deferred transactions, and ask-to-buy gracefully

## HIG Compliance Checklist

### Navigation

- Use `NavigationStack` (not the deprecated `NavigationView`)
- Back buttons must use the standard system chevron -- do not replace with "X" unless dismissing a modal
- Tab bars: maximum 5 tabs; use a "More" tab if additional items are needed
- Avoid hamburger menus -- Apple strongly discourages them on iOS

### Modals and Sheets

- Sheets must have a clear dismiss mechanism (button or swipe-down gesture)
- Full-screen modals must have a visible close or done button
- Alerts must use standard system alerts -- custom alert UI that mimics system alerts is rejected

### System Feature Support

- **Dark Mode** -- the app must not look broken in Dark Mode. Test all screens.
- **Dynamic Type** -- text must scale with the user's preferred text size
- **iPad multitasking** -- support Slide Over and Split View unless there is a justified exclusion
- **Dynamic Island and Live Activities** -- if used, they must display correctly at all sizes
- **System gestures** -- do not disable swipe-from-edge or home indicator gestures

### Widgets and Live Activities

- Widgets must show real, useful content -- no "Open app to see more" placeholders
- Widget timelines must update meaningfully; static widgets that never change are rejected
- Live Activities must display genuinely live, time-sensitive information
- Lock Screen widgets must be legible and functional at small sizes

### Launch Screen

- The launch screen must not be an ad or splash page that delays app usage
- Use a static launch storyboard or a simple branded screen that transitions quickly

### Empty States

- Every screen that can be empty must show guidance (e.g., a call to action or explanation)
- "Nothing here yet" without direction is insufficient

## App Tracking Transparency (ATT)

### When ATT Is Required

If your app tracks users across other companies' apps or websites, you must:

1. Request permission via `ATTrackingManager.requestTrackingAuthorization` before any tracking occurs
2. Respect the user's choice -- do not track if the user denies permission
3. Not gate app functionality behind tracking consent ("Accept tracking or you cannot use this app" is rejected)
4. Provide a clear purpose string in `NSUserTrackingUsageDescription` explaining what tracking is used for

### When ATT Is NOT Required

If you do not track users across apps or websites, do not show the ATT prompt. Apple rejects unnecessary ATT prompts.

### ATT Implementation

```swift
import AppTrackingTransparency

func requestTrackingPermission() async {
    let status = await ATTrackingManager.requestTrackingAuthorization()
    switch status {
    case .authorized:
        // Enable tracking, initialize ad SDKs with tracking
        break
    case .denied, .restricted:
        // Use non-personalized ads, disable cross-app tracking
        break
    case .notDetermined:
        // Should not happen after request, handle gracefully
        break
    @unknown default:
        break
    }
}
```

**Timing:** Request ATT permission after the app has launched and the user has context for why tracking is being requested. Do not show the prompt immediately on first launch.

## EU Digital Markets Act (DMA) Considerations

For apps distributed in the EU:

- Alternative browser engines are permitted on iOS in the EU
- Alternative app marketplaces exist -- apps may be distributed outside the App Store
- External payment links may be allowed under specific conditions, with Apple's commission structure adjusted
- Notarization is required even for sideloaded apps distributed outside the App Store
- Apps using alternative distribution must still meet Apple's notarization requirements for security

## Entitlements and Capabilities

Every entitlement must be justified. Apple reviews these closely:

| Entitlement | Apple Scrutiny |
|---|---|
| Camera | Must explain purpose in `NSCameraUsageDescription` |
| Location (Always) | Must have clear, user-visible reason for background location |
| Push Notifications | Must not be used for marketing without user opt-in |
| HealthKit | Must actually use health data in a meaningful way |
| Background Modes | Each mode (audio, location, VoIP, fetch) must be justified and actively used |
| App Groups | Must explain what shared data is needed |
| Associated Domains | Universal links must actually resolve and function |

### Usage Description Strings

Usage descriptions in Info.plist must be specific about what data is accessed and why:

```
// REJECTED -- too vague
"This app needs your location."

// APPROVED -- specific purpose
"Your location is used to show nearby restaurants on the map."

// REJECTED -- too vague
"This app needs access to your camera."

// APPROVED -- specific purpose
"The camera is used to scan barcodes for price comparison."
```

Apple rejects vague usage descriptions. Always state what the data is used for in user-facing terms.

## Common Mistakes

1. **Missing demo credentials.** Provide App Review login credentials in App Store Connect notes. Most Guideline 2.1 rejections are from reviewers unable to test behind a login.
2. **Privacy manifest mismatch.** Declared data collection in PrivacyInfo.xcprivacy must match App Store privacy nutrition labels and actual network traffic.
3. **Unnecessary ATT prompt.** Do not show the App Tracking Transparency prompt unless you actually track users across apps or websites. Apple rejects unnecessary prompts.
4. **Vague usage descriptions.** "This app needs your location" is rejected. State the specific feature that uses the data.
5. **External payment links for digital content.** Any language or button directing users to purchase digital content outside the app is rejected.
6. **Missing concurrency annotations.** Ensure ATT request and StoreKit calls run on `@MainActor` or appropriate actor context. Mark shared state types as `Sendable` for Swift 6 concurrency safety.

## Pre-Submission Checklist

### Completeness
- [ ] No placeholder content, test data, or lorem ipsum anywhere in the app
- [ ] All features functional without special hardware
- [ ] Demo credentials provided in App Review Information notes
- [ ] No dead-end screens or broken navigation flows

### Metadata
- [ ] App name matches functionality
- [ ] Screenshots are actual app screenshots (not mockups)
- [ ] Description contains no prices, platform references, or competitor names
- [ ] App category is correct for the primary function

### Privacy
- [ ] `PrivacyInfo.xcprivacy` present with all required API reason codes
- [ ] All third-party SDKs include their own privacy manifests
- [ ] Privacy policy URL set in App Store Connect and accessible in-app
- [ ] App Privacy nutrition labels match actual data collection
- [ ] ATT prompt shown only if tracking occurs, and only before tracking begins
- [ ] `NSPrivacyTracking` set correctly (true only if cross-app tracking occurs)

### Payments
- [ ] All digital content uses Apple IAP
- [ ] Subscription terms clearly displayed (price, duration, renewal behavior)
- [ ] No external payment links for digital content
- [ ] Free trial clearly states post-trial pricing
- [ ] Restore purchases button present and functional

### Design
- [ ] Standard navigation patterns used (`NavigationStack`, tab bars)
- [ ] Dark Mode renders correctly on all screens
- [ ] Dynamic Type supported -- text scales properly
- [ ] No custom alerts mimicking system alerts
- [ ] Launch screen is not an ad or extended splash
- [ ] Empty states provide guidance or calls to action

### Technical
- [ ] Built with current Xcode GM release
- [ ] No private API usage
- [ ] No dynamic code download or execution
- [ ] All entitlements justified with specific usage descriptions
- [ ] All background modes justified and actively used
- [ ] Minimum deployment target covers latest two major iOS versions
