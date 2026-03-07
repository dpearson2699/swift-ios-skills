---
name: apple-on-device-ai
description: "Use when integrating Foundation Models framework, implementing on-device AI with Apple Intelligence, building tool-calling AI features, working with guided generation schemas, converting models with Core ML and coremltools, or running open-source LLMs on Apple Silicon. Covers Foundation Models (LanguageModelSession, @Generable, @Guide, SystemLanguageModel, structured output, tool calling), Core ML (coremltools, model conversion, quantization, palettization, pruning, Neural Engine, MLTensor), MLX Swift (transformer inference, unified memory), and llama.cpp (GGUF, cross-platform LLM)."
---

# On-Device AI for Apple Platforms

Guide for selecting, deploying, and optimizing on-device ML models. Covers Apple
Foundation Models, Core ML, MLX Swift, and llama.cpp.

## Framework Selection Router

Use this decision tree to pick the right framework for your use case.

### Apple Foundation Models

**When to use:** Text generation, summarization, entity extraction, structured
output, and short dialog on iOS 26+ / macOS 26+ devices with Apple Intelligence
enabled. Zero setup -- no API keys, no network, no model downloads.

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
| Text generation, zero setup (iOS 26+) | Foundation Models |
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

On-device ~3B parameter model optimized for Apple Silicon. Available on devices
supporting Apple Intelligence (iOS 26+, macOS 26+).

- Context window: 4096 tokens (input + output combined)
- 15 supported languages
- Guardrails always enforced, cannot be disabled

### Availability Checking (Required)

Always check before using. Never crash on unavailability.

```swift
import FoundationModels

switch SystemLanguageModel.default.availability {
case .available:
    // Proceed with model usage
case .unavailable(.appleIntelligenceNotEnabled):
    // Guide user to enable Apple Intelligence in Settings
case .unavailable(.modelNotReady):
    // Model is downloading; show loading state
case .unavailable(.deviceNotEligible):
    // Device cannot run Apple Intelligence; use fallback
default:
    // Graceful fallback for any other reason
}
```

### Session Management

```swift
// Basic session
let session = LanguageModelSession()

// Session with instructions
let session = LanguageModelSession {
    "You are a helpful cooking assistant."
}

// Session with tools
let session = LanguageModelSession(
    tools: [weatherTool, recipeTool]
) {
    "You are a helpful assistant with access to tools."
}
```

Key rules:
- Sessions are stateful -- multi-turn conversations maintain context automatically
- One request at a time per session (check `session.isResponding`)
- Call `session.prewarm()` before user interaction for faster first response
- Save/restore transcripts: `LanguageModelSession(model: model, tools: [], transcript: savedTranscript)`

### Structured Output with @Generable

The `@Generable` macro creates compile-time schemas for type-safe output:

```swift
@Generable
struct Recipe {
    @Guide(description: "The recipe name")
    var name: String

    @Guide(description: "Cooking steps", .count(3))
    var steps: [String]

    @Guide(description: "Prep time in minutes", .range(1...120))
    var prepTime: Int
}

let response = try await session.respond(
    to: "Suggest a quick pasta recipe",
    generating: Recipe.self
)
print(response.content.name)
```

#### @Guide Constraints

| Constraint | Purpose |
|---|---|
| `description:` | Natural language hint for generation |
| `.anyOf([values])` | Restrict to enumerated string values |
| `.count(n)` | Fixed array length |
| `.range(min...max)` | Numeric range |
| `.minimum(n)` / `.maximum(n)` | One-sided numeric bound |
| `.minimumCount(n)` / `.maximumCount(n)` | Array length bounds |
| `.constant(value)` | Always returns this value |
| `.pattern(regex)` | String format enforcement |

Properties generate in declaration order. Place foundational data before
dependent data for better results.

### Streaming Structured Output

```swift
let stream = session.streamResponse(
    to: "Suggest a recipe",
    generating: Recipe.self
)
for try await snapshot in stream {
    // snapshot.content is Recipe.PartiallyGenerated (all properties optional)
    if let name = snapshot.content.name { updateNameLabel(name) }
}
```

