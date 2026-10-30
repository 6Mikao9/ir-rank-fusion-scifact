"""Download the original BEIR SciFact archive and verify its published MD5."""
import hashlib
import pathlib
import urllib.request
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
URL = 'https://public.ukp.informatik.tu-darmstadt.de/thakur/BEIR/datasets/scifact.zip'
MD5 = '5f7d1de60b170fc8027bb7898e2efca1'
dest = ROOT / 'data'
dest.mkdir(exist_ok=True)
archive = dest / 'scifact.zip'
if not archive.exists():
    print('Downloading', URL)
    urllib.request.urlretrieve(URL, archive)
digest = hashlib.md5(archive.read_bytes()).hexdigest()
if digest != MD5:
    raise RuntimeError(f'Archive checksum mismatch: {digest}; expected {MD5}')
with zipfile.ZipFile(archive) as z:
    for member in z.infolist():
        target = (dest / member.filename).resolve()
        if not target.is_relative_to(dest.resolve()):
            raise RuntimeError('Unsafe archive member')
        if not target.exists():
            z.extract(member, dest)
print('Verified and extracted SciFact at', dest / 'scifact')
