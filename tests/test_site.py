#!/usr/bin/env python3
"""
Regression test suite for the static Twin Pick Racks site.

Pure stdlib, and deliberately avoids `unittest`/`copy`/`logging`: on some
machines the local Python 3 install has a corrupted weakref.py (a system
issue, unrelated to this repo) which breaks any module that imports
weakref, including unittest. This runner only imports re/os/sys/html.parser,
which are unaffected, so the suite still runs everywhere. Run with:

    python3 tests/test_site.py

Or via the wrapper: ./tests/run_tests.sh

The goal is to catch the mistakes that are easy to make when adding a new
page, image, or nav entry to a hand-written multi-page HTML site:
  - a broken internal link or image path
  - a path whose case doesn't match the file on disk (invisible on macOS,
    a 404 on GitHub Pages' case-sensitive Linux servers)
  - a page that forgot to update its copy of the shared nav
  - a new page missing standard <head> boilerplate
  - a gallery/hero slider whose markup no longer matches what site.js expects
"""
import os
import re
import sys
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

VOID_TAGS = {
    'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input',
    'link', 'meta', 'param', 'source', 'track', 'wbr',
}

# class names that exist purely as JS hooks / dynamic state, or as
# semantic/layout markers with no dedicated CSS rule of their own (styling
# comes from a combined selector or a sibling class), and so are not
# expected to appear as a standalone CSS selector.
CSS_EXEMPT_CLASSES = {
    'js-year', 'skip-link', 'work-process',
}


# ---------------------------------------------------------------------------
# Minimal test harness (no unittest, see module docstring for why).
# ---------------------------------------------------------------------------

class TestSuite:
    def __init__(self):
        self._tests = []

    def test(self, fn):
        self._tests.append(fn)
        return fn

    def run(self):
        failed = []
        errored = []
        for fn in self._tests:
            name = fn.__name__
            try:
                fn()
            except AssertionError as e:
                failed.append(name)
                print(f"FAIL: {name}")
                for line in str(e).splitlines():
                    print(f"    {line}")
            except Exception as e:
                errored.append(name)
                print(f"ERROR: {name}: {e!r}")
            else:
                print(f"PASS: {name}")
        total = len(self._tests)
        ok = total - len(failed) - len(errored)
        print(f"\n{ok}/{total} tests passed", end='')
        if failed:
            print(f", {len(failed)} failed", end='')
        if errored:
            print(f", {len(errored)} errored", end='')
        print()
        return not failed and not errored


suite = TestSuite()


def check(failures, condition, message):
    if not condition:
        failures.append(message)


def fail_if_any(failures):
    if failures:
        raise AssertionError("\n".join(failures))


# ---------------------------------------------------------------------------
# HTML parsing helpers
# ---------------------------------------------------------------------------

class PageParser(HTMLParser):
    """Collects everything the tests need from one HTML document."""

    def __init__(self, filename):
        super().__init__(convert_charrefs=True)
        self.filename = filename
        self.stack = []
        self.errors = []
        self.elements = []          # list of dicts: tag, attrs, line
        self.ids = []                # list of (id, line)
        self.classes = set()
        self.title_text = []
        self._in_title = False
        self.doctype_seen = False

    def handle_decl(self, decl):
        if decl.strip().lower().startswith('doctype'):
            self.doctype_seen = True

    def _record(self, tag, attrs_list):
        attrs = dict(attrs_list)
        line = self.getpos()[0]
        self.elements.append({'tag': tag, 'attrs': attrs, 'line': line})
        if 'id' in attrs and attrs['id']:
            self.ids.append((attrs['id'], line))
        if 'class' in attrs and attrs['class']:
            for c in attrs['class'].split():
                self.classes.add(c)
        if tag == 'title':
            self._in_title = True

    def handle_starttag(self, tag, attrs):
        self._record(tag, attrs)
        if tag not in VOID_TAGS:
            self.stack.append((tag, self.getpos()[0]))

    def handle_startendtag(self, tag, attrs):
        # self-closed, e.g. <img ... /> or <path .../>
        self._record(tag, attrs)

    def handle_endtag(self, tag):
        if self._in_title and tag == 'title':
            self._in_title = False
        if tag in VOID_TAGS:
            return
        if not self.stack:
            self.errors.append(
                f"{self.filename}:{self.getpos()[0]}: closing </{tag}> with no open tag"
            )
            return
        for depth in range(len(self.stack) - 1, -1, -1):
            if self.stack[depth][0] == tag:
                closed = self.stack[depth:]
                del self.stack[depth:]
                for leftover_tag, leftover_line in closed[1:]:
                    self.errors.append(
                        f"{self.filename}:{leftover_line}: <{leftover_tag}> "
                        f"never closed before </{tag}> at line {self.getpos()[0]}"
                    )
                return
        self.errors.append(
            f"{self.filename}:{self.getpos()[0]}: closing </{tag}> does not "
            f"match any open tag ({[t for t, _ in self.stack]})"
        )

    def handle_data(self, data):
        if self._in_title:
            self.title_text.append(data)

    def close(self):
        super().close()
        for tag, line in self.stack:
            self.errors.append(f"{self.filename}:{line}: <{tag}> was never closed")

    @property
    def title(self):
        return ''.join(self.title_text).strip()


