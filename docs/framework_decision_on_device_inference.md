# Framework Decision For On-Device Inference

This document scopes issue `#2`: deciding the inference framework for running TinyAya locally on mobile devices, with iOS prioritized but Android still in scope.

## Project Constraints

What matters for this project:

- iOS-first delivery because an MLX-based app already exists locally and Apple devices are the shortest path to a working prototype
- Android viability because the longer-term goal is multilingual offline access, not a permanently Apple-only stack
- TinyAya compatibility, ideally without a large amount of custom model conversion work
- good enough latency and memory behavior for child-facing conversational turns
- low integration complexity for a small research team

## Existing Local Advantage

There is already a functioning MLX iOS app at `/Users/batuhanaktas/Development/personal/gemma_hack`.

That app already demonstrates:

- SwiftUI + MLX integration
- local model download and caching
- memory pressure handling on iPhone
- pre/post inference cache clearing
- practical device-side constraints around 4B-class models

This is important because it reduces iOS execution risk significantly.

## Framework Options

### 1. MLX / mlx-swift-lm

Best fit for:

- iOS-first prototyping
- fastest path to a real TinyAya app on Apple hardware

Why it is attractive:

- Apple-built stack designed around Apple Silicon
- strong Swift integration
- you already have working code patterns in `gemma_hack`
- TinyAya already exists in MLX format via `mlx-community/tiny-aya-global-8bit-mlx`

Main limitation:

- not a cross-platform answer
- does not solve Android

Practical conclusion:

- MLX is the best near-term iOS path
- MLX alone should not be treated as the final cross-platform architecture

### 2. llama.cpp

Best fit for:

- broad device/platform coverage
- low-level control
- strong ecosystem support for quantized local inference

Why it is attractive:

- mature C/C++ inference runtime
- official mobile examples exist for both iOS and Android
- good story for GGUF-based deployment and on-device experimentation
- likely the strongest portability option if the model can be brought into a supported format cleanly

Main limitations:

- integration is lower-level than MLX
- iOS developer ergonomics are worse than pure Swift/MLX
- model conversion and tokenizer/chat-template handling need to be verified for TinyAya specifically

Practical conclusion:

- strongest cross-platform candidate today
- best fallback or second-track framework after the iOS MLX prototype

### 3. MLC LLM

Best fit for:

- one higher-level runtime target across iOS and Android
- teams that want a more app-oriented mobile deployment story

Why it is attractive:

- official iOS and Android deployment flows
- unified packaging/deployment story
- better cross-platform ergonomics than wiring llama.cpp by hand in some cases

Main limitations:

- still requires model compatibility and conversion work
- less directly aligned with your already-working MLX iOS code
- smaller practical overlap with the current local prototype than MLX

Practical conclusion:

- credible cross-platform option
- worth evaluating against llama.cpp, but not the first thing to build if the goal is the fastest iOS demo

### 4. ExecuTorch / ONNX Runtime / Core ML routes

Best fit for:

- later-stage optimization or specialized deployment paths

Why they are weaker for this project right now:

- more conversion work
- less direct evidence that TinyAya can be moved cleanly with minimal effort
- not as immediately aligned with the current model and app setup

Practical conclusion:

- not first-choice frameworks for the current stage

## Decision Summary

If the question is:

### "What should we use to get TinyAya running on iPhone fastest?"

Use `MLX`.

### "What should we use if we need one realistic path that can also reach Android?"

Investigate `llama.cpp` first, with `MLC LLM` as the other serious candidate.

## Recommended Strategy

Do not force a single framework decision too early.

Instead:

### Track A: iOS prototype

Use `MLX` first.

Reason:

- you already have a working MLX app structure
- the TinyAya MLX checkpoint already exists
- this gives the fastest path to testing latency, memory, UX, and child-facing response quality on real iPhones

### Track B: cross-platform fallback

Evaluate `llama.cpp` in parallel as the likely Android-capable runtime.

Reason:

- it is the strongest practical portability candidate
- if TinyAya converts and runs acceptably in GGUF, it becomes the likely long-term runtime for Android and possibly a shared runtime story

### Track C: keep MLC LLM as a comparison, not the first build target

Reason:

- it is promising for unified mobile deployment
- but it is not the shortest route to a TinyAya demo given the current repo state

## Recommendation For Issue #2

Recommended decision:

1. `MLX` is the official framework for the first iOS prototype.
2. `llama.cpp` is the primary framework to evaluate for Android viability and possible long-term cross-platform inference.
3. `MLC LLM` is a secondary cross-platform candidate if llama.cpp integration or model compatibility becomes painful.

This is not indecisive. It reflects the actual constraint structure:

- iOS-first and cross-platform are different optimization targets
- the best iOS framework is not automatically the best Android framework

## Immediate Spike Plan

The next engineering spike should answer these questions with code, not opinion:

1. Can `mlx-community/tiny-aya-global-8bit-mlx` run inside a simplified version of the existing MLX app on a real iPhone with acceptable memory and latency?
2. Can the same TinyAya family checkpoint be converted or sourced in a format that runs in `llama.cpp` on mobile?
3. What is the token latency, memory footprint, and response quality delta between the iOS MLX path and the first portable runtime candidate?

## Concrete Acceptance Criteria

For the iOS MLX spike:

- model loads successfully on a physical iPhone
- one benchmark prompt from the repository runs end to end
- first-token latency and total response latency are measured
- peak memory usage is measured

For the cross-platform runtime spike:

- TinyAya or the nearest compatible checkpoint runs in the chosen portable runtime
- at least one mobile target is demonstrated or a desktop simulation is completed with a clearly portable build path
- model packaging/conversion steps are documented

## Sources

Primary sources used for this comparison:

- Apple MLX Swift repositories: `ml-explore/mlx-swift` and `ml-explore/mlx-swift-lm`
- local working MLX app in `/Users/batuhanaktas/Development/personal/gemma_hack`
- llama.cpp official repository and official mobile examples:
  - `ggml-org/llama.cpp`
  - `examples/llama.swiftui`
  - `examples/llama.android`
- MLC LLM official deployment docs for iOS and Android
- Hugging Face model page for `mlx-community/tiny-aya-global-8bit-mlx`
