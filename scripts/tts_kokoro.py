"""
Kokoro TTS Voice Generator for Paleon YouTube Engine
Generates voiceover audio from narration script using Kokoro ONNX (am_michael by default).
Model cache is configured by engine.py; invoke that entrypoint.

Usage:
    python tts_kokoro.py --input script_topic.txt --output voiceover.wav [--voice am_michael] [--speed 1.0]
    python tts_kokoro.py --input script_topic.txt  (auto-outputs voiceover_topic.wav)
"""

import sys
import os
import argparse
import re
import math
import tempfile
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from models import ensure_models

MODEL_FILE = None
VOICES_FILE = None

# Available English voices; suitability should be checked with an audition.
VOICES = {
    "am_adam":    "Nam · English US · Adam",
    "am_michael": "Nam · English US · Michael",
    "am_fenrir":  "Nam · English US · Fenrir",
    "am_puck":    "Nam · English US · Puck",
    "af_heart":   "Nữ · English US · Heart",
    "af_sarah":   "Nữ · English US · Sarah",
    "bf_emma":    "Nữ · English UK · Emma",
    "bm_george":  "Nam · English UK · George",
}

DEFAULT_VOICE = "am_michael"
DEFAULT_SPEED = 1.0
SAMPLE_RATE = 24000

# Conservative character bound, not a model token limit.
MAX_CHUNK_CHARS = 400


def download_models():
    # Engine resolves and verifies cache paths before calling synthesis.
    if MODEL_FILE is None or VOICES_FILE is None:
        raise ValueError("Run voice through engine.py to configure the portable model cache.")


def split_into_sentences(text: str) -> list[str]:
    """Split narration without treating common titles or decimal points as stops."""
    marker = "\uE000"
    if marker in text:
        raise ValueError("Script contains reserved sentence-splitting character.")
    protected = re.sub(r'\b(?:Dr|Mr|Mrs|Ms|Prof|St|Jr|Sr|vs|e\.g|i\.e)\.',
                       lambda m: m.group().replace('.', marker), text, flags=re.I)
    protected = re.sub(r'\b[A-Z]\.(?=\s+[A-Z])',
                       lambda m: m.group().replace('.', marker), protected)
    sentences = re.split(r'(?<=[.!?])\s+', protected.strip())
    sentences = [s.replace(marker, '.') for s in sentences]
    return [s.strip() for s in sentences if s.strip()]


def format_timestamp(seconds: float) -> str:
    """Format seconds into [mm:ss] for transcript timeline."""
    total_sec = int(round(seconds))
    mins = total_sec // 60
    secs = total_sec % 60
    return f"[{mins:02d}:{secs:02d}]"


def format_srt_time(seconds: float) -> str:
    """Format seconds into HH:MM:SS,mmm for SRT subtitles."""
    millis = int((seconds - int(seconds)) * 1000)
    total_sec = int(seconds)
    hours = total_sec // 3600
    mins = (total_sec % 3600) // 60
    secs = total_sec % 60
    return f"{hours:02d}:{mins:02d}:{secs:02d},{millis:03d}"


def group_natural_sentences(sentences: list[str]) -> list[str]:
    """
    Groups very tiny fragments (like single words or < 20 chars) with adjacent sentences
    so each visual beat is a natural spoken thought (2-6 seconds).
    """
    beats = []
    buffer = ""

    bounded = []
    for sentence in sentences:
        part = ""
        for word in sentence.split():
            if len(word) > MAX_CHUNK_CHARS:
                raise ValueError("A narration token exceeds the chunk limit; rewrite it before synthesis.")
            if part and len(part) + 1 + len(word) > MAX_CHUNK_CHARS:
                bounded.append(part)
                part = ""
            part = f"{part} {word}".strip()
        if part:
            bounded.append(part)

    for s in bounded:
        s_clean = s.strip()
        if not s_clean:
            continue

        # If buffer is empty, start buffer
        if not buffer:
            buffer = s_clean
        # If current buffer is very short (< 30 chars), append to it
        elif len(buffer) < 30 and len(buffer) + len(s_clean) < 180:
            buffer = f"{buffer} {s_clean}"
        else:
            beats.append(buffer)
            buffer = s_clean

    if buffer:
        beats.append(buffer)

    return beats


