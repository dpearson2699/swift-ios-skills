# StoreKit 2 Advanced Reference

Covers subscription control styles, offer management, testing, server-side
validation, and advanced subscription handling patterns for StoreKit 2.

## SubscriptionStoreView Control Styles

Apply control styles to change how subscription options render in
`SubscriptionStoreView`.

```swift
// Individual buttons for each subscription option
.subscriptionStoreControlStyle(.buttons)

// Inline picker for compact selection
.subscriptionStoreControlStyle(.picker)

// Picker with the selected option visually emphasized
.subscriptionStoreControlStyle(.prominentPicker)

// Full-page swipeable picker (one option per page)
.subscriptionStoreControlStyle(.pagedPicker)

// Paged picker with prominent selected option
.subscriptionStoreControlStyle(.pagedProminentPicker)

// Minimal inline picker for tight layouts
.subscriptionStoreControlStyle(.compactPicker)

// System decides based on context
.subscriptionStoreControlStyle(.automatic)
```

### Control Placement

Specify where controls appear within the view:

```swift
.subscriptionStoreControlStyle(.picker, placement: .bottom)
// Placement options: .bottom, .leading, .trailing, .scrollView,
// .bottomBar, .buttonsInBottomBar
```

### Button Labels

Control what information subscription buttons display:

```swift
.subscriptionStoreButtonLabel(.multiline)   // Full details (name, price, period)
.subscriptionStoreButtonLabel(.price)       // Price only
.subscriptionStoreButtonLabel(.displayName) // Product name only
.subscriptionStoreButtonLabel(.action)      // Action text ("Subscribe")
.subscriptionStoreButtonLabel(.singleLine)  // Condensed single line
.subscriptionStoreButtonLabel(.automatic)   // System default
```

### Container Backgrounds

```swift
.containerBackground(.blue.gradient, for: .subscriptionStore)

.containerBackground(for: .subscriptionStoreHeader) {
    Image("premium-header").resizable().scaledToFill()
}

.containerBackground(for: .subscriptionStoreFullHeight) {
    LinearGradient(colors: [.blue, .purple], startPoint: .top, endPoint: .bottom)
}
```

### Subscription Store Buttons

```swift
.storeButton(.visible, for: .restorePurchases)
.storeButton(.visible, for: .redeemCode)
.storeButton(.visible, for: .cancellation)
.storeButton(.visible, for: .policies)
.storeButton(.hidden, for: .signIn)
```

### Policy Destinations

```swift
// URL-based
.subscriptionStorePolicyDestination(url: termsURL, for: .termsOfService)
.subscriptionStorePolicyDestination(url: privacyURL, for: .privacyPolicy)

// Custom view
.subscriptionStorePolicyDestination(for: .termsOfService) {
    TermsOfServiceView()
}

// Style policy link text
.subscriptionStorePolicyForegroundStyle(.white)
```

### Decorative Icons per Option

```swift
.subscriptionStoreControlIcon { product, subscriptionInfo in
    if subscriptionInfo.subscriptionPeriod.unit == .year {
        Image(systemName: "star.fill")
    } else {
        Image(systemName: "star")
    }
}
```

### Sign-In Action

```swift
.storeButton(.visible, for: .signIn)
.subscriptionStoreSignInAction {
    showSignInSheet = true
}
```

## Subscription Group Management

### Hierarchical Layouts with SubscriptionOptionGroup

```swift
SubscriptionStoreView(groupID: "premium_group") {
    SubscriptionOptionGroup("Monthly Plans") { product in
        product.subscription?.subscriptionPeriod.unit == .month
    }
    SubscriptionOptionGroup("Annual Plans") { product in
        product.subscription?.subscriptionPeriod.unit == .year
    }
}
```

### Automatic Period Grouping

```swift
SubscriptionStoreView(groupID: "premium_group") {
    SubscriptionPeriodGroupSet()
}
```

### Sections with Headers

```swift
SubscriptionStoreView(groupID: "premium_group") {
    SubscriptionOptionSection("Standard", isIncluded: { product in
        product.subscription?.groupLevel == 1
    }) {
        Text("Basic features included")
    }
    SubscriptionOptionSection("Pro", isIncluded: { product in
        product.subscription?.groupLevel == 2
    }) {
        Text("All features included")
    }
}
```

### Visible Relationships

Filter which subscription levels are shown relative to the current subscription:

```swift
// Show all options
SubscriptionStoreView(groupID: "group_id", visibleRelationships: .all)

// Show only upgrades from current subscription
SubscriptionStoreView(groupID: "group_id", visibleRelationships: .upgrade)
```

### Custom Subscription Store Controls