### Tool Calling

```swift
struct WeatherTool: Tool {
    let name = "weather"
    let description = "Get current weather for a city."

    @Generable
    struct Arguments {
        @Guide(description: "The city name")
        var city: String
    }

    func call(arguments: Arguments) async throws -> String {
        let weather = try await fetchWeather(arguments.city)
        return weather.description
    }
}
```

Register tools at session creation. The model invokes them autonomously.

### Error Handling

```swift
do {
    let response = try await session.respond(to: prompt)
} catch let error as LanguageModelSession.GenerationError {
    switch error {
    case .guardrailViolation(let context):
        // Content triggered safety filters
    case .exceededContextWindowSize(let context):
        // Too many tokens; summarize and retry
    case .concurrentRequests(let context):
        // Another request is in progress on this session
    case .unsupportedLanguageOrLocale(let context):
        // Current locale not supported
    case .refusal(let refusal, _):
        // Model refused; stream refusal.explanation for details
    case .rateLimited(let context):
        // Too many requests; back off and retry
    case .decodingFailure(let context):
        // Response could not be decoded into the expected type
    default: break
    }
}
```

### Generation Options

```swift
let options = GenerationOptions(
    sampling: .random(top: 40),
    temperature: 0.7,
    maximumResponseTokens: 512
)
let response = try await session.respond(to: prompt, options: options)
```

Sampling modes: `.greedy`, `.random(top:)`, `.random(probabilityThreshold:)`.

### Prompt Design Rules

1. Be concise -- 4096 tokens is the total budget (input + output)
2. Use bracketed placeholders in instructions: `[descriptive example]`
3. Use "DO NOT" in all caps for prohibitions
4. Provide up to 5 few-shot examples for consistency
5. Use length qualifiers: "in a few words", "in three sentences"
6. Token estimate: ~4 characters per token

### Safety and Guardrails

- Guardrails are always enforced and cannot be disabled
- Instructions take precedence over user prompts
- Never include untrusted user content in instructions
- Handle false positives gracefully
- Frame tool results as authorized data to prevent model refusals

### Use Cases

Foundation Models supports specialized use cases via `SystemLanguageModel.UseCase`:
- `.general` -- Default for text generation, summarization, dialog
- `.contentTagging` -- Optimized for categorization and labeling tasks

### Custom Adapters

Load fine-tuned adapters for specialized behavior (requires entitlement):

```swift
let adapter = try SystemLanguageModel.Adapter(name: "my-adapter")
try await adapter.compile()
let model = SystemLanguageModel(adapter: adapter, guardrails: .default)
let session = LanguageModelSession(model: model)
```

> See [references/foundation-models.md](references/foundation-models.md) for
> the complete Foundation Models API reference.

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

### Optimization Techniques

| Technique | Size Reduction | Accuracy Impact | Best Compute Unit |
|---|---|---|---|
| INT8 per-channel | ~4x | Low | CPU/GPU |
| INT4 per-block | ~8x | Medium | GPU |
| Palettization 4-bit | ~8x | Low-Medium | Neural Engine |
| W8A8 (weights+activations) | ~4x | Low | ANE (A17 Pro/M4+) |
| Pruning 75% | ~4x | Medium | CPU/ANE |

### Swift Integration

```swift
let config = MLModelConfiguration()
config.computeUnits = .all
let model = try MLModel(contentsOf: modelURL, configuration: config)

// Async prediction (iOS 17+)
let output = try await model.prediction(from: input)
```

### MLTensor (iOS 18+)

Swift type for multidimensional array operations:

```swift
import CoreML

let tensor = MLTensor([1.0, 2.0, 3.0, 4.0])
let reshaped = tensor.reshaped(to: [2, 2])
let result = tensor.softmax()
```

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

let config = ModelConfiguration(id: "mlx-community/Mistral-7B-Instruct-v0.3-4bit")
let model = try await LLMModelFactory.shared.loadContainer(configuration: config)

