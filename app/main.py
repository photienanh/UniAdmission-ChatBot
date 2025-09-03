from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv("server.env")

from backend import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app)
    