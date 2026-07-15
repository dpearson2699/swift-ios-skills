---
name: app-store-optimization
description: "Optimize App Store product pages for search visibility and conversion. Use for App Store Optimization (ASO), keyword research, app name/subtitle/keyword-field strategy, conversion-focused descriptions and promotional text, screenshot captions and ordering, Custom Product Pages with assigned search keywords, In-App Events, Product Page Optimization tests, localized metadata, ratings/review strategy, and in-app review prompt timing with RequestReviewAction or AppStore.requestReview. Also use when routing ASO vs App Store review, privacy/ATT, or StoreKit implementation boundaries."
---

# App Store Optimization (ASO)

Search visibility and conversion optimization for App Store product pages. This skill covers strategic metadata decisions -- which keywords to target, how to structure descriptions for conversion, and how to use Custom Product Pages and in-app events for discoverability. For metadata compliance rules (character limits, screenshot device requirements, rejection triggers), see the `app-store-review` skill.

## Contents

- [Workflow and Boundaries](#workflow-and-boundaries)
- [Title and Subtitle Strategy](#title-and-subtitle-strategy)
- [Keyword Field Strategy](#keyword-field-strategy)
- [Description Structure](#description-structure)
- [Promotional Text](#promotional-text)
- [Screenshot and Preview Optimization](#screenshot-and-preview-optimization)
- [In-App Review Prompts](#in-app-review-prompts)
- [Custom Product Pages](#custom-product-pages)
- [In-App Events](#in-app-events)
- [Product Page Optimization](#product-page-optimization)
- [Ratings and Review Management](#ratings-and-review-management)
- [Localized Metadata Optimization](#localized-metadata-optimization)
- [Common Mistakes](#common-mistakes)
- [Review Checklist](#review-checklist)
- [References](#references)

## Workflow and Boundaries

1. Split recommendations into **Visibility** (indexed metadata, localization,
   ratings, events) and **Conversion** (message, assets, variants, experiments).
2. Name the evidence, owner, target metric, and validation checkpoint for each.
3. Apply the [Review Checklist](#review-checklist).

| Work | Owner |
|---|---|
| Listing, keyword/message fit, assets, page variants, localization, events, ratings strategy | This skill |
| Submission compliance, privacy manifest/labels, ATT wording, rejection risk | `app-store-review` |
| Purchases, paywalls, entitlements, subscription mechanics | `storekit` |

## Title and Subtitle Strategy

Apple indexes the app name and subtitle for search. Together they provide 60 characters (30 + 30) of indexed, high-visibility keyword real estate.

### Positioning framework

Use **Brand -- Keyword** when the brand already has recognition, **Keyword -- Brand** when a new app must compete on category terms, and a blended name when the brand naturally contains a relevant keyword.

### Rules

- Do not repeat words between the name and subtitle -- Apple indexes both, so duplicates waste characters.
- Front-load the highest-value keyword in whichever field has more room.
- Avoid generic filler words ("the", "best", "app") -- they consume space without search value.
- The subtitle should communicate the primary value proposition, not a tagline.

## Keyword Field Strategy

App Store Connect accepts up to 100 UTF-8 bytes in the keyword field (some
Apple overview pages summarize this as 100 characters). Use comma-separated
terms with no spaces after commas; each term must be longer than two
characters.

### Prioritization

Rank candidate keywords by three factors:

| Factor | Weight | Signal |
|--------|--------|--------|
| **Relevance** | Highest | Does the keyword describe what the app actually does? |
| **Search volume** | Medium | Are users actually searching for this term? |
| **Competition** | Lower | How many apps target this keyword? |

Prioritize user intent and metadata fit. Account for the primary category
alongside the app name, subtitle, and keyword field; do not repeat it.

### Tactical rules

- Deduplicate against title and subtitle -- Apple already indexes those words.
- Do not include both singular and plural forms of the same term; Apple treats
  them as duplicates.
- Omit the category name -- Apple adds the app's primary category to search automatically.
- Omit spaces after commas -- they count against the 100-character limit.
- Consider abbreviations and common misspellings if they are genuine search terms.
- Reserve space for the most relevant, highest-intent terms; do not spend characters on terms that only weakly describe the app.

**See:** [references/keyword-research-methodology.md](references/keyword-research-methodology.md) for the full research process, scoring framework, and indexing details.

**Validation checkpoint:** Render the final name, subtitle, and keyword field
together. Count its UTF-8 bytes, split it on commas, reject blank,
space-prefixed, or two-character-or-shorter tokens, compare normalized words
across the three indexed fields and primary
category, and require a relevance or demand signal for every retained term.
Revise the field and repeat the check until every token earns its space.

## Description Structure

Apple's search guidance centers text relevance on the app name, subtitle, keywords, and primary category, plus behavior signals such as downloads, ratings, and reviews. Treat the description as conversion copy, not a place to stuff extra search terms: users who expand it are evaluating whether to download.

### Four-part structure

1. **Hook** (first 1-3 lines) -- the only text visible before the "more" fold. Lead with the strongest benefit or differentiator. This is the most important copy on the page.
2. **Feature highlights** -- 4-6 short feature descriptions. Use Unicode bullet characters (•) since the App Store does not render markdown. Focus on outcomes, not technical details.
3. **Social proof** -- awards, press quotes, user count milestones, or notable ratings. One or two lines.
4. **Call to action** -- a closing line encouraging the download. Keep it short and benefit-focused.

### Formatting notes

- The App Store does not render markdown, HTML, or rich text. Use plain text with Unicode characters for structure.
- Short paragraphs with line breaks between them. Walls of text kill conversion.
- Write per locale -- translate the structure, not the words. See [Localized Metadata Optimization](#localized-metadata-optimization).

## Promotional Text

Promotional text appears above the description, is limited to 170 characters, and can be updated at any time without submitting a new app version.

### Rotation strategy

Update promotional text for feature launches, seasonal moments, awards or press, promotions, and in-app events. Do not leave it static across releases; if there is nothing timely to promote, rotate between the app's strongest selling points.

## Screenshot and Preview Optimization

Most users never scroll past the first 3 visible screenshots. These slots determine whether a user engages with the full product page or moves on.

### First 3 screenshots

- Lead with the primary value proposition -- the screen that best demonstrates why someone should download.
- Never place onboarding, splash, or loading screens in the first 3 slots.
- Each screenshot should demonstrate a different benefit or feature.

### Caption writing

- Write benefit-oriented captions, not feature labels. "Never miss a deadline" converts better than "Calendar View".
- Keep captions to 2-5 words above the screenshot and one short line below.
- Use action verbs: "Track", "Share", "Discover", "Build".

### Ordering strategy

Use slot 1 for the primary value proposition, slot 2 for the core differentiator, slot 3 for the next strongest feature, and later slots for supporting features, social proof, or edge cases.

### App preview video

If a preview video is present, it occupies the first slot. The first frame becomes the poster image when autoplay is disabled -- choose a frame that works as a standalone screenshot.

For screenshot device requirements and compliance rules, see the `app-store-review` skill.

**Validation checkpoint:** Preview each localized product page at first-fold size.
Confirm that the first three visible assets communicate distinct benefits, that
captions match the UI and public claims, and that the ordering answers the same
intent targeted by the page's metadata. Replace or reorder any asset that fails,
then review the first fold again as a set.

## In-App Review Prompts

StoreKit provides `RequestReviewAction` for SwiftUI and `AppStore.requestReview(in:)` for UIKit. Use this section for timing strategy; for the full StoreKit API surface, see the `storekit` skill.

### System behavior

- The system enforces a maximum of 3 prompts per 365-day period per device for users who have not yet rated the app.
- The API is a request, not a guarantee -- StoreKit decides whether to show the prompt.
- During development, the prompt always appears. In TestFlight, it never appears.

### Prompt timing

Good triggers include completing a meaningful task, achieving a milestone or streak, a positive in-app moment, or several active sessions. Bad triggers include first launch, onboarding, errors, crashes, failed transactions, or direct button-tap pre-screens. Do not gate the prompt behind a "Rate this app?" dialog -- Apple discourages intercepting the system prompt and may reject apps that pre-screen.

### Persistent review link

For a settings screen or "Rate us" option, link directly to the App Store review page using the URL format:

```
https://apps.apple.com/app/id{APP_ID}?action=write-review
```

This opens the review writing screen directly and is not subject to the 3x/year system limit.

## Custom Product Pages

Custom Product Pages allow up to 70 variant product pages per app. Each variant can have different screenshots, app preview videos, promotional text, and assigned search keywords -- tailored to a specific audience or acquisition channel.

When recommending Custom Product Pages, explicitly mention both the 70-page capacity and assigned-keyword search visibility, then map each page to a distinct audience, message, keyword/ad intent, and measurement plan.

### Use cases

Use separate pages for paid search ad groups, social campaigns, feature-specific landings, seasonal campaigns, and other acquisition paths where the first screenshot or promotional text should match a distinct user intent.

### Setup

- Each Custom Product Page gets a unique App Store URL usable in ad campaigns, deep links, and web pages.
- Approved pages can also appear in App Store search for assigned keywords from the latest approved app version.
- Pages can be localized independently.
- Create pages in App Store Connect under the Custom Product Pages tab.
- Name pages descriptively for internal tracking (e.g., "Search-FitnessTracking", "Social-HolidayCampaign").

**See:** [references/product-page-variants.md](references/product-page-variants.md) for setup details, URL structure, and campaign mapping strategy.

## In-App Events

In-app events surface in App Store search results, on the Today tab, and in personalized recommendations. They increase visibility during the event window and can re-engage lapsed users.

### Event types

Choose the Apple event badge that matches the actual in-app experience: Challenge, Competition, Live Event, Major Update, New Season, Premiere, or Special Event. Do not manufacture events without real time-bound content.

### Metadata limits

Event name is 30 characters, short description 50, long description 120, and the event card image is required at 16:9 (1920x1080 or similar).

### Strategy

- Schedule events around feature releases, seasonal moments, or content drops.
- Write the name and short description for their event-card context across the
  product page, Search, and Today; measure whether a timely card improves taps.
- Overlap events strategically: end the current event as the next one begins to maintain continuous search visibility.

**See:** [references/product-page-variants.md](references/product-page-variants.md) for event scheduling templates.

## Product Page Optimization

App Store Connect provides native testing for product page elements.

### What can be tested

- App icon (alternate icons)
- Screenshots (order, content, captions)
- App preview video

Each test can include up to three treatments against the original product page, which serves as the default baseline.

### Test design

- Run tests for a minimum of 7 days to account for day-of-week variation.
- Ensure sufficient traffic for statistical significance -- low-traffic apps may need longer test durations.
- Test one hypothesis at a time as a methodology choice (e.g., screenshot order OR caption copy, not both simultaneously), even when App Store Connect allows multiple treatments.
- Select the localizations included in the test; all supported localizations are selected by default.
- A test runs for up to 90 days or until manually stopped. Results appear in App Analytics after at least five first-time downloads are associated with the test.
- PPO recommendations should name the hypothesis, up to three treatments, selected localizations, target metric, and decision rule.

### Interpreting results

- Focus on conversion rate lift (impressions-to-downloads), not absolute download numbers.
- App Store Connect reports conversion rate, lift, and confidence. Treat 90%+ confidence as the threshold for "Performing Better" or "Performing Worse" decisions.
- After applying a winner, wait before starting the next test to establish a clean baseline.

## Ratings and Review Management

Ratings and reviews appear on the product page and in search results, influence App Store search ranking, and affect conversion. The strategy is to earn more positive, recent feedback by prompting only after successful user moments and by responding constructively to issues.

### Review response strategy

- Respond to negative reviews in App Store Connect -- a professional response improves perceived quality even without changing the rating number.
- Acknowledge the issue, state what is being done (or has been fixed), and keep the tone neutral.
- Use review language as customer research: users often describe their goals, frustrations, and category vocabulary in words that can improve future metadata and screenshot messaging.

### Rating reset

When submitting a new version, you can choose to reset the displayed rating. Use this strategically:

Reset only when the displayed rating is significantly below the app's current quality after major improvements. Do not reset a strong, representative rating; do not reset for ordinary bug fixes; and wait for stabilization after a risky redesign.

## Localized Metadata Optimization

Localizing ASO is not the same as translating the app UI. Keyword strategy, descriptions, and screenshot captions must be researched and written per market, not machine-translated from the primary locale.

### Key principles

- **Research keywords per market.** The most-searched term for "photo editor" in Japanese is not a direct translation of "photo editor."
- **Rewrite descriptions per locale.** Adapt the hook-features-proof-CTA structure to local conventions and selling points.
- **Localize each metadata surface.** App Store guidance explicitly calls out localized descriptions, keywords, app previews, and screenshots; do not assume direct translations or unsupported cross-locale indexing behavior.
- **Localize screenshot captions.** Captions in the user's language convert better than untranslated English.

For in-app string localization (String Catalogs, FormatStyle, right-to-left layout), see the `ios-localization` skill.

## Common Mistakes

1. **Writing feature-descriptive captions instead of benefit-oriented screenshot copy.**
2. **Translating keywords instead of researching per-market search terms.**
3. **Prompting for reviews after onboarding, errors, crashes, or failed transactions.**
4. **Ignoring the first three screenshot slots or leading with onboarding/splash screens.**
5. **Running PPO tests without enough duration, traffic, or a single clear hypothesis.**
6. **Reusing identical assets across all Custom Product Pages.**

## Review Checklist

- [ ] Indexed metadata passes the title/subtitle and keyword validation checkpoints
- [ ] Description, promotional text, and first-fold assets pass their conversion checks
- [ ] Metadata and assets are researched, written, ordered, and previewed per locale
- [ ] Review prompts follow a successful user moment and StoreKit's system behavior
- [ ] Page variants, events, and PPO tests name their audience, evidence, metric, and decision rule
- [ ] Public claims and screenshots pass the `app-store-review` compliance checklist

## References

- Keyword research methodology: [references/keyword-research-methodology.md](references/keyword-research-methodology.md)
- Custom Product Pages, A/B testing, and in-app events: [references/product-page-variants.md](references/product-page-variants.md)
