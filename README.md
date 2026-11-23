# Book Graveyard

A small, public browser catalogue for rediscovering books, comparing editions and following original reading links. Live site: [coolcode.ca/bookgraveyard/](https://coolcode.ca/bookgraveyard/).

<!-- coolcode:guide -->
Search any title, author, subject or set of words, optionally limiting the work's first-publication years and Open Library's access category. The starting searches are editable suggestions, not a fixed collection. Results are paginated. Open **Compare editions** on a work, then choose two publication records to compare publisher, date, language, pages, format and ISBN. A work groups editions; its first-publication year and reading-access label do not describe every edition.

The opening screen uses a small, dated real Open Library capture. **Search books** retrieves live results directly from Open Library; failures preserve the previous results. Add books to a reading shelf, export JSON/CSV, or import a saved search/shelf JSON locally. The shelf stays in the current tab unless **Remember this shelf on this device** is selected. A readable-copy label is not a worldwide public-domain determination, and borrowing can require an Open Library/Internet Archive account. “Graveyard” is a discovery theme, not a claim that titles are forgotten or out of print.

**Expand or customize:** edit `web/config.json` to change `defaultSearch`, add any number of `presets`, or change page sizes and timeouts. Each query has `query`, `field` (`all`, `title`, `author`, `subject`), `from`, `to`, `access` (`any`, `public`, `borrowable`, `no_ebook`) and `sort` (`relevance`, `old`, `new`). Visitors can type searches beyond these presets. After changing the opening search, run `python3 scripts/refresh_data.py` once; review `web/data/opening.json`, then run the normal checks and commit to `main`. The Pages workflow builds and publishes the change. This tool needs no API key; Open Library asks the owner to register the application/use case using the form linked in its API documentation.
<!-- /coolcode:guide -->

## Sources and what the labels mean

- [Open Library Search API](https://openlibrary.org/dev/docs/api/search): requested fields are explicit and each page is limited to 12 works by default. First-publication dates come from the catalogue. Unknown dates remain unknown. Search hits with missing or legacy non-work IDs are omitted and counted visibly; the provider's total still includes them, and the original search link exposes the complete source page.
- [Works and Editions API](https://openlibrary.org/dev/docs/api/books): the user opens one work at a time, in pages of 20 editions. **Compare editions** compares catalogue fields, not book text.
- [Search access labels](https://openlibrary.org/search/howto): `public` becomes **Readable copy listed**; `borrowable` becomes **Borrowing listed**; `no_ebook` becomes **Catalogue record**; `printdisabled` becomes **Restricted access**. These are work-level indexed observations, not a promise that a particular edition can be downloaded today.
- [Catalogue licensing](https://openlibrary.org/developers/licensing) and [using the data](https://openlibrary.org/help/faq/using): catalogue metadata is openly reusable; existing rights may apply to contributions and book contents. This app republishes bibliographic metadata, not book text or scans. It does not infer rights from age. Follow the original record to confirm access and rights in your jurisdiction.

No Gutendex demonstration service, scraping, proxies, automatic book downloads or book-cover requests are used. Public-domain and borrowable reading links stay on the original Open Library record so current availability can be checked there.

## API registration and traffic

Public metadata reads need **no key or login**. The owner should complete **Registering Your Application** on [Open Library's current API page](https://openlibrary.org/developers/api). The provider asks for this use-case registration; it is separate from a visitor account needed for some borrowing. No form has been submitted on the owner's behalf.

Suggested application description for the form:

> Book Graveyard is a free, open-source personal book-discovery tool at https://coolcode.ca/bookgraveyard/ (source: https://github.com/jsdyer/bookgraveyard). Visitors request title, author or subject searches and compare two edition records. We link back to Open Library for reading and current availability. The app requests only a bounded page at a time, caches responses within the tab for 15 minutes, and spaces API calls at least 1.2 seconds apart. There is no autocomplete crawl, scheduled bulk collection, redistribution of book files or commercial data resale. A manually refreshed opening example uses one search request and at most one edition-page request. Expected launch traffic is small but not yet measured. The browser sends ordinary browser identification; our manual collector identifies BookGraveyard and its public project URL. Please advise if you prefer another identification method for direct browser requests.

Use your preferred contact email in their form; it is not a GitHub secret and is not required in this static page. If the provider requests an identified collector, you may deliberately set `refreshUserAgent` to `BookGraveyard/1.0 (your-contact-address)`; doing so sends that contact value to Open Library. The supplied configuration contains the public app URL only.

[Documented limits](https://openlibrary.org/developers/api), reviewed November 23, 2026: unidentified requests default to **1 per second**, identified requests with application name/contact **3 per second**. This app deliberately stays below the lower limit. Browsers do not reliably permit an application-controlled User-Agent. Search and edition requests are serialized and spaced at least 1.2 seconds apart; repeated responses are cached in tab memory, and HTTP 429 pauses requests for a minute. This controls a tab, not aggregate traffic from every visitor or multiple tabs. If traffic grows beyond personal discovery use, coordinate with Open Library and use their data dumps for a locally hosted index instead of harvesting the API.

## Expand or customize

`web/config.json` is the source of defaults. Example additional starting point:

```json
{"label":"Early radio","query":"radio","field":"subject","from":"1880","to":"1940","access":"any","sort":"old"}
```

Add it to `presets`; there is no fixed-count assumption. Changing presets alone needs only a build and publication. `defaultSearch` controls the real opening example; refresh that capture when changing it. `pageSize` and `editionPageSize` accept 1–50; keep modest defaults. `requestGapMs` must stay at least 1100. Adjust `timeoutMs`, `cacheMinutes`, `maxShelfItems` and `maxImportBytes` within the documented code validators. `source` is intentionally restricted to the supported Open Library API rather than becoming an arbitrary URL fetcher.

```sh
python3 scripts/refresh_data.py  # Two bounded requests at most; no key
node --test tests/*.test.mjs
python3 -m unittest discover -s tests -v
python3 scripts/build.py
```

The collector prints the requested URLs, checks JSON and required arrays, and replaces the retained capture only after both responses validate. A failure leaves the prior capture untouched. Every capture carries UTC retrieval time and source URL; retrieved time is not a book publication date. Refresh is manual, with no scheduled polling. Git retains earlier committed opening captures; exported visitor receipts are independent copies.

Commit reviewed source/config/data changes to `main`; `.github/workflows/pages.yml` checks the app, builds it offline, runs its browser smoke check and deploys the `dist/` directory to GitHub Pages. Do not commit `dist/` or add a CNAME. The CoolCode routing list is managed separately.

## Privacy and testing

Searching sends the query, selected field, first-year range, access filter and sort to Open Library. An edition lookup sends the selected work ID. No search is sent on initial page load. Import, reading shelf and comparison run in the browser; persistent storage is opt-in under `coolcode:bookgraveyard:shelf`. Removing the checkbox deletes that stored shelf. JSON imports validate their shape and Open Library IDs; rendered records use `textContent`, and links are constructed from validated IDs. CSV values are quoted and formula-like values are escaped. CoolCode's standard page metrics script remains separate from the app's input handling.

The normal build needs Python's standard library and Node for tests, without runtime package dependencies. `tests/browser_smoke.py` is run by CI using the pinned browser-test requirements; it covers a project subpath, arbitrary live-query request construction (with deterministic responses), errors preserving results, comparing editions, shelf export/import and mobile overflow. Stubbed browser tests do not prove future provider availability; check a real arbitrary query after publishing.
