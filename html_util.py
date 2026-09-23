#!/usr/bin/env python3
"""
Convert a comma-delimited CSV file (rows separated by newlines) into a
self-contained HTML table.

Handles ANSI SGR color codes embedded in cell values (e.g. from terminal
output that was captured verbatim into the CSV), such as:

    173.47\x1b[92m \x1b[00m

...and renders them as colored <span> elements instead of raw escape
sequences.

Uses only the standard library (csv, re, argparse) plus lxml.
"""

import csv
import os
import re
from datetime import datetime

from lxml import etree
from lxml.html.builder import E
from lxml.html import tostring


# --------------------------------------------------------------------------
# ANSI -> CSS color mapping (standard 16-color SGR foreground/background codes)
# --------------------------------------------------------------------------

ANSI_ESCAPE_RE = re.compile(r'\x1b\[([0-9;]*)m')

FG_COLORS = {
    30: '#000000', 31: '#cc0000', 32: '#4e9a06', 33: '#c4a000',
    34: '#3465a4', 35: '#75507b', 36: '#06989a', 37: '#d3d7cf',
    90: '#555753', 91: '#ef2929', 92: '#8ae234', 93: '#fce94f',
    94: '#729fcf', 95: '#ad7fa8', 96: '#34e2e2', 97: '#eeeeec',
}

BG_COLORS = {
    40: '#000000', 41: '#cc0000', 42: '#4e9a06', 43: '#c4a000',
    44: '#3465a4', 45: '#75507b', 46: '#06989a', 47: '#d3d7cf',
    100: '#555753', 101: '#ef2929', 102: '#8ae234', 103: '#fce94f',
    104: '#729fcf', 105: '#ad7fa8', 106: '#34e2e2', 107: '#eeeeec',
}


class AnsiState:
    """Tracks the current SGR styling as ANSI codes are applied."""

    def __init__(self):
        self.fg = None
        self.bg = None
        self.bold = False

    def apply(self, codes):
        for code in codes:
            if code == 0:
                self.fg = self.bg = None
                self.bold = False
            elif code == 1:
                self.bold = True
            elif code == 22:
                self.bold = False
            elif code == 39:
                self.fg = None
            elif code == 49:
                self.bg = None
            elif code in FG_COLORS:
                self.fg = FG_COLORS[code]
            elif code in BG_COLORS:
                self.bg = BG_COLORS[code]
            # Unsupported codes (underline, italic, 256-color, etc.) are
            # silently ignored rather than raising.

    def css(self):
        parts = []
        if self.fg:
            parts.append(f'color:{self.fg}')
        if self.bg:
            parts.append(f'background-color:{self.bg}')
        if self.bold:
            parts.append('font-weight:bold')
        return ';'.join(parts)

    def is_default(self):
        return not (self.fg or self.bg or self.bold)


def append_inline(parent, node_or_text):
    """
    Append a text node or an element to `parent`, correctly handling
    lxml's text/tail model (text before the first child goes on
    parent.text; text after a child goes on that child's .tail).
    """
    if isinstance(node_or_text, str):
        if len(parent) == 0:
            parent.text = (parent.text or '') + node_or_text
        else:
            last = parent[-1]
            last.tail = (last.tail or '') + node_or_text
    else:
        parent.append(node_or_text)


def cell_to_element(tag, raw_text):
    """
    Build a <td> or <th> element from raw cell text, converting any
    embedded ANSI escape sequences into styled <span> elements.
    """
    el = E(tag)

    if '\x1b[' not in raw_text:
        el.text = raw_text
        return el

    state = AnsiState()
    pos = 0
    for match in ANSI_ESCAPE_RE.finditer(raw_text):
        chunk = raw_text[pos:match.start()]
        if chunk:
            if state.is_default():
                append_inline(el, chunk)
            else:
                span = E.span(chunk, style=state.css())
                append_inline(el, span)

        code_str = match.group(1)
        codes = [int(c) for c in code_str.split(';') if c != ''] or [0]
        state.apply(codes)

        pos = match.end()

    tail = raw_text[pos:]
    if tail:
        if state.is_default():
            append_inline(el, tail)
        else:
            append_inline(el, E.span(tail, style=state.css()))

    return el


# --------------------------------------------------------------------------
# CSV -> HTML
# --------------------------------------------------------------------------

def parse_header_groups(header, words):
    """
    Walk `header` left to right and group consecutive columns whose names
    follow the pattern "<GROUP> <word>" for every word in `words`, in
    order, all sharing the same <GROUP>. A group is only recognized when
    all len(words) columns are present and match; otherwise each column
    is left as a standalone (single) header.

    Returns a list of items, each either:
        ('single', header_text)
        ('group', group_name, words)
    """
    if not words:
        return [('single', h) for h in header]

    groups = []
    i = 0
    n = len(header)
    while i < n:
        matched = False
        if i + len(words) <= n:
            candidate_group = None
            ok = True
            for j, word in enumerate(words):
                cell = header[i + j]
                suffix = f' {word}'
                if not cell.endswith(suffix):
                    ok = False
                    break
                group = cell[: -len(suffix)]
                if not group:
                    ok = False
                    break
                if candidate_group is None:
                    candidate_group = group
                elif group != candidate_group:
                    ok = False
                    break
            if ok:
                groups.append(('group', candidate_group, words))
                i += len(words)
                matched = True
        if not matched:
            groups.append(('single', header[i]))
            i += 1
    return groups


