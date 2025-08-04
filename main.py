import fastapi
import uvicorn

from backend import *
from frontend import *

from dotenv import load_dotenv
load_dotenv()

app = fastapi.FastAPI()

@app.get('/query')
async def query(handle: str = None):
    # query existing results for linkedin handles

@app.get('/scrape')
async def scrape(handle: str = None):
    # scrape results, return new ones

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=2000)