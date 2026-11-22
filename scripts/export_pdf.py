"""Print generated local HTML to PDF with installed Chromium/Edge.

Requires a local browser; this is optional for running the product/tests.
"""
import argparse
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--browser', help='Absolute path to Chrome/Edge/Chromium')
    args = parser.parse_args()
    candidates = [args.browser, shutil.which('chromium'), shutil.which('google-chrome'),
                  r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
                  r'C:\Program Files\Google\Chrome\Application\chrome.exe']
    browser = next((c for c in candidates if c and Path(c).is_file()), None)
    if not browser:
        parser.error('No Chromium browser found; open docs/report.html and Print to PDF manually.')
    for name in ('report', 'slides'):
        source = ROOT / 'docs' / (name + '.html')
        target = ROOT / 'docs' / (name + '.pdf')
        if not source.exists():
            parser.error('Run python scripts/build_docs.py first.')
        command = [browser, '--headless', '--disable-gpu', '--no-pdf-header-footer',
                   '--disable-extensions', '--no-first-run', '--disable-background-networking',
                   '--user-data-dir=' + str(ROOT / 'docs' / '.browser' / name),
                   '--print-to-pdf=' + str(target), source.as_uri()]
        subprocess.run(command, check=True, timeout=60,
                       creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if not target.exists():
            raise RuntimeError('Browser did not produce ' + str(target))
        print('Created ' + str(target))


if __name__ == '__main__':
    main()
