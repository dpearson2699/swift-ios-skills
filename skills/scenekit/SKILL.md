---
name: scenekit
description: "Maintain and extend existing SceneKit 3D scenes and visualizations. Use when working with SCNView, SCNScene, SCNNode scene graphs, SceneKit geometry/materials/lights/cameras, SCNAction animation, SCNPhysicsBody physics, SCNParticleSystem effects, .scn/.dae/.abc SceneKit assets, shader modifiers, or SwiftUI SceneView. SceneKit is soft-deprecated and in maintenance mode; route new apps, significant updates, USD/USDZ pipelines, and migration planning toward RealityKit."
---

# SceneKit

Maintain existing SceneKit scenes only. Apple deprecated SceneKit at WWDC 2025 and limits it to maintenance; route new projects, major modernization, and USD/USDZ pipelines to RealityKit. Existing apps continue to work.

## Contents

- [Scene Setup](#scene-setup)
- [Nodes and Geometry](#nodes-and-geometry)
- [Materials](#materials)
- [Lighting](#lighting)
- [Cameras](#cameras)
- [Animation](#animation)
- [Physics](#physics)
- [Particle Systems](#particle-systems)
- [Loading Models](#loading-models)
- [SwiftUI Integration](#swiftui-integration)
- [Common Mistakes](#common-mistakes)
- [Review Checklist](#review-checklist)
- [References](#references)

## Scene Setup

### SCNView in UIKit

```swift
import SceneKit

let sceneView = SCNView(frame: view.bounds)
sceneView.scene = SCNScene()
sceneView.allowsCameraControl = true
sceneView.autoenablesDefaultLighting = true
sceneView.backgroundColor = .black
view.addSubview(sceneView)
```

`allowsCameraControl` adds built-in orbit, pan, and zoom gestures. Typically
disabled in production where custom camera control is needed.

### Creating an SCNScene

```swift
let scene = SCNScene()                                          // Empty
guard let scene = SCNScene(named: "art.scnassets/ship.scn")     // .scn in .scnassets
    else { fatalError("Missing scene asset") }
let url = Bundle.main.url(forResource: "ship", withExtension: "dae")!
let scene = try SCNScene(url: url, options: [.checkConsistency: true])
```

## Nodes and Geometry

Every scene has a `rootNode`. All content exists as descendant nodes. Nodes
define position, orientation, and scale in their parent's coordinate system.
SceneKit uses a right-handed coordinate system: +X right, +Y up, +Z toward
the camera.

```swift
let parentNode = SCNNode()
scene.rootNode.addChildNode(parentNode)

let childNode = SCNNode()
childNode.position = SCNVector3(0, 1, 0)  // 1 unit above parent
parentNode.addChildNode(childNode)
```

### Transforms

```swift
node.position = SCNVector3(x: 0, y: 2, z: -5)
node.eulerAngles = SCNVector3(x: 0, y: .pi / 4, z: 0)  // 45-degree Y rotation
node.scale = SCNVector3(2, 2, 2)
node.simdPosition = SIMD3<Float>(0, 2, -5)  // Prefer simd for performance
```

### Built-in Primitives

`SCNBox`, `SCNSphere`, `SCNCylinder`, `SCNCone`, `SCNTorus`, `SCNCapsule`,
`SCNTube`, `SCNPlane`, `SCNFloor`, `SCNText`, `SCNShape` (extruded Bezier path).

```swift
let node = SCNNode(geometry: SCNSphere(radius: 0.5))
```

### Finding Nodes

```swift
let maxNode = scene.rootNode.childNode(withName: "Max", recursively: true)
let enemies = scene.rootNode.childNodes { node, _ in
    node.name?.hasPrefix("enemy") == true
}
```

## Materials

`SCNMaterial` defines surface appearance. Use `firstMaterial` for single-material
geometries or the `materials` array for multi-material.

### Color and Texture

```swift
let material = SCNMaterial()
material.diffuse.contents = UIColor.systemBlue     // Solid color
material.diffuse.contents = UIImage(named: "brick") // Texture
material.normal.contents = UIImage(named: "brick_normal")
sphere.firstMaterial = material
```

### Physically Based Rendering (PBR)

```swift
let pbr = SCNMaterial()
pbr.lightingModel = .physicallyBased
pbr.diffuse.contents = UIImage(named: "albedo")
pbr.metalness.contents = 0.8       // Scalar or texture
pbr.roughness.contents = 0.2       // Scalar or texture
pbr.normal.contents = UIImage(named: "normal")
pbr.ambientOcclusion.contents = UIImage(named: "ao")
```

### Lighting Models

`.physicallyBased` (metalness/roughness), `.blinn` (default), `.phong`,
`.lambert` (diffuse-only), `.constant` (unlit), `.shadowOnly`.

Each material property is an `SCNMaterialProperty` accepting `UIColor`,
`UIImage`, `CGFloat` scalar, `SKTexture`, `CALayer`, or `AVPlayer`.

### Transparency

```swift
material.transparency = 0.5
material.transparencyMode = .dualLayer
material.isDoubleSided = true
```

## Lighting

Attach an `SCNLight` to a node. The light's direction follows the node's
negative Z-axis.

### Light Types

```swift
// Ambient: uniform, no direction
let ambient = SCNLight()
ambient.type = .ambient
ambient.color = UIColor(white: 0.3, alpha: 1)

// Directional: parallel rays (sunlight)
let directional = SCNLight()
directional.type = .directional
directional.castsShadow = true

// Omni: point light, all directions
let omni = SCNLight()
omni.type = .omni
omni.attenuationEndDistance = 20

// Spot: cone-shaped
let spot = SCNLight()
spot.type = .spot
spot.spotInnerAngle = 20
spot.spotOuterAngle = 60
```

Attach to a node:

```swift
let lightNode = SCNNode()
lightNode.light = directional
lightNode.eulerAngles = SCNVector3(-Float.pi / 3, 0, 0)
lightNode.position = SCNVector3(0, 10, 10)
scene.rootNode.addChildNode(lightNode)
```

### Shadows

```swift
light.castsShadow = true
light.shadowMapSize = CGSize(width: 2048, height: 2048)
light.shadowSampleCount = 8
light.shadowRadius = 3.0
light.shadowColor = UIColor(white: 0, alpha: 0.5)
```

### Category Bit Masks

```swift
light.categoryBitMask = 1 << 1     // Category 2
node.categoryBitMask = 1 << 1      // Only lit by category-2 lights
```

SceneKit renders a maximum of 8 lights per node. Use `attenuationEndDistance`
on point/spot lights so SceneKit skips them for distant nodes.

## Cameras

Attach an `SCNCamera` to a node to define a viewpoint.

```swift
let cameraNode = SCNNode()
cameraNode.camera = SCNCamera()
cameraNode.position = SCNVector3(0, 5, 15)
cameraNode.look(at: SCNVector3Zero)
scene.rootNode.addChildNode(cameraNode)
sceneView.pointOfView = cameraNode
```

### Configuration

```swift
camera.fieldOfView = 60                        // Degrees
camera.zNear = 0.1
camera.zFar = 500
camera.automaticallyAdjustsZRange = true

// Orthographic
camera.usesOrthographicProjection = true
camera.orthographicScale = 10
```

Depth-of-field (`wantsDepthOfField`, `focusDistance`, `fStop`) and HDR effects
(`wantsHDR`, `bloomIntensity`, `bloomThreshold`, `screenSpaceAmbientOcclusionIntensity`)
are configured directly on `SCNCamera`.

## Animation

SceneKit provides three animation approaches.

### SCNAction (Declarative, Game-Oriented)

Reusable, composable animation objects attached to nodes.

```swift
let move = SCNAction.move(by: SCNVector3(0, 2, 0), duration: 1)
let rotate = SCNAction.rotateBy(x: 0, y: .pi, z: 0, duration: 1)
node.runAction(.group([move, rotate]))

// Sequential
node.runAction(.sequence([.fadeOut(duration: 0.3), .removeFromParentNode()]))

// Infinite loop
let pulse = SCNAction.sequence([
    .scale(to: 1.2, duration: 0.5),
    .scale(to: 1.0, duration: 0.5)
])
node.runAction(.repeatForever(pulse))
```

### SCNTransaction (Implicit Animation)

```swift
SCNTransaction.begin()
SCNTransaction.animationDuration = 1.0
node.position = SCNVector3(5, 0, 0)
node.opacity = 0.5
SCNTransaction.completionBlock = { print("Done") }
SCNTransaction.commit()
```

### Explicit Animations (Core Animation)

```swift
let animation = CABasicAnimation(keyPath: "rotation")
animation.toValue = NSValue(scnVector4: SCNVector4(0, 1, 0, Float.pi * 2))
animation.duration = 2
animation.repeatCount = .infinity
node.addAnimation(animation, forKey: "spin")
```

## Physics

### Physics Bodies

```swift
node.physicsBody = SCNPhysicsBody(type: .dynamic, shape: nil)   // Forces + collisions
floor.physicsBody = SCNPhysicsBody(type: .static, shape: nil)    // Immovable
platform.physicsBody = SCNPhysicsBody(type: .kinematic, shape: nil) // Code-driven
```

When `shape` is `nil`, SceneKit derives it from geometry. For performance, use
simplified shapes:

```swift
let shape = SCNPhysicsShape(
    geometry: SCNBox(width: 1, height: 2, length: 1, chamferRadius: 0),
    options: nil
)
node.physicsBody = SCNPhysicsBody(type: .dynamic, shape: shape)
node.physicsBody?.mass = 2.0
node.physicsBody?.restitution = 0.3
```

### Applying Forces

```swift
node.physicsBody?.applyForce(SCNVector3(0, 10, 0), asImpulse: false) // Continuous
node.physicsBody?.applyForce(SCNVector3(0, 5, 0), asImpulse: true)   // Instant
node.physicsBody?.applyTorque(SCNVector4(0, 1, 0, 2), asImpulse: true)
```

### Collision Detection

```swift
struct PhysicsCategory {
    static let player:     Int = 1 << 0
    static let enemy:      Int = 1 << 1
    static let ground:     Int = 1 << 2
}

playerNode.physicsBody?.categoryBitMask = PhysicsCategory.player
playerNode.physicsBody?.collisionBitMask = PhysicsCategory.ground | PhysicsCategory.enemy
playerNode.physicsBody?.contactTestBitMask = PhysicsCategory.enemy

scene.physicsWorld.contactDelegate = self

func physicsWorld(_ world: SCNPhysicsWorld, didBegin contact: SCNPhysicsContact) {
    handleCollision(between: contact.nodeA, and: contact.nodeB)
}
```

### Gravity

```swift
scene.physicsWorld.gravity = SCNVector3(0, -9.8, 0)
node.physicsBody?.isAffectedByGravity = false
```

## Particle Systems

`SCNParticleSystem` creates effects like fire, smoke, rain, and sparks.

```swift
let particles = SCNParticleSystem()
particles.birthRate = 100
particles.particleLifeSpan = 2
particles.particleSize = 0.1
particles.particleColor = .orange
particles.emitterShape = SCNSphere(radius: 0.5)
particles.particleVelocity = 2
particles.isAffectedByGravity = true
particles.blendMode = .additive

let emitterNode = SCNNode()
emitterNode.addParticleSystem(particles)
scene.rootNode.addChildNode(emitterNode)
```

Load from Xcode particle editor with
`SCNParticleSystem(named: "fire.scnp", inDirectory: nil)`. Particles can
collide with geometry via `colliderNodes`.

## Loading Models

SceneKit's documented scene-source formats are `.scn`, `.dae`, and `.abc`.
For bundled assets, place scene files in a `.scnassets` folder and texture
images in asset catalogs so Xcode can optimize them for target devices.

USD/USDZ is the RealityKit migration path, not the default SceneKit loading
path. For new projects, significant updates, or SCN-to-USD asset conversion,
handoff to the RealityKit skill.

```swift
enum SceneAssetError: Error { case missingResource, missingNode(String) }

func loadCheckedScene() throws -> SCNScene {
    guard let url = Bundle.main.url(forResource: "model", withExtension: "dae")
    else { throw SceneAssetError.missingResource }

    let scene = try SCNScene(url: url, options: [.checkConsistency: true])
    guard scene.rootNode.childNode(withName: "mesh", recursively: true) != nil
    else { throw SceneAssetError.missingNode("mesh") }
    return scene
}
```

Use this as an authoring/import gate: stop on a consistency or required-node
failure, fix the source asset or import options, then repeat the same check.
For generated `.scn` files, load
[Scene Serialization](references/scenekit-patterns.md#scene-serialization) and
require both export success and a checked reload before commit.

Use `SCNReferenceNode` with `.onDemand` loading policy for large models. For
import-time unit conversion, use `SCNSceneSource.LoadingOption`:

```swift
let source = SCNSceneSource(url: url, options: nil)!
let scene = try source.scene(options: [.convertUnitsToMeters: 1.0])
```

Do not use `SCNScene.Attribute.unit` or `UnitMetersPerUnit`. `SCNScene.Attribute`
is metadata only: `.startTime`, `.endTime`, `.frameRate`, and `.upAxis`.

## SwiftUI Integration

`SceneView` embeds SceneKit in SwiftUI:

```swift
import SwiftUI
import SceneKit

struct SceneKitView: View {
    let scene: SCNScene = {
        let scene = SCNScene()
        let sphere = SCNNode(geometry: SCNSphere(radius: 1))
        sphere.geometry?.firstMaterial?.lightingModel = .physicallyBased
        sphere.geometry?.firstMaterial?.diffuse.contents = UIColor.systemBlue
        sphere.geometry?.firstMaterial?.metalness.contents = 0.8
        scene.rootNode.addChildNode(sphere)
        return scene
    }()

    var body: some View {
        SceneView(scene: scene,
                  options: [.allowsCameraControl, .autoenablesDefaultLighting])
    }
}
```

Options: `.allowsCameraControl`, `.autoenablesDefaultLighting`,
`.jitteringEnabled`, `.temporalAntialiasingEnabled`.

For render loop control, wrap `SCNView` in `UIViewRepresentable` with an
`SCNSceneRendererDelegate` coordinator. See [references/scenekit-patterns.md](references/scenekit-patterns.md).

## Common Mistakes

### Not adding a camera or lights

```swift
// DON'T: Scene renders blank or black -- no camera, no lights
sceneView.scene = scene

// DO: Add camera + lights, or use convenience flags
let cameraNode = SCNNode()
cameraNode.camera = SCNCamera()
cameraNode.position = SCNVector3(0, 5, 15)
scene.rootNode.addChildNode(cameraNode)
sceneView.pointOfView = cameraNode
sceneView.autoenablesDefaultLighting = true
```

### Using exact geometry for physics shapes

```swift
// DON'T
node.physicsBody = SCNPhysicsBody(type: .dynamic,
    shape: SCNPhysicsShape(geometry: complexMesh, options: nil))

// DO: Simplified primitive
node.physicsBody = SCNPhysicsBody(type: .dynamic,
    shape: SCNPhysicsShape(
        geometry: SCNBox(width: 1, height: 2, length: 1, chamferRadius: 0),
        options: nil))
```

### Modifying transforms on dynamic bodies

```swift
// DON'T: Resets physics simulation
dynamicNode.position = SCNVector3(5, 0, 0)

// DO: Use forces/impulses
dynamicNode.physicsBody?.applyForce(SCNVector3(10, 0, 0), asImpulse: true)
```

## Review Checklist

- [ ] Scene has at least one camera node set as `pointOfView`
- [ ] Scene has appropriate lighting (or `autoenablesDefaultLighting` for prototyping)
- [ ] Physics shapes use simplified geometry, not full mesh detail
- [ ] `contactTestBitMask` set for bodies that need collision callbacks
- [ ] `SCNPhysicsContactDelegate` assigned to `scene.physicsWorld.contactDelegate`
- [ ] Dynamic body transforms changed via forces/impulses, not direct position
- [ ] Lights limited to 8 per node; `attenuationEndDistance` set on point/spot lights
- [ ] Materials use `.physicallyBased` lighting model for realistic rendering
- [ ] SceneKit assets use documented `.scn`, `.dae`, or `.abc` scene-source formats
- [ ] Imported and exported assets pass consistency and required-node checks
      before commit
- [ ] Bundled SceneKit textures/images use asset catalogs or Xcode-optimized resources
- [ ] Scene metadata/import options use documented API; no invented `SCNScene.Attribute.unit`
- [ ] New USD/USDZ pipelines or significant updates are routed to RealityKit
- [ ] Game Center authentication, leaderboards, achievements, or multiplayer are handed off to GameKit
- [ ] `SCNReferenceNode` used for large models to enable lazy loading
- [ ] Particle `birthRate` and `particleLifeSpan` balanced to control particle count
- [ ] `categoryBitMask` used to scope lights and cameras to relevant nodes
- [ ] SwiftUI scenes use `SceneView` or `UIViewRepresentable`-wrapped `SCNView`
- [ ] Deprecation acknowledged; RealityKit evaluated for new projects

## References

- See [references/scenekit-patterns.md](references/scenekit-patterns.md) for custom geometry, shader modifiers, constraints, morph targets, hit testing, scene serialization, render loop delegates, performance, SpriteKit overlay, LOD, and Metal shaders.
- [SceneKit documentation](https://sosumi.ai/documentation/scenekit), [SCNSceneSource](https://sosumi.ai/documentation/scenekit/scnscenesource), [SCNView](https://sosumi.ai/documentation/scenekit/scnview), [SceneView](https://sosumi.ai/documentation/scenekit/sceneview)
- [SCNPhysicsShape](https://sosumi.ai/documentation/scenekit/scnphysicsshape), [SCNShadable](https://sosumi.ai/documentation/scenekit/scnshadable)
- [WWDC 2025 session 288: Bring your SceneKit project to RealityKit](https://sosumi.ai/videos/play/wwdc2025/288/)
