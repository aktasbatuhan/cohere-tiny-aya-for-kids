# iOS MVP Status

Current local state:

- an iOS app exists under `ios/MedVisionTracker`
- it now runs a working offline voice loop on a physical iPhone
- the visible assistant name in the app is `Aya`
- the current path is no longer MLX for LLM inference

## What Works

- project builds successfully for iPhone
- TinyAya runs via `llama.cpp`
- speech-to-text runs via `SwiftWhisper` / `whisper.cpp`
- text-to-speech runs via `KokoroSwift`
- the main app flow supports:
  - model load
  - push-to-talk recording
  - Whisper transcription
  - TinyAya response generation
  - Kokoro playback

## Current Runtime Choice

The current iOS MVP uses:

- LLM: `TinyAya` GGUF through `llama.cpp`
- STT: `Whisper tiny`
- TTS: `Kokoro`

This replaced the earlier MLX attempt because the MLX TinyAya checkpoint exposed a `cohere2` model type that was not supported by the current `mlx-swift-lm` runtime.

## Build Command

```bash
xcodebuild \
  -project ios/MedVisionTracker/MedVisionTracker.xcodeproj \
  -scheme TinyAyaKids \
  -destination 'generic/platform=iOS' \
  -derivedDataPath /tmp/tinyaya-ios-dd \
  build
```

## Known Cleanup Needed

- remove or rename inherited internal file names like `MedGemmaService`
- remove stale placeholder screens and old project leftovers from disk
- make dependency setup more durable on a fresh machine
- reduce first-run friction from model downloads
- add repeatable latency and memory measurement on device

## Why This Matters

The point of this stage is no longer proving that an iOS shell can compile. The key result is that Aya now has a real offline voice loop on iPhone, which makes the next work practical:

- testing with more teammates and devices
- measuring memory and latency properly
- improving the product UI
- evaluating whether this stack is stable enough to keep as the iOS-first implementation path
