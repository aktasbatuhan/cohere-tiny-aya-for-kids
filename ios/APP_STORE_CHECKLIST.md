# iOS App Store Submission Checklist

## Code-complete (in this repo)

- [x] OOM fix for multi-turn voice conversations (release Kokoro before LLM load; explicit actor shutdown)
- [x] Auto-load model on first appearance — no manual "Load Aya" button
- [x] Welcome card explaining on-device privacy on first launch
- [x] Mic permission denial banner with deep-link to Settings
- [x] Quick prompts tap-to-send (previously just filled the text field)
- [x] `NSMicrophoneUsageDescription` in Info.plist with privacy language
- [x] `NSSpeechRecognitionUsageDescription` in Info.plist
- [x] `ITSAppUsesNonExemptEncryption = false` in Info.plist
- [x] HTTPS exceptions for HuggingFace model downloads (on-device only)

## Before first TestFlight build

- [ ] **Generate 1024×1024 AppIcon** — replace placeholder at `ios/TinyAyaKids/Assets.xcassets/AppIcon.appiconset/`
- [ ] Build Release config and resolve any warnings (`xcodebuild -configuration Release`)
- [ ] Verify minimum deployment target (iOS 18.0 currently per IPHONEOS_DEPLOYMENT_TARGET)
- [ ] Increment `CFBundleVersion` (build number) for each TestFlight upload

## Before App Store submission

- [ ] **Privacy policy URL** (required). Emphasize: fully on-device, no data leaves the phone, no analytics, no sign-in, no ads
- [ ] App Store screenshots (6.5" iPhone + 6.7" iPhone + iPad at minimum):
  - Welcome/empty state screen
  - Active conversation with Aya
  - "Talking" microphone state
- [ ] App Store description (short + long form)
- [ ] App Store keywords (suggestions: "kids", "AI companion", "offline AI", "child-safe", "voice")
- [ ] Age rating — target 4+ with Kids category eligibility (must not display links to external services, no targeted ads, etc.)
- [ ] Kids Category considerations: cannot include links to web outside app, cannot ask for personal info, no third-party analytics without parental consent
- [ ] App Review notes: explain fully on-device model download (~2GB) on first launch is expected behavior

## Release build command

```bash
cd ios/TinyAyaKids
xcodebuild -scheme TinyAyaKids \
  -configuration Release \
  -destination 'generic/platform=iOS' \
  -allowProvisioningUpdates \
  archive -archivePath build/TinyAyaKids.xcarchive
```

Then export to `.ipa` and upload to App Store Connect via Transporter or `altool`.

## Runtime gotchas for reviewers

- First launch downloads ~2GB TinyAya GGUF model from HuggingFace. Allow 1-3 minutes on first run.
- Whisper + Kokoro models download on first voice use (smaller, ~100-500MB each).
- After initial download, app runs fully offline.
- Memory: ~1.5-2GB peak during inference. On devices with <6GB RAM, expect occasional TTS + LLM memory swaps (already handled gracefully — no user-visible failure).