def generate_voice(
    input_file: str,
    output_file: str = None,
    voice: str = DEFAULT_VOICE,
    speed: float = DEFAULT_SPEED
):
    """Generate voiceover from script text file."""
    if not input_file:
        raise ValueError("Provide --input with a narration text file.")
    input_path = Path(input_file)
    if not input_path.is_file():
        raise ValueError(f"Script file not found: {input_file}")
    if not math.isfinite(speed) or speed <= 0:
        raise ValueError("Speech speed must be a finite positive number.")
    if voice not in VOICES:
        raise ValueError(f"Unsupported voice: {voice}")
    script_text = input_path.read_text(encoding='utf-8-sig').strip()
    if not script_text:
        raise ValueError(f"Script file is empty: {input_file}")
    chunks = group_natural_sentences(split_into_sentences(script_text))

    # Auto-generate output filename if not provided
    if output_file is None:
        stem = input_path.stem.replace("script_", "voiceover_")
        if stem == input_path.stem:
            stem = f"voiceover_{stem}"
        output_file = str(input_path.parent / f"{stem}.wav")

    output_path = Path(output_file)
    if output_path.suffix.lower() != ".wav":
        raise ValueError("Output must use the .wav extension.")

    # Ensure models are downloaded
    download_models()

    word_count = len(script_text.split())
    est_minutes = word_count / 150  # ~150 words per minute narration

    print(f"\n🎙️  KOKORO TTS — VOICE GENERATION")
    print(f"{'='*50}")
    print(f"📄 Script: {input_path.name} ({word_count} words, ~{est_minutes:.1f} min)")
    print(f"🎤 Voice: {voice} — {VOICES.get(voice, 'Custom')}")
    print(f"⚡ Speed: {speed}x")
    print(f"💾 Output: {output_path}")
    print(f"{'='*50}\n")

    # Import Kokoro
    try:
        from kokoro_onnx import Kokoro
        import soundfile as sf
        import numpy as np
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("   Run: pip install kokoro-onnx soundfile numpy")
        sys.exit(1)

    # Initialize Kokoro
    print("🔄 Loading Kokoro model...")
    kokoro = Kokoro(str(MODEL_FILE), str(VOICES_FILE))
    print("✅ Model loaded.\n")

    # Speech chunks are synthesis units; scene planning may group or split them.
    total_chunks = len(chunks)

    print(f"📝 Processing {total_chunks} speech chunks; use the SRT to plan visual beats separately.\n")

    all_audio = []
    timeline_lines = []
    srt_entries = []
    current_time_sec = 0.0
    last_timestamp = None
    expected_sample_rate = None

    for i, chunk in enumerate(chunks):
        pct = (i + 1) * 100 // total_chunks
        start_sec = current_time_sec
        ts_str = format_timestamp(start_sec)
        if ts_str == last_timestamp:
            raise ValueError("Two speech beats round to the same [mm:ss]. Combine very short sentences or reduce speed, then regenerate. No outputs were written.")
        last_timestamp = ts_str
        print(f"  [{pct:3d}%] {ts_str} Beat {i+1}/{total_chunks}: \"{chunk[:55]}{'...' if len(chunk) > 55 else ''}\"")

        try:
            samples, sample_rate = kokoro.create(
                chunk,
                voice=voice,
                speed=speed,
                lang="en-gb" if voice.startswith('b') else "en-us"
            )
            if len(samples) == 0 or sample_rate <= 0 or not np.isfinite(samples).all():
                raise ValueError("Synthesis returned empty or invalid audio.")
            if expected_sample_rate is not None and sample_rate != expected_sample_rate:
                raise ValueError("Sample rate changed between speech beats.")
            expected_sample_rate = sample_rate
            all_audio.append(samples)
            chunk_duration = len(samples) / sample_rate
            end_sec = start_sec + chunk_duration

            # Record timeline and SRT
            timeline_lines.append(f"{ts_str} {chunk}")
            srt_entries.append(f"{i+1}\n{format_srt_time(start_sec)} --> {format_srt_time(end_sec)}\n{chunk}\n")

            # Add a natural silence gap between sentences (150ms)
            silence = np.zeros(int(sample_rate * 0.15), dtype=samples.dtype)
            all_audio.append(silence)
            current_time_sec = end_sec + 0.15

        except Exception as e:
            raise RuntimeError(f"Synthesis failed at beat {i+1}/{total_chunks}: {chunk[:100]!r}. No outputs were written; fix the cause and retry.") from e

    # Concatenate all audio
    if not all_audio:
        print("❌ No audio generated.")
        sys.exit(1)

    final_audio = np.concatenate(all_audio)
    duration_sec = len(final_audio) / sample_rate
    duration_min = duration_sec / 60
    # Reserve PCM16 headroom with one uniform gain for the entire narration.
    # This prevents conversion clipping, not pre-existing model distortion;
    # it is neither per-chunk normalization nor loudness matching.
    peak = float(np.max(np.abs(final_audio)))
    output_gain = 0.98 / peak if peak > 0.98 else 1.0
    if output_gain < 1.0:
        final_audio = final_audio * output_gain
    print(f"PCM16 output gain: {output_gain:.6f} ({20 * math.log10(output_gain):.2f} dB); input sample peak: {peak:.6f}")

    # Prepare all files before replacing existing outputs. Synthesis failures above
    # never touch prior files. Each final replacement is atomic on the same volume.
    output_path.parent.mkdir(parents=True, exist_ok=True)
    stem_name = output_path.stem.replace("voiceover_", "")
    transcript_path = output_path.parent / f"transcript_timestamped_{stem_name}.txt"
    srt_path = output_path.parent / f"voiceover_{stem_name}.srt"
    with tempfile.TemporaryDirectory(prefix=".tts-", dir=output_path.parent) as staging:
        stage = Path(staging)
        sf.write(str(stage / output_path.name), final_audio, sample_rate, subtype="PCM_16")
        (stage / transcript_path.name).write_text("\n".join(timeline_lines) + "\n", encoding='utf-8')
        (stage / srt_path.name).write_text("\n".join(srt_entries) + "\n", encoding='utf-8')
        for target in [output_path, transcript_path, srt_path]:
            os.replace(stage / target.name, target)

    print(f"\n{'='*60}")
    print(f"✅ VOICE & TIMELINE GENERATION COMPLETE!")
    print(f"🎙️ Audio File:       {output_path}")
    print(f"📄 Rounded transcript: {transcript_path} ({len(timeline_lines)} speech chunks; SRT supplies precise boundaries)")
    print(f"⏱️ SRT Subtitles:    {srt_path}")
    print(f"⏳ Total Duration:   {int(duration_min)}:{int(duration_sec % 60):02d} ({duration_sec:.1f}s)")
    print(f"📊 Sample Rate:      {sample_rate} Hz")
    print(f"{'='*60}")

    return str(output_path), str(transcript_path), str(srt_path), duration_sec


