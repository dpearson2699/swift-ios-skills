# LiteRT-LM Reference

Run open `.litertlm` models such as Gemma 4 on iPhone, iPad, and Mac with
LiteRT-LM, Google's open-source on-device runtime. The same model file runs in
Android apps.

## Contents

- [Add the Package](#add-the-package)
- [Load a Model and Stream a Reply](#load-a-model-and-stream-a-reply)
- [Stop and Unload](#stop-and-unload)
- [Common Mistakes](#common-mistakes)
- [Review Checklist](#review-checklist)

## Add the Package

- Swift Package Manager: `https://github.com/google-ai-edge/LiteRT-LM`, exact
  version `0.19.1`, product `LiteRTLM` (iOS 15+, macOS 12+).
- The package checkout uses Git LFS. Xcode started without `git-lfs` on its
  PATH (for example from the Dock, with Git LFS installed by Homebrew) stops
  with `Git LFS is not installed`. `xcodebuild` run from a shell that has
  `git-lfs` on its PATH resolves and builds the package.
- Model: `gemma-4-E2B-it.litertlm` (2.6 GB) from the Hugging Face repo
  `litert-community/gemma-4-E2B-it-litert-lm`. The engine takes a file path:
  copy the file into the app container or download it on first launch.

## Load a Model and Stream a Reply

```swift
import Foundation
import LiteRTLM

actor LocalModel {
    private var engine: Engine?
    private var conversation: Conversation?
    private var stopped = false

    func load(modelPath: String, backend: Backend = .gpu) async throws {
        let caches = FileManager.default.urls(for: .cachesDirectory, in: .userDomainMask)[0]
        let config = try EngineConfig(modelPath: modelPath, backend: backend, cacheDir: caches.path)
        let engine = Engine(engineConfig: config)
        try await engine.initialize()
        self.engine = engine
    }

    func reply(
        to prompt: String, maxOutputTokens: Int? = nil
    ) async throws -> sending AsyncThrowingStream<Message, Error> {
        guard let engine else { throw CocoaError(.featureUnsupported) }
        if stopped { conversation = nil; stopped = false }
        if conversation == nil { conversation = try await engine.createConversation() }
        guard let conversation else { throw CocoaError(.featureUnsupported) }
        return conversation.sendMessageStream(Message(prompt), maxOutputTokens: maxOutputTokens)
    }

    // Cancelling the Task that reads the stream does not stop decoding; cancel the conversation.
    // A cancelled conversation is not reused: the next reply releases it and starts a new one.
    // Releasing it here, while its stream is still open, would delete it inside LiteRT-LM's callback.
    func stop() {
        if !stopped { try? conversation?.cancel() }
        stopped = true
    }

    func unload() {
        conversation = nil
        engine = nil
    }
}
```

```swift
import LiteRTLM

func answer(_ model: LocalModel, to prompt: String) async throws -> String {
    var text = ""
    for try await chunk in try await model.reply(to: prompt) {
        text += chunk.toString
    }
    return text
}
```

- `initialize()` loads the weights; keep it off the main actor (the actor above
  does). The first load on a device also writes a GPU cache of about 0.8 GB to
  `cacheDir`, so it takes longer than later loads.
- Backends: `.gpu` (Metal) and `.cpu()`.

## Stop and Unload

- `stop()` calls `conversation.cancel()`, which stops decoding. Cancelling the
  Task that reads the stream only stops reading; it does not cancel decoding.
- After `stop()`, the reading loop ends by throwing a `CANCELLED` error.
- A cancelled conversation is not reused: the next message on it fails at once.
  Let the stopped stream end, then call `reply(to:)`, which starts a new
  conversation. Releasing the conversation while its stream is still open
  deletes it inside LiteRT-LM's stream callback, and the next reply stalls.
- `unload()` releases the conversation and the engine, which frees the weights.
  Call it after the reply stream has ended; after `stop()`, let the stream end
  first. Load again later with a new `Engine`.

## Common Mistakes

1. Cancelling only the Task that reads the stream. Call `cancel()` on the
   conversation.
2. Sending the next prompt to a cancelled conversation. Start a new one.
3. Calling `initialize()` twice on one `Engine`; the second call throws
   `alreadyInitialized`.
4. Loading a download without checking its size. A truncated `.litertlm` fails
   to load with an error that does not mention the size.
5. Releasing the conversation or the engine while a reply stream is still open.
   Let the stream end first.

## Review Checklist

- [ ] Package pinned to an exact LiteRT-LM version
- [ ] Engine initialized off the main actor, once
- [ ] Stop button calls `conversation.cancel()`, and the next prompt uses a new conversation
- [ ] Engine released when the feature closes, after the last reply stream has ended
- [ ] Tested on a physical device
