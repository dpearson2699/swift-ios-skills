# App Review Guidelines -- Privacy and Security

App Store review rules relevant to security, privacy manifests, data handling,
and App Tracking Transparency. Extracted from Apple's App Store Review
Guidelines for self-contained reference.

## PrivacyInfo.xcprivacy -- Privacy Manifest Requirements (Guideline 5.1.1)

This is the fastest-growing rejection category. A privacy manifest is
**required** if your app or any of its dependencies uses certain categories
of APIs.

### When a Privacy Manifest Is Required

A `PrivacyInfo.xcprivacy` file must be present if your app uses ANY of these
API categories:

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

Each API category requires one or more reason codes explaining why the API
is accessed:

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

Every third-party SDK must include its own privacy manifest. Apple
specifically audits these categories of SDKs:

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

Apple compares your privacy manifest declarations against your App Store
privacy nutrition labels and actual network traffic. Mismatches cause
rejection.

## Data Use, Sharing, and Privacy Policy (Guideline 5.1.2)

- A privacy policy URL must be set in App Store Connect AND accessible within the app
- The privacy policy must accurately describe what data you collect, how you use it, and who you share it with
- App Store privacy nutrition labels must match your actual data collection practices
- Apple cross-references your privacy manifest, nutrition labels, and observed network traffic

## App Tracking Transparency (ATT)

### When ATT Is Required

If your app tracks users across other companies' apps or websites, you must:

1. Request permission via `ATTrackingManager.requestTrackingAuthorization` before any tracking occurs
2. Respect the user's choice -- do not track if the user denies permission
3. Not gate app functionality behind tracking consent ("Accept tracking or you cannot use this app" is rejected)
4. Provide a clear purpose string in `NSUserTrackingUsageDescription` explaining what tracking is used for

### When ATT Is NOT Required

If you do not track users across apps or websites, do not show the ATT
prompt. Apple rejects unnecessary ATT prompts.

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

**Timing:** Request ATT permission after the app has launched and the user
has context for why tracking is being requested. Do not show the prompt
immediately on first launch.

## Pre-Submission Privacy Checklist

- [ ] `PrivacyInfo.xcprivacy` present with all required API reason codes
- [ ] All third-party SDKs include their own privacy manifests
- [ ] Privacy policy URL set in App Store Connect and accessible in-app
- [ ] App Privacy nutrition labels match actual data collection
- [ ] ATT prompt shown only if tracking occurs, and only before tracking begins
- [ ] `NSPrivacyTracking` set correctly (true only if cross-app tracking occurs)
- [ ] All entitlements justified with specific usage descriptions
