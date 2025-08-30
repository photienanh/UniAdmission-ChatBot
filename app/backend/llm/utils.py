import uuid
from typing import List

def generate_id() -> str:
    return str(uuid.uuid4())