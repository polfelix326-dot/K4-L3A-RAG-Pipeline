"""Regression checks for the ZIP-only corpus and source traceability."""
from datetime import datetime
import hashlib
import json
from pathlib import Path

import pytest

from src.import_archive import ARCHIVE, archive_records, main, validate_landing
from src.task3_convert_markdown import article_body, convert_all

ROOT = Path(__file__).resolve().parents[1]


def metadata(path):
    front, body = path.read_text(encoding='utf-8').split('---\n', 2)[1:]
    return {k: json.loads(v) for k, v in (line.split(': ', 1) for line in front.strip().splitlines())}, body


def test_landing_is_exactly_the_supplied_archive():
    records = validate_landing()
    assert sum('/legal/' in name for name in records) == 3
    assert sum('/news/' in name for name in records) == 6
    outputs = {ROOT / name.replace('/landing/', '/standardized/').rsplit('.', 1)[0] for name in records}
    assert {p.with_suffix('') for p in (ROOT / 'data/standardized').rglob('*.md')} == outputs


def test_every_markdown_has_verified_landing_provenance():
    archive_sha = hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()
    for path in (ROOT / 'data/standardized').glob('*/*.md'):
        meta, body = metadata(path)
        landing = ROOT / meta['source_file']
        assert meta['source_sha256'] == hashlib.sha256(landing.read_bytes()).hexdigest()
        assert meta['archive_member'] == meta['source_file']
        assert meta['archive_sha256'] == archive_sha
        assert len(body.strip()) >= 200
        if path.parent.name == 'news':
            original = json.loads(landing.read_text(encoding='utf-8'))
            assert meta['url'] == original['url']
            assert meta['date_crawled'] == original['date_crawled']
            datetime.fromisoformat(meta['date_crawled'])
        else:
            verified = json.loads((ROOT / 'docs/public_sources.json').read_text(encoding='utf-8'))[landing.name]
            assert meta['url'] == verified['url']
            assert meta['source_sha256'] == verified['sha256']
            assert meta['date_crawled'] is None


def test_pipeline_is_offline_and_byte_identical_on_rerun(monkeypatch):
    def no_network(*args, **kwargs):
        raise AssertionError('ZIP pipeline must not access the network')
    monkeypatch.setattr('requests.sessions.Session.request', no_network)
    files = [p for p in (ROOT / 'data').rglob('*') if p.is_file()]
    before = {p: p.read_bytes() for p in files}
    main()
    assert {p: p.read_bytes() for p in (ROOT / 'data').rglob('*') if p.is_file()} == before


def test_news_body_removes_navigation_and_retains_source_span():
    for path in (ROOT / 'data/standardized/news').glob('*.md'):
        meta, body = metadata(path)
        original = json.loads((ROOT / meta['source_file']).read_text(encoding='utf-8'))
        selected, start, end = article_body(original['content_markdown'])
        assert (start, end) == (meta['content_start_line'], meta['content_end_line'])
        assert selected == '\n'.join(original['content_markdown'].splitlines()[start - 1:end])
        assert 'Bài viết liên quan' not in body
        assert 'Bài viết cùng chủ đề' not in body
        assert 'Bỏ qua đến nội dung chính' not in body
    kanazawa = (ROOT / 'data/standardized/news/article_01.md').read_text(encoding='utf-8')
    assert '80.000 JPY/tháng' in kanazawa
    assert '21/09/2026' in kanazawa


def test_converter_rejects_non_archive_landing(monkeypatch, tmp_path):
    import src.import_archive as importer
    monkeypatch.setattr(importer, 'ROOT', tmp_path)
    for name, content in archive_records().items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    extra = tmp_path / 'data/landing/news/outside.json'
    extra.write_text('{}')
    with pytest.raises(ValueError, match='extra='):
        validate_landing()


def test_pdf_table_keeps_level_score_relationship():
    text = (ROOT / 'data/standardized/legal/1011.md').read_text(encoding='utf-8')
    for level, ielts, toefl, aptis, vstep in [('3', '4.5', '42', 'B1', '4.0'), ('4', '5.5', '72', 'B2', '6.0'), ('5', '7.0', '95', 'C1', '8.5')]:
        row = next(line for line in text.splitlines() if line.startswith(f'| Bậc {level} | {ielts} |'))
        assert f'| {toefl} iBT | {aptis} |' in row
        assert f'VSTEP.3-5 ({vstep})' in row
