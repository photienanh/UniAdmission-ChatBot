from fastapi import FastAPI
from backend.database.jwt_ import SECRECT_KEY
from backend import (
    DBSession,
    static_router,
    auth_router,
    chat_router,
    # service_router # Not used yet
    NoCacheOnDeleteMiddleWare, SessionMiddleware
)

DBSession.setup()

app = FastAPI()
app.add_middleware(NoCacheOnDeleteMiddleWare)
app.add_middleware(SessionMiddleware, secret_key=SECRECT_KEY)
app.include_router(static_router, tags=["Static"]) # Use this due to diffirent in api of flask
app.include_router(auth_router, tags=["Authenticaton"])
app.include_router(chat_router, tags=["Chat"])
