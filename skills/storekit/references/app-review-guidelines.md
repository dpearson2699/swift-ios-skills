# App Review Guidelines -- In-App Purchases and Subscriptions

App Store review rules relevant to in-app purchases, subscriptions, and
payment compliance. Extracted from Apple's App Store Review Guidelines for
self-contained reference.

## In-App Purchase Rules (Guideline 3.1.1)

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

## Common IAP Rejection Reasons

1. **External payment links for digital content.** Any language or button directing users to purchase digital content outside the app is rejected.
2. **Missing restore purchases.** A visible restore purchases button is required on any paywall or subscription view.
3. **Unclear subscription terms.** Price, duration, and renewal behavior must be clearly displayed before the user commits. Free trials must state post-trial pricing.
4. **Incorrect product categorization.** Consumables, non-consumables, and auto-renewable subscriptions must be correctly categorized in App Store Connect.

## Pre-Submission Payments Checklist

- [ ] All digital content uses Apple IAP
- [ ] Subscription terms clearly displayed (price, duration, renewal behavior)
- [ ] No external payment links for digital content
- [ ] Free trial clearly states post-trial pricing
- [ ] Restore purchases button present and functional
- [ ] Consumables, non-consumables, and subscriptions correctly categorized
- [ ] Transaction verification uses StoreKit 2 APIs or server-side validation
- [ ] Ask to Buy / deferred transactions handled gracefully
