#!/usr/bin/env python3
import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def fail(msg, detail=None, code=1):
    print(msg, file=sys.stderr)
    if detail:
        print(detail.strip(), file=sys.stderr)
    sys.exit(code)


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def main():
    ap = argparse.ArgumentParser(description='OCR a tweet screenshot for x-research.')
    ap.add_argument('image', help='Path to screenshot image')
    ap.add_argument('--lang', default='eng', help='tesseract language, e.g. eng | chi_sim | chi_tra (default: eng)')
    args = ap.parse_args()

    image = Path(args.image).expanduser()
    if not image.exists():
        fail(f'Image not found: {image}')
    if shutil.which('tesseract') is None:
        fail('Missing dependency: tesseract')

    with tempfile.TemporaryDirectory(prefix='x-ocr-') as tmp:
        outbase = Path(tmp) / 'ocr'
        code, stdout, stderr = run(['tesseract', str(image), str(outbase), '-l', args.lang])
        if code != 0:
            fail('tesseract OCR failed', stderr)
        txt = outbase.with_suffix('.txt')
        if not txt.exists():
            fail('OCR text output not produced')
        text = txt.read_text(errors='ignore').strip()
        if not text:
            fail('OCR produced no readable text')
        print(text)


if __name__ == '__main__':
    main()
