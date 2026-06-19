import logging
from asyncio import Semaphore, timeout
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from urllib.parse import unquote, urlsplit

from playwright.async_api import Browser, Playwright, async_playwright
from playwright.async_api import Error as PlaywrightError
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from pypdf import PdfReader

from app.core.exceptions import (
    PDFReaderError,
    PDFRendererConfigurationError,
    PDFRenderError,
    PDFRenderTimeoutError,
    RenderCapacityError,
)

RESUME_ASSET_BASE_URL = "http://resume-assets.local/"
RESUME_ASSET_DIR = (
    Path(__file__).parent.parent / "templates/resume_templates"
).resolve()
CONTENT_TYPES = {
    ".css": "text/css",
    ".ttf": "font/ttf",
    ".otf": "font/otf",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
}


@dataclass
class PDFResult:
    pdf: bytes
    pages: int


logger = logging.getLogger(__name__)


async def route_assets(route):
    request_url = route.request.url
    parsed_url = urlsplit(request_url)
    rel_path = unquote(parsed_url.path.lstrip("/"))
    asset_path = (RESUME_ASSET_DIR / rel_path).resolve()

    try:
        asset_path.relative_to(RESUME_ASSET_DIR)
    except ValueError:
        logger.warning("resume_asset_path_rejected", extra={"url": request_url})
        await route.abort()
        return

    if not asset_path.is_file():
        logger.warning(
            "resume_asset_missing",
            extra={"url": request_url, "path": str(asset_path)},
        )
        await route.abort()
        return

    content_type = CONTENT_TYPES.get(asset_path.suffix.lower())
    if content_type is None:
        logger.warning(
            "resume_asset_type_rejected",
            extra={"url": request_url, "path": str(asset_path)},
        )
        await route.abort()
        return

    await route.fulfill(
        path=str(asset_path),
        content_type=content_type,
    )


def log_request_failed(request):
    logger.warning(
        "playwright_request_failed",
        extra={"url": request.url, "failure": request.failure},
    )


class PDFManager:
    def __init__(
        self,
        max_concurrency: int = 2,
        timeout: float = 10,
        render_timeout: float = 10,
    ):
        self.max_concurrency = max_concurrency
        self.semaphore = None
        self.timeout = timeout
        self.render_timeout = render_timeout
        self.playwright: Playwright | None = None
        self.browser: Browser | None = None

    async def start(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        self.semaphore = Semaphore(self.max_concurrency)

    async def stop(self):
        if self.browser:
            await self.browser.close()
            self.browser = None
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None

    async def create_pdf(self, html_string: str) -> PDFResult:
        # set up timeout
        # set up semaphore
        # try block for playwright
        if self.semaphore is None or self.playwright is None or self.browser is None:
            raise PDFRendererConfigurationError()
        try:
            async with timeout(self.timeout):
                await self.semaphore.acquire()
        except TimeoutError:
            raise RenderCapacityError()

        try:
            async with await self.browser.new_context() as context:
                async with await context.new_page() as page:
                    page.set_default_timeout(self.render_timeout * 1000)
                    page.on("requestfailed", log_request_failed)
                    try:
                        await page.route(f"{RESUME_ASSET_BASE_URL}**", route_assets)
                        await page.emulate_media(media="print")
                        await page.set_content(html_string, wait_until="load")
                        try:
                            async with timeout(self.render_timeout):
                                await page.evaluate("() => document.fonts.ready")
                        except TimeoutError:
                            raise PDFRenderTimeoutError()
                        pdf_bytes = await page.pdf(
                            prefer_css_page_size=True,
                            print_background=True,
                        )
                    except PlaywrightTimeoutError:
                        raise PDFRenderTimeoutError()
                    except PlaywrightError:
                        raise PDFRenderError()
                    try:
                        pdf_doc = PdfReader(BytesIO(pdf_bytes))
                    except Exception:
                        raise PDFReaderError()
                    return PDFResult(pdf=pdf_bytes, pages=len(pdf_doc.pages))
        finally:
            self.semaphore.release()
