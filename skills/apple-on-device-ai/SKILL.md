---
name: apple-on-device-ai
description: "Build private, on-device AI features on iPhone, iPad, and Mac with Foundation Models, Core ML, MLX Swift, or llama.cpp. Use when choosing an Apple-local model runtime, building an Apple Intelligence chatbot or tool-calling feature, running an LLM on Apple Silicon, converting or compressing a Python model for Core ML, or comparing on-device inference backends. For Swift Core ML loading and prediction code, use the coreml skill."
---

# On-Device AI for Apple Platforms

Guide for selecting, deploying, and optimizing on-device ML models. Covers Apple
Foundation Models, Core ML, MLX Swift, and llama.cpp.

## Contents

- [Framework Selection Router](#framework-selection-router)
- [Apple Foundation Models Overview](#apple-foundation-models-overview)
- [Core ML Overview](#core-ml-overview)
- [MLX Swift Overview](#mlx-swift-overview)
- [Multi-Backend Architecture](#multi-backend-architecture)
- [Performance Best Practices](#performance-best-practices)
- [Common Mistakes](#common-mistakes)
- [Review Checklist](#review-checklist)
- [References](#references)

## Framework Selection Router

Use this decision tree to pick the right framework for your use case.

### Apple Foundation Models

**When to use:** Text generation, summarization, entity extraction, structured
output, and short dialog on iOS 26+ / macOS 26+ devices with Apple Intelligence
enabled. No app-managed API key, network round trip, or model hosting; still
handle system model asset readiness.

**Best for:**
- Generating text or structured data with `@Generable` types
- Summarization, classification, content tagging
- Tool-augmented generation with the `Tool` protocol
- Apps that need guaranteed on-device privacy

**Not suited for:** Complex math, code generation, factual accuracy tasks,
or apps targeting pre-iOS 26 devices.

### Core ML

**When to use:** Deploying custom trained models (vision, NLP, audio) across all
Apple platforms. Converting models from PyTorch, TensorFlow, or scikit-learn
with coremltools.

**Best for:**
- Image classification, object detection, segmentation
- Custom NLP classifiers, sentiment analysis models
- Audio/speech models via SoundAnalysis integration
- Any scenario needing Neural Engine optimization
- Models requiring quantization, palettization, or pruning

### MLX Swift

**When to use:** Running specific open-source LLMs (Llama, Mistral, Qwen, Gemma)
on Apple Silicon with maximum throughput. Research and prototyping.

**Best for:**
- Highest sustained token generation on Apple Silicon
- Running Hugging Face models from `mlx-community`
- Research requiring automatic differentiation
- Fine-tuning workflows on Mac

### llama.cpp

**When to use:** Cross-platform LLM inference using GGUF model format. Production
deployments needing broad device support.

**Best for:**
- GGUF quantized models (Q4_K_M, Q5_K_M, Q8_0)
- Cross-platform apps (iOS + Android + desktop)
- Maximum compatibility with open-source model ecosystem

### Quick Reference

| Scenario | Framework |
|---|---|
| Text generation on Apple Intelligence devices (iOS 26+) | Foundation Models |
| Structured output from on-device LLM | Foundation Models (`@Generable`) |
| Image classification, object detection | Core ML |
| Custom model from PyTorch/TensorFlow | Core ML + coremltools |
| Running specific open-source LLMs | MLX Swift or llama.cpp |
| Maximum throughput on Apple Silicon | MLX Swift |
| Cross-platform LLM inference | llama.cpp |
| OCR and text recognition | Vision framework |
| Sentiment analysis, NER, tokenization | Natural Language framework |
| Training custom classifiers on device | Create ML |

## Apple Foundation Models Overview

Use the system language model for short generation, summarization, tagging,
structured output, and tool-augmented tasks on Apple Intelligence devices. Gate
every entry point before creating a session:

```swift
import FoundationModels

switch SystemLanguageModel.default.availability {
case .available:
    guard SystemLanguageModel.default.supportsLocale(Locale.current) else {
        // Use locale fallback before generating
        break
    }
    // Proceed with model usage
case .unavailable(.appleIntelligenceNotEnabled):
    // Guide user to enable Apple Intelligence in Settings
case .unavailable(.modelNotReady):
    // System model assets are not ready; show loading state
case .unavailable(.deviceNotEligible):
    // Device cannot run Apple Intelligence; use fallback
case .unavailable(let reason):
    // Unknown or future unavailable reason; use fallback and log reason
}
```

Then create a session and keep its shared context budget small:

```swift
let session = LanguageModelSession {
    "You are a helpful cooking assistant."
}
session.prewarm()
let response = try await session.respond(to: "Suggest a quick pasta recipe")
```

Required guardrails:

- Sessions are stateful and accept one request at a time; serialize access and
  check `isResponding` before issuing another response.
- Instructions, tools, schemas, prompts, transcripts, and output share the
  context window. Register only necessary tools and keep schemas compact.
- Resolve the locale with `supportsLocale(_:)`; do not raw-match language lists.
- Keep untrusted user content in prompts, never instructions. System guardrails
  remain active, so handle refusal and other generation errors with fallback UI.

Load [the Foundation Models reference](references/foundation-models.md) when the
task needs `@Generable`, `@Guide`, streaming, tool definitions, transcripts,
generation options, custom adapters, prompt design, or detailed error handling.

## Core ML Overview

Apple's framework for deploying trained models. Automatically dispatches to the
optimal compute unit (CPU, GPU, or Neural Engine).

### Model Formats

| Format | Extension | When to Use |
|---|---|---|
| `.mlpackage` | Directory (mlprogram) | All new models (iOS 15+) |
| `.mlmodel` | Single file (neuralnetwork) | Legacy only (iOS 11-14) |
| `.mlmodelc` | Compiled | Pre-compiled for faster loading |

Always use mlprogram (`.mlpackage`) for new work.

### Conversion Pipeline (coremltools)

```python
import coremltools as ct

# PyTorch conversion (torch.jit.trace)
model.eval()  # CRITICAL: always call eval() before tracing
traced = torch.jit.trace(model, example_input)
mlmodel = ct.convert(
    traced,
    inputs=[ct.TensorType(shape=(1, 3, 224, 224), name="image")],
    minimum_deployment_target=ct.target.iOS18,
    convert_to='mlprogram',
)
mlmodel.save("Model.mlpackage")
```

### Validate, Fix, and Reconvert

1. Freeze representative source-model fixtures and acceptable output/task
   tolerances before conversion.
2. Convert, then run the same fixtures through the source and Core ML models.
3. If output parity or task metrics miss tolerance, inspect shapes, operators,
   precision, and preprocessing; fix the conversion and rerun the fixtures.
4. Compress only after the uncompressed model passes. Revalidate accuracy after
   each compression change and undo or tune changes that miss the threshold.
5. Profile the passing model on physical target devices, then repeat until
   correctness, latency, memory, and package-size targets all pass.

### Boundary with `coreml`

This skill owns Python-side conversion, compression, profiling, and framework
selection. Use the sibling `coreml` skill for Swift app integration, prediction
APIs, runtime configuration, Vision request wiring, and detailed model loading.

> See [references/coreml-conversion.md](references/coreml-conversion.md) for the
> full conversion pipeline and [references/coreml-optimization.md](references/coreml-optimization.md)
> for optimization techniques.

## MLX Swift Overview

Apple's ML framework for Swift. Highest sustained generation throughput on
Apple Silicon via unified memory architecture.

### Loading and Running LLMs

```swift
import MLX
import MLXLLM
import MLXLMCommon
import MLXLMHFAPI

let container = try await LLMModelFactory.shared.loadContainer(
    from: HubClient.default,
    using: TokenizersLoader(),
    configuration: .init(id: "mlx-community/Qwen3-4B-4bit")
)
let session = ChatSession(container)
print(try await session.respond(to: "Hello"))
```

### Model Selection by Device

| Device | RAM | Recommended Model | RAM Usage |
|---|---|---|---|
| iPhone 12-14 | 4-6 GB | SmolLM2-135M or Qwen 2.5 0.5B | ~0.3 GB |
| iPhone 15 Pro+ | 8 GB | Gemma 3n E4B 4-bit | ~3.5 GB |
| Mac 8 GB | 8 GB | Llama 3.2 3B 4-bit | ~3 GB |
| Mac 16 GB+ | 16 GB+ | Mistral 7B 4-bit | ~6 GB |

### Memory Management

1. Never exceed 60% of total RAM on iOS
2. Set MLX cache limits: `Memory.cacheLimit = 512 * 1024 * 1024`
3. Unload MLX and llama.cpp models on backgrounding or memory pressure; for MLX,
   also call `Memory.clearCache()` after generation-heavy phases
4. Use "Increased Memory Limit" entitlement for larger models
5. Validate MLX Swift and llama.cpp on physical Apple Silicon; Simulator cannot
   exercise Metal-dependent inference, memory, or performance

> See [references/mlx-swift.md](references/mlx-swift.md) for full MLX Swift
> patterns and llama.cpp integration.

## Multi-Backend Architecture

When an app needs multiple AI backends (e.g., Foundation Models + MLX fallback):

```swift
func respond(to prompt: String) async throws -> String {
    if SystemLanguageModel.default.isAvailable {
        return try await foundationModelsRespond(prompt)
    } else if canLoadMLXModel() {
        return try await mlxRespond(prompt)
    } else {
        throw AIError.noBackendAvailable
    }
}
```

Serialize all model access through a coordinator actor to prevent contention:

```swift
actor ModelCoordinator {
    func withExclusiveAccess<T>(_ work: () async throws -> T) async rethrows -> T {
        try await work()
    }
}
```

For custom Core ML models, name only the conversion/optimization handoff here:
send Swift app integration, model loading, Vision wiring, and prediction
lifecycle to `coreml`. Keep private user content, such as journals, on device
unless product explicitly opts into a nonlocal fallback.

## Performance Best Practices

1. Run outside debugger for accurate benchmarks (Xcode: Cmd-Opt-R, uncheck
   "Debug Executable")
2. Call `session.prewarm()` for Foundation Models before user interaction
3. Pre-compile Core ML models to `.mlmodelc` for faster loading
4. Use EnumeratedShapes over RangeDim for Neural Engine optimization
5. Use 4-bit palettization for best Neural Engine memory/latency gains
6. Hand off detailed Vision, Natural Language, and Swift Core ML runtime
   integration to the sibling framework skills

## Common Mistakes

1. **No availability check.** Starting generation without checking
   `SystemLanguageModel.default.availability` leaves unsupported devices with
   failures instead of fallback UI.
2. **No fallback UI.** Users on pre-iOS 26 or devices without Apple Intelligence
   see nothing. Always provide a graceful degradation path.
3. **Exceeding the context window.** The token budget covers input + output.
   Monitor usage via `tokenCount(for:)` and summarize when needed.
4. **Concurrent requests on one session.** `LanguageModelSession` supports one
   request at a time. Check `session.isResponding` or serialize access.
5. **Untrusted content in instructions.** User input placed in the instructions
   parameter bypasses guardrail boundaries. Keep user content in the prompt.
6. **Skipping conversion parity checks.** Compare the source and Core ML model
   on fixed fixtures, then fix and reconvert before compressing or shipping.
7. **Forgetting `model.eval()` before Core ML tracing.** PyTorch models must be
   in eval mode before `torch.jit.trace`. Training-mode artifacts corrupt output.
8. **Using neuralnetwork format.** Always use `mlprogram` (.mlpackage) for new
   Core ML models. The legacy neuralnetwork format is deprecated.
9. **Exceeding 60% RAM on iOS (MLX Swift).** Large models cause OOM kills.
10. **Trusting MLX simulator results.** Validate Metal-dependent behavior on
   physical devices; Simulator is only a UI/control-flow smoke test.
11. **Not clearing MLX caches.** Pair model unload with `Memory.clearCache()`.

## Review Checklist

- [ ] Framework selection matches use case and target OS version
- [ ] Foundation Models: availability checked before every API call
- [ ] Foundation Models: graceful fallback when model unavailable
- [ ] Foundation Models: session prewarm called before user interaction
- [ ] Foundation Models: `@Generable` properties in logical generation order
- [ ] Foundation Models: token budget accounted for (check `contextSize`)
- [ ] Core ML: model format is mlprogram (.mlpackage) for iOS 15+
- [ ] Core ML: source/Core ML parity passes fixed fixtures and task tolerances
- [ ] Core ML: compressed model revalidated and profiled on physical targets
- [ ] MLX Swift: model size appropriate for target device RAM
- [ ] MLX Swift: cache limits set, caches cleared, models unloaded
- [ ] All model access serialized through coordinator actor
- [ ] Concurrency: model types and tool implementations are `Sendable`-conformant or `@MainActor`-isolated
- [ ] Physical device testing performed (not simulator)

## References

- [Foundation Models API](references/foundation-models.md) -- LanguageModelSession, `@Generable`, tool calling, prompt design
- [Core ML Conversion](references/coreml-conversion.md) -- Model conversion from PyTorch, TensorFlow, other frameworks
- [Core ML Optimization](references/coreml-optimization.md) -- Quantization, palettization, pruning, performance tuning
- [MLX Swift & llama.cpp](references/mlx-swift.md) -- MLX Swift patterns, llama.cpp integration, memory management