def load_page(filename):
    path = os.path.join(ROOT, filename)
    with open(path, 'r', encoding='utf-8') as fh:
        raw = fh.read()
    parser = PageParser(filename)
    parser.feed(raw)
    parser.close()
    return raw, parser


def discover_pages():
    return sorted(f for f in os.listdir(ROOT) if f.endswith('.html'))


PAGES = discover_pages()
RAW = {}
PARSED = {}
for _f in PAGES:
    _raw, _parsed = load_page(_f)
    RAW[_f] = _raw
    PARSED[_f] = _parsed


BG_IMAGE_RE = re.compile(r'background-image\s*:\s*url\(\s*([^)\s]+?)\s*\)')
CSS_CLASS_SELECTOR_RE = re.compile(r'\.([a-zA-Z_][\w-]*)')
CSS_URL_RE = re.compile(r'url\(\s*[\'"]?([^)\'"]+)[\'"]?\s*\)')


def path_exists_case_sensitive(rel_path):
    """Like os.path.exists, but rejects case mismatches (macOS HFS+/APFS
    is case-insensitive by default; GitHub Pages is not)."""
    parts = rel_path.split('/')
    current = ROOT
    for part in parts:
        if part in ('', '.'):
            continue
        if part == '..':
            return False
        try:
            entries = os.listdir(current)
        except (FileNotFoundError, NotADirectoryError):
            return False
        if part not in entries:
            return False
        current = os.path.join(current, part)
    return True


def is_external(url):
    return bool(re.match(r'^([a-zA-Z][a-zA-Z0-9+.-]*:|//)', url))


def split_href(href):
    """Return (path_part, fragment_or_None)."""
    if '#' in href:
        path_part, frag = href.split('#', 1)
        return path_part, frag
    return href, None


def nav_link_items(page):
    """Extract the (text, normalized_href) pairs from the primary nav."""
    raw = RAW[page]
    nav_match = re.search(r'<nav[^>]*aria-label="Primary".*?</nav>', raw, re.S)
    if not nav_match:
        raise AssertionError(f"{page}: could not locate <nav aria-label=\"Primary\">")
    nav_html = nav_match.group(0)
    items = re.findall(r'<a href="([^"]+)"[^>]*>(.*?)</a>', nav_html, re.S)
    normalized = []
    for href, text in items:
        text = re.sub(r'<[^>]+>', '', text).strip()
        if href.startswith('index.html#'):
            href = href[len('index.html'):]
        normalized.append((text, href))
    return normalized


def css_defined_classes():
    css_path = os.path.join(ROOT, 'assets', 'css', 'site.css')
    with open(css_path, 'r', encoding='utf-8') as fh:
        css = fh.read()
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
    return set(CSS_CLASS_SELECTOR_RE.findall(css))


# ---------------------------------------------------------------------------
# Tests: well-formed HTML
# ---------------------------------------------------------------------------

@suite.test
def test_pages_discovered():
    failures = []
    check(failures, 'index.html' in PAGES, "index.html not found at repo root")
    check(failures, len(PAGES) >= 8, f"expected >=8 html pages, found {len(PAGES)}")
    fail_if_any(failures)


