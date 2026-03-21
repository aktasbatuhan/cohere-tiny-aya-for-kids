# iOS Team Testing Guide

This document explains how teammates can build and test the current Aya iOS MVP locally.

## What The App Does

The current prototype runs the full voice loop on device:

- STT with `Whisper tiny`
- LLM inference with `TinyAya` via `llama.cpp`
- TTS with `Kokoro`

The visible assistant name in the app is `Aya`.

## Project Location

Open the Xcode project at:

- [ios/MedVisionTracker/MedVisionTracker.xcodeproj](/Users/batuhanaktas/Development/personal/cohere-tiny-aya-for-kids/ios/MedVisionTracker/MedVisionTracker.xcodeproj)

## Requirements

- Xcode 17+
- iOS 18+ device for the current Kokoro path
- an Apple developer signing identity available in Xcode
- internet access on first run to download model assets

## Runtime Stack

The current implementation uses:

- `SwiftWhisper` / `whisper.cpp` for speech-to-text
- `llama.cpp` for TinyAya GGUF inference
- `KokoroSwift` for text-to-speech

Important model assets downloaded on first use:

- TinyAya GGUF from Hugging Face
- Whisper tiny model
- Kokoro model weights
- Kokoro voice pack

The first run is therefore much slower than later runs.

## Build Steps

1. Open the Xcode project.
2. Select the `TinyAyaKids` scheme.
3. Select a physical iPhone running iOS 18 or later.
4. Confirm signing under the app target if Xcode asks.
5. Build and run.

Equivalent command line build:

```bash
xcodebuild \
  -project ios/MedVisionTracker/MedVisionTracker.xcodeproj \
  -scheme TinyAyaKids \
  -destination 'generic/platform=iOS' \
  -derivedDataPath /tmp/tinyaya-ios-dd \
  build
```

## Test Flow

1. Launch the app.
2. Tap `Load Aya`.
3. Wait for the TinyAya model to finish loading.
4. Tap `Talk To Aya`.
5. Speak a short prompt.
6. Tap `Stop And Send`.
7. Wait for Whisper transcription, TinyAya generation, and Kokoro playback.

## Known Limitations

- The app shell was repurposed from an older project, so some internal file names still need cleanup.
- First-run asset downloads are slow.
- Memory pressure still needs proper measurement across multiple device types.
- Some older placeholder screens still exist on disk even though the current app uses the simplified voice-first screen.
- The Kokoro package path should be rechecked on a completely fresh machine to ensure package resolution stays stable.

## What To Report After Testing

For each test run, please capture:

- device model
- iOS version
- whether model download succeeded
- whether the full voice loop completed
- first-response latency feel
- whether the device became hot
- any crash or freeze point

## Current Goal Of This MVP

This is not the final product UI. The goal of the current iOS app is to prove that Aya can run as a fully offline voice companion on a real iPhone before the team invests in a broader product pass.
