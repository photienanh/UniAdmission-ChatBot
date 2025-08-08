from .openai_api import generate_search_keywords as openai_gen


def generate_search_keywords(message: str):
    result = openai_gen(message)
    while len(result) > 0 and result[0] == '"':
        result = result[1:]
    while len(result) > 0 and result[-1] == '"':
        result = result[:-1]
    return result