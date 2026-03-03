# Core ML Model Conversion Reference

Complete reference for converting models to Core ML format using coremltools.

## coremltools Installation

```bash
pip install coremltools
```

Current version: 9.0 (November 2025). Requires Python 3.10-3.13.

## Architecture Overview

```
Your App (SwiftUI / UIKit)
  |-- Vision, Natural Language, SoundAnalysis, Foundation Models
  |-- Core ML (model loading, prediction, compilation)
  |-- Metal Performance Shaders Graph (GPU) / Accelerate (CPU) / Neural Engine (ANE)
```

## Model Formats

| Format | Extension | Model Type | When to Use |
|---|---|---|---|
| `.mlpackage` | Directory | mlprogram | All new models (iOS 15+) |
| `.mlmodel` | Single file | neuralnetwork | Legacy only (iOS 11-14) |
| `.mlmodelc` | Compiled | Either | Pre-compiled for faster loading |

Always use mlprogram (.mlpackage) for new work. Neural network format is frozen
and receives no new features.

### mlprogram vs neuralnetwork

| Aspect | neuralnetwork | mlprogram |
|---|---|---|
| GPU precision | Float16 only | Float16 and Float32 |
| Optimization APIs | Limited | Full (quantize, palettize, prune) |
| Stateful models | No | Yes (iOS 18+) |
| Multifunction models | No | Yes (iOS 18+) |
| On-device training | Supported | Not supported |
| Weight storage | Embedded in protobuf | Separated (memory-efficient) |

## Unified Conversion API

```python
import coremltools as ct

mlmodel = ct.convert(
    model,                          # PyTorch traced/exported model or TF model
    source='auto',                  # 'auto', 'pytorch', 'tensorflow'
    inputs=None,                    # list of TensorType/ImageType
    outputs=None,                   # list of TensorType/ImageType
    minimum_deployment_target=None, # ct.target.iOS15 through ct.target.iOS26
    convert_to='mlprogram',         # 'mlprogram' (default) or 'neuralnetwork'
    compute_precision=None,         # ct.precision.FLOAT16 (default), FLOAT32
    compute_units=ct.ComputeUnit.ALL,
    skip_model_load=False,          # True when converting on Linux
    states=None,                    # list of StateType for stateful models
    pass_pipeline=None,             # PassPipeline for graph optimization
)
mlmodel.save("Model.mlpackage")
```

## Converting from PyTorch

### torch.jit.trace (Recommended)

```python
import torch
import coremltools as ct

model = MyModel()
model.eval()  # CRITICAL: always call eval() before tracing

example_input = torch.rand(1, 3, 224, 224)
traced_model = torch.jit.trace(model, example_input)

mlmodel = ct.convert(
    traced_model,
    inputs=[ct.TensorType(shape=example_input.shape, name="input")],
    minimum_deployment_target=ct.target.iOS16,
)
mlmodel.save("MyModel.mlpackage")
```

### torch.export (Beta)

```python
import torch
import coremltools as ct

model.eval()
example_inputs = (torch.rand(1, 3, 224, 224),)

# Dynamic shapes defined at export time
batch_dim = torch.export.Dim(name="batch", min=1, max=128)
exported = torch.export.export(model, example_inputs,
    dynamic_shapes={"x": {0: batch_dim}})

mlmodel = ct.convert(exported)
```

Key difference: `torch.export` defines dynamic shapes upfront (auto-converted
to RangeDim). `torch.jit.trace` defines shapes in `ct.convert()` via
RangeDim/EnumeratedShapes.

## Converting from TensorFlow

```python
import tensorflow as tf
import coremltools as ct

# Keras model
tf_model = tf.keras.applications.MobileNetV2()
mlmodel = ct.convert(tf_model)

# SavedModel directory
mlmodel = ct.convert("/path/to/saved_model/")

# HDF5 file
mlmodel = ct.convert("/path/to/model.h5")

# Frozen graph (.pb)
mlmodel = ct.convert("frozen_graph.pb",
    inputs=[ct.TensorType(shape=(1, 224, 224, 3))])
```

## Converting from scikit-learn

```python
from sklearn.linear_model import LinearRegression
import coremltools as ct

model = LinearRegression()
model.fit(X_train, y_train)

mlmodel = ct.converters.sklearn.convert(
    model, ["feature1", "feature2"], "prediction"
)
mlmodel.save("Regressor.mlmodel")
```