@suite.test
def test_tags_balanced():
    failures = []
    for f in PAGES:
        errors = PARSED[f].errors
        check(failures, not errors, f"{f}: " + "; ".join(errors))
    fail_if_any(failures)


@suite.test
def test_doctype_present():
    failures = []
    for f in PAGES:
        check(
            failures,
            RAW[f].lstrip().lower().startswith('<!doctype html>'),
            f"{f} must start with <!DOCTYPE html>",
        )
    fail_if_any(failures)


# ---------------------------------------------------------------------------
# Tests: <head> boilerplate
# ---------------------------------------------------------------------------

@suite.test
def test_html_lang():
    failures = []
    for f in PAGES:
        htmls = [e for e in PARSED[f].elements if e['tag'] == 'html']
        check(failures, len(htmls) == 1, f"{f} must have exactly one <html> tag")
        if htmls:
            check(failures, bool(htmls[0]['attrs'].get('lang')), f"{f} <html> is missing lang attribute")
    fail_if_any(failures)


@suite.test
def test_title_present_and_prefixed():
    failures = []
    for f in PAGES:
        title = PARSED[f].title
        check(failures, bool(title), f"{f} has an empty <title>")
        if title:
            check(
                failures, title.startswith('Twin Pick Racks'),
                f"{f} <title> ({title!r}) should start with 'Twin Pick Racks' for brand consistency",
            )
    fail_if_any(failures)


@suite.test
def test_titles_unique():
    titles = {}
    for f in PAGES:
        t = PARSED[f].title
        titles.setdefault(t, []).append(f)
    dupes = {t: fs for t, fs in titles.items() if len(fs) > 1}
    if dupes:
        raise AssertionError(f"Duplicate <title> values across pages: {dupes}")


@suite.test
def test_charset_and_viewport():
    failures = []
    for f in PAGES:
        metas = [e['attrs'] for e in PARSED[f].elements if e['tag'] == 'meta']
        check(
            failures, any(m.get('charset', '').lower() == 'utf-8' for m in metas),
            f"{f} is missing <meta charset=\"utf-8\">",
        )
        check(
            failures, any(m.get('name') == 'viewport' for m in metas),
            f"{f} is missing the responsive viewport meta tag",
        )
    fail_if_any(failures)


@suite.test
def test_site_css_and_js_linked():
    failures = []
    for f in PAGES:
        links = [e['attrs'].get('href', '') for e in PARSED[f].elements if e['tag'] == 'link']
        scripts = [e['attrs'].get('src', '') for e in PARSED[f].elements if e['tag'] == 'script']
        check(failures, 'assets/css/site.css' in links, f"{f} does not link assets/css/site.css")
        check(failures, 'assets/js/site.js' in scripts, f"{f} does not include assets/js/site.js")
    fail_if_any(failures)


# ---------------------------------------------------------------------------
# Tests: ids
# ---------------------------------------------------------------------------

@suite.test
def test_no_duplicate_ids():
    failures = []
    for f in PAGES:
        seen = {}
        for id_val, line in PARSED[f].ids:
            if id_val in seen:
                failures.append(f"{f}:{line}: id='{id_val}' duplicates the one at line {seen[id_val]}")
            else:
                seen[id_val] = line
    fail_if_any(failures)


# ---------------------------------------------------------------------------
# Tests: navigation consistency
# ---------------------------------------------------------------------------

@suite.test
def test_nav_matches_reference_on_every_page():
    reference = nav_link_items('index.html')
    failures = []
    for f in PAGES:
        if f == 'index.html':
            continue
        actual = nav_link_items(f)
        check(
            failures, actual == reference,
            f"{f}'s primary nav does not match index.html's nav "
            f"(expected {reference}, got {actual})",
        )
    fail_if_any(failures)


@suite.test
def test_every_top_level_page_is_reachable_from_nav():
    reference_hrefs = {href for _text, href in nav_link_items('index.html')}
    failures = []
    for f in PAGES:
        if f == 'index.html':
            continue
        check(
            failures, f in reference_hrefs,
            f"{f} exists but is not linked from the primary nav on index.html",
        )
    fail_if_any(failures)


# ---------------------------------------------------------------------------
# Tests: internal links and same/cross-page anchors
# ---------------------------------------------------------------------------

