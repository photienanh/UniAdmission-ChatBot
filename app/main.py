from config_ import os

from backend import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app)
    