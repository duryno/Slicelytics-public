#!/usr/bin/env python3
"""Build a Slicelytics link for a dataset (and optionally a second one to compare), then print or open it.

The data goes in the URL's #fragment, which browsers never send to a server.
Standard library only.

Examples:
  slicelytics_link.py results.csv --view '{"v":1,"view":"visualize","props":["p95_ms"],"x":"day","chart":"line"}'
  slicelytics_link.py run-41.ndjson --compare run-42.ndjson --open
  slicelytics_link.py data.json --open --app          # macOS: in the installed Slicelytics app
"""

import argparse
import base64
import glob
import gzip
import json
import os
import plistlib
import subprocess
import sys
import urllib.parse

FORMATS = {
    '.json': 'json',
    '.ndjson': 'ndjson',
    '.jsonl': 'ndjson',
    '.csv': 'csv',
    '.toon': 'toon',
}
ROUTES = ('explore', 'compare', 'visualize')

# Measured 2026-09-22 on macOS: a 964 KB link opened via `open` arrived intact, a 1.29 MB one
# failed with "argument list too long" (ARG_MAX is 1 MiB). Chrome itself caps URLs at 2 MB.
MAX_OPEN_CHARS = 900_000
# Every printed character is model output and something the user has to copy.
MAX_PRINT_CHARS = 8_000


def read_dataset(path):
    """Returns (text, format, name) for a data file, decompressing .gz."""
    name = os.path.basename(path)
    stem = name[:-3] if name.endswith('.gz') else name
    ext = os.path.splitext(stem)[1].lower()
    if ext not in FORMATS:
        sys.exit(f'{path}: unsupported format "{ext}" - use one of {", ".join(FORMATS)}')

    opener = gzip.open if name.endswith('.gz') else open
    with opener(path, 'rt', encoding='utf-8') as f:
        return f.read(), FORMATS[ext], stem


def encode(text):
    return base64.urlsafe_b64encode(gzip.compress(text.encode('utf-8'))).decode().rstrip('=')


def parse_view(view):
    """The view as JSON text: given inline, or as a path to a .json file."""
    if view is None:
        return None
    raw = open(view, encoding='utf-8').read() if os.path.isfile(view) else view
    try:
        spec = json.loads(raw)
    except json.JSONDecodeError as e:
        sys.exit(f'--view is not valid JSON: {e}')
    if not isinstance(spec, dict):
        sys.exit('--view must be a JSON object')
    spec.setdefault('v', 1)
    return spec


def find_app_id(base):
    """The Chrome app id of the installed Slicelytics app for this origin (macOS)."""
    host = urllib.parse.urlparse(base).netloc
    for plist_path in glob.glob(
        os.path.expanduser('~/Applications/Chrome Apps.localized/*.app/Contents/Info.plist')
    ):
        with open(plist_path, 'rb') as f:
            info = plistlib.load(f)
        if urllib.parse.urlparse(info.get('CrAppModeShortcutURL', '')).netloc == host:
            return info['CrAppModeShortcutID']
    return None


def open_link(url, base, in_app):
    if len(url) > MAX_OPEN_CHARS:
        sys.exit(
            f'The link is {len(url):,} characters - over the {MAX_OPEN_CHARS:,} that can be passed '
            'to another program. Use the watched folder instead.'
        )

    if in_app:
        app_id = find_app_id(base)
        if not app_id:
            sys.exit(f'No installed Slicelytics app for {base} - drop --app to open it in the browser.')
        # Chrome-internal flag, not a public API - fine locally, may change
        subprocess.run(
            [
                '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
                f'--app-id={app_id}',
                f'--app-launch-url-for-shortcuts-menu-item={url}',
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    elif sys.platform == 'darwin':
        subprocess.run(['open', url], check=True)
    elif sys.platform.startswith('win'):
        os.startfile(url)  # type: ignore[attr-defined]
    else:
        subprocess.run(['xdg-open', url], check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('data', help='dataset file: .json, .ndjson/.jsonl, .csv or .toon, optionally .gz')
    parser.add_argument('--compare', help='a second dataset file, to compare with the first')
    parser.add_argument('--name', help='name shown for the dataset (default: file name)')
    parser.add_argument('--compare-name', help='name shown for the compared dataset (default: file name)')
    parser.add_argument('--view', help='ViewSpec JSON, inline or a path to a .json file')
    parser.add_argument('--base', default='https://slicelytics.com', help='default: %(default)s')
    parser.add_argument('--open', action='store_true', help='open the link instead of printing it')
    parser.add_argument('--app', action='store_true', help='with --open, on macOS: open in the installed app')
    args = parser.parse_args()

    text, fmt, name = read_dataset(args.data)
    params = {'v': 1, 'data': encode(text), 'format': fmt, 'name': args.name or name}
    if args.compare:
        text2, fmt2, name2 = read_dataset(args.compare)
        params.update(compare=encode(text2), compareFormat=fmt2, compareName=args.compare_name or name2)

    spec = parse_view(args.view)
    route = (spec or {}).get('view') or ('compare' if args.compare else 'explore')
    if route not in ROUTES:
        sys.exit(f'"view" must be one of {", ".join(ROUTES)}')

    url = f'{args.base.rstrip("/")}/data/{route}'
    if spec:
        url += '?view=' + urllib.parse.quote(json.dumps(spec, separators=(',', ':')), safe='')
    url += '#' + urllib.parse.urlencode(params)

    print(f'link: {len(url):,} characters', file=sys.stderr)
    if args.open:
        open_link(url, args.base, args.app)
        return

    if len(url) > MAX_PRINT_CHARS:
        print(
            f'warning: over {MAX_PRINT_CHARS:,} characters - open it (--open) or use the watched '
            'folder rather than showing it to the user',
            file=sys.stderr,
        )
    print(url)


if __name__ == '__main__':
    main()