## Converting from XGBoost

```python
import xgboost
import coremltools as ct

model = xgboost.XGBClassifier()
model.fit(X_train, y_train)
mlmodel = ct.converters.xgboost.convert(model)
```

## ONNX Conversion (Deprecated)

ONNX direct conversion is deprecated since coremltools 6. Convert from the
original framework (PyTorch or TensorFlow) instead. If you only have an ONNX
file, convert back to PyTorch first using `onnx2torch`.

## Input and Output Types

### TensorType

```python
ct.TensorType(
    name="input",              # must match model input name
    shape=(1, 3, 224, 224),    # tuple of int, RangeDim, or EnumeratedShapes
    dtype=np.float32,          # np.float32, np.float16, np.int32, np.int8 (iOS26+)
    default_value=None,        # np.ndarray: makes input optional at runtime
)
```

### ImageType

```python
ct.ImageType(
    name="image",
    shape=(1, 3, 224, 224),
    scale=1/255.0,                   # per-channel scaling
    bias=[-0.485/0.229, -0.456/0.224, -0.406/0.225],  # ImageNet normalization
    color_layout=ct.colorlayout.RGB, # RGB, BGR, GRAYSCALE, GRAYSCALE_FLOAT16
    channel_first=True,              # True for PyTorch (NCHW), False for TF (NHWC)
)
```

### StateType (iOS 18+)

```python
ct.StateType(
    wrapped_type=ct.TensorType(shape=(1, 8, 128, 64), dtype=np.float16),
    name="kv_cache",
)
```

## Flexible Input Shapes

### Fixed Shape

```python
inputs=[ct.TensorType(shape=(1, 3, 224, 224))]
```

### RangeDim (Variable Dimensions)

```python
inputs=[ct.TensorType(shape=(
    1, 3,
    ct.RangeDim(lower_bound=128, upper_bound=512, default=224),
    ct.RangeDim(lower_bound=128, upper_bound=512, default=224),
))]
```

### EnumeratedShapes (Best Performance)

```python
inputs=[ct.TensorType(shape=ct.EnumeratedShapes(
    shapes=[(1,3,224,224), (1,3,384,384), (1,3,512,512)],
    default=(1,3,224,224),
))]
```

**Rule:** Prefer EnumeratedShapes over RangeDim when you have a known set of
sizes. EnumeratedShapes allows the Neural Engine to optimize for each shape at
compilation time. RangeDim only optimizes for the default shape.

**Rule:** Before iOS 18, only ONE input can use EnumeratedShapes. Starting
iOS 18, multiple inputs can use EnumeratedShapes.

## Deployment Targets

| Target | Model Type | Key Feature Unlocks |
|---|---|---|
| `ct.target.iOS13` | neuralnetwork | Basic neural network |
| `ct.target.iOS15` | mlprogram | FP16 precision, typed tensors |
| `ct.target.iOS16` | mlprogram | Palettized weights, sparse weights |
| `ct.target.iOS17` | mlprogram | W8A8 activation quantization (A17 Pro+) |
| `ct.target.iOS18` | mlprogram | Stateful models, multifunction, per-block quantization |
| `ct.target.iOS26` | mlprogram | INT8 I/O dtype, state read/write |

Corresponding macOS targets: `macOS10_15`, `macOS12`, `macOS13`, `macOS14`,
`macOS15`, `macOS26`.

## Compute Precision

| Value | Description |
|---|---|
| `ct.precision.FLOAT16` | Default for mlprogram. Smaller, faster. |
| `ct.precision.FLOAT32` | Higher accuracy. Use when FP16 causes issues. |

### Mixed Precision (Selective Per-Op)

```python
def keep_layernorm_fp32(op):
    if op.op_type == "layer_norm":
        return False  # keep in FP32
    return True  # convert to FP16

mlmodel = ct.convert(model,
    compute_precision=ct.transform.FP16ComputePrecision(
        op_selector=keep_layernorm_fp32
    ))
```

## Compute Units

| Value | Description | When to Use |
|---|---|---|
| `.all` | CPU + GPU + Neural Engine | Default, recommended |
| `.cpuOnly` | CPU exclusively | Debugging, FP32 accuracy |
| `.cpuAndGPU` | CPU and GPU, no ANE | When ANE causes issues |
| `.cpuAndNeuralEngine` | CPU and ANE, no GPU | Energy efficiency (macOS 13+) |

