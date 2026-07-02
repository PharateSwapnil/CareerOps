"""Drives a real, visible (headed) browser via Playwright to assist with
filling out a job application form.

IMPORTANT - NOT LIVE-TESTED: this module could not be executed or verified
end-to-end in the dev sandbox this was written in. `pip install playwright`
succeeds, but `playwright install chromium` (which downloads the actual
browser binary, ~150-300MB from cdn.playwright.dev) failed - that host
isn't in this sandbox's network egress allowlist. The decision logic this
module calls into (field_classifier.py) is fully unit-tested; this module's
own Playwright-driving code is not, and should be manually verified against
a real browser and a real application form (Greenhouse and Lever are the
best starting points, since this project already has first-class support
for both as job providers) before being relied on.

SAFETY PROPERTIES - these are load-bearing, not incidental:
- Always launches Playwright in HEADED mode (a real, visible browser
  window) - never headless. The user must be able to see everything the
  automation does, in real time, on their own screen.
- Never attempts to solve a CAPTCHA. A CAPTCHA anywhere on the page halts
  automation and hands control back to the user.
- Never fills a password field or otherwise attempts to authenticate.
  Any password input on the page halts automation.
- Never clicks the final "Submit"/"Apply" button. Once the form is filled
  as far as it safely can be, the session moves to AWAITING_SUBMIT and
  stops - the human reviews the filled form and clicks Submit themselves,
  in the real browser window, every single time. This isn't a fallback for
  an edge case; it's the mandatory final step of every session.
- Only fills values that came from the user's own CareerOps++ profile/resume
  data - nothing is fetched from elsewhere or invented.
"""
import logging

from app.services.browser_automation.field_classifier import (
    ApplicantProfile,
    DetectedField,
    PauseReason,
    build_fill_plan,
    page_has_auth_signal,
    page_has_captcha_signal,
)

logger = logging.getLogger(__name__)


class PlaywrightNotAvailableError(Exception):
    """Raised when the playwright package or its browser binary isn't
    installed - a clear, actionable error rather than a bare ImportError,
    since this is an optional heavy dependency (see requirements.txt)."""


class BrowserAutomationSession:
    """One in-process, in-memory automation session, wrapping a live
    Playwright browser/page. Not persisted across server restarts - the DB
    row (ApplicationAutomationSession) is the durable audit trail; this
    object is the live handle, held in session_manager.py's registry.
    """

    def __init__(self, session_id: int, job_url: str, profile: ApplicantProfile) -> None:
        self.session_id = session_id
        self.job_url = job_url
        self.profile = profile
        self._playwright = None
        self._browser = None
        self._page = None
        self.filled_fields: list[tuple[str, str]] = []

    async def start(self) -> tuple[str, str | None]:
        """Launches a headed browser, navigates to the job URL, and runs
        one fill pass. Returns (status, pause_detail)."""
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise PlaywrightNotAvailableError(
                "playwright is not installed. Run `pip install playwright` "
                "and `playwright install chromium` to enable browser-assisted "
                "applications."
            ) from exc

        try:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(headless=False)
            self._page = await self._browser.new_page()
            await self._page.goto(self.job_url, wait_until="domcontentloaded")
        except Exception as exc:
            raise PlaywrightNotAvailableError(
                f"Could not launch a browser (browser binary likely not installed - "
                f"run `playwright install chromium`): {exc}"
            ) from exc

        return await self._scan_and_fill()

    async def resume(self) -> tuple[str, str | None]:
        """Called after the user has manually handled a pause (solved the
        CAPTCHA, logged in, or filled the field the automation couldn't).
        Re-scans the current page state and continues."""
        if self._page is None:
            raise RuntimeError("Session was never started or has already been closed")
        return await self._scan_and_fill()

    async def close(self) -> None:
        if self._browser is not None:
            await self._browser.close()
        if self._playwright is not None:
            await self._playwright.stop()
        self._page = None
        self._browser = None
        self._playwright = None

    async def _scan_and_fill(self) -> tuple[str, str | None]:
        page = self._page

        page_html = await page.content()
        if page_has_captcha_signal(page_html):
            return "paused_captcha", "A CAPTCHA was detected on the page"

        page_text = await page.inner_text("body")
        if page_has_auth_signal(page_text):
            # Confirmed further by an actual password input, not just the
            # word "login" appearing somewhere incidental on the page.
            password_inputs = await page.query_selector_all('input[type="password"]')
            if password_inputs:
                return "paused_auth", "A login/authentication form was detected"

        detected_fields = await self._detect_fields(page)
        plan = build_fill_plan(detected_fields, self.profile)

        for field, value in plan.fills:
            await self._fill_field(page, field, value)
            self.filled_fields.append((field.label, self._preview(value)))

        if plan.pause_reason == PauseReason.AUTH:
            return "paused_auth", plan.pause_detail
        if plan.pause_reason == PauseReason.UNKNOWN_REQUIRED_FIELD:
            return "paused_unknown_field", plan.pause_detail

        return "awaiting_submit", None

    async def _detect_fields(self, page) -> list[DetectedField]:
        """Scans the page for form inputs and their best-effort labels.
        Label resolution (matching an <input> to its <label>) is the part
        most likely to need real-world tuning per-ATS-platform once this
        can actually be tested against live forms."""
        raw_fields = await page.evaluate(
            """
            () => {
                const inputs = Array.from(document.querySelectorAll('input, textarea, select'));
                return inputs.map(el => {
                    let label = '';
                    if (el.labels && el.labels.length > 0) {
                        label = el.labels[0].innerText;
                    } else if (el.getAttribute('aria-label')) {
                        label = el.getAttribute('aria-label');
                    } else if (el.placeholder) {
                        label = el.placeholder;
                    }
                    return {
                        label: label || '',
                        input_type: el.type || el.tagName.toLowerCase(),
                        name: el.name || el.id || '',
                        required: el.required || false,
                    };
                });
            }
            """
        )
        return [
            DetectedField(
                label=f["label"],
                input_type=f["input_type"],
                name=f["name"],
                required=f["required"],
            )
            for f in raw_fields
        ]

    async def _fill_field(self, page, field: DetectedField, value: str) -> None:
        # NOTE: matching back from a DetectedField to the actual page
        # element for filling is left as a best-effort name-attribute
        # selector here; a more robust implementation would carry the
        # element handle through from _detect_fields rather than
        # re-querying by name. Flagged as a real gap to close during live
        # testing, not glossed over - see the module docstring.
        if not field.name:
            return
        selector = f'[name="{field.name}"]'
        if field.input_type == "file":
            await page.set_input_files(selector, value)
        else:
            await page.fill(selector, value)

    @staticmethod
    def _preview(value: str) -> str:
        return value if len(value) <= 60 else value[:57] + "..."
