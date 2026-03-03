# Core ML Optimization Reference

Complete reference for optimizing Core ML models: quantization, palettization,
pruning, performance tuning, and profiling.

## Optimization Technique Selection

| Technique | Size Reduction | Accuracy Impact | Best Compute Unit | Min OS |
|---|---|---|---|---|
| INT8 per-channel | ~4x | Low | CPU/GPU | iOS 16 |
| INT4 per-block | ~8x | Medium | GPU | iOS 18 |
| Palettization 4-bit | ~8x | Low-Medium | Neural Engine | iOS 16 |
| Palettization 2-bit | ~16x | Medium-High | Neural Engine | iOS 16 |
| W8A8 (weights+activations) | ~4x | Low | ANE (A17 Pro/M4+) | iOS 17 |
| Pruning 50% | ~2x | Low | CPU/ANE | iOS 16 |
| Pruning 75% | ~4x | Medium | CPU/ANE | iOS 16 |

## Post-Training Weight Quantization (Data-Free)

### INT8 Per-Channel Symmetric

```python
import coremltools as ct
import coremltools.optimize as cto

model = ct.models.MLModel("model.mlpackage")

op_config = cto.coreml.OpLinearQuantizerConfig(
    mode="linear_symmetric",  # or "linear" (asymmetric with zero-point)
    weight_threshold=512,     # only quantize tensors with > N elements
)
config = cto.coreml.OptimizationConfig(global_config=op_config)
compressed = cto.coreml.linear_quantize_weights(model, config=config)
compressed.save("model_int8.mlpackage")
```

### INT4 Per-Block (PyTorch, Data-Free)

```python
import coremltools.optimize as cto

config = cto.torch.quantization.PostTrainingQuantizerConfig.from_dict({
    "global_config": {
        "weight_dtype": "int4",
        "granularity": "per_block",
        "block_size": 128,
    }
})
quantizer = cto.torch.quantization.PostTrainingQuantizer(model, config)
quantized_model = quantizer.compress()
```

### GPTQ Calibration-Based Quantization

```python
config = cto.torch.layerwise_compression.LayerwiseCompressorConfig.from_dict({
    "global_config": {
        "algorithm": "gptq",
        "weight_dtype": 4,
        "granularity": "per_block",
        "block_size": 128,
    },
    "calibration_nsamples": 16,
})
compressor = cto.torch.layerwise_compression.LayerwiseCompressor(model, config)
compressed_model = compressor.compress(calibration_dataloader)
```

## Palettization (Weight Clustering)

Especially effective on the Neural Engine. 4-bit palettization typically
preserves accuracy better than 4-bit linear quantization.

### Post-Conversion Palettization

```python
op_config = cto.coreml.OpPalettizerConfig(
    mode="kmeans",                     # "kmeans" or "uniform"
    nbits=4,                           # {1, 2, 3, 4, 6, 8}
    granularity="per_grouped_channel", # iOS 18+ for grouped
    group_size=16,
)
config = cto.coreml.OptimizationConfig(global_config=op_config)
palettized = cto.coreml.palettize_weights(model, config=config)
```

### Available Bit Widths

| Bits | Unique Values | Size Reduction | Typical Quality |
|---|---|---|---|
| 8 | 256 | ~2x | Excellent |
| 6 | 64 | ~2.7x | Very good |
| 4 | 16 | ~8x | Good |
| 3 | 8 | ~10.7x | Moderate |
| 2 | 4 | ~16x | Fair |
| 1 | 2 | ~32x | Poor (binary) |

## Pruning (Weight Sparsification)

### Magnitude Pruning

```python
config = cto.coreml.OptimizationConfig(
    global_config=cto.coreml.OpMagnitudePrunerConfig(
        target_sparsity=0.75,
        weight_threshold=2048,
    )
)
pruned = cto.coreml.prune_weights(model, config=config)
```

### Threshold Pruning

```python
config = cto.coreml.OptimizationConfig(
    global_config=cto.coreml.OpThresholdPrunerConfig(
        threshold=1e-12,
        minimum_sparsity_percentile=0.5,
    )
)
pruned = cto.coreml.prune_weights(model, config=config)
```

## Joint Compression (Stacking Techniques)

Apply multiple compression techniques in sequence:

```python
# Palettize first, then prune on top
palettized = cto.coreml.palettize_weights(model, pal_config)
final = cto.coreml.prune_weights(
    palettized, prune_config, joint_compression=True
)
```

## Per-Op Configuration

Fine-grained control over which operations get compressed:

```python
config = cto.coreml.OptimizationConfig(
    global_config=global_op_config,
    op_type_configs={
        "linear": linear_config,
        "conv": conv_config,
    },
    op_name_configs={
        "embedding_layer": None,  # None = skip compression
    },
)
```

## Quantization-Aware Training (QAT)

Train with quantization in the loop for best accuracy:

