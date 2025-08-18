import os
from .utils import *
IS_DEVELOPEMENT = bool_(os.getenv("IS_DEVELOPMENT", True))
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dwwawdjdwawwdsawra213adwdawm908421")
JWT_DURATION = int(os.getenv("JWT_DURATION", "3600"))

