---
name: realitykit
description: "Build iOS augmented reality and 3D experiences with RealityKit and ARKit. Use when adding RealityView content, loading entities or USDZ models, anchoring objects to planes or world positions, distinguishing entity hit tests from ARKit real-world raycasts, handling AR camera availability, world tracking, scene updates, or RealityKit entity gestures and interactions."
---

# RealityKit

Build AR experiences on iOS using RealityKit for rendering and ARKit for world
tracking. Covers `RealityView`, entity management, raycasting, scene
understanding, and gesture-based interactions. Targets Swift 6.3 / iOS 26+.

## Contents

- [Setup](#setup)
- [RealityView Basics](#realityview-basics)
- [Loading and Creating Entities](#loading-and-creating-entities)
- [Anchoring and Placement](#anchoring-and-placement)
- [Raycasting](#raycasting)
- [Gestures and Interaction](#gestures-and-interaction)
- [Scene Understanding](#scene-understanding)
- [Common Mistakes](#common-mistakes)
- [Review Checklist](#review-checklist)
- [References](#references)

## Setup

### Project Configuration

1. Add `NSCameraUsageDescription` to Info.plist
2. On iOS, `RealityViewCameraContent` displays an AR camera view by default (iOS 18+, macOS 15+); use `.virtual` camera mode for explicit non-AR fallback
3. No entitlement is required for basic AR. If AR is core to the app, add the `arkit` required-device capability; otherwise gate AR UI with `isSupported`.

### Device Requirements

Check the exact AR configuration's `isSupported` value before presenting AR UI.

```swift
import ARKit

guard ARWorldTrackingConfiguration.isSupported else {
    showUnsupportedDeviceMessage()
    return
}
```

### Key Types

| Type | Platform | Role |
|---|---|---|
| `RealityView` | iOS 18+, visionOS 1+ | SwiftUI view that hosts RealityKit content |
| `RealityViewCameraContent` | iOS 18+, macOS 15+ | Content displayed through an AR camera view on iOS, non-AR on macOS |
| `Entity` | All | Base class for all scene objects |
| `ModelEntity` | All | Entity with a visible 3D model |
| `AnchorEntity` | All | Tethers entities to a real-world anchor |

## RealityView Basics

`RealityView` is the SwiftUI entry point for RealityKit.
`RealityViewCameraContent` is the iOS/macOS content type. On iOS, it uses an AR
camera view by default and can use `content.camera = .virtual` for non-AR mode
when requested or when AR/camera access is unavailable.

```swift
import ARKit
import SwiftUI
import RealityKit

struct ARExperienceView: View {
    var body: some View {
        RealityView { (content: RealityViewCameraContent) in
            if !ARWorldTrackingConfiguration.isSupported {
                content.camera = .virtual
            }

            let sphere = ModelEntity(
                mesh: .generateSphere(radius: 0.05),
                materials: [SimpleMaterial(
                    color: .blue,
                    isMetallic: true
                )]
            )
            sphere.position = [0, 0, -0.5]  // 50cm in front of camera
            content.add(sphere)
        }
    }
}
```

### Make and Update Pattern

Use the `update` closure to respond to SwiftUI state changes:

```swift
struct PlacementView: View {
    @State private var modelColor: UIColor = .red

    var body: some View {
        RealityView { content in
            let box = ModelEntity(
                mesh: .generateBox(size: 0.1),
                materials: [SimpleMaterial(
                    color: .red,
                    isMetallic: false
                )]
            )
            box.name = "colorBox"
            box.position = [0, 0, -0.5]
            content.add(box)
        } update: { content in
            if let box = content.entities.first(
                where: { $0.name == "colorBox" }
            ) as? ModelEntity {
                box.model?.materials = [SimpleMaterial(
                    color: modelColor,
                    isMetallic: false
                )]
            }
        }

        Button("Change Color") {
            modelColor = modelColor == .red ? .green : .red
        }
    }
}
```

## Loading and Creating Entities

### Loading from USDZ Files

Load 3D models asynchronously to avoid blocking the main thread:

```swift
RealityView { content in
    if let robot = try? await ModelEntity(named: "robot") {
        robot.position = [0, -0.2, -0.8]
        robot.scale = [0.01, 0.01, 0.01]
        content.add(robot)
    }
}
```

### Adding Components

Entities use an ECS (Entity Component System) architecture. Add components
to give entities behavior:

```swift
let box = ModelEntity(
    mesh: .generateBox(size: 0.1),
    materials: [SimpleMaterial(color: .red, isMetallic: false)]
)

// Make it respond to physics
box.components.set(PhysicsBodyComponent(
    massProperties: .default,
    material: .default,
    mode: .dynamic
))

// Add collision shape for interaction
box.components.set(CollisionComponent(
    shapes: [.generateBox(size: [0.1, 0.1, 0.1])]
))

// Enable input targeting for gestures
box.components.set(InputTargetComponent())
```

## Anchoring and Placement

### AnchorEntity

Use `AnchorEntity` to anchor content to detected surfaces or world positions:

```swift
RealityView { content in
    // Anchor to a horizontal surface
    let floorAnchor = AnchorEntity(.plane(
        .horizontal,
        classification: .floor,
        minimumBounds: [0.2, 0.2]
    ))

    let model = ModelEntity(
        mesh: .generateBox(size: 0.1),
        materials: [SimpleMaterial(color: .orange, isMetallic: false)]
    )
    floorAnchor.addChild(model)
    content.add(floorAnchor)
}
```

### Anchor Targets

| Target | Description |
|---|---|
| `.plane(.horizontal, ...)` | Horizontal surfaces (floors, tables) |
| `.plane(.vertical, ...)` | Vertical surfaces (walls) |
| `.plane(.any, ...)` | Any detected plane |
| `.world(transform:)` | Fixed world-space position |

## Raycasting

Keep RealityKit scene queries separate from ARKit real-world raycasts:

- `RealityViewCameraContent.ray(through:in:to:)` returns a camera ray in
  RealityKit coordinate spaces. It projects a screen point into the virtual
  scene; it is not proof of a detected physical surface.
- `RealityViewCameraContent.hitTest(point:in:query:mask:)` hits virtual
  entities made hittable by `CollisionComponent` shapes. Use those shapes for
  entity picking and targeted gestures, not ARKit plane detection.
- Use `AnchorEntity(.plane(...))` for simple placement on detected planes.
- Use ARKit `ARRaycastQuery` plus `ARSession.raycast(_:)` when the task needs
  a one-shot intersection with real-world surfaces, then anchor with
  `AnchorEntity(raycastResult:)`.

```swift
let results = session.raycast(query)
if let result = results.first {
    let anchor = AnchorEntity(raycastResult: result)
    anchor.addChild(model)
    content.add(anchor)
}
```

Do not treat entity hit tests as substitutes for ARKit surface raycasts.

## Gestures and Interaction

For gesture-based entity interaction, add `CollisionComponent` for the hittable
shape and `InputTargetComponent` for input targeting.

### Drag Gesture on Entities

```swift
struct DraggableARView: View {
    var body: some View {
        RealityView { content in
            let box = ModelEntity(
                mesh: .generateBox(size: 0.1),
                materials: [SimpleMaterial(color: .blue, isMetallic: true)]
            )
            box.position = [0, 0, -0.5]
            box.components.set(CollisionComponent(
                shapes: [.generateBox(size: [0.1, 0.1, 0.1])]
            ))
            box.components.set(InputTargetComponent())
            box.name = "draggable"
            content.add(box)
        }
        .gesture(
            DragGesture()
                .targetedToAnyEntity()
                .onChanged { value in
                    let entity = value.entity
                    guard let parent = entity.parent else { return }
                    entity.position = value.convert(
                        value.location3D,
                        from: .local,
                        to: parent
                    )
                }
        )
    }
}
```

## Scene Understanding

### Per-Frame Updates

Subscribe to `SceneEvents.Update` for continuous scene work rather than driving
RealityKit with a SwiftUI timer. Keep the subscription alive and use
`event.deltaTime`; see [Entity Animations](references/realitykit-patterns.md#entity-animations).

### Platform Boundaries

On visionOS, ARKit provides a different API surface with `ARKitSession`,
`WorldTrackingProvider`, and `PlaneDetectionProvider`. These visionOS-specific
types are not available on iOS. On iOS, RealityKit handles world tracking
automatically through `RealityViewCameraContent`.

For iOS architecture or migration notes, gate AR with
`ARWorldTrackingConfiguration.isSupported`, host content with
`RealityViewCameraContent`, and build scenes from `Entity`/`ModelEntity` placed
with `AnchorEntity`.

**Handoffs:** `CollisionComponent` + `InputTargetComponent` handle RealityKit
interaction; `AccessibilityComponent` handles entity accessibility metadata;
detailed SwiftUI gestures and VoiceOver/Switch Control policy belong to siblings.

Treat existing `SCNView`/`SCNNode` work as either a separate SceneKit path or an
explicit migration to RealityKit, not a mixed scene graph.

## Common Mistakes

### DON'T: Skip AR capability checks

Use the configuration-specific support check from Setup before presenting AR.
Show non-AR content or an explicit unavailable state when it fails.

### DON'T: Load heavy models synchronously

Loading large USDZ files on the main thread causes frame drops and hangs.
The `make` closure of `RealityView` is `async` -- use it.

```swift
// WRONG -- synchronous load blocks the main thread
RealityView { content in
    let model = try! Entity.load(named: "large-scene")
    content.add(model)
}

// CORRECT -- async load
RealityView { content in
    if let model = try? await ModelEntity(named: "large-scene") {
        content.add(model)
    }
}
```

### DON'T: Forget collision and input target components for interactive entities

Interactive entities need both components shown in
[Gestures and Interaction](#gestures-and-interaction); without them, taps and
drags pass through.

### DON'T: Create new entities in the update closure

The `update` closure runs on every SwiftUI state change. Creating entities
there duplicates content on each render pass.

```swift
// WRONG -- duplicates entities on every state change
RealityView { content in
    // empty
} update: { content in
    let sphere = ModelEntity(mesh: .generateSphere(radius: 0.05))
    content.add(sphere)  // Added again on every update
}

// CORRECT -- create in make, modify in update
RealityView { content in
    let sphere = ModelEntity(mesh: .generateSphere(radius: 0.05))
    sphere.name = "mySphere"
    content.add(sphere)
} update: { content in
    if let sphere = content.entities.first(
        where: { $0.name == "mySphere" }
    ) as? ModelEntity {
        // Modify existing entity
        sphere.position.y = newYPosition
    }
}
```

### DON'T: Ignore camera permission

RealityKit on iOS needs camera access. If the user denies permission, the
view shows a black screen with no explanation.

```swift
// WRONG -- no permission handling
RealityView { content in
    // Black screen if camera denied
}

// CORRECT -- check and request permission
struct ARContainerView: View {
    @State private var cameraAuthorized = false

    var body: some View {
        Group {
            if cameraAuthorized {
                RealityView { content in
                    // AR content
                }
            } else {
                ContentUnavailableView(
                    "Camera Access Required",
                    systemImage: "camera.fill",
                    description: Text("Enable camera in Settings to use AR.")
                )
            }
        }
        .task {
            let status = AVCaptureDevice.authorizationStatus(for: .video)
            if status == .authorized {
                cameraAuthorized = true
            } else if status == .notDetermined {
                cameraAuthorized = await AVCaptureDevice
                    .requestAccess(for: .video)
            }
        }
    }
}
```

## Review Checklist

- [ ] `NSCameraUsageDescription` set in Info.plist
- [ ] AR device capability checked before presenting AR views
- [ ] Camera permission requested and denial handled with a fallback UI
- [ ] `arkit` required-device capability added when AR is the app's core purpose
- [ ] 3D models loaded asynchronously in the `make` closure
- [ ] Entities created in `make`, modified in `update` (not created in `update`)
- [ ] Interaction prerequisites and sibling handoffs follow the Gestures section
- [ ] Entity hit tests, camera rays, and ARKit surface raycasts follow the Raycasting distinctions
- [ ] `SceneEvents.Update` subscriptions used for per-frame logic (not SwiftUI timers)
- [ ] Large scenes use `ModelEntity(named:)` async loading, not `Entity.load(named:)`
- [ ] Anchor entities target appropriate surface types for the use case
- [ ] Entity names set for lookup in the `update` closure

## References

- Read [references/realitykit-patterns.md](references/realitykit-patterns.md) for physics, animations, lighting, ECS, accessibility, and performance patterns.
- [RealityKit framework](https://sosumi.ai/documentation/realitykit)
- [RealityView](https://sosumi.ai/documentation/realitykit/realityview)
- [RealityViewCameraContent](https://sosumi.ai/documentation/realitykit/realityviewcameracontent)
- [RealityViewCamera](https://sosumi.ai/documentation/realitykit/realityviewcamera)
- [Entity](https://sosumi.ai/documentation/realitykit/entity)
- [ModelEntity](https://sosumi.ai/documentation/realitykit/modelentity)
- [AnchorEntity](https://sosumi.ai/documentation/realitykit/anchorentity)
- [ARKit framework](https://sosumi.ai/documentation/arkit)
- [ARKit in iOS](https://sosumi.ai/documentation/arkit/arkit-in-ios)
- [Verifying Device Support and User Permission](https://sosumi.ai/documentation/arkit/verifying-device-support-and-user-permission)
- [ARWorldTrackingConfiguration](https://sosumi.ai/documentation/arkit/arworldtrackingconfiguration)
- [ARRaycastQuery](https://sosumi.ai/documentation/arkit/arraycastquery)
- [ARSession.raycast(_:)](https://sosumi.ai/documentation/arkit/arsession/raycast(_:))
- [Loading entities from a file](https://sosumi.ai/documentation/realitykit/loading-entities-from-a-file)
