"""Build course reports/slides without changing global TeX settings."""
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
tex = shutil.which('xelatex')
tectonic = shutil.which('tectonic')
if not tectonic:
    portable = ROOT / '.tools' / 'tectonic-msvc' / 'tectonic.exe'
    if portable.exists():
        tectonic = str(portable)
targets = [ROOT/'reports'/'reading.tex', ROOT/'reports'/'project.tex',
           ROOT/'presentations'/'reading-slides.tex', ROOT/'presentations'/'project-slides.tex']
if not tex and not tectonic:
    sys.exit('Install TeX Live/MiKTeX with XeLaTeX, or put tectonic on PATH, then rerun.')
for target in targets:
    if not target.exists():
        sys.exit(f'Missing source: {target.name}')
    if tex:
        cmd = [tex, '-interaction=nonstopmode', '-halt-on-error', target.name]
        subprocess.run(cmd, cwd=target.parent, check=True)
        if '\\bibliography{' in target.read_text(encoding='utf-8'):
            bibtex = shutil.which('bibtex')
            if not bibtex:
                sys.exit('bibtex is required for report references.')
            subprocess.run([bibtex, target.stem], cwd=target.parent, check=True)
        subprocess.run(cmd, cwd=target.parent, check=True)
        subprocess.run(cmd, cwd=target.parent, check=True)
    else:
        subprocess.run([tectonic, '--keep-logs', target.name], cwd=target.parent, check=True)
    print('Built', target.relative_to(ROOT).with_suffix('.pdf'))
