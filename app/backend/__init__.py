from .static import router as static_router
from .auth import router as auth_router
from .service_hub import router as service_router
from .chat import router as chat_router
from .database import DBSession

from .middlewares import NoCacheOnDeleteMiddleWare, SessionMiddleware