```swift
// Custom button for a specific subscription option
SubscriptionStoreButton(option)

// Custom picker with confirmation
SubscriptionStorePicker(pickerContent: { option in
    Text(option.displayName)
}, confirmation: { selectedOption in
    Text("Subscribe to \(selectedOption.displayName)")
})
```

## Introductory Offers

### Checking Eligibility

```swift
// Per-product eligibility
let isEligible = product.subscription?.isEligibleForIntroOffer ?? false

// Per-group eligibility
let groupEligible = await Product.SubscriptionInfo.isEligibleForIntroOffer(
    for: groupID
)
```

### Accessing Offer Details

```swift
if let introOffer = product.subscription?.introductoryOffer {
    let price = introOffer.displayPrice       // Localized price
    let period = introOffer.period            // SubscriptionPeriod
    let count = introOffer.periodCount        // Number of periods
    let mode = introOffer.paymentMode         // .freeTrial, .payAsYouGo, .payUpFront

    switch introOffer.paymentMode {
    case .freeTrial:
        Text("Free for \(count) \(period.unit)")
    case .payAsYouGo:
        Text("\(price)/\(period.unit) for \(count) periods")
    case .payUpFront:
        Text("\(price) for \(count) \(period.unit)")
    default:
        EmptyView()
    }
}
```

### Introductory offers apply automatically when eligible. No special purchase options needed.

## Promotional Offers

Promotional offers require server-side signature generation.

### Accessing Promotional Offers

```swift
let promoOffers = product.subscription?.promotionalOffers ?? []
for offer in promoOffers {
    print("Offer: \(offer.id ?? "nil"), price: \(offer.displayPrice)")
}
```

### Purchasing with a Promotional Offer

```swift
// 1. Get signature from your server
let signature = Product.SubscriptionOffer.Signature(
    keyID: serverKeyID,
    nonce: serverNonce,
    timestamp: serverTimestamp,
    signature: serverSignatureData
)

// 2. Purchase with the offer
let result = try await product.purchase(options: [
    .promotionalOffer(offerID: offer.id!, signature: signature)
])
```

### SwiftUI Automatic Promotional Offer

```swift
.subscriptionPromotionalOffer(offer: promoOffer, signature: signature)
```

### Preferred Offer Selection

Let the system choose the best offer for each user:

```swift
.preferredSubscriptionOffer { product, subscription, eligibleOffers in
    // Return the best offer, or nil for no offer
    return eligibleOffers.first
}
```

## Win-Back Offers

Target former subscribers who cancelled. Available since iOS 18.

### Accessing Win-Back Offers

```swift
let winBackOffers = product.subscription?.winBackOffers ?? []
```

### Checking Eligibility via Renewal Info

```swift
let statuses = try await Product.SubscriptionInfo.Status.status(for: groupID)
for status in statuses {
    guard case .verified(let renewalInfo) = status.renewalInfo else { continue }
    let eligibleIDs = renewalInfo.eligibleWinBackOfferIDs
    // Display offers matching these IDs
}
```

### Purchasing with a Win-Back Offer

```swift
let result = try await product.purchase(options: [
    .winBackOffer(winBackOffer)
])
```

## Offer Codes

### Redemption Sheet

```swift
@State private var showRedeemSheet = false

var body: some View {
    Button("Redeem Code") { showRedeemSheet = true }
        .offerCodeRedemption(isPresented: $showRedeemSheet) { result in
            switch result {
            case .success:
                await storeManager.updateEntitlements()
            case .failure(let error):
                print("Redemption failed: \(error)")
            }
        }
}
```

### Show Redeem Button on Subscription Store

```swift
.storeButton(.visible, for: .redeemCode)
```

### Verifying Applied Offers in Transactions

```swift
if let offerType = transaction.offerType {
    switch offerType {
    case .introductory: break  // Introductory offer applied
    case .promotional: break   // Check transaction.offerID
    case .code: break          // Offer code redeemed
    case .winBack: break       // Win-back offer applied
    default: break
    }
}
```

## Server-Side Validation

### Sending JWS to Server

StoreKit 2 transactions are JWS (JSON Web Signature) tokens. Send the raw
JWS string to your server for validation.

```swift
case .success(let verification):
    let transaction = try checkVerified(verification)

    // Send to server for validation
    let jwsString = verification.jwsRepresentation
    try await sendToServer(jws: jwsString, productID: transaction.productID)

    await transaction.finish()
```

### Server-Side Verification

On your server, use Apple's App Store Server Library:
- `verifyAndDecodeTransaction(signedTransaction:)` to validate and decode
- `verifyAndDecodeRenewalInfo(signedRenewalInfo:)` for subscription renewal info
- The JWS format matches `JWSTransaction` from the App Store Server API and
  App Store Server Notifications V2

