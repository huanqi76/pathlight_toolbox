import fastapi
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi import HTTPException

from backend import *
from frontend import *
from backend.run import scrape

from dotenv import load_dotenv
load_dotenv()

app = fastapi.FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

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

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=2000)