"""Import only the supplied archive; never fetch or follow source URLs."""
from datetime import datetime
import hashlib
import json
from pathlib import PurePosixPath
import zipfile

from src.data_utils import ROOT, atomic_write, read_json, write_json

ARCHIVE = ROOT / 'k4-day8-data.zip'


def archive_records():
    """Validate all inputs before writing anything; ignore macOS and derived files."""
    records = {}
    with zipfile.ZipFile(ARCHIVE) as archive:
        for info in archive.infolist():
            name = PurePosixPath(info.filename)
            if info.is_dir() or not info.filename.startswith('data/landing/'):
                continue
            if any(part.startswith('.') for part in name.parts):
                continue
            if len(name.parts) != 4 or name.parts[2] not in {'legal', 'news'}:
                raise ValueError(f'Unexpected archive member: {info.filename}')
            if info.filename in records:
                raise ValueError(f'Duplicate archive member: {info.filename}')
            content = archive.read(info)
            if name.parts[2] == 'news':
                if name.suffix != '.json':
                    raise ValueError(f'Expected article JSON: {name}')
                article = json.loads(content.decode('utf-8'))
                for key in ('url', 'title', 'date_crawled', 'content_markdown'):
                    if not isinstance(article.get(key), str) or not article[key].strip():
                        raise ValueError(f'Missing {key}: {name}')
                datetime.fromisoformat(article['date_crawled'])
            elif name.suffix.lower() not in {'.pdf', '.doc', '.docx'}:
                raise ValueError(f'Unsupported policy input: {name}')
            elif name.suffix.lower() == '.pdf' and not content.startswith(b'%PDF-'):
                raise ValueError(f'Invalid PDF: {name}')
            records[info.filename] = content
    for branch in ('legal', 'news'):
        if not any(f'/landing/{branch}/' in name for name in records):
            raise ValueError(f'Archive has no {branch} inputs')
    return records


def import_branch(branch):
    records = archive_records()
    archive_sha = hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()
    verified_sources = read_json(ROOT / 'docs/public_sources.json')
    for member, content in sorted(records.items()):
        if PurePosixPath(member).parts[2] != branch:
            continue
        path = ROOT / member
        atomic_write(path, content)
        if branch == 'legal':
            source = verified_sources.get(path.name, {})
            sha = hashlib.sha256(content).hexdigest()
            if source.get('sha256') != sha:
                raise ValueError(f'Public-source mapping not verified for ZIP PDF: {path.name}')
            write_json(path.with_suffix('.metadata.json'), {
                'title': path.stem,
                'url': source['url'],
                'date_crawled': None,
                'metadata_note': 'URL verified against public PDF by SHA-256; archive crawl date unknown.',
                'source_verification': source['verification'],
                'source_verified_on': source['verified_on'],
                'sha256': sha,
                'source_archive': ARCHIVE.name,
                'archive_sha256': archive_sha,
                'archive_member': member,
            })
        print(f'Imported: {member}')


def validate_landing():
    records = archive_records()
    expected = set(records)
    expected.update(str(PurePosixPath(n).with_suffix('.metadata.json'))
                    for n in records if '/legal/' in n)
    actual = {p.relative_to(ROOT).as_posix()
              for p in (ROOT / 'data/landing').rglob('*')
              if p.is_file() and not p.name.startswith('.')}
    if actual != expected:
        raise ValueError(f'Landing differs from ZIP: missing={expected - actual}, extra={actual - expected}')
    for member, content in records.items():
        if (ROOT / member).read_bytes() != content:
            raise ValueError(f'Landing content differs from ZIP: {member}')
    return records


def main():
    import_branch('legal')
    import_branch('news')
    from src.task3_convert_markdown import convert_all
    convert_all()


if __name__ == '__main__':
    main()