```python
from coremltools.optimize.torch.quantization import (
    LinearQuantizer, LinearQuantizerConfig, ModuleLinearQuantizerConfig
)

config = LinearQuantizerConfig(
    global_config=ModuleLinearQuantizerConfig(
        quantization_scheme="symmetric",
        milestones=[0, 1000, 1000, 0],
    )
)
quantizer = LinearQuantizer(model, config)
quantizer.prepare(example_inputs=[1, 3, 224, 224], inplace=True)

# Training loop
for inputs, labels in data:
    output = model(inputs)
    loss = loss_fn(output, labels)
    loss.backward()
    optimizer.step()
    quantizer.step()

model = quantizer.finalize(inplace=True)
```

## Swift Integration

### Loading Models

```swift
// From Xcode-compiled model (auto-generated class)
let model = try MyImageClassifier(configuration: MLModelConfiguration())

// From URL at runtime
let config = MLModelConfiguration()
config.computeUnits = .all
let model = try MLModel(contentsOf: modelURL, configuration: config)

// From pre-compiled model (.mlmodelc) for faster loading
let compiledURL = try MLModel.compileModel(at: sourceModelURL)
let model = try MLModel(contentsOf: compiledURL)
```

### MLModelConfiguration

```swift
let config = MLModelConfiguration()
config.computeUnits = .all
config.allowLowPrecisionAccumulationOnGPU = true
// config.functionName = "adapter_1"  // For multifunction models (iOS 18+)
```

### Synchronous Prediction

```swift
let input = MyModelInput(image: pixelBuffer)
let output = try model.prediction(input: input)
let label = output.classLabel
```

### Async Prediction (iOS 17+)

```swift
let output = try await model.prediction(input: input)
```

Thread-safe, supports Task cancellation, integrates with Swift concurrency.
~60% faster than synchronous for batch workloads.

### Batch Prediction

```swift
let batchInputs: [MyModelInput] = images.map { MyModelInput(image: $0) }
let batchOutputs = try model.predictions(inputs: batchInputs)
```

### MLFeatureProvider

```swift
let features = try MLDictionaryFeatureProvider(dictionary: [
    "input": MLFeatureValue(pixelBuffer: pixelBuffer),
    "threshold": MLFeatureValue(double: 0.5),
])
let output = try model.prediction(from: features)
```

### Vision Framework Integration

```swift
import Vision
import CoreML

let vnModel = try VNCoreMLModel(for: MyDetector().model)
let request = VNCoreMLRequest(model: vnModel) { request, error in
    guard let results = request.results as? [VNClassificationObservation] else { return }
    let topResult = results.first
    print("\(topResult?.identifier ?? ""): \(topResult?.confidence ?? 0)")
}
let handler = VNImageRequestHandler(cgImage: image)
try handler.perform([request])
```

### Natural Language Integration

```swift
import NaturalLanguage

let nlModel = try NLModel(mlModel: SentimentClassifier().model)
let sentiment = nlModel.predictedLabel(for: "Great product!")
```

## MLTensor (iOS 18+)

Swift type for multidimensional array operations:

```swift
import CoreML

let tensor = MLTensor([1.0, 2.0, 3.0, 4.0])
let reshaped = tensor.reshaped(to: [2, 2])
let result = tensor.softmax()
let matmulResult = tensorA.matmul(tensorB)
```

## Neural Engine Best Practices

1. Use EnumeratedShapes instead of RangeDim for ANE optimization
2. Avoid unsupported ANE ops -- they cause fallback to CPU/GPU with transfer
   overhead
3. Use palettization (4-bit or 6-bit) for best ANE memory/latency gains
4. W8A8 quantization on A17 Pro / M4+ enables optimized INT8 compute on ANE

## Model Loading Optimization

1. Pre-compile models -- use `.mlmodelc` for instant loading after first
   compilation
2. Cache compiled models to a fixed location after `MLModel.compileModel(at:)`
3. Use `bisect_model()` for very large models that are slow to load
4. Use `MLComputePlan` (iOS 17+) for programmatic profiling

## Profiling

1. **Xcode Performance tab** -- open .mlpackage in Xcode to see load time,
   prediction time, per-op compute unit assignment
2. **Core ML Instrument** in Instruments app -- runtime profiling
3. **MLComputePlan API** -- programmatic access to profiling data
4. **coremltools debugging** -- MLModelValidator, MLModelComparator,
   MLModelInspector, MLModelBenchmarker

### Reshape Frequency Hint

```python
model = ct.models.MLModel("model.mlpackage",
    optimization_hints={
        "reshapeFrequency": ct.ReshapeFrequency.Infrequent
    })
```

## Common Optimization Mistakes

1. **Applying quantization without checking accuracy.** Always validate after
   compression. Use MLModelComparator to compare outputs.
2. **Ignoring weight_threshold.** Small tensors (< 512 elements) should not be
   quantized -- overhead outweighs the benefit.
3. **Using synchronous predictions in async contexts.** Use async prediction
   (iOS 17+) in Swift concurrency code.
4. **Not pre-compiling models.** First load triggers device-specific
   compilation, which can be slow.
5. **Ignoring compute_units configuration.** Default `.all` is correct for
   production. `.cpuOnly` is for debugging only.
6. **Not testing on physical devices.** Simulator does not support Metal GPU or
   Neural Engine.