@suite.test
def test_local_links_resolve():
    failures = []
    for f in PAGES:
        for el in PARSED[f].elements:
            if el['tag'] != 'a':
                continue
            href = el['attrs'].get('href')
            if not href or is_external(href) or href.startswith('javascript:'):
                continue
            path_part, frag = split_href(href)
            if path_part:
                if not path_exists_case_sensitive(path_part):
                    failures.append(
                        f"{f}:{el['line']}: link target '{path_part}' does not exist "
                        "(check spelling/case — GitHub Pages is case-sensitive)"
                    )
                    continue
                target_page = path_part
            else:
                target_page = f
            if frag:
                target_parsed = PARSED.get(target_page)
                if target_parsed is None:
                    failures.append(
                        f"{f}:{el['line']}: cannot verify anchor '#{frag}', "
                        f"'{target_page}' is not an HTML page in this repo"
                    )
                    continue
                target_ids = {i for i, _ in target_parsed.ids}
                if frag not in target_ids:
                    failures.append(f"{f}:{el['line']}: '#{frag}' has no matching id in {target_page}")
    fail_if_any(failures)


# ---------------------------------------------------------------------------
# Tests: images and other assets
# ---------------------------------------------------------------------------

@suite.test
def test_img_src_resolves_case_sensitively():
    failures = []
    for f in PAGES:
        for el in PARSED[f].elements:
            if el['tag'] != 'img':
                continue
            if 'src' not in el['attrs']:
                failures.append(f"{f}:{el['line']}: <img> has no src attribute")
                continue
            src = el['attrs']['src']
            if not src:
                # Intentionally empty (e.g. the lightbox template <img>,
                # filled in by JS at runtime) — nothing to resolve.
                continue
            if not is_external(src) and not path_exists_case_sensitive(src):
                failures.append(
                    f"{f}:{el['line']}: image '{src}' not found on disk (check spelling/case)"
                )
    fail_if_any(failures)


@suite.test
def test_img_has_alt_attribute():
    failures = []
    for f in PAGES:
        for el in PARSED[f].elements:
            if el['tag'] != 'img':
                continue
            check(
                failures, 'alt' in el['attrs'],
                f"{f}:{el['line']}: <img src='{el['attrs'].get('src')}'> is missing an alt attribute",
            )
    fail_if_any(failures)


@suite.test
def test_data_full_gallery_targets_resolve():
    failures = []
    for f in PAGES:
        for el in PARSED[f].elements:
            data_full = el['attrs'].get('data-full')
            if data_full is None:
                continue
            check(
                failures, path_exists_case_sensitive(data_full),
                f"{f}:{el['line']}: gallery data-full '{data_full}' not found on disk",
            )
            check(
                failures, bool((el['attrs'].get('data-caption') or '').strip()),
                f"{f}:{el['line']}: gallery item missing a non-empty data-caption",
            )
    fail_if_any(failures)


@suite.test
def test_background_image_urls_resolve():
    failures = []
    for f in PAGES:
        for match in BG_IMAGE_RE.finditer(RAW[f]):
            url = match.group(1).strip('\'"')
            if not is_external(url):
                check(
                    failures, path_exists_case_sensitive(url),
                    f"{f}: background-image url '{url}' not found on disk",
                )
    fail_if_any(failures)


@suite.test
def test_favicon_and_link_hrefs_resolve():
    failures = []
    for f in PAGES:
        for el in PARSED[f].elements:
            if el['tag'] != 'link':
                continue
            href = el['attrs'].get('href', '')
            if not href or is_external(href):
                continue
            check(
                failures, path_exists_case_sensitive(href),
                f"{f}:{el['line']}: <link href='{href}'> not found on disk",
            )
    fail_if_any(failures)


@suite.test
def test_social_meta_image_resolves():
    failures = []
    for f in PAGES:
        for el in PARSED[f].elements:
            if el['tag'] != 'meta':
                continue
            prop = el['attrs'].get('property') or el['attrs'].get('name')
            if prop not in ('og:image', 'twitter:image'):
                continue
            content = el['attrs'].get('content', '')
            check(
                failures, bool(content) and not is_external(content) and path_exists_case_sensitive(content),
                f"{f}:{el['line']}: <meta {prop}> content '{content}' does not resolve to a file on disk",
            )
    fail_if_any(failures)