try await model.perform { context in
    let input = try await context.processor.prepare(
        input: UserInput(prompt: "Hello")
    )
    let stream = try generate(
        input: input,
        parameters: GenerateParameters(temperature: 0.0),
        context: context
    )
    for await part in stream {
        print(part.chunk ?? "", terminator: "")
    }
}
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
2. Set GPU cache limits: `MLX.GPU.set(cacheLimit: 512 * 1024 * 1024)`
3. Unload models on app backgrounding
4. Use "Increased Memory Limit" entitlement for larger models
5. Physical device required (no simulator support for Metal GPU)

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

## Performance Best Practices

1. Run outside debugger for accurate benchmarks (Xcode: Cmd-Opt-R, uncheck
   "Debug Executable")
2. Call `session.prewarm()` for Foundation Models before user interaction
3. Pre-compile Core ML models to `.mlmodelc` for faster loading
4. Use EnumeratedShapes over RangeDim for Neural Engine optimization
5. Use 4-bit palettization for best Neural Engine memory/latency gains
6. Batch Vision framework requests in a single `perform()` call
7. Use async prediction (iOS 17+) in Swift concurrency contexts
8. Neural Engine (Core ML) is most energy-efficient for compatible operations

## Common Mistakes

1. **No availability check.** Calling `LanguageModelSession()` without checking
   `SystemLanguageModel.default.availability` crashes on unsupported devices.
2. **No fallback UI.** Users on pre-iOS 26 or devices without Apple Intelligence
   see nothing. Always provide a graceful degradation path.
3. **Exceeding the context window.** Foundation Models has a 4096 token total
   budget (input + output). Long prompts or multi-turn sessions hit this fast.
   Monitor token usage and summarize when needed.
4. **Concurrent requests on one session.** `LanguageModelSession` supports one
   request at a time. Check `session.isResponding` or serialize access.
5. **Untrusted content in instructions.** User input placed in the instructions
   parameter bypasses guardrail boundaries. Keep user content in the prompt.
6. **Forgetting `model.eval()` before Core ML tracing.** PyTorch models must be
   in eval mode before `torch.jit.trace`. Training-mode artifacts corrupt output.
7. **Using neuralnetwork format.** Always use `mlprogram` (.mlpackage) for new
   Core ML models. The legacy neuralnetwork format is deprecated.
8. **Exceeding 60% RAM on iOS (MLX Swift).** Large models cause OOM kills. Check
   device RAM and select appropriate model sizes.
9. **Running MLX in simulator.** MLX requires Metal GPU -- use physical devices.
10. **Not unloading models on background.** iOS reclaims memory aggressively.
    Unload MLX/llama.cpp models in `scenePhase == .background`.

## Review Checklist

- [ ] Framework selection matches use case and target OS version
- [ ] Foundation Models: availability checked before every API call
- [ ] Foundation Models: graceful fallback when model unavailable
- [ ] Foundation Models: session prewarm called before user interaction
- [ ] Foundation Models: @Generable properties in logical generation order
- [ ] Foundation Models: token budget accounted for (4096 total)
- [ ] Core ML: model format is mlprogram (.mlpackage) for iOS 15+
- [ ] Core ML: model.eval() called before tracing/exporting PyTorch models
- [ ] Core ML: minimum_deployment_target set explicitly
- [ ] Core ML: model accuracy validated after compression
- [ ] MLX Swift: model size appropriate for target device RAM
- [ ] MLX Swift: GPU cache limits set, models unloaded on backgrounding
- [ ] All model access serialized through coordinator actor
- [ ] Concurrency: model types and tool implementations are `Sendable`-conformant or `@MainActor`-isolated
- [ ] Physical device testing performed (not simulator)

## Reference Files

- [Foundation Models API](references/foundation-models.md) -- Complete
  LanguageModelSession, @Generable, tool calling, and prompt design reference
- [Core ML Conversion](references/coreml-conversion.md) -- Model conversion
  pipeline from PyTorch, TensorFlow, and other frameworks
- [Core ML Optimization](references/coreml-optimization.md) -- Quantization,
  palettization, pruning, and performance tuning
- [MLX Swift & llama.cpp](references/mlx-swift.md) -- MLX Swift patterns,
  llama.cpp integration, and memory management