def main():
    parser = argparse.ArgumentParser(
        description="Kokoro TTS Voice Generator for Paleon YouTube Engine"
    )
    parser.add_argument("--input", "-i", required=False, default=None,
                        help="Path to narration script .txt file")
    parser.add_argument("--output", "-o", default=None,
                        help="Output .wav file path (auto-generated if omitted)")
    parser.add_argument("--voice", "-v", default=DEFAULT_VOICE,
                        choices=list(VOICES.keys()),
                        help=f"Voice to use (default: {DEFAULT_VOICE})")
    parser.add_argument("--speed", "-s", type=float, default=DEFAULT_SPEED,
                        help=f"Speech speed multiplier (default: {DEFAULT_SPEED})")
    parser.add_argument("--list-voices", action="store_true",
                        help="List available voices and exit")

    args = parser.parse_args()

    if args.list_voices:
        print("Available Kokoro Voices:")
        for vid, desc in VOICES.items():
            marker = " ← DEFAULT" if vid == DEFAULT_VOICE else ""
            print(f"  {vid:15s}  {desc}{marker}")
        sys.exit(0)

    try:
        generate_voice(input_file=args.input, output_file=args.output,
                       voice=args.voice, speed=args.speed)
    except (ValueError, RuntimeError, OSError) as e:
        parser.exit(1, f"Error: {e}\n")


if __name__ == "__main__":
    main()