@suite.test
def test_css_and_js_files_exist():
    failures = []
    check(failures, path_exists_case_sensitive('assets/css/site.css'), "assets/css/site.css is missing")
    check(failures, path_exists_case_sensitive('assets/js/site.js'), "assets/js/site.js is missing")
    fail_if_any(failures)


# ---------------------------------------------------------------------------
# Tests: CSS classes actually defined
# ---------------------------------------------------------------------------

@suite.test
def test_html_classes_are_defined_in_css():
    defined = css_defined_classes()
    failures = []
    for f in PAGES:
        used = PARSED[f].classes
        missing = sorted(c for c in used if c not in defined and c not in CSS_EXEMPT_CLASSES)
        check(
            failures, not missing,
            f"{f} uses CSS classes with no matching selector in site.css: {missing} "
            "(typo, or site.css needs updating)",
        )
    fail_if_any(failures)


@suite.test
def test_css_url_references_resolve():
    css_path = os.path.join(ROOT, 'assets', 'css', 'site.css')
    with open(css_path, 'r', encoding='utf-8') as fh:
        css = fh.read()
    failures = []
    for match in CSS_URL_RE.finditer(css):
        url = match.group(1).strip()
        if is_external(url) or url.startswith('data:'):
            continue
        rel = url
        if rel.startswith('../'):
            rel = rel[len('../'):]
        elif rel.startswith('./'):
            rel = rel[len('./'):]
        check(
            failures,
            path_exists_case_sensitive(rel) or path_exists_case_sensitive('assets/css/' + url),
            f"site.css: url('{url}') does not resolve to a file on disk",
        )
    fail_if_any(failures)


# ---------------------------------------------------------------------------
# Tests: hero slider invariants (depended on by assets/js/site.js)
# ---------------------------------------------------------------------------

@suite.test
def test_hero_slide_count_matches_dot_count():
    failures = []
    for f in PAGES:
        elements = PARSED[f].elements
        slide_count = sum(
            1 for e in elements
            if e['tag'] == 'div' and 'hero-slide' in e['attrs'].get('class', '').split()
        )
        dot_count = sum(
            1 for e in elements
            if e['tag'] == 'button' and 'hero-dot' in e['attrs'].get('class', '').split()
        )
        if slide_count == 0 and dot_count == 0:
            continue
        check(
            failures, slide_count == dot_count,
            f"{f}: {slide_count} .hero-slide element(s) but {dot_count} .hero-dot button(s) — "
            "site.js indexes slides and dots together, so these must match",
        )
    fail_if_any(failures)


@suite.test
def test_hero_exactly_one_active_slide():
    failures = []
    for f in PAGES:
        elements = PARSED[f].elements
        slides = [e for e in elements if e['tag'] == 'div' and 'hero-slide' in e['attrs'].get('class', '').split()]
        if not slides:
            continue
        active = [s for s in slides if 'is-active' in s['attrs'].get('class', '').split()]
        check(
            failures, len(active) == 1,
            f"{f}: expected exactly one .hero-slide.is-active on initial page load, found {len(active)}",
        )
    fail_if_any(failures)


# ---------------------------------------------------------------------------
# Tests: gallery lightbox invariants
# ---------------------------------------------------------------------------

@suite.test
def test_lightbox_scaffold_present_when_gallery_used():
    required_ids = {'lightbox'}
    required_classes = {'lightbox-img', 'lightbox-caption', 'lightbox-close', 'lightbox-prev', 'lightbox-next'}
    failures = []
    for f in PAGES:
        has_gallery_items = any(
            'gallery-item' in e['attrs'].get('class', '').split()
            for e in PARSED[f].elements
        )
        if not has_gallery_items:
            continue
        ids = {i for i, _ in PARSED[f].ids}
        classes = PARSED[f].classes
        check(
            failures, required_ids <= ids,
            f"{f}: missing lightbox #id scaffold for gallery-item usage",
        )
        check(
            failures, required_classes <= classes,
            f"{f}: missing lightbox classes {required_classes - classes} needed by site.js",
        )
    fail_if_any(failures)


if __name__ == '__main__':
    ok = suite.run()
    sys.exit(0 if ok else 1)
