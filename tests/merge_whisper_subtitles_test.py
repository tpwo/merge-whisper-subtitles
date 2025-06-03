from __future__ import annotations

from pathlib import Path

from merge_whisper_subtitles import main


def test_compare_outputs(tmpdir):
    out = Path(tmpdir, 'output.srt')
    main(['testing/input.words.srt', '--output-file', out.as_posix()])
    expected = Path('testing', 'expected.srt')
    assert out.read_text() == expected.read_text()
