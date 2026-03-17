# STT & TTS (Mac)

Voice pipeline on Apple Silicon using [mlx-audio](https://github.com/Blaizzy/mlx-audio): **Kokoro** for TTS, **Whisper tiny** for STT. Runs locally on Mac (no Xcode); same setup can be used on mobile via mlx-audio-swift.

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
mlx_audio.stt.generate --model mlx-community/whisper-tiny-asr-fp16 --audio your_file.wav --output-path ./output
```

Add `--stream` for partial results as the file is processed. Add `--format json` for timestamps.

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
| STT        | `mlx_audio.stt.generate --model mlx-community/whisper-tiny-asr-fp16 --audio your_file.wav --output-path ./output` |
