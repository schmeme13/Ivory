"""Fetch the authors' checkpoint; validate against Zenodo's published checksum."""
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
target = ROOT / 'data' / 'models' / 'piano.pth'
target.parent.mkdir(parents=True, exist_ok=True)
with urllib.request.urlopen('https://zenodo.org/api/records/4034264', timeout=60) as response:
    record = json.load(response)
entry = next(f for f in record['files'] if f['key'].endswith('.pth'))
algorithm, expected = entry['checksum'].split(':', 1)
def checksum(path):
    digest = hashlib.new(algorithm)
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()
if target.exists() and checksum(target) == expected:
    print('Verified model is already installed.')
else:
    temp = target.with_suffix('.download')
    print('Downloading the research checkpoint (about 165 MB)...', flush=True)
    urllib.request.urlretrieve(entry['links']['self'], temp)
    if checksum(temp) != expected:
        temp.unlink(missing_ok=True)
        raise RuntimeError('Checkpoint checksum did not match Zenodo.')
    temp.replace(target)
    (target.parent / 'source.json').write_text(json.dumps({'record': record['id'], 'file': entry['key'], 'checksum': entry['checksum']}, indent=2))
    print('Model downloaded and verified.')