### Device Verification

Bind transactions to specific devices to prevent replay attacks:

```swift
let deviceVerification = transaction.deviceVerification
let nonce = transaction.deviceVerificationNonce
// Send both to server for additional validation
```

## StoreKit Testing in Xcode

### StoreKit Configuration Files

1. Create a StoreKit Configuration file in Xcode: File > New > File >
   StoreKit Configuration File
2. Add products matching your App Store Connect configuration
3. Set the configuration in the scheme: Edit Scheme > Run > Options >
   StoreKit Configuration

### Configuration File Contents

Define products with:
- Product ID, reference name, product type
- Price and locale
- Subscription group and level (for subscriptions)
- Introductory and promotional offers
- Family Sharing settings

### Testing Features

```swift
// Simulate Ask to Buy
try await product.purchase(options: [.simulatesAskToBuyInSandbox(true)])

// Test-only: set purchase date and renewal behavior
try await product.purchase(options: [
    .purchaseDate(Date(), renewalBehavior: .default)
])

// Test-only: apply offer code by reference name
try await product.purchase(options: [.codeOffer(referenceName: "SUMMER2024")])
```

### StoreKit Testing Capabilities

- Simulate failed transactions, interrupted purchases, refunds
- Speed up subscription renewals (renewals happen in minutes, not months)
- Test grace period and billing retry states
- Clear purchase history between test runs
- Test offer redemption flows
- Simulate subscription expiration and cancellation

### Transaction Manager in Xcode

Use Debug > StoreKit > Manage Transactions to:
- View all test transactions
- Delete transactions to reset state
- Request refunds
- Expire subscriptions
- Approve or decline Ask to Buy requests

## Subscription Renewal States

### Active States (grant access)

```swift
switch status.state {
case .subscribed:
    // Active, auto-renewing subscription
    grantAccess()

case .inGracePeriod:
    // Payment failed but grace period active -- still grant access
    // Show a gentle prompt to update payment method
    grantAccess()
    showPaymentUpdatePrompt()
```

### Degraded States (consider limited or no access)

```swift
case .inBillingRetryPeriod:
    // Payment failed, Apple is retrying -- access decision is yours
    // Apple recommends granting limited access to encourage payment update
    grantLimitedAccess()
    showPaymentFailedBanner()

case .expired:
    // Subscription ended -- check expirationReason
    revokeAccess()
    if let reason = renewalInfo.expirationReason {
        switch reason {
        case .autoRenewDisabled: showResubscribeOffer()
        case .billingError: showUpdatePaymentMethod()
        case .didNotConsentToPriceIncrease: showPriceInfo()
        case .productUnavailable: break
        default: break
        }
    }

case .revoked:
    // Apple refunded -- must revoke access
    revokeAccess()
```

### Expiration Reasons

| Reason | Meaning |
|---|---|
| `.autoRenewDisabled` | User voluntarily cancelled |
| `.billingError` | Payment method failed |
| `.didNotConsentToPriceIncrease` | User did not agree to price increase |
| `.productUnavailable` | Product no longer available |
| `.unknown` | Unspecified reason |

## Grace Period and Billing Retry

### Grace Period

When enabled in App Store Connect, subscribers retain access for a short
period after a billing failure. Check `status.state == .inGracePeriod` and
the `gracePeriodExpirationDate` on renewal info.

```swift
if status.state == .inGracePeriod,
   case .verified(let renewalInfo) = status.renewalInfo {
    let expirationDate = renewalInfo.gracePeriodExpirationDate
    // Grant access but prompt to update payment method
}
```

### Billing Retry

Apple automatically retries failed payments. During billing retry, the
subscription state is `.inBillingRetryPeriod`. Check `renewalInfo.isInBillingRetry`.

## Refund Handling

### Initiating Refund Requests

```swift
// From a transaction instance
let refundStatus = try await transaction.beginRefundRequest(in: windowScene)

// From a transaction ID
let refundStatus = try await Transaction.beginRefundRequest(
    for: transactionID, in: windowScene
)
```

### SwiftUI Refund Sheet

```swift
@State private var showRefund = false

Button("Request Refund") { showRefund = true }
    .refundRequestSheet(for: transactionID, isPresented: $showRefund) { result in
        // Handle refund request dismissal
    }
```

### Detecting Refunds

Refunds appear via `Transaction.updates` with a non-nil `revocationDate`.
Always check `revocationDate` when evaluating entitlements.

```swift
if let revocationDate = transaction.revocationDate {
    revokeAccess(for: transaction.productID)
    // revocationPercentage indicates partial vs full refund
    let percentage = transaction.revocationPercentage
}
```

