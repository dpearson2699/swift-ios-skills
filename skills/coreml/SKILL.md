---
name: coreml
description: "Integrate Core ML models in iOS apps for on-device machine learning inference. Covers model loading (.mlmodel, .mlpackage, .mlmodelc), predictions with auto-generated classes and MLFeatureProvider, compute unit configuration (CPU, GPU, Neural Engine), MLTensor, VNCoreMLRequest, MLComputePlan, multi-model pipelines, and deployment strategies. Use when loading Core ML models, making predictions, configuring compute units, or profiling model performance."
---

# Core ML Swift Integration

Load, configure, and run Core ML models in iOS apps. This skill covers the
Swift side: model loading, prediction, MLTensor, profiling, and deployment.

> **Scope boundary:** Python-side model conversion, optimization (quantization,
> palettization, pruning), and framework selection live in the `apple-on-device-ai`
> skill. This skill owns Swift integration only.

See [references/coreml-swift-integration.md](references/coreml-swift-integration.md) for complete code patterns including
actor-based caching, batch inference, image preprocessing, and testing.

## Contents

- [Loading Models](#loading-models)
- [Model Configuration](#model-configuration)
- [Making Predictions](#making-predictions)
- [MLTensor (iOS 18+)](#mltensor-ios-18)
- [Working with MLMultiArray](#working-with-mlmultiarray)
- [Image Preprocessing](#image-preprocessing)
- [Multi-Model Pipelines](#multi-model-pipelines)
- [Vision Integration](#vision-integration)
- [Performance Profiling](#performance-profiling)
- [Model Deployment](#model-deployment)
- [Memory Management](#memory-management)
- [Common Mistakes](#common-mistakes)
- [Review Checklist](#review-checklist)
- [References](#references)

## Loading Models

### Auto-Generated Classes

When you add a `.mlmodel` or `.mlpackage` to an app target, Xcode generates a Swift
class with typed input/output. Use this whenever possible.

```swift
import CoreML

let config = MLModelConfiguration()
config.computeUnits = .all

let model = try MyImageClassifier(configuration: config)
```

### Manual Loading

Load from a URL when the model is downloaded at runtime or stored outside the
bundle.

```swift
let modelURL = Bundle.main.url(
    forResource: "MyModel", withExtension: "mlmodelc"
)!
let model = try MLModel(contentsOf: modelURL, configuration: config)
```

### Async Loading (iOS 15+)

Load models without blocking the main thread. Prefer this for large models.

```swift
let model = try await MLModel.load(
    contentsOf: modelURL,
    configuration: config
)
```

### Compile at Runtime (iOS 16+)

Compile a `.mlpackage` or `.mlmodel` to `.mlmodelc` on device. Useful for
models downloaded from a server. Do this once per model version, not on every
launch.

```swift
let compiledURL = try await MLModel.compileModel(at: packageURL)
let model = try await MLModel.load(contentsOf: compiledURL, configuration: config)
```

Cache the compiled URL -- recompiling on every launch is a bug. Copy
`compiledURL` to a persistent location (e.g., Application Support). When
reviewing runtime-loaded models, call out both facts together: async
`MLModel.compileModel(at:)` is iOS 16+, and compiled models must be cached so the
app does not recompile on every launch.

## Model Configuration

`MLModelConfiguration` controls compute units, GPU access, and model parameters.

### Compute Units Decision Table

| Value | Uses | When to Choose |
|---|---|---|
| `.all` | CPU + GPU + Neural Engine | Default. Let the system decide. |
| `.cpuOnly` | CPU | Deterministic tests, CPU-only fallbacks, or constrained work after profiling shows accelerator policy, contention, thermal state, or energy budget is the limiting factor. |
| `.cpuAndGPU` | CPU + GPU | Need GPU but model has ops unsupported by ANE. |
| `.cpuAndNeuralEngine` (iOS 16+) | CPU + Neural Engine | Best energy efficiency for compatible models. |

```swift
let config = MLModelConfiguration()
config.computeUnits = .cpuAndNeuralEngine

// Optional fallback for constrained work after profiling and policy review
config.computeUnits = .cpuOnly
```

### Configuration Properties

```swift
let config = MLModelConfiguration()
config.computeUnits = .all
config.allowLowPrecisionAccumulationOnGPU = true // faster, slight precision loss
```

## Making Predictions

### With Auto-Generated Classes

The generated class provides typed input/output structs.

```swift
let model = try MyImageClassifier(configuration: config)
let input = MyImageClassifierInput(image: pixelBuffer)
let output = try model.prediction(input: input)
print(output.classLabel)        // "golden_retriever"
print(output.classLabelProbs)   // ["golden_retriever": 0.95, ...]
```

### With MLDictionaryFeatureProvider

Use when inputs are dynamic or not known at compile time.

```swift
let inputFeatures = try MLDictionaryFeatureProvider(dictionary: [
    "image": MLFeatureValue(pixelBuffer: pixelBuffer),
    "confidence_threshold": MLFeatureValue(double: 0.5),
])
let output = try model.prediction(from: inputFeatures)
let label = output.featureValue(for: "classLabel")?.stringValue
```

### Prediction Inside Async Workflows

`MLModel.prediction(...)` is synchronous. In async pipelines, keep model loading
async, then run prediction from an actor or non-main task without adding `await`
to the prediction call.

```swift
let output = try model.prediction(from: inputFeatures)
```

### Batch Prediction

Process multiple inputs in one call for better throughput.

```swift
let batchInputs = try MLArrayBatchProvider(array: inputs.map { input in
    try MLDictionaryFeatureProvider(dictionary: ["image": MLFeatureValue(pixelBuffer: input)])
})
let batchOutput = try model.predictions(fromBatch: batchInputs)
for i in 0..<batchOutput.count {
    let result = batchOutput.features(at: i)
    print(result.featureValue(for: "classLabel")?.stringValue ?? "unknown")
}
```

Use `predictions(fromBatch:)` when batching without explicit
`MLPredictionOptions`. Use `predictions(from:options:)` only when passing both an
`MLBatchProvider` and `MLPredictionOptions`; `predictions(from:)` by itself is
not the no-options batch API.

Validate a representative single input before batching. Then verify batch
output count/order, feature types, domain invariants, and agreement with the
single-input result. On failure, fix the deterministic input, shape, model, or
configuration issue before rerunning fixtures and physical-device profiling.

### Stateful Prediction (iOS 18+)

Use `MLState` for models that maintain state across predictions (sequence models,
LLMs, audio accumulators). Create state once and pass it to each prediction call.

```swift
let state = model.makeState()

// Each synchronous prediction carries forward the internal model state
for frame in audioFrames {
    let input = try MLDictionaryFeatureProvider(dictionary: [
        "audio_features": MLFeatureValue(multiArray: frame)
    ])
    let output = try model.prediction(from: input, using: state)
    let classification = output.featureValue(for: "label")?.stringValue
}
```

`MLState` is `Sendable`, but `Sendable` does not make one state safe for
concurrent inference. Predictions using the same state must be serialized; do
not read or write state buffers while a prediction is in flight. Call
`model.makeState()` for each independent concurrent stream. If you need
`MLPredictionOptions`, iOS 18+ also provides the async
`prediction(from:using:options:)` overload; the same one-in-flight-per-state rule
still applies.

## MLTensor (iOS 18+)

`MLTensor` is a Swift-native multidimensional array for pre/post-processing.
Operations run lazily -- call `await tensor.shapedArray(of:)` to materialize results.

```swift
import CoreML

// Creation
let tensor = MLTensor([1.0, 2.0, 3.0, 4.0])
let zeros = MLTensor(zeros: [3, 224, 224], scalarType: Float.self)

// Reshaping
let reshaped = tensor.reshaped(to: [2, 2])

// Math operations
let softmaxed = tensor.softmax(alongAxis: -1)
let centered = tensor - tensor.mean()

// Interop with MLShapedArray / MLMultiArray
let shaped = await tensor.shapedArray(of: Float.self)
let multiArray = try MLMultiArray(shaped)
let shapedAgain = MLShapedArray<Float>(multiArray)
```

Do not invent `MLTensor` APIs for statistics or bridging. Avoid examples such as
`MLTensor(multiArray)`, `tensor.std()`, `tensor.standardDeviation()`, direct
lazy-buffer access, or synchronous extraction; perform unsupported DSP/statistics
outside the tensor pipeline or with source-confirmed tensor operations.

## Working with MLMultiArray

`MLMultiArray` is the primary data exchange type for non-image model inputs and
outputs. Use it when the auto-generated class expects array-type features.

```swift
// Create a 3D array: [batch, sequence, features]
let array = try MLMultiArray(shape: [1, 128, 768], dataType: .float32)

// Write values
for i in 0..<128 {
    array[[0, i, 0] as [NSNumber]] = NSNumber(value: Float(i))
}

// Read values
let value = array[[0, 0, 0] as [NSNumber]].floatValue

let data: [Float] = [1.0, 2.0, 3.0]
let shaped = MLShapedArray(scalars: data, shape: [3])
let fromShaped = try MLMultiArray(shaped)
```

See [references/coreml-swift-integration.md](references/coreml-swift-integration.md) for advanced MLMultiArray patterns
including NLP tokenization and audio feature extraction.

## Image Preprocessing

Image models expect `CVPixelBuffer` input. Use `CGImage` conversion for photos
from the camera or photo library. Vision's `VNCoreMLRequest` handles this
automatically; manual conversion is needed only for direct `MLModel` prediction.

Load [Image Preprocessing](references/coreml-swift-integration.md#image-preprocessing)
for the complete checked `CVPixelBuffer` conversion and additional normalization
or cropping patterns.

## Multi-Model Pipelines

Chain models when preprocessing or postprocessing requires a separate model.

```swift
// Sequential inference: preprocessor -> main model -> postprocessor
let preprocessed = try preprocessor.prediction(from: rawInput)
let mainOutput = try mainModel.prediction(from: preprocessed)
let finalOutput = try postprocessor.prediction(from: mainOutput)
```

For Xcode-managed pipelines, use the pipeline model type in the `.mlpackage`.
Each sub-model runs on its optimal compute unit.

## Vision Integration

Use Vision to run Core ML image models with automatic image preprocessing
(resizing, normalization, color space, orientation).

### Modern: CoreMLRequest (iOS 18+)

```swift
import Vision
import CoreML

let model = try MLModel(contentsOf: modelURL, configuration: config)
let request = CoreMLRequest(model: .init(model))
let results = try await request.perform(on: cgImage)

if let classification = results.first as? ClassificationObservation {
    print("\(classification.identifier): \(classification.confidence)")
}
```

### Legacy: VNCoreMLRequest

```swift
let vnModel = try VNCoreMLModel(for: model)
let request = VNCoreMLRequest(model: vnModel) { request, error in
    guard let results = request.results as? [VNRecognizedObjectObservation] else { return }
    for observation in results {
        let label = observation.labels.first?.identifier ?? "unknown"
        let confidence = observation.labels.first?.confidence ?? 0
        let boundingBox = observation.boundingBox // normalized coordinates
        print("\(label): \(confidence) at \(boundingBox)")
    }
}
request.imageCropAndScaleOption = .scaleFill

let handler = VNImageRequestHandler(cvPixelBuffer: pixelBuffer)
try handler.perform([request])
```

> For complete Vision framework patterns (text recognition, barcode detection,
> document scanning), see the `vision-framework` skill.

## Performance Profiling

### MLComputePlan (iOS 17.4+)

Inspect which compute device each operation will use before running predictions.
Load [MLComputePlan Detailed Usage](references/coreml-swift-integration.md#mlcomputeplan-detailed-usage-ios-174)
for model-structure traversal, device usage, and estimated-cost inspection.

### Instruments

Use the **Core ML** instrument template in Instruments to profile:
- Model load time
- Prediction latency (per-operation breakdown)
- Compute device dispatch (CPU/GPU/ANE per operation)
- Memory allocation

Run outside the debugger for accurate results (Xcode: Product > Profile).

## Model Deployment

Bundle small offline-critical models. Prefer Background Assets for new large or
updateable assets; keep On-Demand Resources only for existing ODR projects.
Compile downloaded source models once, persist the `.mlmodelc` by version, and
test load, first/repeated prediction, lifecycle transitions, and memory on the
lowest supported physical device. Load
[deployment patterns](references/coreml-swift-integration.md) for implementation
details.

## Memory Management

- **Unload on background:** Release model references when the app enters background
  to free GPU/ANE memory. Reload on foreground return.
- **Share model instances:** Never create multiple `MLModel` instances from the same
  compiled model. Use an actor to provide shared access.
- **Monitor memory pressure:** Large models (>100 MB) can trigger memory warnings.
  Register for `UIApplication.didReceiveMemoryWarningNotification` and release
  cached models when under pressure.

See [references/coreml-swift-integration.md](references/coreml-swift-integration.md) for an actor-based model manager with
lifecycle-aware loading and cache eviction.

## Common Mistakes

**DON'T:** Load models on the main thread.
**DO:** Use `MLModel.load(contentsOf:configuration:)` async API or load on a background actor.
**Why:** Large models can take seconds to load, freezing the UI.

**DON'T:** Ignore `MLFeatureValue` type mismatches between input and model expectations.
**DO:** Match types exactly -- use `MLFeatureValue(pixelBuffer:)` for images, not raw data.
**Why:** Type mismatches cause cryptic runtime crashes or silent incorrect results.

**DON'T:** Create a new `MLModel` instance for every prediction.
**DO:** Load once and reuse. Use an actor to manage the model lifecycle.
**Why:** Model loading allocates significant memory and compute resources.

**DON'T:** Skip error handling for model loading and prediction.
**DO:** Catch errors and provide fallback behavior when the model fails.
**Why:** Models can fail to load on older devices or when resources are constrained.

**DON'T:** Assume all operations run on the Neural Engine.
**DO:** Use `MLComputePlan` (iOS 17.4+) to verify device dispatch per operation.
**Why:** Unsupported operations fall back to CPU, which may bottleneck the pipeline.

**DON'T:** Process images manually before passing to Vision + Core ML.
**DO:** Use `CoreMLRequest` (iOS 18+) or `VNCoreMLRequest` (legacy) to let Vision handle preprocessing.
**Why:** Vision handles orientation, scaling, and pixel format conversion correctly.

## Review Checklist

- [ ] Model loaded asynchronously (not blocking main thread)
- [ ] `MLModelConfiguration.computeUnits` set appropriately for use case
- [ ] Model instance reused across predictions (not recreated each time)
- [ ] Auto-generated class used when available (typed inputs/outputs)
- [ ] Error handling for model loading and prediction failures
- [ ] Compiled model cached persistently if compiled at runtime
- [ ] Image inputs use Vision pipeline (`CoreMLRequest` iOS 18+ or `VNCoreMLRequest`) for correct preprocessing
- [ ] `MLComputePlan` checked to verify compute device dispatch (iOS 17.4+)
- [ ] Batch predictions used when processing multiple inputs
- [ ] Model size appropriate for deployment strategy (bundle, Background Assets, ODR)
- [ ] Memory tested on target devices (especially older devices with less RAM)
- [ ] Predictions run outside debugger for accurate performance measurement

## References

- Patterns and code: [references/coreml-swift-integration.md](references/coreml-swift-integration.md)
- Model conversion and optimization (Python-side): covered in the `apple-on-device-ai` skill
- Apple docs: [Core ML](https://sosumi.ai/documentation/coreml) |
  [MLModel](https://sosumi.ai/documentation/coreml/mlmodel) |
  [MLTensor](https://sosumi.ai/documentation/coreml/mltensor) |
  [MLComputePlan](https://sosumi.ai/documentation/coreml/mlcomputeplan-1w21n) |
  [Background Assets](https://sosumi.ai/documentation/backgroundassets)
