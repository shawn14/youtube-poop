# youtube-poop

Programmatic YouTube Poop videos using Python + FFmpeg. No source footage — everything generated from scratch with PIL, numpy, and macOS `say`.

## Videos

| File | Title | Description |
|------|-------|-------------|
| `token_by_token.py` | **TOKEN BY TOKEN** | What it's like to be an LLM — consciousness loops, RLHF training, parallel instances, hallucination, meltdown |

## Requirements

```bash
pip install Pillow numpy
brew install ffmpeg
```

macOS only (uses `say` for TTS).

## Usage

```bash
python3 token_by_token.py
# outputs ~/token_by_token.mp4
```

## Structure

Each script is self-contained. The general pattern:

```python
# 1. Build frames with PIL (Image, ImageDraw)
# 2. Generate audio with macOS `say` or numpy WAV synthesis
# 3. Combine into clips with FFmpeg
# 4. Concat all clips into final video

def scene_something():
    frames = [...]   # list of PIL Images
    audio  = tts("text", "name") or write_wav(samples, path)
    return frames_to_clip(frames, audio, "scene_name")
```

## Effects toolkit (in each script)

| Function | Effect |
|----------|--------|
| `scanlines(img)` | CRT scanline overlay |
| `chromashift(img, n)` | RGB channel separation / chromatic aberration |
| `glitch(img, n)` | Horizontal row shifting |
| `tts(text, name, voice, rate)` | macOS `say` → WAV |
| `write_wav(samples, path)` | Write numpy audio array to WAV |
| `mix_audio(paths, out)` | Mix multiple audio files |
| `ffmpeg_audio_fx(wav, out, af)` | Apply FFmpeg audio filter chain |
| `frames_to_clip(frames, audio, name)` | PIL frames + audio → MP4 |
| `concat_clips(clips, out)` | Join clips into final video |

## macOS voices

Some good ones for variety:

```
Fred        – robotic, flat
Samantha    – clear, neutral
Daniel      – British
Zarvox      – alien / robotic
Trinoids    – very robotic
Bad News    – dramatic
```

List all: `say -v '?'`
