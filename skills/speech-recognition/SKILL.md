---
name: speech-recognition
description: "Transcribe speech to text using Apple's Speech framework. Use when implementing live microphone transcription with AVAudioEngine, recognizing recorded audio files, handling speech and microphone authorization, choosing on-device vs server-backed SFSpeechRecognizer behavior, or adopting SpeechAnalyzer, SpeechTranscriber, DictationTranscriber, AssetInventory, and async result streams on iOS 26+."
---

# Speech Recognition

Transcribe live and pre-recorded audio to text using Apple's Speech framework.
Covers `SpeechAnalyzer` / `SpeechTranscriber` (iOS 26+) and
`SFSpeechRecognizer` (iOS 10+) fallback guidance.

**Scope boundary:** Use this skill for speech-to-text recognition, speech
authorization, microphone capture plumbing, and result handling. Hand off text
analysis, language identification after transcription, sentiment, embeddings,
and translation to `natural-language`; hand off audio playback UI to `avkit`;
hand off summarization or generation over transcripts to `apple-on-device-ai`.

## Contents

- [SpeechAnalyzer Strategy (iOS 26+)](#speechanalyzer-strategy-ios-26)
- [SFSpeechRecognizer Setup](#sfspeechrecognizer-setup)
- [Authorization](#authorization)
- [Live Microphone Transcription](#live-microphone-transcription)
- [Pre-Recorded Audio File Recognition](#pre-recorded-audio-file-recognition)
- [On-Device vs Server Recognition](#on-device-vs-server-recognition)
- [Handling Results](#handling-results)
- [Common Mistakes](#common-mistakes)
- [Review Checklist](#review-checklist)
- [References](#references)

## SpeechAnalyzer Strategy (iOS 26+)

Use `SpeechAnalyzer` for modern iOS 26+ speech analysis, especially long-form
recordings, live transcription, time-indexed transcripts, and fully on-device
flows. Keep `SFSpeechRecognizer` for iOS 10+ deployment targets, server-backed
locale coverage, or existing callback/delegate implementations.

Read [SpeechAnalyzer patterns](references/speechanalyzer-patterns.md) when
implementing an iOS 26+ transcription pipeline, model asset handling, volatile
results, or file/buffer examples.

### SpeechAnalyzer setup checklist

1. Choose the module:
   - `SpeechTranscriber` for the newer general-purpose on-device model.
   - `DictationTranscriber` when `SpeechTranscriber` is unavailable for the
     current device or locale and dictation-compatible support is acceptable.
   - `SpeechDetector` only in conjunction with a transcriber when voice
     activity detection is worth the accuracy/power tradeoff.
2. Check support before creating the session:
   - `SpeechTranscriber.isAvailable`
   - `SpeechTranscriber.supportedLocale(equivalentTo:)`
   - `SpeechTranscriber.installedLocales` / `supportedLocales` when showing
     language choices.
3. Pick a documented preset:
   - `.transcription` for basic accurate transcription.
   - `.progressiveTranscription` for live UI updates.
   - `.timeIndexedProgressiveTranscription` when playback highlighting needs
     `audioTimeRange`.
4. Install required assets with `AssetInventory.assetInstallationRequest`.
5. Convert live audio buffers to
   `SpeechAnalyzer.bestAvailableAudioFormat(compatibleWith:)` before yielding
   `AnalyzerInput`.
6. Consume module results from their `AsyncSequence` in a separate task.
7. Finish explicitly with `finalizeAndFinish(through:)`,
   `finalizeAndFinishThroughEndOfInput()`, or `cancelAndFinishNow()`.

Do not use an `offlineTranscription` preset; Apple does not document one.
Finishing an `AsyncStream` input sequence does not finish the analyzer session.

## SFSpeechRecognizer Setup

### Creating a recognizer with locale

```swift
import Speech

// Default locale (user's current language)
let recognizer = SFSpeechRecognizer()

// Specific locale
let recognizer = SFSpeechRecognizer(locale: Locale(identifier: "en-US"))

// Check if recognition is available for this locale
guard let recognizer, recognizer.isAvailable else {
    print("Speech recognition not available")
    return
}
```

### Monitoring availability changes

```swift
final class SpeechManager: NSObject, SFSpeechRecognizerDelegate {
    private let recognizer = SFSpeechRecognizer()!

    override init() {
        super.init()
        recognizer.delegate = self
    }

    func speechRecognizer(
        _ speechRecognizer: SFSpeechRecognizer,
        availabilityDidChange available: Bool
    ) {
        // Update UI — disable record button when unavailable
    }
}
```

## Authorization

Request **both** speech recognition and microphone permissions before starting
live transcription. Add these keys to `Info.plist`:

- `NSSpeechRecognitionUsageDescription`
- `NSMicrophoneUsageDescription`

```swift
import Speech
import AVFoundation

func requestPermissions() async -> Bool {
    let speechStatus = await withCheckedContinuation { continuation in
        SFSpeechRecognizer.requestAuthorization { status in
            continuation.resume(returning: status)
        }
    }
    guard speechStatus == .authorized else { return false }

    let micStatus: Bool
    if #available(iOS 17, *) {
        micStatus = await AVAudioApplication.requestRecordPermission()
    } else {
        micStatus = await withCheckedContinuation { continuation in
            AVAudioSession.sharedInstance().requestRecordPermission { granted in
                continuation.resume(returning: granted)
            }
        }
    }
    return micStatus
}
```

## Live Microphone Transcription

The standard pattern: `AVAudioEngine` captures microphone audio → buffers are
appended to `SFSpeechAudioBufferRecognitionRequest` → results stream in.

```swift
import Speech
import AVFoundation

final class LiveTranscriber {
    private let recognizer = SFSpeechRecognizer(locale: Locale(identifier: "en-US"))!
    private let audioEngine = AVAudioEngine()
    private var recognitionRequest: SFSpeechAudioBufferRecognitionRequest?
    private var recognitionTask: SFSpeechRecognitionTask?

    func startTranscribing() throws {
        // Cancel any in-progress task
        recognitionTask?.cancel()
        recognitionTask = nil

        // Configure audio session
        let audioSession = AVAudioSession.sharedInstance()
        try audioSession.setCategory(.record, mode: .measurement, options: .duckOthers)
        try audioSession.setActive(true, options: .notifyOthersOnDeactivation)

        // Create request
        let request = SFSpeechAudioBufferRecognitionRequest()
        request.shouldReportPartialResults = true
        self.recognitionRequest = request

        // Start recognition task
        recognitionTask = recognizer.recognitionTask(with: request) { result, error in
            if let result {
                let text = result.bestTranscription.formattedString
                print("Transcription: \(text)")

                if result.isFinal {
                    self.stopTranscribing()
                }
            }
            if let error {
                print("Recognition error: \(error)")
                self.stopTranscribing()
            }
        }

        // Install audio tap
        let inputNode = audioEngine.inputNode
        let recordingFormat = inputNode.outputFormat(forBus: 0)
        inputNode.installTap(onBus: 0, bufferSize: 1024, format: recordingFormat) {
            buffer, _ in
            request.append(buffer)
        }

        audioEngine.prepare()
        try audioEngine.start()
    }

    func stopTranscribing() {
        audioEngine.stop()
        audioEngine.inputNode.removeTap(onBus: 0)
        recognitionRequest?.endAudio()
        recognitionRequest = nil
        recognitionTask?.cancel()
        recognitionTask = nil
    }
}
```

## Pre-Recorded Audio File Recognition

Use `SFSpeechURLRecognitionRequest` for audio files on disk:

```swift
func transcribeFile(at url: URL) async throws -> String {
    guard let recognizer = SFSpeechRecognizer(), recognizer.isAvailable else {
        throw SpeechError.unavailable
    }
    let request = SFSpeechURLRecognitionRequest(url: url)
    request.shouldReportPartialResults = false

    return try await withCheckedThrowingContinuation { continuation in
        var didResume = false
        recognizer.recognitionTask(with: request) { result, error in
            guard !didResume else { return }
            if let error {
                didResume = true
                continuation.resume(throwing: error)
            } else if let result, result.isFinal {
                didResume = true
                continuation.resume(
                    returning: result.bestTranscription.formattedString
                )
            }
        }
    }
}
```

## On-Device vs Server Recognition

`SFSpeechRecognizer` can use on-device recognition for supported locales on
iOS 13+. If `supportsOnDeviceRecognition` is false, the recognizer requires a
network connection. `requiresOnDeviceRecognition` only has effect when the
recognizer supports it.

```swift
let recognizer = SFSpeechRecognizer(locale: Locale(identifier: "en-US"))!

// Check if on-device is supported for this locale
if recognizer.supportsOnDeviceRecognition {
    let request = SFSpeechAudioBufferRecognitionRequest()
    request.requiresOnDeviceRecognition = true  // Force on-device
}
```

`SFSpeechRecognizer` requests may still be a poor fit for long-form capture.
Apple documents a roughly one-minute task limit for speech recognition and
other service limits. For long recordings on iOS 26+, prefer `SpeechAnalyzer`;
otherwise chunk or restart recognition before the limit and preserve transcript
state across tasks.

## Handling Results

### Partial vs final results

With `shouldReportPartialResults`, replace the displayed partial transcript until `SFSpeechRecognitionResult.isFinal` commits it. This is separate from `SpeechTranscriber.Result.isFinal`, whose volatile attributed range must be replaced by the final result for that range. The live example and [references/speechanalyzer-patterns.md](references/speechanalyzer-patterns.md) contain the canonical loops.

### Accessing alternative transcriptions and confidence

```swift
recognizer.recognitionTask(with: request) { result, error in
    guard let result else { return }

    // Best transcription
    let best = result.bestTranscription

    // All alternatives (sorted by confidence, descending)
    for transcription in result.transcriptions {
        for segment in transcription.segments {
            print("\(segment.substring): \(segment.confidence)")
        }
    }
}
```

### Adding punctuation (iOS 16+)

```swift
let request = SFSpeechAudioBufferRecognitionRequest()
request.addsPunctuation = true
```

### Contextual strings

Improve recognition of domain-specific terms:

```swift
let request = SFSpeechAudioBufferRecognitionRequest()
request.contextualStrings = ["SwiftUI", "Xcode", "CloudKit"]
```

## Common Mistakes

| Mistake | Fix |
|---|---|
| Live audio requests only speech authorization | Require both speech and microphone permission. |
| Recognizer availability is checked once | Observe delegate availability changes and model loss of service. |
| Final/error/rollover paths perform different cleanup | Use one `stopTranscribing()` owner for engine stop, tap removal, `endAudio`, and task cancellation. |
| On-device mode is forced for every locale | Check `supportsOnDeviceRecognition` and provide a fallback. |
| One `SFSpeechRecognizer` task is used for long-form capture | Prefer SpeechAnalyzer on iOS 26+ or roll bounded segments while preserving committed transcript. |
| Finishing analyzer input is treated as session completion | Explicitly finalize through the last sample or cancel-and-finish. |
| Volatile SpeechAnalyzer results are appended | Replace the volatile range until a final result commits it. |
| A second recognition task starts before the first ends | Cancel/finish the active task and complete cleanup before replacement. |

Load [references/speechanalyzer-patterns.md](references/speechanalyzer-patterns.md) for complete analyzer finalization and volatile-result code.

## Review Checklist

- [ ] `NSSpeechRecognitionUsageDescription` is in Info.plist
- [ ] `NSMicrophoneUsageDescription` is in Info.plist (if using live audio)
- [ ] Authorization is requested before starting recognition
- [ ] `SFSpeechRecognizerDelegate` is set to handle `availabilityDidChange`
- [ ] Audio engine is stopped and tap removed when recognition ends
- [ ] `recognitionRequest.endAudio()` is called when done recording
- [ ] Previous `recognitionTask` is canceled before starting a new one
- [ ] `supportsOnDeviceRecognition` is checked before requiring on-device mode
- [ ] Partial results are handled separately from final (`isFinal`) results
- [ ] `SFSpeechRecognizer` one-minute/service limits are accounted for
- [ ] For iOS 26+: `AssetInventory` assets are installed before using `SpeechAnalyzer`
- [ ] For iOS 26+: `SpeechTranscriber.isAvailable` and locale support are checked
- [ ] For iOS 26+: live buffers are converted to the analyzer-compatible format
- [ ] For iOS 26+: analyzer sessions are explicitly finalized or canceled
- [ ] For iOS 26+: volatile results are replaced by finalized results, not duplicated

## References

- [Speech framework](https://sosumi.ai/documentation/speech)
- [SpeechAnalyzer](https://sosumi.ai/documentation/speech/speechanalyzer)
- [SpeechTranscriber](https://sosumi.ai/documentation/speech/speechtranscriber)
- [SpeechTranscriber.Preset](https://sosumi.ai/documentation/speech/speechtranscriber/preset)
- [DictationTranscriber](https://sosumi.ai/documentation/speech/dictationtranscriber)
- [SpeechDetector](https://sosumi.ai/documentation/speech/speechdetector)
- [SFSpeechRecognizer](https://sosumi.ai/documentation/speech/sfspeechrecognizer)
- [SFSpeechAudioBufferRecognitionRequest](https://sosumi.ai/documentation/speech/sfspeechaudiobufferrecognitionrequest)
- [SFSpeechURLRecognitionRequest](https://sosumi.ai/documentation/speech/sfspeechurlrecognitionrequest)
- [SFSpeechRecognitionResult](https://sosumi.ai/documentation/speech/sfspeechrecognitionresult)
- [SFSpeechRecognitionRequest](https://sosumi.ai/documentation/speech/sfspeechrecognitionrequest)
- [AssetInventory](https://sosumi.ai/documentation/speech/assetinventory)
- [Asking Permission to Use Speech Recognition](https://sosumi.ai/documentation/speech/asking-permission-to-use-speech-recognition)
- [Recognizing Speech in Live Audio](https://sosumi.ai/documentation/speech/recognizing-speech-in-live-audio)
- [Bring advanced speech-to-text to your app with SpeechAnalyzer](https://sosumi.ai/videos/play/wwdc2025/277)
