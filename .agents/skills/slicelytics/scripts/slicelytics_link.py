#!/usr/bin/env python3
"""Build a Slicelytics link for a dataset (and optionally a second one to compare), then print or open it.

The data goes in the URL's #fragment, which browsers never send to a server. It's compressed with
Zstandard where this Python has it (3.14+, or the backports.zstd package), else gzip, and stored
column by column when that makes the link shorter. Standard library only.

Examples:
  slicelytics_link.py results.csv --view '{"v":1,"view":"visualize","props":["p95_ms"],"x":"day","chart":"line"}'
  slicelytics_link.py run-41.ndjson --compare run-42.ndjson --open
  slicelytics_link.py data.json --open --app          # macOS: in the installed Slicelytics app
"""

import argparse
import base64
import csv
import glob
import gzip
import io
import json
import os
import plistlib
import re
import subprocess
import sys
import urllib.parse
from datetime import datetime, timedelta, timezone

try:
    from compression import zstd  # Python 3.14+
except ImportError:
    try:
        from backports import zstd  # the same module for older Pythons, if installed
    except ImportError:
        zstd = None

FORMATS = {
    '.json': 'json',
    '.ndjson': 'ndjson',
    '.jsonl': 'ndjson',
    '.csv': 'csv',
    '.tsv': 'tsv',
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


def encode(text, fmt):
    """Returns (data, format) for a link: the text as it is, or column by column, whichever is shorter."""
    candidates = [(text, fmt)]
    columns = to_columns(text, fmt)
    if columns:
        candidates.append((columns, 'columns'))
    return min(((compress(t), f) for t, f in candidates), key=lambda c: len(c[0]))


def compress(text):
    data = text.encode('utf-8')
    data = zstd.compress(data, level=19) if zstd else gzip.compress(data)
    return base64.urlsafe_b64encode(data).decode().rstrip('=')


# The `columns` format: a list of items stored column by column, which compresses better.
# {"rows": N, "columns": [{"name": ..., "values" | "delta" (+ "time") | "object": ..., "absent": [rows]}]},
# plus "csv" when the columns rebuild a CSV or TSV file's text. Values stay exactly as they are: what
# can't be stored exactly isn't stored as columns (None), and the text goes as it is.

MAX_SAFE_INTEGER = 2**53 - 1
EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
TIME_FORMATS = {
    'ms': re.compile(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z'),
    's': re.compile(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ'),
    'date': re.compile(r'\d{4}-\d\d-\d\d'),
}


def to_columns(text, fmt):
    """The text as a `columns` document, or None if it isn't a list of objects or a CSV/TSV it can rebuild exactly."""
    if fmt in ('csv', 'tsv'):
        return delimited_columns(text, ',' if fmt == 'csv' else '\t')
    try:
        if fmt == 'json':
            items = json.loads(text)
        elif fmt == 'ndjson':
            # as Slicelytics reads NDJSON: every non-empty line is an item
            items = [json.loads(line) for line in text.split('\n') if line]
        else:
            return None
    except ValueError:
        return None

    doc = item_columns(items)
    if doc is None:
        return None
    try:
        # no NaN or lone surrogates: JavaScript couldn't read them back
        text = json.dumps(doc, ensure_ascii=False, allow_nan=False, separators=(',', ':'))
        text.encode('utf-8')
        return text
    except (ValueError, UnicodeEncodeError):
        return None


def item_columns(items):
    """None unless the items are objects whose fields come in one order, which they're rebuilt in,
    and that mostly share their fields."""
    if not isinstance(items, list) or not all(isinstance(item, dict) for item in items):
        return None
    names = field_names(items)
    position = {name: i for i, name in enumerate(names)}
    if any(position[a] > position[b] for item in items for a, b in zip(item, list(item)[1:])):
        return None
    # mostly missing, e.g. objects keyed by id or date: the lists of absent rows would outgrow the values
    if len(names) * len(items) > 2 * sum(len(item) for item in items):
        return None

    columns = []
    for name in names:
        absent = [i for i, item in enumerate(items) if name not in item]
        column = {'name': name, **({'absent': absent} if absent else {})}
        column.update(encode_column([item[name] for item in items if name in item], typed=True))
        columns.append(column)
    return {'rows': len(items), 'columns': columns}


def field_names(items):
    """Every field. One first seen in a later item goes after the one it follows there, keeping items' order."""
    names, seen = [], set()
    for item in items:
        previous = None
        for name in item:
            if name not in seen:
                names.insert(0 if previous is None else names.index(previous) + 1, name)
                seen.add(name)
            previous = name
    return names


def encode_column(values, typed):
    """`typed`: JSON values. Otherwise CSV cells: strings, whose integers must read back as the same text."""
    time = time_format(values)
    if time:
        return {'delta': deltas([parse_time(v, time) for v in values]), 'time': time}

    ints = values if typed else [int(v) if re.fullmatch(r'-?[1-9]\d*|0', v) else None for v in values]
    if (
        len(values) > 1
        and all(type(v) is int and abs(v) <= MAX_SAFE_INTEGER for v in ints)
        and all(a <= b for a, b in zip(ints, ints[1:]))
    ):
        delta = deltas(ints)
        if all(abs(d) <= MAX_SAFE_INTEGER for d in delta):
            return {'delta': delta}

    if typed and values and all(isinstance(v, dict) for v in values):
        nested = item_columns(values)
        if nested:
            return {'object': nested}

    return {'values': values}


def time_format(values):
    if not values or not isinstance(values[0], str):
        return None
    time = next((f for f, pattern in TIME_FORMATS.items() if pattern.fullmatch(values[0])), None)
    if time and all(is_exact_time(v, time) for v in values):
        return time
    return None


def is_exact_time(value, time):
    """Reads back the same: strptime also takes e.g. single-digit months, and some dates don't exist."""
    if not isinstance(value, str) or not TIME_FORMATS[time].fullmatch(value):
        return False
    t = parse_time(value, time)
    return t is not None and format_time(t, time) == value


def parse_time(value, time):
    """In the format's unit: days, seconds or milliseconds since the epoch."""
    try:
        if time == 'date':
            return (datetime.strptime(value, '%Y-%m-%d').replace(tzinfo=timezone.utc) - EPOCH).days
        moment = datetime.strptime(value[:19], '%Y-%m-%dT%H:%M:%S').replace(tzinfo=timezone.utc)
        seconds = (moment - EPOCH) // timedelta(seconds=1)
        return seconds if time == 's' else seconds * 1000 + int(value[20:23])
    except ValueError:
        return None


def format_time(value, time):
    """As JavaScript's toISOString() shapes it."""
    if time == 'date':
        d = EPOCH + timedelta(days=value)
        return f'{d.year:04d}-{d.month:02d}-{d.day:02d}'
    d = EPOCH + timedelta(milliseconds=value if time == 'ms' else value * 1000)
    out = f'{d.year:04d}-{d.month:02d}-{d.day:02d}T{d.hour:02d}:{d.minute:02d}:{d.second:02d}'
    return out + (f'.{d.microsecond // 1000:03d}Z' if time == 'ms' else 'Z')


def deltas(values):
    return [v - values[i - 1] if i else v for i, v in enumerate(values)]


def delimited_columns(text, delimiter):
    """The CSV or TSV as columns of its cells, kept as text - Slicelytics reads the rebuilt text as the
    file, so it types the values as it would the file's. Only if the rebuilt text is identical."""
    try:
        rows = list(csv.reader(io.StringIO(text, newline=''), delimiter=delimiter))
    except csv.Error:  # e.g. a field over the module's size limit
        return None
    if not rows or any(len(row) != len(rows[0]) for row in rows):
        return None
    newline = '\r\n' if '\r\n' in text else '\n'
    trailing = text.endswith(newline)
    rebuilt = newline.join(delimiter.join(quote_field(cell, delimiter) for cell in row) for row in rows)
    if rebuilt + (newline if trailing else '') != text:
        return None

    header, body = rows[0], rows[1:]
    columns = [
        {'name': name, **encode_column([row[c] for row in body], typed=False)} for c, name in enumerate(header)
    ]
    layout = {'newline': newline, 'trailingNewline': trailing, **({'delimiter': '\t'} if delimiter == '\t' else {})}
    doc = {'rows': len(body), 'columns': columns, 'csv': layout}
    return json.dumps(doc, ensure_ascii=False, separators=(',', ':'))


def quote_field(field, delimiter):
    return '"' + field.replace('"', '""') + '"' if delimiter in field or re.search(r'["\r\n]', field) else field


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
    parser.add_argument('data', help='dataset file: .json, .ndjson/.jsonl, .csv, .tsv or .toon, optionally .gz')
    parser.add_argument('--compare', help='a second dataset file, to compare with the first')
    parser.add_argument('--name', help='name shown for the dataset (default: file name)')
    parser.add_argument('--compare-name', help='name shown for the compared dataset (default: file name)')
    parser.add_argument('--view', help='ViewSpec JSON, inline or a path to a .json file')
    parser.add_argument('--base', default='https://slicelytics.com', help='default: %(default)s')
    parser.add_argument('--open', action='store_true', help='open the link instead of printing it')
    parser.add_argument('--app', action='store_true', help='with --open, on macOS: open in the installed app')
    args = parser.parse_args()

    text, fmt, name = read_dataset(args.data)
    data, fmt = encode(text, fmt)
    params = {'v': 1, 'data': data, 'format': fmt, 'name': args.name or name}
    if args.compare:
        text2, fmt2, name2 = read_dataset(args.compare)
        data2, fmt2 = encode(text2, fmt2)
        params.update(compare=data2, compareFormat=fmt2, compareName=args.compare_name or name2)

    spec = parse_view(args.view)
    route = (spec or {}).get('view') or ('compare' if args.compare else 'explore')
    if route not in ROUTES:
        sys.exit(f'"view" must be one of {", ".join(ROUTES)}')

    url = f'{args.base.rstrip("/")}/data/{route}'
    if spec:
        url += '?view=' + urllib.parse.quote(json.dumps(spec, separators=(',', ':')), safe='')
    url += '#' + urllib.parse.urlencode(params)

    print(f'link: {len(url):,} characters ({"zstd" if zstd else "gzip"})', file=sys.stderr)
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
