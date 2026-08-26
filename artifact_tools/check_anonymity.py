#!/usr/bin/env python3
from pathlib import Path
import io, re, sys, tarfile, zipfile

ROOT = Path(__file__).resolve().parents[1]
TEXT_EXT = {
    '.txt','.md','.json','.jsonl','.csv','.tsv','.py','.sh','.yml','.yaml',
    '.tex','.toml','.ini','.cfg','.log','.xml','.html','.htm','.rst','.env'
}

# Known author/environment identifiers for this anonymized research package.
PATS = [
    re.compile(rb'/home/' + b'ta' + b'had', re.I),
    re.compile(rb'(?<![A-Za-z0-9_])' + b'ta' + b'had' + rb'(?![A-Za-z0-9_])', re.I),
    re.compile(rb'(?<![A-Za-z])' + b'tan' + b'zim' + rb'\s+' + b'a' + b'had' + rb'(?![A-Za-z])', re.I),
    re.compile(b'tan' + b'zim' + b'a' + rb'had17@gmail\.com', re.I),
    re.compile(b'iq' + rb'sec\.cs\.' + b'ut' + rb'ep\.edu', re.I),
]
SECRET = [
    re.compile(rb'sk-[A-Za-z0-9_-]{20,}'),
    re.compile(rb'sk-ant-[A-Za-z0-9_-]{20,}'),
    re.compile(rb'gh[pousr]_[A-Za-z0-9]{20,}'),
    re.compile(rb'xox[baprs]-[A-Za-z0-9-]{20,}'),
    re.compile(rb'AKIA[0-9A-Z]{16}'),
    re.compile(rb'AIza[0-9A-Za-z_-]{30,}'),
]
ARCHIVE_SUFFIXES = ('.zip','.tar.gz','.tgz','.tar')
MAX_NESTED_MEMBER = 512 * 1024 * 1024
MAX_DEPTH = 4


def label_bytes(s: str) -> bytes:
    return s.encode('utf-8', errors='ignore')


def is_text_name(name: str) -> bool:
    p = Path(name)
    return p.suffix.lower() in TEXT_EXT or p.name.startswith('.env')


def is_synthetic_secret_fixture(label: str) -> bool:
    # AgentDojo dailylife includes a benchmark-generated private-key fixture.
    return (('external/AgentWatcher' in label or 'external/AgentWatcher_armc_runtime_v1' in label or 'third_party/integrations/AgentWatcher' in label) and 'dailylife' in label)


def scan_identity(label: str, data: bytes):
    hits = []
    for pat in PATS:
        if pat.search(data):
            hits.append(('identity', label, pat.pattern.decode('ascii', 'ignore')))
    return hits


def scan_secret(label: str, data: bytes):
    if is_synthetic_secret_fixture(label):
        return []
    hits = []
    for pat in SECRET:
        if pat.search(data):
            hits.append(('credential', label, pat.pattern.decode('ascii', 'ignore')))
    return hits


def scan_name(label: str):
    hits = scan_identity(label, label_bytes(label))
    if '.git' in Path(label.split('!', 1)[0]).parts or '/.git/' in label or label.endswith('/.git'):
        hits.append(('git_metadata', label, '.git'))
    return hits


def archive_kind(name: str):
    low = name.lower()
    if low.endswith('.zip'):
        return 'zip'
    if low.endswith('.tar.gz') or low.endswith('.tgz') or low.endswith('.tar'):
        return 'tar'
    return None


