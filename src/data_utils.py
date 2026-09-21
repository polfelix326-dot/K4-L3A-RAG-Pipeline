"""Shared deterministic I/O for the data checkpoint."""
from datetime import datetime, timezone
import json
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
import requests

ROOT = Path(__file__).resolve().parent.parent
USER_AGENT = 'UETDataLearningBot/1.0'
_ROBOTS = {}

def now():
    return datetime.now(timezone.utc).isoformat()

def fetch(url):
    origin = '{0.scheme}://{0.netloc}'.format(urlparse(url))
    if origin not in _ROBOTS:
        r = requests.get(origin + '/robots.txt', headers={'User-Agent': USER_AGENT}, timeout=(15, 60))
        parser = RobotFileParser()
        if r.status_code == 404:
            parser.parse([])
        else:
            r.raise_for_status()
            if 'text/html' in r.headers.get('Content-Type', ''):
                raise ValueError(f'Unexpected robots response: {origin}')
            parser.parse(r.text.splitlines())
        _ROBOTS[origin] = parser
    if not _ROBOTS[origin].can_fetch(USER_AGENT, url):
        raise ValueError(f'robots.txt disallows: {url}')
    r = requests.get(url, headers={'User-Agent': USER_AGENT}, timeout=(15, 60))
    r.raise_for_status()
    return r

def atomic_write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() == content:
        return
    temp = path.with_suffix(path.suffix + '.tmp')
    try:
        temp.write_bytes(content)
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)

def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))

def write_json(path, value):
    atomic_write(path, (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