def build_thead(header, sub_headers):
    groups = parse_header_groups(header, sub_headers)

    top_row_cells = []
    sub_row_cells = []
    for item in groups:
        if item[0] == 'single':
            th = cell_to_element('th', item[1])
            th.set('rowspan', '2')
            top_row_cells.append(th)
        else:
            _, group_name, words = item
            group_th = cell_to_element('th', group_name)
            group_th.set('colspan', str(len(words)))
            group_th.set('class', 'group-header')
            top_row_cells.append(group_th)
            for word in words:
                sub_row_cells.append(cell_to_element('th', word))

    rows = [E.tr(*top_row_cells)]
    if sub_row_cells:
        rows.append(E.tr(*sub_row_cells))
    return E.thead(*rows)


def build_html(rows, title='CSV Export', sub_headers=None):
    """
    Args:
        rows: list of CSV rows (first row is the header).
        title: page title.
        sub_headers: optional list of exactly 3 words (e.g. ['word0',
            'word1', 'word2']). When present, any run of 3 consecutive
            header columns named "<GROUP> word0", "<GROUP> word1",
            "<GROUP> word2" (same GROUP, in that order) is rendered as a
            spanning group header over a sub-header row. Columns that
            don't match this pattern render as normal single headers.
    """
    if not rows:
        raise ValueError('No rows found in CSV.')

    header, *body = rows

    thead = build_thead(header, sub_headers)
    tbody = E.tbody(
        *[E.tr(*[cell_to_element('td', cell) for cell in row]) for row in body]
    )
    table = E.table(thead, tbody, {'class': 'data-table'})

    style = E.style("""
        body {
            font-family: 'Courier New', Consolas, monospace;
            background: #1e1e1e;
            color: #d3d7cf;
            padding: 2rem;
        }
        h1 { font-size: 1.1rem; font-weight: normal; color: #888; }
        table.data-table {
            border-collapse: collapse;
            width: 100%;
            font-size: 0.9rem;
        }
        table.data-table th, table.data-table td {
            border: 1px solid #444;
            padding: 6px 10px;
            text-align: left;
            white-space: pre;
        }
        table.data-table th {
            background: #2d2d2d;
            color: #eee;
            position: sticky;
            top: 0;
            text-align: center;
        }
        table.data-table th.group-header {
            background: #383838;
            border-bottom: 1px solid #555;
        }
        table.data-table tr:nth-child(even) td {
            background: #252525;
        }
    """)

    doc = E.html(
        E.head(E.meta(charset='utf-8'), E.title(title), style),
        E.body(E.h1(f'{title} — generated {datetime.now().strftime("%m_%d_%y_%H_%M")}'), table),
    )
    return doc


DAGGER = '\u2020'


def superscript_daggers(html_str):
    """
    Wrap every literal dagger character (U+2020, '†') in <sup> tags.

    Applied to the fully serialized HTML string (not per-cell), so it
    catches every dagger in the document regardless of where the text
    came from -- table cells, the title, the h1, or any section added
    to build_html() in the future. There's no way to type an actual
    superscript dagger glyph, so this is done with the <sup> tag instead.
    """
    return html_str.replace(DAGGER, f'<sup>{DAGGER}</sup>')


def create_html(filename, output_filename=None, title=None, sub_headers=None):
    """
    Read a CSV file (rows separated by newlines, ',' as the only delimiter)
    and write it out as a styled, ANSI-color-aware HTML table.

    Args:
        filename: Path to the input CSV file.
        output_filename: Path to write the HTML file to. If omitted,
            defaults to `filename` with its extension replaced by `.html`.
        title: Optional page title. Defaults to `filename`.
        sub_headers: optional list of exactly 3 words (e.g. ['word0',
            'word1', 'word2']). When provided, header columns named
            "<GROUP> word0", "<GROUP> word1", "<GROUP> word2" (all 3,
            same GROUP, consecutive, in that order) are rendered as a
            2-level header: a spanning "<GROUP>" cell over the 3 words.
            Columns that don't match the pattern are left as-is.

    Returns:
        The path the HTML file was written to.
    """
    with open(filename, newline='', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter=',')
        rows = [row for row in reader]

    doc = build_html(rows, title=title or filename, sub_headers=sub_headers)

    if output_filename is None:
        base, _ext = os.path.splitext(filename)
        output_filename = base + '.html'

    html_str = tostring(doc, doctype='<!DOCTYPE html>', pretty_print=True, encoding='unicode')
    html_str = superscript_daggers(html_str)

    with open(output_filename, 'wb') as f:
        f.write(html_str.encode('utf-8'))

    return output_filename