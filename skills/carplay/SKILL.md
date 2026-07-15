---
name: carplay
description: "Build CarPlay-enabled apps using the CarPlay framework. Use when creating navigation, audio, communication, EV charging, parking, or food ordering apps for the car display, working with CPTemplateApplicationScene, CPInterfaceController template hierarchies, CPListTemplate, CPMapTemplate, CPNowPlayingTemplate, configuring CarPlay entitlements, or integrating with CarPlay Simulator for testing."
---

# CarPlay

Build category-entitled, template-based CarPlay apps for the vehicle display.
Scope: Swift 6.3, iOS 26+.

See [references/carplay-patterns.md](references/carplay-patterns.md) for extended patterns including full
navigation sessions, dashboard scenes, and advanced template composition.

Scope boundary: full CarPlay framework apps use category entitlements,
`CPTemplateApplicationScene`, `CPTemplateApplicationSceneDelegate`,
`CPInterfaceController`, and system `CPTemplate` navigation. CarPlay-visible
WidgetKit widgets and ActivityKit Live Activities are separate system
experiences; route their implementation to those domains while keeping
CarPlay-specific validation here.

## Contents

- [Entitlements and Setup](#entitlements-and-setup)
- [Scene Configuration](#scene-configuration)
- [Templates Overview](#templates-overview)
- [Navigation Apps](#navigation-apps)
- [Audio Apps](#audio-apps)
- [Communication Apps](#communication-apps)
- [Point of Interest Apps](#point-of-interest-apps)
- [Testing with CarPlay Simulator](#testing-with-carplay-simulator)
- [Common Mistakes](#common-mistakes)
- [Review Checklist](#review-checklist)
- [References](#references)

## Entitlements and Setup

Request the category-specific entitlement from
[Apple's CarPlay entitlement form](https://developer.apple.com/contact/carplay),
accept the addendum, then provision the approved category key below.

### Entitlement Keys by Category

| Entitlement | Category |
|---|---|
| `com.apple.developer.carplay-audio` | Audio |
| `com.apple.developer.carplay-communication` | Communication |
| `com.apple.developer.carplay-maps` | Navigation |
| `com.apple.developer.carplay-charging` | EV Charging |
| `com.apple.developer.carplay-parking` | Parking |
| `com.apple.developer.carplay-quick-ordering` | Quick Food Ordering |

### Project Configuration

1. Update the App ID in the developer portal under Additional Capabilities.
2. Generate a new provisioning profile for the updated App ID.
3. In Xcode, disable automatic signing and import the CarPlay provisioning profile.
4. Add an `Entitlements.plist` with the entitlement key set to `true`.
5. Set Code Signing Entitlements build setting to the `Entitlements.plist` path.

### Key Types

| Type | Role |
|---|---|
| `CPTemplateApplicationScene` | UIScene subclass for the CarPlay display |
| `CPTemplateApplicationSceneDelegate` | Scene connect/disconnect lifecycle |
| `CPInterfaceController` | CarPlay-provided controller for setting the root template and pushing, presenting, or popping templates |
| `CPTemplate` | Abstract base for all CarPlay templates |
| `CPSessionConfiguration` | Vehicle display limits and content style |

## Scene Configuration

Declare the CarPlay scene in `Info.plist` and implement
`CPTemplateApplicationSceneDelegate` to respond when CarPlay connects.

### Info.plist Scene Manifest

```plist
<key>UIApplicationSceneManifest</key>
<dict>
    <key>UIApplicationSupportsMultipleScenes</key>
    <true/>
    <key>UISceneConfigurations</key>
    <dict>
        <key>CPTemplateApplicationSceneSessionRoleApplication</key>
        <array>
            <dict>
                <key>UISceneClassName</key>
                <string>CPTemplateApplicationScene</string>
                <key>UISceneConfigurationName</key>
                <string>CarPlaySceneConfiguration</string>
                <key>UISceneDelegateClassName</key>
                <string>$(PRODUCT_MODULE_NAME).CarPlaySceneDelegate</string>
            </dict>
        </array>
    </dict>
</dict>
```

### Scene Delegate (Non-Navigation)

Non-navigation apps receive an interface controller only. No window.

```swift
import CarPlay

final class CarPlaySceneDelegate: UIResponder,
    CPTemplateApplicationSceneDelegate {

    var interfaceController: CPInterfaceController?

    func templateApplicationScene(
        _ templateApplicationScene: CPTemplateApplicationScene,
        didConnect interfaceController: CPInterfaceController
    ) {
        self.interfaceController = interfaceController
        interfaceController.setRootTemplate(buildRootTemplate(),
                                            animated: true, completion: nil)
    }

    func templateApplicationScene(
        _ templateApplicationScene: CPTemplateApplicationScene,
        didDisconnectInterfaceController interfaceController: CPInterfaceController
    ) {
        self.interfaceController = nil
    }
}
```

### Scene Delegate (Navigation)

Navigation apps receive both an interface controller and a `CPWindow`.
Set the window's root view controller to draw map content.

```swift
func templateApplicationScene(
    _ templateApplicationScene: CPTemplateApplicationScene,
    didConnect interfaceController: CPInterfaceController,
    to window: CPWindow
) {
    self.interfaceController = interfaceController
    self.carWindow = window
    window.rootViewController = MapViewController()

    let mapTemplate = CPMapTemplate()
    mapTemplate.mapDelegate = self
    interfaceController.setRootTemplate(mapTemplate, animated: true,
                                        completion: nil)
}
```

## Templates Overview

CarPlay provides a fixed set of template types. The app supplies content;
the system renders it on the vehicle display.

### General Purpose Templates

| Template | Purpose |
|---|---|
| `CPTabBarTemplate` | Container with tabbed child templates |
| `CPListTemplate` | Scrollable sectioned list |
| `CPGridTemplate` | Grid of tappable icon buttons (max 8) |
| `CPInformationTemplate` | Key-value info with up to 3 actions |
| `CPAlertTemplate` | Modal alert with up to 2 actions |
| `CPActionSheetTemplate` | Modal action sheet |

### Category-Specific Templates

| Template | Category |
|---|---|
| `CPMapTemplate` | Navigation -- map overlay with nav bar |
| `CPSearchTemplate` | Navigation -- destination search |
| `CPNowPlayingTemplate` | Audio -- shared Now Playing screen |
| `CPPointOfInterestTemplate` | EV Charging / Parking / Food -- POI map |
| `CPContactTemplate` | Communication -- contact card |

### Navigation Hierarchy

Use `pushTemplate(_:animated:completion:)` to add templates to the stack.
Use `presentTemplate(_:animated:completion:)` for modal display.
Use `popTemplate(animated:completion:)` to go back.
`CPTabBarTemplate` must be set as root -- it cannot be pushed or presented.

### CPTabBarTemplate

```swift
let browseTab = CPListTemplate(title: "Browse",
                               sections: [CPListSection(items: listItems)])
browseTab.tabImage = UIImage(systemName: "list.bullet")

let tabBar = CPTabBarTemplate(templates: [browseTab, settingsTab])
tabBar.delegate = self
interfaceController.setRootTemplate(tabBar, animated: true, completion: nil)
```

### CPListTemplate

```swift
let item = CPListItem(text: "Favorites", detailText: "12 items")
item.handler = { selectedItem, completion in
    self.interfaceController?.pushTemplate(detailTemplate, animated: true,
                                           completion: nil)
    completion()
}

let section = CPListSection(items: [item], header: "Library",
                            sectionIndexTitle: nil)
let listTemplate = CPListTemplate(title: "My App", sections: [section])
```

## Navigation Apps

Navigation apps use `com.apple.developer.carplay-maps`. They are the only
category that receives a `CPWindow` for drawing map content. The root
template must be a `CPMapTemplate`.

### Trip Preview and Route Selection

```swift
let routeChoice = CPRouteChoice(
    summaryVariants: ["Fastest Route", "Fast"],
    additionalInformationVariants: ["Via Highway 101"],
    selectionSummaryVariants: ["25 min"]
)
let trip = CPTrip(origin: origin, destination: destination,
                  routeChoices: [routeChoice])
mapTemplate.showTripPreviews([trip], textConfiguration: nil)
```

### Starting a Navigation Session

```swift
extension CarPlaySceneDelegate: CPMapTemplateDelegate {
    func mapTemplate(_ mapTemplate: CPMapTemplate,
                     startedTrip trip: CPTrip,
                     using routeChoice: CPRouteChoice) {
        let session = mapTemplate.startNavigationSession(for: trip)
        session.pauseTrip(for: .loading, description: "Calculating route...")

        let maneuver = CPManeuver()
        maneuver.instructionVariants = ["Turn right onto Main St"]
        maneuver.symbolImage = UIImage(systemName: "arrow.turn.up.right")
        session.upcomingManeuvers = [maneuver]

        let estimates = CPTravelEstimates(
            distanceRemaining: Measurement(value: 5.2, unit: .miles),
            timeRemaining: 900)
        session.updateEstimates(estimates, for: maneuver)
    }
}
```

### Map Buttons

```swift
let zoomIn = CPMapButton { _ in self.mapViewController.zoomIn() }
zoomIn.image = UIImage(systemName: "plus.magnifyingglass")
mapTemplate.mapButtons = [zoomIn, zoomOut]
```

### CPSearchTemplate

```swift
extension CarPlaySceneDelegate: CPSearchTemplateDelegate {
    func searchTemplate(_ searchTemplate: CPSearchTemplate,
                        updatedSearchText searchText: String,
                        completionHandler: @escaping ([CPListItem]) -> Void) {
        performSearch(query: searchText) { results in
            completionHandler(results.map {
                CPListItem(text: $0.name, detailText: $0.address)
            })
        }
    }

    func searchTemplate(_ searchTemplate: CPSearchTemplate,
                        selectedResult item: CPListItem,
                        completionHandler: @escaping () -> Void) {
        // Navigate to selected destination
        completionHandler()
    }
}
```

## Audio Apps

Audio apps use `com.apple.developer.carplay-audio`. They display browsable
content in lists and use `CPNowPlayingTemplate` for playback controls.
`CPInformationTemplate` is not available to audio-entitled apps.

### Now Playing Template

`CPNowPlayingTemplate` is a shared singleton. It reads metadata from
`MPNowPlayingInfoCenter`. Do not instantiate a new one.

```swift
let nowPlaying = CPNowPlayingTemplate.shared
nowPlaying.isUpNextButtonEnabled = true
nowPlaying.isAlbumArtistButtonEnabled = true
nowPlaying.updateNowPlayingButtons([
    CPNowPlayingShuffleButton { _ in self.toggleShuffle() },
    CPNowPlayingRepeatButton { _ in self.toggleRepeat() }
])
nowPlaying.add(self) // Register as CPNowPlayingTemplateObserver
```

### Siri Assistant Cell

Audio apps supporting `INPlayMediaIntent` can show an assistant cell.
Communication apps use `INStartCallIntent` with `.startCall`.

```swift
let config = CPAssistantCellConfiguration(
    position: .top, visibility: .always, assistantAction: .playMedia)
let listTemplate = CPListTemplate(
    title: "Playlists",
    sections: [CPListSection(items: items)],
    assistantCellConfiguration: config)
```

## Communication Apps

Communication apps use `com.apple.developer.carplay-communication`.
They display message lists and contacts, and support `INStartCallIntent`
for Siri-initiated calls.
`CPMessageListItem` has no app-provided selection handler. When selected,
CarPlay invokes Siri compose, read, or reply behavior based on the item's
phone/email, unread state, or existing conversation configuration.

```swift
let leading = CPMessageListItemLeadingConfiguration(
    leadingItem: .star, leadingImage: nil, unread: true)
let trailing = CPMessageListItemTrailingConfiguration(
    trailingItem: .none, trailingImage: nil)

let message = CPMessageListItem(
    conversationIdentifier: "conv-123",
    text: "Jane",
    leadingConfiguration: leading,
    trailingConfiguration: trailing,
    detailText: "Meeting at 3pm",
    trailingText: "2:45 PM")

let messageList = CPListTemplate(title: "Messages",
                                 sections: [CPListSection(items: [message])])
```

## Point of Interest Apps

EV charging, parking, and food ordering apps use `CPPointOfInterestTemplate`
and `CPInformationTemplate` to display locations and details.
`CPPointOfInterestTemplate` displays a maximum of 12 points of interest.

### CPPointOfInterestTemplate

```swift
let poi = CPPointOfInterest(
    location: MKMapItem(placemark: MKPlacemark(
        coordinate: CLLocationCoordinate2D(latitude: 37.7749,
                                           longitude: -122.4194))),
    title: "SuperCharger Station", subtitle: "4 available",
    summary: "150 kW DC fast charging",
    detailTitle: "SuperCharger Station", detailSubtitle: "$0.28/kWh",
    detailSummary: "Open 24 hours",
    pinImage: UIImage(systemName: "bolt.fill"))

poi.primaryButton = CPTextButton(title: "Navigate",
                                 textStyle: .confirm) { _ in }

let poiTemplate = CPPointOfInterestTemplate(
    title: "Nearby Chargers", pointsOfInterest: [poi], selectedIndex: 0)
poiTemplate.pointOfInterestDelegate = self
```

### CPInformationTemplate

```swift
let infoTemplate = CPInformationTemplate(
    title: "Order Summary", layout: .leading,
    items: [
        CPInformationItem(title: "Item", detail: "Burrito Bowl"),
        CPInformationItem(title: "Total", detail: "$12.50")],
    actions: [
        CPTextButton(title: "Place Order", textStyle: .confirm) { _ in
            self.placeOrder() },
        CPTextButton(title: "Cancel", textStyle: .cancel) { _ in
            self.interfaceController?.popTemplate(animated: true,
                                                  completion: nil) }])
```

## Testing with CarPlay Simulator

1. Build and run in Xcode with the iOS simulator.
2. Choose I/O > External Displays > CarPlay.

Default window: 800x480 at `@2x`. Enable extra options for navigation apps:

```bash
defaults write com.apple.iphonesimulator CarPlayExtraOptions -bool YES
```

### Recommended Test Configurations

| Configuration | Pixels | Scale |
|---|---|---|
| Minimum | 748 x 456 | `@2x` |
| Portrait | 768 x 1024 | `@2x` |
| Standard | 800 x 480 | `@2x` |
| High-resolution | 1920 x 720 | @3x |

Simulator cannot test locked-iPhone behavior, Siri, audio coexistence with
car radio, or physical input hardware (knobs, touch pads). Test on a real
CarPlay-capable vehicle or aftermarket head unit when possible.
Design primary CarPlay flows so they do not require iPhone input while
CarPlay is active.

## Common Mistakes

### DON'T: Use the wrong scene delegate method

Navigation apps must implement `templateApplicationScene(_:didConnect:to:)`
(with `CPWindow`). Non-navigation apps use
`templateApplicationScene(_:didConnect:)` (no window). Using the wrong
variant produces no CarPlay UI.

### DON'T: Draw custom UI in the navigation window

`CPWindow` is exclusively for map content. All overlays, alerts, and
controls must use CarPlay templates.

### DON'T: Push or present CPTabBarTemplate

`CPTabBarTemplate` can only be set as root. Pushing or presenting it fails.
Use `setRootTemplate(_:animated:completion:)`.

### DON'T: Instantiate CPNowPlayingTemplate

Use `CPNowPlayingTemplate.shared`. Creating a new instance causes issues.

### DON'T: Add handlers to CPMessageListItem

`CPMessageListItem` is Siri-managed, unlike `CPListItem`. Do not set
`message.handler`; use the item configuration and `userInfo` for context.

### DON'T: Treat widgets as CarPlay template apps

CarPlay-visible widgets and Live Activities belong to WidgetKit and
ActivityKit. Use this skill for category-entitled CarPlay template app scenes
and for validating those surfaces in the car context.

### DON'T: Ignore vehicle display limits

Check `CPSessionConfiguration.limitedUserInterfaces` and respect
`maximumItemCount` / `maximumSectionCount` on list templates.

### DON'T: Forget to call the completion handler

`CPListItem.handler` must call its completion handler in every code path.
Failure leaves the list in a loading state.

## Review Checklist

- [ ] Correct CarPlay entitlement key in `Entitlements.plist`
- [ ] `UIApplicationSupportsMultipleScenes` set to `true`
- [ ] `CPTemplateApplicationSceneSessionRoleApplication` scene in Info.plist
- [ ] Scene delegate class name matches `UISceneDelegateClassName`
- [ ] Correct delegate method used (with/without `CPWindow`)
- [ ] Root template set in `didConnect` before returning
- [ ] Interface controller and window references cleared on disconnect
- [ ] `CPTabBarTemplate` only used as root, never pushed
- [ ] `CPNowPlayingTemplate.shared` used, not a new instance
- [ ] Communication rows use `CPMessageListItem` without custom handlers
- [ ] WidgetKit/ActivityKit surfaces routed outside CarPlay template app code
- [ ] `maximumItemCount`/`maximumSectionCount` checked before populating lists
- [ ] `CPListItem.handler` calls completion in every path
- [ ] Map-only content in `CPWindow` root view controller (navigation apps)
- [ ] App functions while iPhone is locked
- [ ] Tested at minimum, standard, and high-resolution simulator sizes
- [ ] Audio session deactivated when not actively playing

## References

- Extended patterns (dashboard, instrument cluster, full nav flow, tab composition): [references/carplay-patterns.md](references/carplay-patterns.md)
- [CarPlay framework](https://sosumi.ai/documentation/carplay)
- [CPTemplateApplicationSceneDelegate](https://sosumi.ai/documentation/carplay/cptemplateapplicationscenedelegate)
- [CPInterfaceController](https://sosumi.ai/documentation/carplay/cpinterfacecontroller)
- [CPMapTemplate](https://sosumi.ai/documentation/carplay/cpmaptemplate)
- [CPListTemplate](https://sosumi.ai/documentation/carplay/cplisttemplate)
- [CPNowPlayingTemplate](https://sosumi.ai/documentation/carplay/cpnowplayingtemplate)
- [CPPointOfInterestTemplate](https://sosumi.ai/documentation/carplay/cppointofinteresttemplate)
- [CPNavigationSession](https://sosumi.ai/documentation/carplay/cpnavigationsession)
- [Requesting CarPlay Entitlements](https://sosumi.ai/documentation/carplay/requesting-carplay-entitlements)
- [Displaying Content in CarPlay](https://sosumi.ai/documentation/carplay/displaying-content-in-carplay)
- [Using the CarPlay Simulator](https://sosumi.ai/documentation/carplay/using-the-carplay-simulator)
- [CarPlay HIG](https://sosumi.ai/design/human-interface-guidelines/carplay)
