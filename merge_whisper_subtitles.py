from __future__ import annotations

import argparse
import re
from datetime import timedelta
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('input_file', help='input srt file with words')
    parser.add_argument('-o', '--output-file', help='output file name')
    args = parser.parse_args(argv)

    with open(args.input_file) as f:
        srt_text = f.read()

    segments = parse_srt(srt_text)
    grouped = group_and_fix_segments(segments)
    output_srt = render_srt(grouped)

    if not args.output_file:
        output_file = Path(args.input_file).stem + '_merged.srt'
    else:
        output_file = args.output_file

    with open(output_file, 'w+') as f:
        f.write(output_srt)

    return 0


def parse_srt(srt_str):
    re.compile(r'(\d+)\n([\d:,]+) --> ([\d:,]+)\n(.+)', re.DOTALL)
    entries = []
    blocks = srt_str.strip().split('\n\n')
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) < 3:
            continue
        index = int(lines[0])
        start, end = lines[1].split(' --> ')
        text = ' '.join(lines[2:])
        entries.append(
            {
                'index': index,
                'start': parse_timestamp(start),
                'end': parse_timestamp(end),
                'text': text,
            }
        )
    return entries


def parse_timestamp(ts):
    h, m, s_ms = ts.split(':')
    s, ms = s_ms.split(',')
    return timedelta(
        hours=int(h), minutes=int(m), seconds=int(s), milliseconds=int(ms)
    )


def format_timestamp(td):
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    milliseconds = int(td.microseconds / 1000 + td.seconds * 1000)
    milliseconds = (
        td.total_seconds() * 1000
        - (hours * 3600 + minutes * 60 + seconds) * 1000
    )
    return f'{hours:02}:{minutes:02}:{seconds:02},{int(milliseconds):03}'


def group_and_fix_segments(
    segments,
    max_phrase_duration=timedelta(seconds=3),
    min_phrase_duration=timedelta(milliseconds=500),
    max_pause=timedelta(milliseconds=400),
):
    grouped = []
    current_group = []
    group_start = None
    previous_word = None

    def flush_group():
        if not current_group:
            return
        start_time = current_group[0]['start']
        end_time = current_group[-1]['end']
        duration = end_time - start_time

        # Clamp duration
        if duration < min_phrase_duration:
            end_time = start_time + min_phrase_duration
        elif duration > max_phrase_duration:
            end_time = start_time + max_phrase_duration

        # Redistribute timings evenly
        step = (end_time - start_time) / len(current_group)
        for i, word in enumerate(current_group):
            word['start'] = start_time + i * step
            word['end'] = word['start'] + step

        grouped.append(current_group.copy())

    for word in segments:
        # Fix glitched word
        duration = word['end'] - word['start']
        if duration > timedelta(seconds=2):
            word['end'] = word['start'] + timedelta(milliseconds=400)

        # Detect long pause between words
        if (
            previous_word
            and (word['start'] - previous_word['end']) > max_pause
        ):
            flush_group()
            current_group = []
            group_start = None

        if not current_group:
            current_group = [word]
            group_start = word['start']
        else:
            current_group.append(word)

        # Phrase duration limit
        if word['end'] - group_start >= max_phrase_duration:
            flush_group()
            current_group = []
            group_start = None

        previous_word = word

    if current_group:
        flush_group()

    # Ensure no overlaps
    for i in range(1, len(grouped)):
        prev = grouped[i - 1][-1]['end']
        if grouped[i][0]['start'] < prev:
            shift = prev - grouped[i][0]['start']
            for word in grouped[i]:
                word['start'] += shift
                word['end'] += shift

    return grouped


def render_srt(groups):
    lines = []
    for i, group in enumerate(groups, 1):
        start = format_timestamp(group[0]['start'])
        end = format_timestamp(group[-1]['end'])
        text = ' '.join([s['text'] for s in group])
        lines.append(f'{i}\n{start} --> {end}\n{text}\n')
    return '\n'.join(lines)


if __name__ == '__main__':
    raise SystemExit(main())
