#!/usr/bin/env python
"""QA browser isolato dell'app locale; non usa profili o sessioni personali."""
import json
import os
import time

from data_model import WEB_DIR

os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(WEB_DIR / ".cache" / "browsers"))


def main():
    from playwright.sync_api import sync_playwright, expect
    target = WEB_DIR / "qa"
    target.mkdir(exist_ok=True)
    results = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 1080}, device_scale_factor=1)
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        start = time.perf_counter()
        page.goto("http://127.0.0.1:8501", wait_until="domcontentloaded")
        expect(page.get_by_text("-540.640,69 €", exact=True)).to_be_visible(timeout=120000)
        expect(page.locator('[data-testid="stPlotlyChart"] .js-plotly-plot')).to_have_count(3, timeout=60000)
        results.append({"view": "desktop_overview", "seconds": round(time.perf_counter() - start, 3)})
        page.screenshot(path=str(target / "desktop_overview.png"), full_page=True)
        page.get_by_role("heading", name="Contributo per paese", exact=True).scroll_into_view_if_needed()
        page.screenshot(path=str(target / "desktop_contributions.png"), full_page=True)
        page.get_by_test_id("stSidebar").get_by_text("Conto Economico", exact=True).click()
        expect(page.get_by_role("heading", name="Conto Economico", exact=True)).to_be_visible()
        expect(page.get_by_text("-14.214.839,86 €", exact=True)).to_be_visible()
        expect(page.locator('[data-testid="stPlotlyChart"] .js-plotly-plot')).to_have_count(1, timeout=60000)
        page.screenshot(path=str(target / "desktop_conto_economico.png"), full_page=True)
        results.append({"view": "desktop_conto_economico", "passed": True})
        page.get_by_test_id("stSidebar").get_by_text("Dettaglio e controlli", exact=True).click()
        expect(page.get_by_role("heading", name="Profili orari", exact=True)).to_be_visible()
        page.screenshot(path=str(target / "desktop_detail.png"), full_page=True)
        results.append({"view": "desktop_detail", "passed": True})
        mobile = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=1,
                                     is_mobile=True, has_touch=True)
        mobile_page = mobile.new_page()
        mobile_page.on("pageerror", lambda error: errors.append(str(error)))
        mobile_page.goto("http://127.0.0.1:8501", wait_until="domcontentloaded")
        expect(mobile_page.get_by_text("-540.640,69 €", exact=True)).to_be_visible(timeout=120000)
        expect(mobile_page.locator('[data-testid="stPlotlyChart"] .js-plotly-plot')).to_have_count(3, timeout=60000)
        overflow = mobile_page.evaluate("document.documentElement.scrollWidth > window.innerWidth + 1")
        if overflow:
            raise AssertionError("Overflow orizzontale su viewport mobile")
        mobile_page.screenshot(path=str(target / "mobile_overview.png"), full_page=True)
        mobile_page.get_by_role("heading", name="Contributo per controparte", exact=True).scroll_into_view_if_needed()
        mobile_page.screenshot(path=str(target / "mobile_contributions.png"), full_page=True)
        results.append({"view": "mobile_overview", "width": 390, "horizontal_overflow": overflow})
        if errors:
            raise AssertionError("Errori JavaScript: " + str(errors))
        browser.close()
    (target / "browser_validation.json").write_text(json.dumps({"passed": True, "checks": results,
          "javascript_errors": errors, "cloud_access_tested": False}, indent=2) + "\n", encoding="utf-8")
    print("QA browser desktop/mobile: OK")


if __name__ == "__main__":
    main()
