# SceneKit Patterns

Advanced patterns and techniques for SceneKit development. Covers custom geometry
construction, shader modifiers, node constraints, morph targets, hit testing,
scene serialization, performance optimization, and SpriteKit overlay rendering.

## Contents

- [Custom Geometry](#custom-geometry)
- [Shader Modifiers](#shader-modifiers)
- [Node Constraints](#node-constraints)
- [Morph Targets](#morph-targets)
- [Hit Testing](#hit-testing)
- [Scene Serialization](#scene-serialization)
- [Render Loop and Delegates](#render-loop-and-delegates)
- [Performance Optimization](#performance-optimization)
- [SpriteKit Overlay](#spritekit-overlay)
- [Level of Detail](#level-of-detail)
- [SCNProgram and Metal Shaders](#scnprogram-and-metal-shaders)

## Custom Geometry

Build geometry from vertex data using `SCNGeometrySource` and
`SCNGeometryElement`.

### Triangle Mesh

```swift
import SceneKit

func makeTriangle() -> SCNGeometry {
    let vertices: [SCNVector3] = [
        SCNVector3(-0.5, 0, 0),
        SCNVector3( 0.5, 0, 0),
        SCNVector3( 0,   1, 0)
    ]
    let normals: [SCNVector3] = [
        SCNVector3(0, 0, 1),
        SCNVector3(0, 0, 1),
        SCNVector3(0, 0, 1)
    ]
    let texCoords: [CGPoint] = [
        CGPoint(x: 0, y: 0),
        CGPoint(x: 1, y: 0),
        CGPoint(x: 0.5, y: 1)
    ]
    let indices: [UInt16] = [0, 1, 2]

    let vertexSource = SCNGeometrySource(vertices: vertices)
    let normalSource = SCNGeometrySource(normals: normals)
    let uvSource = SCNGeometrySource(textureCoordinates: texCoords)

    let element = SCNGeometryElement(
        indices: indices,
        primitiveType: .triangles
    )

    return SCNGeometry(sources: [vertexSource, normalSource, uvSource],
                       elements: [element])
}
```

### Generic Data Source

For custom attributes or interleaved data, use the general-purpose initializer:

```swift
let data = Data(bytes: vertexData, count: vertexData.count * MemoryLayout<Float>.stride)

let source = SCNGeometrySource(
    data: data,
    semantic: .vertex,
    vectorCount: vertexCount,
    usesFloatComponents: true,
    componentsPerVector: 3,
    bytesPerComponent: MemoryLayout<Float>.stride,
    dataOffset: 0,
    dataStride: MemoryLayout<Float>.stride * 3
)
```

### Updating Geometry Per Frame

For dynamic meshes, recreate geometry sources each frame. Alternatively, use
Metal buffers directly for zero-copy updates:

```swift
let device = MTLCreateSystemDefaultDevice()!
let buffer = device.makeBuffer(
    bytes: vertices,
    length: vertices.count * MemoryLayout<SIMD3<Float>>.stride,
    options: .storageModeShared
)!

let source = SCNGeometrySource(
    buffer: buffer,
    vertexFormat: .float3,
    semantic: .vertex,
    vertexCount: vertices.count,
    dataOffset: 0,
    dataStride: MemoryLayout<SIMD3<Float>>.stride
)
```

### Primitive Types

| Type | Description |
|---|---|
| `.triangles` | Every 3 indices form one triangle |
| `.triangleStrip` | Shared edges between consecutive triangles |
| `.line` | Every 2 indices form one line segment |
| `.point` | Each index renders as a point |
| `.polygon` | Indices define polygons (first value = vertex count) |

## Shader Modifiers

Shader modifiers inject GLSL or Metal Shading Language snippets into SceneKit's
rendering pipeline at specific entry points.

### Entry Points

| Entry Point | Use Case |
|---|---|
| `.geometry` | Modify vertex positions |
| `.surface` | Modify material surface properties |
| `.lightingModel` | Custom lighting calculation |
| `.fragment` | Final pixel color adjustment |

### Vertex Displacement (Geometry Modifier)

```swift
let waveShader = """
#pragma arguments
float amplitude;
float frequency;

float wave = amplitude * sin(frequency * _geometry.position.x + u_time);
_geometry.position.y += wave;
"""

material.shaderModifiers = [.geometry: waveShader]
material.setValue(Float(0.2), forKey: "amplitude")
material.setValue(Float(5.0), forKey: "frequency")
```

### Surface Color Modifier

```swift
let desatShader = """
float gray = dot(_surface.diffuse.rgb, float3(0.299, 0.587, 0.114));
_surface.diffuse.rgb = mix(_surface.diffuse.rgb, float3(gray), 0.5);
"""

material.shaderModifiers = [.surface: desatShader]
```

### Fragment Modifier

```swift
let scanlineShader = """
float line = step(0.5, fract(_surface.position.y * 50.0));
_output.color.rgb *= mix(0.8, 1.0, line);
"""

material.shaderModifiers = [.fragment: scanlineShader]
```

### Passing Values to Shaders

Use `setValue(_:forKey:)` on the material or geometry. SceneKit matches the key
name to `#pragma arguments` declarations:

```swift
material.setValue(NSValue(scnVector3: SCNVector3(1, 0, 0)), forKey: "customDirection")
material.setValue(Float(0.25), forKey: "amplitude")
```

Shader modifiers receive documented SceneKit uniforms such as `u_time`,
`u_modelTransform`, `u_viewTransform`, and `u_projectionTransform`. `scn_frame`
is for custom `SCNProgram` Metal shader functions, not shader modifiers.

## Node Constraints

Constraints automatically adjust a node's transform each frame.

### Look-At Constraint

```swift
let lookAt = SCNLookAtConstraint(target: targetNode)
lookAt.isGimbalLockEnabled = true  // Prevent upside-down flipping
cameraNode.constraints = [lookAt]
```

### Distance Constraint

Keep a node within a distance range of another:

```swift
let distance = SCNDistanceConstraint(target: targetNode)
distance.minimumDistance = 3
distance.maximumDistance = 10
followerNode.constraints = [distance]
```

### Billboard Constraint

Make a node always face the camera:

```swift
let billboard = SCNBillboardConstraint()
billboard.freeAxes = .Y  // Only rotate around Y axis
labelNode.constraints = [billboard]
```

### Replicator Constraint

Copy position/orientation from another node:

```swift
let replicator = SCNReplicatorConstraint(target: leaderNode)
replicator.positionOffset = SCNVector3(2, 0, 0)
replicator.replicatesOrientation = true
followerNode.constraints = [replicator]
```

### IK Constraint

Inverse kinematics for skeletal animation:

```swift
let ik = SCNIKConstraint.inverseKinematicsConstraint(chainRootNode: shoulderNode)
ik.setMaxAllowedRotationAngle(90, forJoint: elbowNode)
handNode.constraints = [ik]

// Move the target to trigger IK
ik.targetPosition = SCNVector3(1, 2, 0)
```

### Combining Constraints

Constraints are evaluated in order. Use `influenceFactor` (0-1) to blend:

```swift
lookAt.influenceFactor = 0.8
distance.influenceFactor = 1.0
cameraNode.constraints = [lookAt, distance]
```

## Morph Targets

`SCNMorpher` blends between base geometry and target geometries for facial
expressions, shape keys, or procedural deformation.

```swift
let morpher = SCNMorpher()

// Target geometries must share the same vertex count and topology
morpher.targets = [smileGeometry, frownGeometry, blinkGeometry]

// Names for programmatic access
morpher.targets[0].name = "smile"
morpher.targets[1].name = "frown"
morpher.targets[2].name = "blink"

node.morpher = morpher

// Set blend weights (0.0 = base, 1.0 = full target shape)
node.morpher?.setWeight(0.5, forTargetAt: 0)          // 50% smile
node.morpher?.setWeight(0.0, forTargetNamed: "frown")  // No frown
```

### Animating Morph Weights

```swift
let animation = CABasicAnimation(keyPath: "morpher.weights[0]")
animation.fromValue = 0.0
animation.toValue = 1.0
animation.duration = 0.5
animation.autoreverses = true
node.addAnimation(animation, forKey: "smile")
```

### Morph Calculation Modes

```swift
morpher.calculationMode = .additive     // Weights add to base (default)
morpher.calculationMode = .normalized   // Weights normalized to sum to 1
```

## Hit Testing

Determine which nodes a screen point or ray intersects.

### Screen-Space Hit Testing

```swift
// From a tap gesture
let location = gesture.location(in: sceneView)
let hits = sceneView.hitTest(location, options: [
    .searchMode: SCNHitTestSearchMode.all.rawValue,
    .boundingBoxOnly: false,
    .firstFoundOnly: false
])

if let first = hits.first {
    let node = first.node
    let worldPoint = first.worldCoordinates
    let localPoint = first.localCoordinates
    let normal = first.worldNormal
    let texCoord = first.textureCoordinates(withMappingChannel: 0)
}
```

### Ray-Based Hit Testing

```swift
let hits = scene.rootNode.hitTestWithSegment(
    from: SCNVector3(0, 10, 0),
    to: SCNVector3(0, -10, 0),
    options: [
        .searchMode: SCNHitTestSearchMode.closest.rawValue
    ]
)
```

### Hit Test Options

| Option | Type | Purpose |
|---|---|---|
| `.searchMode` | `SCNHitTestSearchMode` | `.closest`, `.all`, `.any` |
| `.boundingBoxOnly` | `Bool` | Test bounding box instead of geometry |
| `.firstFoundOnly` | `Bool` | Stop after first hit |
| `.rootNode` | `SCNNode` | Limit search to subtree |
| `.categoryBitMask` | `Int` | Filter by node category |
| `.ignoreHiddenNodes` | `Bool` | Skip hidden nodes (default `true`) |

### Filtering Hits by Category

```swift
let interactableCategory = 1 << 2
node.categoryBitMask = interactableCategory

let hits = sceneView.hitTest(location, options: [
    .categoryBitMask: interactableCategory
])
```

## Scene Serialization

### Writing a Scene to File

```swift
let scene = SCNScene()
// ... populate scene ...

let url = FileManager.default.temporaryDirectory.appendingPathComponent("scene.scn")
let success = scene.write(to: url, options: nil, delegate: nil) { totalProgress, error, _ in
    print("Export progress: \(totalProgress)")
}

guard success else { throw SceneSerializationError.exportFailed }
let reloaded = try SCNScene(url: url, options: [.checkConsistency: true])
guard reloaded.rootNode.childNodes.isEmpty == false else {
    throw SceneSerializationError.missingContent
}
```

Treat this as a development or test gate: fix the source scene or export options
after failure, then repeat the export and checked reload. Do not loop over the
same deterministic invalid asset at runtime.

```swift
enum SceneSerializationError: Error {
    case exportFailed
    case missingContent
}
```

### Loading Options and Scene Attributes

Use `SCNSceneSource.LoadingOption` when importing files that need unit or axis
conversion:

```swift
let source = SCNSceneSource(url: url, options: nil)!
let scene = try source.scene(options: [
    .checkConsistency: true,
    .convertToYUp: true,
    .convertUnitsToMeters: 1.0
])
```

Use `SCNScene.Attribute` only for documented scene metadata such as `.startTime`,
`.endTime`, `.frameRate`, and `.upAxis`.

### Archiving Nodes

Individual nodes conform to `NSSecureCoding`:

```swift
let data = try NSKeyedArchiver.archivedData(
    withRootObject: node,
    requiringSecureCoding: true
)

let restored = try NSKeyedUnarchiver.unarchivedObject(
    ofClass: SCNNode.self,
    from: data
)
```

## Render Loop and Delegates

### SCNSceneRendererDelegate

Hook into the render loop for per-frame updates:

```swift
class GameController: NSObject, SCNSceneRendererDelegate {
    var previousTime: TimeInterval = 0

    func renderer(_ renderer: any SCNSceneRenderer, updateAtTime time: TimeInterval) {
        let deltaTime = time - previousTime
        previousTime = time
        updateGameLogic(deltaTime: deltaTime)
    }

    func renderer(_ renderer: any SCNSceneRenderer, didApplyAnimationsAtTime time: TimeInterval) {
        // After animations are applied, before physics
    }

    func renderer(_ renderer: any SCNSceneRenderer, didSimulatePhysicsAtTime time: TimeInterval) {
        // After physics simulation
    }

    func renderer(_ renderer: any SCNSceneRenderer, willRenderScene scene: SCNScene,
                  atTime time: TimeInterval) {
        // Just before rendering
    }

    func renderer(_ renderer: any SCNSceneRenderer, didRenderScene scene: SCNScene,
                  atTime time: TimeInterval) {
        // After rendering completes
    }
}

sceneView.delegate = gameController
```

### Render Loop Order

1. `updateAtTime` -- game logic
2. Actions and animations applied
3. `didApplyAnimationsAtTime`
4. Constraints evaluated
5. `didApplyConstraintsAtTime`
6. Physics simulation
7. `didSimulatePhysicsAtTime`
8. `willRenderScene`
9. GPU render
10. `didRenderScene`

### Frame Rate Control

```swift
sceneView.preferredFramesPerSecond = 60
sceneView.isPlaying = true          // Enable continuous rendering
sceneView.rendersContinuously = true // Render even without changes
```

## Performance Optimization

### Geometry

- **Flatten hierarchies:** `node.flattenedClone()` merges child geometries sharing
  the same material into a single draw call.
- **Reduce polygon count:** Use lower-poly meshes for distant or small objects.
- **Share geometry:** Assign the same `SCNGeometry` instance to multiple nodes.
- **Level of Detail:** Use `SCNLevelOfDetail` for automatic LOD switching.

### Materials

- **Share materials:** Reuse `SCNMaterial` instances across geometries.
- **Minimize transparent surfaces:** Transparency is expensive; use
  `writesToDepthBuffer` and sort render order.
- **Use texture atlases:** Reduce draw calls by combining textures.
- **Avoid unnecessary PBR:** Use `.lambert` or `.constant` for objects where
  lighting detail is not needed.

### Lighting and Shadows

- **Limit light count:** SceneKit processes up to 8 lights per node.
- **Use `attenuationEndDistance`:** Let SceneKit skip lights for distant nodes.
- **Bake static lighting:** Use light maps (multiply property) for immovable
  environments instead of real-time lights.
- **Shadow map size:** Smaller `shadowMapSize` improves performance at the cost
  of shadow quality.

### Physics

- **Simplified shapes:** Always use primitive shapes (box, sphere, capsule) for
  physics, not mesh-accurate shapes.
- **Allow resting:** Keep `allowsResting = true` so static bodies are skipped.
- **Disable when off-screen:** Set `physicsBody = nil` for inactive bodies.
- **Category masks:** Use collision and contact masks to reduce pairwise checks.

### Scene Graph

- **Minimize node count:** Each node has overhead. Use `flattenedClone()` or
  combine meshes in a DCC tool when possible.
- **`movabilityHint`:** Set `.fixed` on static objects so SceneKit can optimize
  rendering.
- **`renderingOrder`:** Render opaque objects first (lower values), then
  transparent objects.
- **Culling:** SceneKit frustum-culls automatically. Ensure bounding volumes are
  reasonable for effective culling.

### Debugging

```swift
sceneView.showsStatistics = true  // FPS, draw calls, triangles
sceneView.debugOptions = [
    .showBoundingBoxes,
    .showWireframe,
    .showPhysicsShapes,
    .showLightInfluences,
    .showLightExtents,
    .renderAsWireframe
]
```

Statistics panel fields:
- **fps:** Frames per second
- **draws:** Number of draw calls (target: < 100 for 60 fps)
- **tris:** Triangle count
- **verts:** Vertex count

## SpriteKit Overlay

Render 2D HUD content on top of the 3D scene using a SpriteKit overlay scene.

```swift
import SpriteKit

let overlay = SKScene(size: sceneView.bounds.size)
overlay.scaleMode = .resizeFill

let scoreLabel = SKLabelNode(text: "Score: 0")
scoreLabel.fontName = "Helvetica-Bold"
scoreLabel.fontSize = 24
scoreLabel.position = CGPoint(x: 100, y: overlay.size.height - 50)
overlay.addChild(scoreLabel)

sceneView.overlaySKScene = overlay
```

Update the overlay from the render loop:

```swift
func renderer(_ renderer: any SCNSceneRenderer, updateAtTime time: TimeInterval) {
    DispatchQueue.main.async {
        self.scoreLabel.text = "Score: \(self.score)"
    }
}
```

### SpriteKit Inside 3D Geometry

Render a SpriteKit scene as a material texture:

```swift
let spriteScene = SKScene(size: CGSize(width: 512, height: 512))
// ... add SpriteKit nodes ...

let material = SCNMaterial()
material.diffuse.contents = spriteScene
planeNode.geometry?.firstMaterial = material
```

## Level of Detail

`SCNLevelOfDetail` automatically switches geometry based on distance or screen
coverage.

```swift
let highDetail = SCNSphere(radius: 1)    // 48 segments
let medDetail = SCNSphere(radius: 1)     // 24 segments
medDetail.segmentCount = 24
let lowDetail = SCNSphere(radius: 1)     // 12 segments
lowDetail.segmentCount = 12

highDetail.levelsOfDetail = [
    SCNLevelOfDetail(geometry: medDetail, screenSpaceRadius: 50),   // < 50px on screen
    SCNLevelOfDetail(geometry: lowDetail, screenSpaceRadius: 20)    // < 20px on screen
]

// Or use world-space distance
highDetail.levelsOfDetail = [
    SCNLevelOfDetail(geometry: medDetail, worldSpaceDistance: 20),
    SCNLevelOfDetail(geometry: lowDetail, worldSpaceDistance: 50)
]
```

## SCNProgram and Metal Shaders

Replace SceneKit's entire rendering pipeline for a geometry with a custom Metal
shader program.

```swift
let program = SCNProgram()
program.vertexFunctionName = "myVertex"
program.fragmentFunctionName = "myFragment"

// Map SceneKit semantics to shader inputs
program.setSemantic(.modelViewProjectionTransform, forSymbol: "mvpTransform", options: nil)
program.setSemantic(.modelViewTransform, forSymbol: "mvTransform", options: nil)
program.setSemantic(.normalTransform, forSymbol: "normalTransform", options: nil)

material.program = program
```

Metal shader example:

```metal
#include <metal_stdlib>
using namespace metal;
#include <SceneKit/scn_metal>

struct VertexIn {
    float3 position [[attribute(SCNVertexSemanticPosition)]];
    float3 normal   [[attribute(SCNVertexSemanticNormal)]];
    float2 texcoord [[attribute(SCNVertexSemanticTexcoord0)]];
};

struct NodeBuffer {
    float4x4 modelTransform;
    float4x4 normalTransform;
};

struct VertexOut {
    float4 position [[position]];
    float2 texcoord;
    float3 normal;
};

vertex VertexOut myVertex(VertexIn in [[stage_in]],
                          constant SCNSceneBuffer& scn_frame [[buffer(0)]],
                          constant NodeBuffer& scn_node [[buffer(1)]]) {
    VertexOut out;
    out.position = scn_frame.viewProjectionTransform
                   * scn_node.modelTransform
                   * float4(in.position, 1.0);
    out.texcoord = in.texcoord;
    out.normal = (scn_node.normalTransform * float4(in.normal, 0.0)).xyz;
    return out;
}

fragment float4 myFragment(VertexOut in [[stage_in]]) {
    float3 lightDir = normalize(float3(1, 1, 1));
    float diffuse = max(dot(normalize(in.normal), lightDir), 0.0);
    return float4(float3(diffuse), 1.0);
}
```

### Passing Textures to Custom Programs

```swift
material.setValue(SCNMaterialProperty(contents: UIImage(named: "texture")!),
                  forKey: "diffuseTexture")
```

In the shader, declare the texture parameter with a matching name:

```metal
fragment float4 myFragment(VertexOut in [[stage_in]],
                           texture2d<float> diffuseTexture [[texture(0)]]) {
    constexpr sampler s(filter::linear);
    float4 color = diffuseTexture.sample(s, in.texcoord);
    return color;
}
```
