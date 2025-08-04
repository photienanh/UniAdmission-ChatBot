from fastapi import FastAPI
from config import SECRET_KEY
from backend import (
    DBSession,
    static_router,
    auth_router,
    chat_router,
    model_router,
    set_ping_filter,
    NoCacheOnDeleteMiddleWare, SessionMiddleware
)
set_ping_filter()

DBSession.setup()

app = FastAPI()
app.add_middleware(NoCacheOnDeleteMiddleWare)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
app.include_router(static_router, tags=["Static"]) # Use this due to diffirent in api of flask
app.include_router(auth_router, tags=["Authenticaton"])
app.include_router(chat_router, tags=["Chat"])
app.include_router(model_router, tags=["Models"])

if __name__ == "__main__":
    print("App starting")
    import uvicorn
    uvicorn.run(app)