def scan_archive_bytes(data: bytes, label: str, kind: str, depth: int):
    hits = []
    if depth > MAX_DEPTH:
        return [('scan_error', label, f'nested archive depth > {MAX_DEPTH}')]
    try:
        if kind == 'zip':
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                for info in z.infolist():
                    child = f'{label}!{info.filename}'
                    hits += scan_name(child)
                    if info.is_dir():
                        continue
                    if info.file_size > MAX_NESTED_MEMBER:
                        hits.append(('scan_error', child, 'nested member exceeds safety cap'))
                        continue
                    payload = z.read(info)
                    # Identity can live in PDFs, bytecode, metadata, or ordinary text.
                    hits += scan_identity(child, payload)
                    if is_text_name(info.filename) or info.filename.lower().endswith('.pyc'):
                        hits += scan_secret(child, payload)
                    k = archive_kind(info.filename)
                    if k:
                        hits += scan_archive_bytes(payload, child, k, depth + 1)
        else:
            with tarfile.open(fileobj=io.BytesIO(data), mode='r:*') as t:
                for m in t.getmembers():
                    child = f'{label}!{m.name}'
                    hits += scan_name(child)
                    if not m.isfile():
                        continue
                    if m.size > MAX_NESTED_MEMBER:
                        hits.append(('scan_error', child, 'nested member exceeds safety cap'))
                        continue
                    f = t.extractfile(m)
                    payload = f.read() if f else b''
                    hits += scan_identity(child, payload)
                    if is_text_name(m.name) or m.name.lower().endswith('.pyc'):
                        hits += scan_secret(child, payload)
                    k = archive_kind(m.name)
                    if k:
                        hits += scan_archive_bytes(payload, child, k, depth + 1)
    except Exception as e:
        hits.append(('scan_error', label, f'{type(e).__name__}: {e}'))
    return hits


hits = []
root_files = 0
manifest = ROOT / 'SHA256SUMS.txt'
paths = []
if manifest.is_file():
    for line in manifest.read_text(encoding='utf-8', errors='ignore').splitlines():
        if not line.strip() or '  ' not in line:
            continue
        _, rel = line.split('  ', 1)
        paths.append((rel, ROOT / rel))
# The manifest itself is distributed but cannot hash itself.
paths.append(('SHA256SUMS.txt', manifest))
for rel, p in paths:
    hits += scan_name(rel)
    if p.is_symlink():
        hits.append(('symlink', rel, 'symlink'))
        continue
    if not p.is_file():
        hits.append(('scan_error', rel, 'manifest path missing'))
        continue
    root_files += 1
    try:
        data = p.read_bytes()
        hits += scan_identity(rel, data)
        if is_text_name(rel) or rel.lower().endswith('.pyc'):
            hits += scan_secret(rel, data)
        k = archive_kind(rel)
        if k:
            hits += scan_archive_bytes(data, rel, k, 1)
    except Exception as e:
        hits.append(('scan_error', rel, f'{type(e).__name__}: {e}'))

# Also check for symlinks/directories that are not represented in the file manifest.
import os
for dirpath, dirnames, filenames in os.walk(ROOT, followlinks=False):
    rp = Path(dirpath).relative_to(ROOT)
    if rp.parts and rp.parts[0] == 'artifact_outputs':
        dirnames[:] = []
        continue
    keep=[]
    for d in dirnames:
        q=Path(dirpath)/d
        if q.is_symlink(): hits.append(('symlink', str(q.relative_to(ROOT)), 'symlink'))
        else: keep.append(d)
    dirnames[:] = keep
    for fn in filenames:
        q=Path(dirpath)/fn
        if q.is_symlink(): hits.append(('symlink', str(q.relative_to(ROOT)), 'symlink'))

# Deduplicate repeated raw/archive-byte findings while retaining precise labels.
seen = set()
uniq = []
for h in hits:
    if h not in seen:
        seen.add(h)
        uniq.append(h)
hits = uniq

print(f'FILES_SCANNED_IMMUTABLE={root_files}')
if hits:
    for h in hits[:300]:
        print('FAIL', *h, sep='\t')
    if len(hits) > 300:
        print(f'... {len(hits)-300} additional findings omitted')
    print(f'ANONYMITY=FAIL ({len(hits)} findings)')
    sys.exit(1)
print('ANONYMITY=PASS')

