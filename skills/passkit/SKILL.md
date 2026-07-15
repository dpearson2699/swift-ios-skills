---
name: passkit
description: "Integrate Apple Pay payments and Wallet passes using PassKit. Use when adding Apple Pay buttons, creating payment requests, handling payment authorization, adding passes to Wallet, configuring merchant capabilities, managing shipping/contact fields, or working with PKPaymentRequest, PKPaymentAuthorizationController, PKPaymentButton, AddPassToWalletButton, PKPass, PKAddPassesViewController, PKPassLibrary, Wallet pass distribution, or Apple Pay checkout flows for physical goods, real-world services, donations, and eligible recurring payments."
---

# PassKit

Accept Apple Pay payments for physical goods, real-world services, donations,
and eligible recurring payments, and add passes to the user's Wallet. Covers
payment buttons, payment requests, authorization, Wallet passes, and merchant
configuration. Targets Swift 6.3 / iOS 26+.

For advanced Apple Pay flows, one `PKPaymentRequest` can set only one optional
advanced request type: recurring, automatic reload, deferred, Apple Pay Later
availability, or multi-token contexts. Use separate payment requests when a
checkout needs more than one of those modes.

## Contents

- [Setup](#setup)
- [Displaying the Apple Pay Button](#displaying-the-apple-pay-button)
- [Creating a Payment Request](#creating-a-payment-request)
- [Presenting the Payment Sheet](#presenting-the-payment-sheet)
- [Handling Payment Authorization](#handling-payment-authorization)
- [Wallet Passes](#wallet-passes)
- [Checking Pass Library](#checking-pass-library)
- [Common Mistakes](#common-mistakes)
- [Review Checklist](#review-checklist)
- [References](#references)

## Setup

### Project Configuration

1. Enable the **Apple Pay** capability in Xcode
2. Create a Merchant ID in the Apple Developer portal (format: `merchant.com.example.app`)
3. Generate and install a Payment Processing Certificate for your merchant ID
4. Add the merchant ID to your entitlements

### Availability Check

Always verify the device can make payments before showing Apple Pay UI. If you
check for an active card with `canMakePayments(usingNetworks:capabilities:)`,
Apple's HIG expects Apple Pay to be a primary, prominent payment option wherever
you use that check.

```swift
import PassKit

func canMakePayments() -> Bool {
    // Check device supports Apple Pay at all
    guard PKPaymentAuthorizationController.canMakePayments() else {
        return false
    }
    // Check user has cards for the networks you support
    return PKPaymentAuthorizationController.canMakePayments(
        usingNetworks: [.visa, .masterCard, .amex, .discover],
        capabilities: .threeDSecure
    )
}
```

## Displaying the Apple Pay Button

### SwiftUI

Use the built-in `PayWithApplePayButton` view in SwiftUI. Use Apple-provided
button APIs for any control labeled Apple Pay; custom buttons must not include
the Apple Pay logo or "Apple Pay" text.

```swift
import SwiftUI
import PassKit

struct CheckoutView: View {
    var body: some View {
        PayWithApplePayButton(.buy) {
            startPayment()
        }
        .payWithApplePayButtonStyle(.black)
        .frame(height: 48)
        .padding()
    }
}
```

### UIKit

Use `PKPaymentButton` for UIKit-based interfaces.

```swift
let button = PKPaymentButton(
    paymentButtonType: .buy,
    paymentButtonStyle: .black
)
button.cornerRadius = 12
button.addTarget(self, action: #selector(startPayment), for: .touchUpInside)
```

**Button types:** `.plain`, `.buy`, `.setUp`, `.inStore`, `.donate`,
`.checkout`, `.continue`, `.book`, `.subscribe`, `.reload`, `.addMoney`,
`.topUp`, `.order`, `.rent`, `.support`, `.contribute`, `.tip`

## Creating a Payment Request

Build a `PKPaymentRequest` with your merchant details and the items being purchased.
PassKit amount APIs take `NSDecimalNumber`, not `Double`.

```swift
func createPaymentRequest() -> PKPaymentRequest {
    let request = PKPaymentRequest()
    request.merchantIdentifier = "merchant.com.example.app"
    request.countryCode = "US"
    request.currencyCode = "USD"
    request.supportedNetworks = [.visa, .masterCard, .amex, .discover]
    request.merchantCapabilities = .threeDSecure

    request.paymentSummaryItems = [
        PKPaymentSummaryItem(
            label: "Widget",
            amount: NSDecimalNumber(string: "9.99")
        ),
        PKPaymentSummaryItem(
            label: "Shipping",
            amount: NSDecimalNumber(string: "4.99")
        ),
        PKPaymentSummaryItem(
            label: "My Store",
            amount: NSDecimalNumber(string: "14.98")
        ) // Total
    ]

    return request
}
```

The **last item** in `paymentSummaryItems` is treated as the total and its label
appears in the Pay line on the payment sheet.

### Requesting Shipping and Contact Info

Request only the contact fields needed to price, fulfill, or legally process the
order.
Collect required product choices, optional notes, per-item shipping destinations,
and pickup locations before the Apple Pay button when the payment sheet cannot
collect them accurately.

```swift
request.requiredShippingContactFields = [.postalAddress, .emailAddress, .name]
request.requiredBillingContactFields = [.postalAddress]

let standard = PKShippingMethod(
    label: "Standard",
    amount: NSDecimalNumber(string: "4.99")
)
standard.identifier = "standard"
standard.detail = "5-7 business days"

let express = PKShippingMethod(
    label: "Express",
    amount: NSDecimalNumber(string: "9.99")
)
express.identifier = "express"
express.detail = "1-2 business days"

request.shippingMethods = [standard, express]

request.shippingType = .shipping // .delivery, .storePickup, .servicePickup
```

### Supported Networks

| Network | Constant |
|---|---|
| Visa | `.visa` |
| Mastercard | `.masterCard` |
| American Express | `.amex` |
| Discover | `.discover` |
| China UnionPay | `.chinaUnionPay` |
| JCB | `.JCB` |
| Maestro | `.maestro` |
| Electron | `.electron` |
| Interac | `.interac` |

Query available networks at runtime with `PKPaymentRequest.availableNetworks()`.

## Presenting the Payment Sheet

Use `PKPaymentAuthorizationController` (works in both SwiftUI and UIKit, no view controller needed). The controller's delegate is weak, so retain the controller for the life of the sheet.

```swift
final class CheckoutCoordinator: NSObject {
    private var paymentController: PKPaymentAuthorizationController?

    @MainActor
    func startPayment() {
        let controller = PKPaymentAuthorizationController(
            paymentRequest: createPaymentRequest()
        )
        paymentController = controller
        controller.delegate = self
        controller.present { [weak self] presented in
            if !presented {
                self?.paymentController = nil
            }
        }
    }
}
```

## Handling Payment Authorization

Implement `PKPaymentAuthorizationControllerDelegate` to process the payment token.

```swift
extension CheckoutCoordinator: PKPaymentAuthorizationControllerDelegate {
    func paymentAuthorizationController(
        _ controller: PKPaymentAuthorizationController,
        didAuthorizePayment payment: PKPayment,
        handler completion: @escaping (PKPaymentAuthorizationResult) -> Void
    ) {
        // Send payment.token.paymentData to your payment processor
        Task {
            do {
                try await paymentService.process(payment.token)
                completion(PKPaymentAuthorizationResult(status: .success, errors: nil))
            } catch {
                completion(PKPaymentAuthorizationResult(status: .failure, errors: [error]))
            }
        }
    }

    func paymentAuthorizationControllerDidFinish(
        _ controller: PKPaymentAuthorizationController
    ) {
        controller.dismiss { [weak self] in
            self?.paymentController = nil
        }
    }
}
```

### Handling Shipping Changes

```swift
func paymentAuthorizationController(
    _ controller: PKPaymentAuthorizationController,
    didSelectShippingMethod shippingMethod: PKShippingMethod,
    handler completion: @escaping (PKPaymentRequestShippingMethodUpdate) -> Void
) {
    let updatedItems = recalculateItems(with: shippingMethod)
    let update = PKPaymentRequestShippingMethodUpdate(paymentSummaryItems: updatedItems)
    completion(update)
}
```

## Wallet Passes

### Adding a Pass to Wallet

Load signed `.pkpass` data, verify the device can add passes, then present
`PKAddPassesViewController` when you want the user to review the pass before
adding it. `PKPass(data:)` expects signed pass data and can throw invalid-data
or invalid-signature errors. Name `invalid-data` and `invalid-signature`
failures explicitly instead of hiding them behind a bare `try?` in review
guidance.

```swift
func addPassToWallet(data: Data) {
    guard PKAddPassesViewController.canAddPasses() else {
        return
    }

    do {
        let pass = try PKPass(data: data)
        guard let addController = PKAddPassesViewController(pass: pass) else {
            return
        }
        addController.delegate = self
        present(addController, animated: true)
    } catch {
        // Signed pass data is invalid or the signature cannot be validated.
        showRecoverablePassError(error)
    }
}
```

### SwiftUI Wallet Button

Use `AddPassToWalletButton` as the SwiftUI equivalent to `PKAddPassButton`.

```swift
import PassKit
import SwiftUI

struct AddPassButton: View {
    let passData: Data
    @State private var addedToWallet = false

    var body: some View {
        if PKAddPassesViewController.canAddPasses(),
           let pass = try? PKPass(data: passData) {
            AddPassToWalletButton([pass]) { added in
                addedToWallet = added
            }
            .addPassToWalletButtonStyle(.blackOutline)
            .frame(width: 250, height: 50)
        }
    }
}
```

## Checking Pass Library

Use `PKPassLibrary` to inspect and manage passes the user already has. Check
`PKPassLibrary.isPassLibraryAvailable()` before pass-library operations, but use
`PKAddPassesViewController.canAddPasses()` to decide whether the device can add
passes. `passes()` only returns passes your app can access through its
entitlements. When replacing an existing pass, check the Boolean result from
`replacePass(with:)` and handle failure. For signed pass bundle construction,
update web services, and `replacePass(with:)`, read
[references/wallet-passes.md](references/wallet-passes.md).

```swift
let library = PKPassLibrary()

// Check if a specific pass is already in Wallet
let hasPass = library.containsPass(pass)

// Retrieve passes your app can access
let passes = library.passes()

// Check if pass library is available
guard PKPassLibrary.isPassLibraryAvailable() else { return }
```

## Common Mistakes

### DON'T: Use StoreKit for physical goods

Apple Pay (PassKit) is for **physical goods, real-world services, donations, and
eligible recurring payments**. StoreKit is for virtual goods, app features, and
digital-content subscriptions. Using the wrong framework leads to App Review
rejection.

### DON'T: Hardcode merchant ID in multiple places

```swift
// WRONG: Merchant ID scattered across the codebase
let request1 = PKPaymentRequest()
request1.merchantIdentifier = "merchant.com.example.app"
// ...elsewhere:
let request2 = PKPaymentRequest()
request2.merchantIdentifier = "merchant.com.example.app" // easy to get out of sync

// CORRECT: Centralize configuration
enum PaymentConfig {
    static let merchantIdentifier = "merchant.com.example.app"
    static let countryCode = "US"
    static let currencyCode = "USD"
    static let supportedNetworks: [PKPaymentNetwork] = [.visa, .masterCard, .amex]
}
```

## Review Checklist

- [ ] Apple Pay capability enabled and merchant ID configured in Developer portal
- [ ] Payment Processing Certificate generated and installed
- [ ] `canMakePayments(usingNetworks:)` checked before showing Apple Pay button
- [ ] Apple Pay is prominent wherever active-card availability is checked
- [ ] Product choices, optional details, and complex shipping choices collected before payment sheet
- [ ] Last item in `paymentSummaryItems` is the total with merchant display name
- [ ] Payment summary and token-context amounts use `NSDecimalNumber`
- [ ] Payment token sent to server for processing (never decoded client-side)
- [ ] `PKPaymentAuthorizationController` retained while presented and cleared after finish
- [ ] `paymentAuthorizationControllerDidFinish` dismisses the controller
- [ ] Shipping method changes recalculate totals via delegate callback
- [ ] StoreKit used for virtual goods/digital content; Apple Pay used for physical goods, services, donations, and eligible recurring payments
- [ ] Wallet passes loaded from signed `.pkpass` bundles
- [ ] `PKPass(data:)` invalid-data and invalid-signature failures surfaced
- [ ] `PKPassLibrary.isPassLibraryAvailable()` used for pass operations, not add-pass capability
- [ ] `PKAddPassesViewController.canAddPasses()` checked before add-pass UI
- [ ] `PKPassLibrary.replacePass(with:)` Boolean result checked when replacing a pass
- [ ] Apple Pay button uses system-provided `PKPaymentButton` or `PayWithApplePayButton`
- [ ] Add-to-Wallet UI uses system-provided `PKAddPassButton`, `AddPassToWalletButton`, or `PKAddPassesViewController`
- [ ] Error states handled in authorization result (network failures, declined cards)

## References

- Extended patterns (recurring/deferred payments, coupon codes, multi-merchant, pass bundles, pass updates): [references/wallet-passes.md](references/wallet-passes.md)
- [PassKit framework](https://sosumi.ai/documentation/passkit)
- [PKPaymentRequest](https://sosumi.ai/documentation/passkit/pkpaymentrequest)
- [PKPaymentAuthorizationController](https://sosumi.ai/documentation/passkit/pkpaymentauthorizationcontroller)
- [PKPaymentButton](https://sosumi.ai/documentation/passkit/pkpaymentbutton)
- [PayWithApplePayButton](https://sosumi.ai/documentation/passkit/paywithapplepaybutton)
- [AddPassToWalletButton](https://sosumi.ai/documentation/passkit/addpasstowalletbutton)
- [PKPass](https://sosumi.ai/documentation/passkit/pkpass)
- [PKAddPassesViewController](https://sosumi.ai/documentation/passkit/pkaddpassesviewcontroller)
- [PKPassLibrary](https://sosumi.ai/documentation/passkit/pkpasslibrary)
- [PKPaymentNetwork](https://sosumi.ai/documentation/passkit/pkpaymentnetwork)
- [Apple Pay HIG](https://sosumi.ai/design/human-interface-guidelines/apple-pay)