## Stateful Models (iOS 18+)

Persist intermediate values across inference runs. Critical for LLM KV-cache.

### Python Conversion

```python
mlmodel = ct.convert(
    traced_model,
    inputs=[ct.TensorType(shape=(1,), name="x")],
    outputs=[ct.TensorType(name="y")],
    states=[ct.StateType(
        wrapped_type=ct.TensorType(shape=(1,)),
        name="accumulator",
    )],
    minimum_deployment_target=ct.target.iOS18,
)

# Python prediction with state
state = mlmodel.make_state()
result = mlmodel.predict({"x": np.array([2.0])}, state=state)
```

### Swift Usage

```swift
let model = try MLModel(contentsOf: modelURL, configuration: config)
let state = model.makeState()
let input = try MLDictionaryFeatureProvider(
    dictionary: ["x": MLFeatureValue(double: 2.0)]
)
let output = try model.prediction(from: input, using: state)
```

Impact: Llama 3.1 with stateful KV-cache achieves 16.26 tokens/s vs 1.25
tokens/s without (13x improvement).

## Multifunction Models (iOS 18+)

Pack multiple model functions (e.g., LoRA adapters) into a single .mlpackage.
Shared weights are deduplicated.

```python
desc = ct.utils.MultiFunctionDescriptor()
desc.add_function("base.mlpackage", src_function_name="main",
                  target_function_name="base")
desc.add_function("adapter1.mlpackage", src_function_name="main",
                  target_function_name="style_1")
desc.default_function_name = "base"
ct.utils.save_multifunction(desc, "combined.mlpackage")
```

```swift
let config = MLModelConfiguration()
config.functionName = "style_1"
let model = try MLModel(contentsOf: modelURL, configuration: config)
```

## Model Utilities

```python
# Inspect model
spec = mlmodel.get_spec()
print(spec.description)

# Rename inputs/outputs
ct.utils.rename_feature(spec, "old_name", "new_name")

# Set metadata
mlmodel.author = "Author"
mlmodel.short_description = "Description"
mlmodel.input_description["image"] = "RGB image 224x224"

# Split large models for debugging
ct.models.utils.bisect_model("large.mlpackage", "./output/")

# Create pipeline from multiple models
pipeline = ct.models.utils.make_pipeline(model1, model2)

# Randomize weights (for testing)
random_model = ct.models.utils.randomize_weights(mlmodel)
```

## Graph Pass Control

```python
# Skip specific optimization passes
pipeline = ct.PassPipeline()
pipeline.remove_passes({"common::fuse_conv_batchnorm"})
mlmodel = ct.convert(model, pass_pipeline=pipeline)

# Predefined pipelines
ct.PassPipeline.EMPTY              # no passes
ct.PassPipeline.CLEANUP            # minimal cleanup
ct.PassPipeline.DEFAULT_PRUNING    # optimized for pruned models
ct.PassPipeline.DEFAULT_PALETTIZATION  # optimized for palettized models
```

## Custom Composite Operators

When PyTorch uses ops not natively supported:

```python
from coremltools.converters.mil.frontend.torch.torch_op_registry import register_torch_op
from coremltools.converters.mil.frontend.torch.ops import _get_inputs
from coremltools.converters.mil import Builder as mb

@register_torch_op
def selu(context, node):
    x = _get_inputs(context, node, expected=1)[0]
    x = mb.elu(x=x, alpha=1.6732632423543772)
    x = mb.mul(x=x, y=1.0507009873554805, name=node.name)
    context.add(x)
```

## Common Mistakes to Avoid

1. **Forgetting model.eval().** PyTorch models MUST be in eval mode before
   tracing or exporting.
2. **Using RangeDim when EnumeratedShapes would work.** Known input sizes
   should use EnumeratedShapes for better Neural Engine performance.
3. **Targeting neuralnetwork format for new models.** Always use mlprogram.
4. **Not specifying minimum_deployment_target.** Always set it explicitly.
5. **Using Float32 when Float16 suffices.** Float16 is the default and correct
   for most models.
6. **Converting from ONNX directly.** ONNX conversion is deprecated. Convert
   from the original framework.
7. **Not testing on physical devices.** Simulator does not support Metal GPU
   or Neural Engine.