## Family Sharing

### Checking Ownership Type

```swift
switch transaction.ownershipType {
case .purchased:
    // User purchased directly
    break
case .familyShared:
    // Shared via Family Sharing -- may be revoked if sharer leaves
    break
default:
    break
}
```

### Family Shareable Products

Check `product.isFamilyShareable` to determine if a product supports
Family Sharing. Enable Family Sharing in App Store Connect per product.

Family Sharing changes arrive via `Transaction.updates`. When a family
member stops sharing, the transaction is revoked.

## Ask to Buy Handling

Ask to Buy applies to child accounts in Family Sharing. The purchase
returns `.pending` and must be approved by the family organizer.

```swift
case .pending:
    // Show UI indicating purchase needs parental approval
    showPendingApprovalState()
    // When approved, the transaction arrives via Transaction.updates
```

### Testing Ask to Buy

```swift
try await product.purchase(options: [.simulatesAskToBuyInSandbox(true)])
```

Then approve or decline in Xcode's Transaction Manager.

## .currentEntitlementTask SwiftUI Modifier

### Basic Usage

```swift
.currentEntitlementTask(for: "com.app.premium") { state in
    self.entitlementState = state
}
```

### EntitlementTaskState Pattern

```swift
enum EntitlementTaskState<Value> {
    case loading
    case success(Value)    // Value is VerificationResult<Transaction>?
    case failure(any Error)
}
```

Use `map` and `flatMap` for transformations:

```swift
.currentEntitlementTask(for: ProductID.premium) { state in
    self.isPremium = state.map { $0 != nil } ?? false
}
```

### Related Task Modifiers

```swift
// Load a single product
.storeProductTask(for: "com.app.premium") { taskState in
    // taskState: Product.TaskState (.loading, .success(Product), .unavailable, .failure)
}

// Load multiple products
.storeProductsTask(for: ["id1", "id2"]) { taskState in
    // taskState: Product.CollectionTaskState (.loading, .success([Product], unavailable:), .failure)
}

// Monitor subscription status
.subscriptionStatusTask(for: "group_id") { taskState in
    // Receive subscription status updates
}
```

## Subscription Status Listener

Listen for real-time subscription status changes:

```swift
func listenForStatusChanges() -> Task<Void, Never> {
    Task {
        for await (groupID, statuses) in Product.SubscriptionInfo.Status.all {
            for status in statuses {
                guard case .verified(let renewalInfo) = status.renewalInfo else { continue }
                await handleStatusChange(state: status.state, renewalInfo: renewalInfo)
            }
        }
    }
}
```

## Product Promotion Management

Control the order and visibility of promoted in-app purchases on the App Store
product page:

```swift
// Product.PromotionInfo provides device-level promotion customization
// Configure in App Store Connect and override per-device as needed
```

## Price Increase Handling

```swift
if case .verified(let renewalInfo) = status.renewalInfo {
    switch renewalInfo.priceIncreaseStatus {
    case .noIncreasePending: break
    case .pending:
        // User has not yet consented -- show price increase info
        showPriceIncreaseConsent(newPrice: renewalInfo.renewalPrice,
                                 currency: renewalInfo.currency)
    case .agreed:
        // User accepted the price increase
        break
    }
}
```

## Unfinished Transactions

Process transactions that were not finished in previous sessions:

```swift
func processUnfinishedTransactions() async {
    for await result in Transaction.unfinished {
        guard case .verified(let transaction) = result else { continue }
        await deliverContent(for: transaction)
        await transaction.finish()
    }
}
```

Call this at app launch alongside the `Transaction.updates` listener to
ensure no purchases are lost.

## Common Advanced Mistakes

### Not processing unfinished transactions at launch

```swift
// WRONG: Only listen for updates, ignore pending deliveries
init() { transactionListener = listenForTransactions() }

// CORRECT: Process unfinished transactions AND listen for updates
init() {
    transactionListener = listenForTransactions()
    Task { await processUnfinishedTransactions() }
}
```

### Treating billing retry as expired

```swift
// WRONG: Revoking access during billing retry
case .inBillingRetryPeriod: revokeAccess()

// CORRECT: Grant limited access and prompt payment update
case .inBillingRetryPeriod:
    grantLimitedAccess()
    showUpdatePaymentPrompt()
```

### Not handling Family Sharing revocation

```swift
// WRONG: Assuming family-shared access is permanent
if transaction.ownershipType == .familyShared {
    grantPermanentAccess()
}

// CORRECT: Check revocation status and listen for changes
if transaction.ownershipType == .familyShared,
   transaction.revocationDate == nil {
    grantAccess()  // May be revoked later via Transaction.updates
}
```
