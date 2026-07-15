---
name: authentication
description: "Implement iOS authentication flows with AuthenticationServices and LocalAuthentication. Use when building Sign in with Apple, passkey/WebAuthn registration or sign-in with ASAuthorizationPlatformPublicKeyCredentialProvider, ASAuthorizationController credential state and revocation handling, ASWebAuthenticationSession OAuth or third-party login, Password AutoFill, identity-token server validation, or local biometric re-authentication with LAContext."
---

# Authentication

Implement authentication flows on iOS using the AuthenticationServices
framework, including Sign in with Apple, passkeys, OAuth/third-party web
auth, Password AutoFill, and biometric re-authentication.

## Contents

- [Sign in with Apple](#sign-in-with-apple)
- [Credential Handling](#credential-handling)
- [Credential State Checking](#credential-state-checking)
- [Token Validation](#token-validation)
- [Existing Account Setup Flows](#existing-account-setup-flows)
- [Passkeys](#passkeys)
- [ASWebAuthenticationSession (OAuth)](#aswebauthenticationsession-oauth)
- [Password AutoFill Credentials](#password-autofill-credentials)
- [Biometric Authentication](#biometric-authentication)
- [Security Boundaries](#security-boundaries)
- [SwiftUI SignInWithAppleButton](#swiftui-signinwithapplebutton)
- [Common Mistakes](#common-mistakes)
- [Review Checklist](#review-checklist)
- [References](#references)

## Sign in with Apple

Add the "Sign in with Apple" capability in Xcode before using these APIs.

### UIKit: ASAuthorizationController Setup

```swift
import AuthenticationServices

final class LoginViewController: UIViewController {
    func startSignInWithApple() {
        let provider = ASAuthorizationAppleIDProvider()
        let request = provider.createRequest()
        request.requestedScopes = [.fullName, .email]

        let controller = ASAuthorizationController(authorizationRequests: [request])
        controller.delegate = self
        controller.presentationContextProvider = self
        controller.performRequests()
    }
}

extension LoginViewController: ASAuthorizationControllerPresentationContextProviding {
    func presentationAnchor(for controller: ASAuthorizationController) -> ASPresentationAnchor {
        view.window!
    }
}
```

### Delegate: Handling Success and Failure

```swift
extension LoginViewController: ASAuthorizationControllerDelegate {
    func authorizationController(
        controller: ASAuthorizationController,
        didCompleteWithAuthorization authorization: ASAuthorization
    ) {
        guard let credential = authorization.credential
            as? ASAuthorizationAppleIDCredential else { return }

        let userID = credential.user  // Stable, unique, per-team identifier
        let email = credential.email  // nil after first authorization
        let fullName = credential.fullName  // nil after first authorization
        let identityToken = credential.identityToken  // JWT for server validation
        let authCode = credential.authorizationCode  // Short-lived code for server exchange

        // Save userID to Keychain for credential state checks
        // See references/keychain-biometric.md for Keychain patterns
        saveUserID(userID)

        // Send identityToken and authCode to your server
        authenticateWithServer(identityToken: identityToken, authCode: authCode)
    }

    func authorizationController(
        controller: ASAuthorizationController,
        didCompleteWithError error: any Error
    ) {
        switch (error as? ASAuthorizationError)?.code {
        case .canceled, .notInteractive:
            break
        case .failed:
            showError("Authorization failed")
        default:
            showError("Authorization failed: \(error.localizedDescription)")
        }
    }
}
```

## Credential Handling

| Credential data | Required handling |
|---|---|
| `user` | Persist this stable, per-team identifier for credential-state checks. |
| `email`, `fullName` | These optional values arrive only on first authorization; cache them immediately. |
| `identityToken`, `authorizationCode` | Send them to the server for validation or exchange; never trust them as client-side proof. |

Treat `realUserStatus` only as a fraud-prevention signal, not authentication
proof.

## Credential State Checking

Check credential state on every app launch. The user may revoke access at
any time via Settings > Apple Account > Sign-In & Security.

```swift
func checkCredentialState() {
    let provider = ASAuthorizationAppleIDProvider()
    guard let userID = loadSavedUserID() else {
        showLoginScreen()
        return
    }

    provider.getCredentialState(forUserID: userID) { state, _ in
        DispatchQueue.main.async {
            switch state {
            case .authorized:
                proceedToMainApp()
            case .revoked:
                // User revoked -- sign out and clear local data
                signOut()
                showLoginScreen()
            case .notFound:
                showLoginScreen()
            case .transferred:
                // App transferred to new team -- migrate user identifier
                migrateUser()
            @unknown default:
                showLoginScreen()
            }
        }
    }
}
```

### Credential Revocation Notification

```swift
NotificationCenter.default.addObserver(
    forName: ASAuthorizationAppleIDProvider.credentialRevokedNotification,
    object: nil,
    queue: .main
) { _ in
    // Sign out immediately
    AuthManager.shared.signOut()
}
```

## Token Validation

The `identityToken` is a JWT. Send it to your server for validation --
never trust it client-side alone.

Server-side, validate the JWT against Apple's public keys at
`https://appleid.apple.com/auth/keys` (JWKS). Verify: `iss` is
`https://appleid.apple.com`, `aud` matches your bundle ID, and `exp` has not
passed. Exchange the short-lived authorization code on the server and store
the resulting app session token in Keychain.

## Existing Account Setup Flows

On launch, silently check for existing Sign in with Apple and password
credentials before showing a login screen:

```swift
func performExistingAccountSetupFlows() {
    let appleIDRequest = ASAuthorizationAppleIDProvider().createRequest()
    let passwordRequest = ASAuthorizationPasswordProvider().createRequest()

    let controller = ASAuthorizationController(
        authorizationRequests: [appleIDRequest, passwordRequest]
    )
    controller.delegate = self
    controller.presentationContextProvider = self
    controller.performRequests(
        options: .preferImmediatelyAvailableCredentials
    )
}
```

Call this in `viewDidAppear` or on app launch. If no existing credentials
are found, the delegate receives a `.notInteractive` error -- handle it
silently and show your normal login UI.

## Passkeys

Use passkeys only for a relying-party domain configured with a `webcredentials:`
Associated Domain and AASA entry. Registration and assertion each require a
fresh server challenge, an `ASAuthorizationPlatformPublicKeyCredentialProvider`,
an authorization controller with an active presentation anchor, and server-side
verification before issuing a session.

Load [references/passkeys.md](references/passkeys.md) for the canonical
registration, assertion, result handling, AutoFill-assisted, and physical
security-key flows.

## ASWebAuthenticationSession (OAuth)

Use `ASWebAuthenticationSession` for OAuth and third-party authentication
(Google, GitHub, etc.). Never use `WKWebView` for auth flows.

```swift
import AuthenticationServices

final class OAuthController: NSObject, ASWebAuthenticationPresentationContextProviding {
    private weak var presentationAnchor: ASPresentationAnchor?

    init(presentationAnchor: ASPresentationAnchor) {
        self.presentationAnchor = presentationAnchor
    }

    func startOAuthFlow() {
        let authURL = URL(string:
            "https://provider.com/oauth/authorize?client_id=YOUR_ID&redirect_uri=myapp://callback&response_type=code"
        )!
        let session = ASWebAuthenticationSession(
            url: authURL, callback: .customScheme("myapp")
        ) { callbackURL, error in
            guard let callbackURL, error == nil,
                  let code = URLComponents(url: callbackURL, resolvingAgainstBaseURL: false)?
                      .queryItems?.first(where: { $0.name == "code" })?.value else { return }
            Task { await self.exchangeCodeForTokens(code) }
        }
        session.presentationContextProvider = self
        session.prefersEphemeralWebBrowserSession = true  // No shared cookies
        session.start()
    }

    func presentationAnchor(for session: ASWebAuthenticationSession) -> ASPresentationAnchor {
        guard let presentationAnchor else {
            fatalError("ASWebAuthenticationSession needs the active window")
        }
        return presentationAnchor
    }
}
```

In SwiftUI, use `@Environment(\.webAuthenticationSession)` and call
`authenticate(using:callback:preferredBrowserSession:additionalHeaderFields:)`
with `.customScheme("myapp")` or `.https(host:path:)`; prefer `.ephemeral`
only when the provider flow should avoid shared browser cookies.

## Password AutoFill Credentials

Offer `ASAuthorizationPasswordProvider` alongside Sign in with Apple using the
single controller in [Existing Account Setup Flows](#existing-account-setup-flows).
Handle `ASPasswordCredential` in that controller's delegate.

Set `textContentType` on text fields for AutoFill to work:

```swift
usernameField.textContentType = .username
passwordField.textContentType = .password
```

## Biometric Authentication

Use `LAContext` from LocalAuthentication for local re-authentication before
showing account settings or starting sensitive actions. Do not treat a returned
`Bool` as proof to unlock a stored secret; protect secrets with Keychain access
control instead. See [references/keychain-biometric.md](references/keychain-biometric.md)
for the canonical `LAContext`, fallback, `SecAccessControl`, and
`.biometryCurrentSet` patterns.

**Required:** Add `NSFaceIDUsageDescription` to Info.plist. Missing this
key crashes on Face ID devices.

## Security Boundaries

This skill owns user-facing account authentication: Sign in with Apple,
passkeys, Password AutoFill, ASAuthorizationController, OAuth session
presentation, credential state, and local biometric re-authentication. Route
deep security work to `swift-security`: Keychain architecture/migration,
CryptoKit, Secure Enclave, certificate pinning/trust, keychain sharing, storage
hardening, and OWASP MASVS/MASTG. Keep only the storage minimum here: tokens and
secrets belong in Keychain; `LAContext.evaluatePolicy` alone must not release
protected secrets.

## SwiftUI SignInWithAppleButton

Use `SignInWithAppleButton` in SwiftUI views when the login surface is SwiftUI.
Request `.fullName` and `.email`, downcast a successful result to
`ASAuthorizationAppleIDCredential`, and pass it to the shared
[Token Validation](#token-validation) flow. Style with
`.signInWithAppleButtonStyle(...)`.

## Common Mistakes

- Assuming a saved local session means the Apple ID credential is still valid.
  Check credential state at launch and handle revocation notifications.
- Showing a full login screen before trying existing account setup flows.
  Treat `.notInteractive` as the normal "no local credential" path.
- Force-unwrapping `email` or `fullName`. Cache them on first authorization and
  handle `nil` later.
- Creating an `ASAuthorizationController` without a presentation context
  provider. Authorization UI needs the active presentation anchor.
- Storing identity tokens, authorization codes, access tokens, passwords, or
  passkey server state in `UserDefaults`, files, or Core Data. Store secrets in
  Keychain and keep relying-party passkey verification server-side.
- Adding passkey requests without `webcredentials:` Associated Domains for the
  relying-party domain, or trying to use app-native passkeys for unrelated
  websites.
- Expanding authentication work into CryptoKit, Secure Enclave, certificate
  pinning, or OWASP MASVS. Route those to `swift-security`.

## Review Checklist

- [ ] "Sign in with Apple" capability added in Xcode project
- [ ] `ASAuthorizationControllerPresentationContextProviding` implemented
- [ ] Credential state checked on every app launch (`getCredentialState(forUserID:completion:)`)
- [ ] `credentialRevokedNotification` observer registered; sign-out handled
- [ ] `email` and `fullName` cached on first authorization (not assumed available later)
- [ ] `identityToken` sent to server for validation, not trusted client-side only
- [ ] Tokens stored in Keychain, not UserDefaults or files
- [ ] `performExistingAccountSetupFlows` called before showing login UI
- [ ] Error cases handled: `.canceled`, `.failed`, `.notInteractive`
- [ ] `NSFaceIDUsageDescription` in Info.plist for biometric auth
- [ ] `ASWebAuthenticationSession` used for OAuth (not `WKWebView`)
- [ ] `prefersEphemeralWebBrowserSession` set for OAuth when appropriate
- [ ] `textContentType` set on username/password fields for AutoFill
- [ ] Passkey relying party has `webcredentials:` Associated Domains configured
- [ ] Passkey registration/assertion challenges come from the server and are verified server-side
- [ ] Deep Keychain, CryptoKit, Secure Enclave, certificate pinning, and MASVS work routed to `swift-security`

## References

- Keychain & biometric patterns: [references/keychain-biometric.md](references/keychain-biometric.md)
- Passkey patterns: [references/passkeys.md](references/passkeys.md)
- [AuthenticationServices](https://sosumi.ai/documentation/authenticationservices)
- [ASAuthorizationAppleIDProvider](https://sosumi.ai/documentation/authenticationservices/asauthorizationappleidprovider)
- [ASAuthorizationAppleIDCredential](https://sosumi.ai/documentation/authenticationservices/asauthorizationappleidcredential)
- [ASAuthorizationController](https://sosumi.ai/documentation/authenticationservices/asauthorizationcontroller)
- [ASWebAuthenticationSession](https://sosumi.ai/documentation/authenticationservices/aswebauthenticationsession)
- [Supporting passkeys](https://sosumi.ai/documentation/authenticationservices/supporting-passkeys)
- [ASAuthorizationPlatformPublicKeyCredentialProvider](https://sosumi.ai/documentation/authenticationservices/asauthorizationplatformpublickeycredentialprovider)
- [ASAuthorizationPasswordProvider](https://sosumi.ai/documentation/authenticationservices/asauthorizationpasswordprovider)
- [SignInWithAppleButton](https://sosumi.ai/documentation/authenticationservices/signinwithapplebutton)
- [Implementing User Authentication with Sign in with Apple](https://sosumi.ai/documentation/authenticationservices/implementing-user-authentication-with-sign-in-with-apple)
