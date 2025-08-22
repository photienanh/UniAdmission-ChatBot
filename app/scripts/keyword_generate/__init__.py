from .openai_api import generate_search_keywords as openai_gen


def generate_search_keywords(message: str):
    return openai_gen(message)