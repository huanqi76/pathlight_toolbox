"""
Scrapes every record on a LinkedIn Interests tab that either
(a) auto-loads when you reach the bottom, or
(b) shows a “Show more results” button.

EDIT the ALL-CAP constants below if LinkedIn changes its DOM.
"""
import csv, pathlib, sys, textwrap
from playwright.async_api import async_playwright, TimeoutError as PWTimeout
from utils import *

# ─────────────────────────── USER SETTINGS ──────────────────────────────
START_URLS = build_linkedin_urls(fetch_handles())

SHOW_MORE_TEXT = "Show more results"

# one row per interest card
ITEM_SELECTOR = "*[id^='profilePagedListComponent'][id*='-COMPANIES-INTERESTS']"

# the company name inside the row
FULL_SELECTOR = (
    "*[id^='profilePagedListComponent'][id*='-COMPANIES-INTERESTS'] "
    "span:first-child"
)
# ─────────────────────────────────────────────────────────────────────────

# Safety knobs (tweak if LinkedIn is slow)
SCROLL_PAUSE_MS = 15000      # wait this long after each End / click
STALL_LIMIT     = 4         # end-presses with no new cards before give up
MAX_SCROLLS     = 300       # absolute cap (avoid infinite loop)

# ─────────────────────────────────────────────────────────────────────────

FLUSH_EVERY = 200
OUT_PATH = pathlib.Path(__file__).with_suffix(".csv")

def flush(buffer: list[list[str]], *, header_written: bool) -> bool:
    """
    Write buffered rows to disk and clear the buffer.  
    Returns True if a header line was just written (so caller knows).
    """
    if not buffer:
        return header_written         # nothing to do

    # create parent dirs if needed
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    write_header = not OUT_PATH.exists() and not header_written
    mode = "a" if OUT_PATH.exists() else "w"

    with OUT_PATH.open(mode, newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if write_header:
            w.writerow(["source_url", "name", "run_date"])
        w.writerows(buffer)

    print(f"✓ flushed {len(buffer):>4} rows → {OUT_PATH}")
    buffer.clear()
    return header_written or write_header

# ──────────────────────────── CORE LOGIC ────────────────────────────────
async def load_everything(ctx) -> None:
    """
    Scroll until ITEM_SELECTOR stops growing.
    • Always wheel-scroll the list container (never relies on End or buttons).
    • Waits only on the LinkedIn spinner — no networkidle, so no timeouts.
    """
    stalled, seen = 0, -1

    for _ in range(MAX_SCROLLS):
        # 1 ── scroll ~1 viewport on whichever element owns the scrollbar
        await ctx.evaluate("""
        () => {
            // 1) grab the first interest row
            const firstRow =
            document.querySelector('*[id^="profilePagedListComponent"]');
            if (!firstRow) return;

            // 2) walk up until we find an ancestor that can scroll
            const scrollBox = (function findScrollable(el) {
                while (el && el !== document.documentElement) {
                    const st = window.getComputedStyle(el);
                    if (
                        (st.overflowY === 'auto' || st.overflowY === 'scroll') &&
                        el.scrollHeight > el.clientHeight
                    ) return el;
                    el = el.parentElement;
                }
                return document.scrollingElement;          // fallback
            })(firstRow);

            // 3) move one viewport
            scrollBox.scrollBy({ top: scrollBox.clientHeight,
                                behavior: 'instant' });
        }
        """)

        # 2 ── wait for spinner cycle  (appears → disappears) or timeout
        try:
            # wait until spinner shows (max 5 s); ignore if it never appears
            await ctx.locator("div.artdeco-loader") \
                    .wait_for(state="attached", timeout=7_000)
            # then wait until it’s gone (max 15 s)
            await ctx.locator("div.artdeco-loader") \
                    .wait_for(state="detached", timeout=7_000)
        except PWTimeout:
            # Either spinner never appeared or stayed too long; keep going
            pass

        await ctx.wait_for_timeout(500)   # debounce

        # 3 ── progress check
        new_seen = await ctx.locator(ITEM_SELECTOR).count()
        if new_seen == seen:
            stalled += 1
            if stalled >= STALL_LIMIT:
                print("⇢ No new rows after", STALL_LIMIT, "tries — stopping.")
                break
        else:
            seen, stalled = new_seen, 0
            print(f"⇢ rows collected: {seen}")

async def scrape() -> None:
    async with async_playwright() as p:
        browser  = await p.chromium.launch(headless=False, slow_mo=250)
        context  = await browser.new_context(storage_state="/Users/anqihu/Desktop/investor_follow_tracker/auth/state.json")

        buffer: list[list[str]] = []
        header_written = False
        total_rows = 0

        try:
            for url in START_URLS:

                page     = await context.new_page()
                await page.goto(url, wait_until="domcontentloaded", timeout=70000)   

                await page.wait_for_selector(
                    "*[id^='profilePagedListComponent']",
                    state="attached",
                    timeout=15_000
                )
                print("Rows visible immediately:",
                    await page.locator(ITEM_SELECTOR).count())

                candidate = await page.evaluate("""
                () => {
                const row = document.querySelector('*[id^="profilePagedListComponent"]');
                if (!row) return null;

                let el = row;
                while (el && el !== document.documentElement) {
                    const style = window.getComputedStyle(el);
                    const canScroll =
                    (style.overflowY === 'auto' || style.overflowY === 'scroll') &&
                    el.scrollHeight > el.clientHeight;

                    if (canScroll) return el.className || el.id || '<<anonymous>>';
                    el = el.parentElement;
                }
                return 'document';
                }
                """)
                print("⇢ Scroll container Playwright found →", candidate) 

                first_batch = await page.locator(ITEM_SELECTOR).count()
                if first_batch == 0:
                    msg = textwrap.dedent(f"""
                        🛑 ITEM_SELECTOR matches 0 elements on the first screen.
                        Re-inspect the page and update ITEM_SELECTOR / FULL_SELECTOR.
                    """)
                    sys.exit(msg)

                await load_everything(page)
                names = await page.locator(FULL_SELECTOR).all_inner_texts()
                clean_names = [n.strip().split("\n")[0] for n in names]
                # print(f"{url}  → scraped {len(clean_names)} names")

                run_rows = [[url, name, TODAY] for name in names]   #  ← add TODAY
                buffer.extend(run_rows)
                total_rows += len(run_rows)

                # flush if we hit the threshold
                if len(buffer) >= FLUSH_EVERY:
                    header_written = flush(buffer, header_written=header_written)

                await page.close()

        finally:
            header_written = flush(buffer, header_written=header_written)
        
        print(f"⇢ {total_rows} rows scraped this run")