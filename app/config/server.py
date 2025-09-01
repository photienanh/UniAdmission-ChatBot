import os
from .utils import *
from dotenv import load_dotenv
load_dotenv()

IS_DEVELOPEMENT = bool_(os.getenv("IS_DEVELOPMENT"))
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_DURATION = int(os.getenv("JWT_DURATION"))