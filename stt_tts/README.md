# STT & TTS on Mac (Kokoro + Whisper)

Runs **speech-to-text (STT)** and **text-to-speech (TTS)** on Apple Silicon via [mlx-audio](https://github.com/Blaizzy/mlx-audio). No Xcode needed for Mac. TTS: **Kokoro**. STT: **Whisper** (default). For the voice pipeline (child speaks → STT → TinyAya → TTS → device speaks), run these on Mac first; the same models can be used on mobile (e.g. via Xcode / mlx-audio-swift).

---

## Prerequisites

- Apple Silicon Mac (M1–M4), Python, Hugging Face token in `.env` (see below).

---

## Setup

From the **repository root** (parent of this folder):

```bash
python3 -m venv .venv
.venv/bin/pip install "mlx-audio[tts,stt]"
```

Copy this folder’s `.env.example` to `.env` in the **repo root** and set `HF_TOKEN=your_token` ([get one](https://huggingface.co/settings/tokens)). Optional: `brew install ffmpeg` for MP3/FLAC.

---

## Run TTS

```bash
source .venv/bin/activate && source .env
mlx_audio.tts.generate --model mlx-community/Kokoro-82M-bf16 --text 'Hello!' --lang_code a --play
```

Save to folder: add `--output_path ./my_audio`. Other voices: `--voice af_heart` (see mlx-audio docs).

---

## Run STT

```bash
source .venv/bin/activate && source .env
mlx_audio.stt.generate --model mlx-community/whisper-large-v3-turbo-asr-fp16 --audio your_file.wav --output-path ./output
```

Add `--stream` to get partial results as the file is processed. Add `--format json` for timestamps.

**When to use Voxtral Realtime instead of Whisper:** For low-latency, conversational use (e.g. live back-and-forth with a kid), **Voxtral Realtime** is better—it’s built for streaming and gives words as the user speaks. Use it if Whisper’s delay feels too high. Model: `mlx-community/Voxtral-Mini-4B-Realtime-2602-4bit` (or `-fp16`). Same CLI with `--model <voxtral-model>` and `--stream`; it’s heavier (4B) so check performance on your device.

---

## Troubleshooting

- **Command not found:** Run `source .venv/bin/activate` first (you should see `(.venv)` in the prompt).
- **HF_TOKEN warning:** Set `export HF_TOKEN=your_token` in `.env` (no space after `=`) and run `source .env`.
- **externally-managed-environment:** Use `.venv/bin/pip` or activate the venv before using `pip`.

---

## Quick reference

| Task   | Command |
|--------|---------|
| TTS (play) | `mlx_audio.tts.generate --model mlx-community/Kokoro-82M-bf16 --text 'Your text' --lang_code a --play` |
| TTS (save) | `mlx_audio.tts.generate --model mlx-community/Kokoro-82M-bf16 --text 'Your text' --lang_code a --output_path ./my_audio` |
| STT        | `mlx_audio.stt.generate --model mlx-community/whisper-large-v3-turbo-asr-fp16 --audio your_file.wav --output-path ./output` |
