import fastapi
import uvicorn
import re
import os
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi import HTTPException
from typing import List, Optional

from backend import *
from frontend import *
from backend.run import scrape
from backend.database import init_db
from backend.connection_service import ConnectionService

from dotenv import load_dotenv
load_dotenv()

@asynccontextmanager
async def lifespan(app: fastapi.FastAPI):
    await init_db()
    yield

app = fastapi.FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get('/')
async def root():
    return FileResponse('frontend/index.html')

# @app.get('/query')
# async def query(handle: str = None):
#     # query existing results for linkedin handles

@app.post('/scrape')
async def scrape_endpoint():
    try:
        result = await scrape()
        return JSONResponse({
            "status": "success",
            "message": "Scraping completed successfully",
            "data_count": len(result[::2]) if result else 0
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}")

@app.get('/connections')
async def get_connections(handle: Optional[str] = None):
    """Get connections for a specific handle or all connections"""
    try:
        if handle:
            connections = await ConnectionService.get_connections_by_handle(handle)
        else:
            # Extract handle from URL if available
            url = os.getenv("URL")
            if url:
                match = re.search(r"/in/([^/]+)/details", url)
                if match:
                    current_handle = match.group(1)
                    connections = await ConnectionService.get_connections_by_handle(current_handle)
                else:
                    connections = await ConnectionService.get_all_connections()
            else:
                connections = await ConnectionService.get_all_connections()
        
        return JSONResponse({
            "status": "success",
            "connections": [
                {
                    "id": conn.id,
                    "handle": conn.handle,
                    "company": conn.company,
                    "date_scraped": conn.date_scraped.isoformat()
                }
                for conn in connections
            ],
            "count": len(connections)
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve connections: {str(e)}")

@app.post('/migrate')
async def migrate_csv_data():
    """Migrate existing CSV data to PostgreSQL"""
    try:
        migrated_count = await ConnectionService.migrate_from_csv()
        return JSONResponse({
            "status": "success",
            "message": f"Migration completed successfully",
            "migrated_count": migrated_count
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Migration failed: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=2000)