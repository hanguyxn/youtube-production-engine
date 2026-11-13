"""
Timestamp Alignment Utility for Ancient Humans YouTube Engine
Converts SRT or VTT captions into standardized [mm:ss] transcript format.
This formats existing cues; it does not perform speech alignment.
Usage:
    python align_timestamps.py input_file.srt --output output_file.txt [--chunk-seconds 5]
"""

import sys
import re
import argparse
import math
from pathlib import Path

# Force UTF-8 stdout for Windows consoles
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')


def parse_time_to_seconds(time_str: str) -> float:
    time_str = time_str.strip().replace(',', '.')
    parts = time_str.split(':')
    if len(parts) == 3:
        h, m, s = parts
        return int(h) * 3600 + int(m) * 60 + float(s)
    elif len(parts) == 2:
        m, s = parts
        return int(m) * 60 + float(s)
    else:
        return float(time_str)

def format_seconds(seconds: float) -> str:
    total_sec = int(round(seconds))
    mins = total_sec // 60
    secs = total_sec % 60
    return f"[{mins:02d}:{secs:02d}]"

def parse_srt_or_vtt(content: str):
    entries = []
    # Match timestamps like 00:00:01,234 --> 00:00:04,567 or 00:01.234 --> 00:04.567
    stamp = r'(?:\d{2,}:)?[0-5]\d:[0-5]\d[,\.]\d{1,3}'
    pattern = re.compile(rf'^({stamp})\s*-->\s*({stamp})(?:\s+.*)?$')

    blocks = re.split(r'\n\s*\n', content)
    for block in blocks:
        lines = [l.strip() for l in block.strip().split('\n') if l.strip()]
        if not lines:
            continue
        if lines[0].startswith(('WEBVTT', 'NOTE', 'STYLE', 'REGION')):
            continue
        indices = [i for i, line in enumerate(lines) if '-->' in line]
        if len(indices) != 1:
            raise ValueError(f"Expected one caption timing line in block: {lines[0]!r}")
        index = indices[0]
        ts_match = pattern.fullmatch(lines[index])
        if not ts_match:
            raise ValueError(f"Invalid caption timing: {lines[index]!r}")
        start_sec = parse_time_to_seconds(ts_match.group(1))
        end_sec = parse_time_to_seconds(ts_match.group(2))
        if end_sec <= start_sec or (entries and start_sec < entries[-1][1]):
            raise ValueError("Caption cues must have positive duration, be ordered, and not overlap.")
        text = ' '.join(re.sub(r'<[^>]+>', '', line) for line in lines[index+1:]).strip()
        if not text:
            raise ValueError(f"Caption at {start_sec} has no text.")
        entries.append((start_sec, end_sec, text))

    return entries

def chunk_entries(entries, min_chunk_seconds=3.0):
    """Combine cues until the current beat reaches the minimum; tail may be shorter."""
    if not math.isfinite(min_chunk_seconds) or min_chunk_seconds <= 0:
        raise ValueError("Minimum chunk duration must be a finite positive number.")
    if not entries:
        return []

    chunked = []
    current_start = entries[0][0]
    current_texts = [entries[0][2]]
    current_end = entries[0][1]

    for start, end, text in entries[1:]:
        # Check if adding this entry would keep the chunk within min duration
        # If current chunk already meets the threshold, flush it first
        if current_end - current_start >= min_chunk_seconds:
            chunked.append((current_start, ' '.join(current_texts)))
            current_start = start
            current_texts = [text]
            current_end = end
        else:
            current_texts.append(text)
            current_end = end

    if current_texts:
        chunked.append((current_start, ' '.join(current_texts)))

    return chunked

def main():
    parser = argparse.ArgumentParser(description="Convert SRT/VTT to [mm:ss] format")
    parser.add_argument("input", help="Path to input .srt or .vtt file")
    parser.add_argument("-o", "--output", help="Path to output .txt file", default=None)
    parser.add_argument("-c", "--chunk-seconds", type=float, default=3.0, help="Minimum seconds per visual beat (default: 3.0s)")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"File not found: {input_path}")
        sys.exit(1)

    content = input_path.read_text(encoding='utf-8-sig')
    try:
        raw_entries = parse_srt_or_vtt(content)
        beats = chunk_entries(raw_entries, args.chunk_seconds)
    except ValueError as e:
        parser.exit(1, f"Error: {e}\n")
    if not raw_entries:
        print("No timestamped subtitles detected. Please check file format.")
        sys.exit(1)

    timestamps = [format_seconds(start) for start, _ in beats]
    if len(set(timestamps)) != len(timestamps):
        parser.exit(1, "Error: duplicate rounded timestamps; increase --chunk-seconds.\n")
    output_lines = [f"{format_seconds(start)} {text}" for start, text in beats]
    result_text = "\n".join(output_lines)

    if args.output:
        out_path = Path(args.output)
        out_path.write_text(result_text, encoding='utf-8')
        print(f"Wrote {len(output_lines)} timestamped lines to {out_path}")
    else:
        print(f"--- Processed {len(output_lines)} Visual Beats ---")
        print(result_text)

if __name__ == "__main__":
    main()
