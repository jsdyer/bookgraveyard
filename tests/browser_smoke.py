"""CI browser checks: bounded catalogue requests, comparison, saved receipts and mobile."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import shutil
import tempfile
import threading
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main():
    screenshots = ROOT / 'browser-checks'
    screenshots.mkdir(exist_ok=True)
    seed = json.loads((ROOT/'web/data/opening.json').read_text())
    with tempfile.TemporaryDirectory() as temporary:
        shutil.copytree(ROOT/'dist', Path(temporary)/'bookgraveyard')
        server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=temporary))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page(viewport={'width': 1280, 'height': 1000})
                errors, requests = [], []
                fail = {'value': False}
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.route('**/assets/tool-metrics.js', lambda route: route.fulfill(body='', content_type='text/javascript'))

                def source(route):
                    requests.append(route.request.url)
                    if fail['value']:
                        route.fulfill(status=503, content_type='application/json', body='{}', headers={'Access-Control-Allow-Origin':'*'})
                    elif '/editions.json' in route.request.url:
                        route.fulfill(json=seed['editions'][0]['data'], headers={'Access-Control-Allow-Origin':'*'})
                    else:
                        payload = json.loads(json.dumps(seed['search']))
                        payload['docs'][0]['title'] = '<img src=x onerror=alert(1)> Test metadata'
                        route.fulfill(json=payload, headers={'Access-Control-Allow-Origin':'*'})

                page.route('https://openlibrary.org/**', source)
                page.goto(f'http://127.0.0.1:{server.server_port}/bookgraveyard/')
                page.locator('#results .book-card').first.wait_for()
                # Assert source text: the caption is visually uppercased by CSS.
                assert 'Retained opening search' in page.locator('#capture-label').text_content()
                assert len(requests) == 0, 'Page load must not query the provider'
                initial_count = page.locator('#results .book-card').count()
                page.locator('#canadian-books article').first.wait_for()
                page.locator('#canadian-group').select_option('Nova Scotia')
                assert page.locator('#canadian-books article').count() > 0
                page.locator('#canadian-random').click()
                assert len(page.locator('#canadian-passage blockquote').inner_text()) > 100
                page.get_by_role('button',name='Save to Canadian list',exact=True).first.click()
                page.locator('#canadian-saved').check()
                assert page.locator('#canadian-books article').count() == 1
                page.locator('#canadian-speed').fill('300')
                assert '300 words/minute' in page.locator('#canadian-books').inner_text()
                page.locator('#canadian-group').select_option('')
                page.locator('#canadian-saved').uncheck()
                page.locator('#query').fill('papermaking')
                page.locator('#field').select_option('subject')
                page.locator('#search').click()
                page.wait_for_function("document.querySelector('#capture-label').textContent.startsWith('Live search')")
                assert 'subject=papermaking' in requests[-1]
                assert page.locator('#results .book-card').count() == initial_count
                assert page.locator('#results .book-card img').count() == 0
                assert '<img src=x' in page.locator('#results .book-card h3').first.text_content()
                page.get_by_role('button', name='+ Your shelf', exact=True).first.click()
                assert page.locator('#shelf-count').text_content() == '1'
                with page.expect_download() as saved:
                    page.locator('#export-shelf').click()
                shelf_path = Path(temporary)/'shelf.json'
                saved.value.save_as(shelf_path)
                assert json.loads(shelf_path.read_text())['kind'] == 'shelf'
                page.locator('#clear-shelf').click()
                page.locator('#import').set_input_files(shelf_path)
                page.wait_for_function("document.querySelector('#shelf-count').textContent==='1'")
                page.locator('#remember').check()
                assert page.evaluate("localStorage.getItem('coolcode:bookgraveyard:shelf') !== null")
                page.locator('#remember').uncheck()
                assert page.evaluate("localStorage.getItem('coolcode:bookgraveyard:shelf') === null")
                comparison_key = seed['editions'][0]['work'].split('/')[-1]
                page.locator('#results .book-card').filter(has_text=comparison_key).get_by_role('button', name='Compare editions', exact=True).click()
                page.locator('.edition-option').first.wait_for()
                page.locator('.edition-option input').nth(0).check()
                page.locator('.edition-option input').nth(1).check()
                assert page.locator('#comparison article').count() == 2
                page.locator('#close-editions').click()
                fail['value'] = True
                page.locator('#query').fill('different failure query')
                page.locator('#search').click()
                page.wait_for_function("document.querySelector('#status').textContent.includes('Previous results are unchanged')")
                assert page.locator('#results .book-card').count() == initial_count
                page.screenshot(path=str(screenshots/'desktop.png'), full_page=True)
                page.set_viewport_size({'width':390,'height':844})
                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
                page.screenshot(path=str(screenshots/'mobile.png'), full_page=True)
                assert not errors, errors
                browser.close()
            print('Browser checks passed: retained data, arbitrary search, preserved errors, editions, shelf export/import and mobile')
        finally:
            server.shutdown()


if __name__ == '__main__':
    main()
