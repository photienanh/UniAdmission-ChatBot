from fastapi import FastAPI
from config import SECRET_KEY
from backend import (
    DBSession,
    static_router,
    auth_router,
    chat_router,
    service_router,
    NoCacheOnDeleteMiddleWare, SessionMiddleware
)

DBSession.setup()

app = FastAPI()
app.add_middleware(NoCacheOnDeleteMiddleWare)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
app.include_router(static_router, tags=["Static"]) # Use this due to diffirent in api of flask
app.include_router(auth_router, tags=["Authenticaton"])
app.include_router(chat_router, tags=["Chat"])
app.include_router(service_router, tags=["Service"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app)