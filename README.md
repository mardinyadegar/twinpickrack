# twinpickrack

## Tests

`tests/test_site.py` checks the site for broken links/images, case-sensitive
path mismatches (macOS is case-insensitive, GitHub Pages is not), nav
consistency across pages, and the markup `assets/js/site.js` depends on
(hero slider, gallery lightbox). Run it with:

```
python3 tests/test_site.py
```

A pre-commit hook runs it automatically and blocks the commit on failure.
Fresh clones need to install it once:

```
./tests/install-hooks.sh
```
