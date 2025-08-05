import argparse, asyncio
from scraping.infinite_scroll import scrape
from processing.csv_to_sheet import push_to_gsheet

async def run():
    csv_path = await scrape()
    await push_to_gsheet(csv_path)

if __name__ == "__main__":
    asyncio.run(run())