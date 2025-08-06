import json
import os
import re
import sys
import textwrap
import asyncio
import csv
from datetime import datetime
from playwright.async_api import async_playwright, TimeoutError as PWTimeout

from dotenv import load_dotenv

load_dotenv()

async def scrape():

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=250)
        context = await browser.new_context(storage_state=os.getenv("STORAGE_STATE_PATH"))

        page = await context.new_page()
        await page.goto(os.getenv("URL"), wait_until="domcontentloaded", timeout=70000)

        await page.wait_for_selector(
            "*[id^='profilePagedListComponent']",
            state="attached",
            timeout=15_000
        )
        print("Rows visible immediately:",
              await page.locator(os.getenv("ITEM_SELECTOR")).count())

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

        await scroll(page)
        await page.close()

async def scroll(ctx):
    stalled, seen = 0, -1
    names = []

    for _ in range(int(os.getenv("MAX_SCROLLS"))):
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

        await ctx.wait_for_timeout(500)

        # 3 ── progress check
        new_seen = await ctx.locator(os.getenv("ITEM_SELECTOR")).count()
        if new_seen == seen:
            stalled += 1
            if stalled >= int(os.getenv("STALL_LIMIT")):
                print("⇢ No new rows after", int(os.getenv("STALL_LIMIT")), "tries — stopping.")
                break
        else:
            seen, stalled = new_seen, 0
            names = await ctx.locator(os.getenv("FULL_SELECTOR")).all_inner_texts()

            match = re.search(r"/in/([^/]+)/details", os.getenv("URL"))
            handle = match.group(1)
            current_date = datetime.now().strftime("%Y-%m-%d")
            
            # Write to CSV
            csv_filename = "results.csv"
            file_exists = os.path.exists(csv_filename)
            
            with open(csv_filename, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                
                # Write header if file doesn't exist
                if not file_exists:
                    writer.writerow(["handle", "company", "date"])
                
                # Write new companies (every other item in names)
                for company in names[::2]:
                    writer.writerow([handle, company, current_date])
            
            print(f"⇢ rows collected: {len(names[::2])}")

    return names

# asyncio.run(scrape())