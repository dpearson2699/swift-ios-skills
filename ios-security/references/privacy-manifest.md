# Privacy Manifests -- Security Perspective

This reference covers the security-relevant aspects of PrivacyInfo.xcprivacy:
required-reason API declarations, data collection types, and tracking domains.
For submission requirements and App Review compliance checklists, see
`app-review-guidelines.md` in this references folder.

## Required API Declarations

If your code or any dependency calls these APIs, you must declare them in
PrivacyInfo.xcprivacy with an approved reason code.

| API Category | Common APIs | Reason Codes |
|---|---|---|
| File timestamp | `stat()`, `getattrlist()`, file modification dates | `C617.1` (app container), `3B52.1` (user-selected files), `0A2A.1` (third-party SDK on behalf of user) |
| System boot time | `mach_absolute_time()`, `ProcessInfo.systemUptime` | `35F9.1` (elapsed time) |
| Disk space | `volumeAvailableCapacityKey`, `attributesOfFileSystem` | `E174.1` (check write space) |
| User defaults | `UserDefaults.standard` | `CA92.1` (app's own defaults), `1C8F.1` (same app group) |
| Active keyboards | `UITextInputMode.activeInputModes` | `3EC4.1` (customize UI) |

### Why This Matters for Security

These APIs are categorized as "required reason" because they can be used for
device fingerprinting. The privacy manifest system forces apps to declare
legitimate uses, making fingerprinting-based tracking harder to hide.

## Data Collection Declarations

Declare what data your app collects and how it is used:

```xml
<key>NSPrivacyCollectedDataTypes</key>
<array>
    <dict>
        <key>NSPrivacyCollectedDataType</key>
        <string>NSPrivacyCollectedDataTypeEmailAddress</string>
        <key>NSPrivacyCollectedDataTypeLinked</key>
        <true/>
        <key>NSPrivacyCollectedDataTypeTracking</key>
        <false/>
        <key>NSPrivacyCollectedDataTypePurposes</key>
        <array>
            <string>NSPrivacyCollectedDataTypePurposeAppFunctionality</string>
        </array>
    </dict>
</array>
```

Key fields:
- `NSPrivacyCollectedDataTypeLinked`: Whether the data is linked to the user's identity.
- `NSPrivacyCollectedDataTypeTracking`: Whether the data is used for tracking.

## Tracking Domains

Declare domains used for tracking. These are blocked if the user denies
App Tracking Transparency (ATT):

```xml
<key>NSPrivacyTrackingDomains</key>
<array>
    <string>analytics.example.com</string>
</array>
```

## Auditing Dependencies

```bash
# Find existing privacy manifests
find . -name "PrivacyInfo.xcprivacy" -not -path "*/SourcePackages/*"

# Check dependency locations
# SPM: .build/checkouts/
# CocoaPods: Pods/
# Frameworks: *.framework bundles
```

Every third-party SDK that accesses required-reason APIs must include its own
PrivacyInfo.xcprivacy. If it does not, file an issue with the SDK maintainer.
Xcode will aggregate all privacy manifests during the build.

## App Tracking Transparency (ATT)

ATT is the runtime companion to privacy manifest tracking declarations:

```swift
import AppTrackingTransparency

func requestTrackingPermission() async -> ATTrackingManager.AuthorizationStatus {
    await ATTrackingManager.requestTrackingAuthorization()
}

// Check current status
let status = ATTrackingManager.trackingAuthorizationStatus
switch status {
case .authorized:    break // User allowed tracking
case .denied:        break // User denied
case .restricted:    break // Restricted (parental controls, MDM)
case .notDetermined: break // Haven't asked yet
@unknown default:    break
}
```

Rules:
- Request AFTER app launch, not on the first screen. Show context first.
- The `NSUserTrackingUsageDescription` in Info.plist must clearly explain the purpose.
- If the user denies, respect it. Do not repeatedly prompt.
- Do not gate features behind tracking consent.
- If `trackingAuthorizationStatus` is `.denied`, do not send data to any
  domains listed in `NSPrivacyTrackingDomains`.
