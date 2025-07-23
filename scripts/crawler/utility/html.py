from typing import NamedTuple
import re
import os
import aiofiles

class AnchorData(NamedTuple):
    href: str
    text: str

def get_root_url(url: str):
    return "/".join(url.split("/")[:3])
def url_reconstructor(path_url: str, url:str):
    if len(url) > 0 and url[-1] == "#":
        url = url[:-1]
    root_url = get_root_url(path_url)
    """
    Three type:
    1. Full url: http....
    2. Relative url: /home....
    3. Query: ?
    """
    if url.startswith("http://") or url.startswith("https://"):
        result = url
    elif url.startswith("/"):
        result = root_url + url
    else:
        result = path_url + url
    if "#" in result.split("/")[-1]:
        result = "#".join(result.split("#")[:-1])
    return result
def extract_anchor_data(html: str) -> list[AnchorData]:
    matches = re.findall(r'<a(.*?)/a>', html, re.DOTALL) # Shortest match, so it capture <a></a>
    urls = []
    for match in matches:
        hrefs = re.findall(r'href="(.*?)"', match)
        texts = re.findall(r'>(.*?)<', match)
        if hrefs:
            urls.append(AnchorData(hrefs[0], texts[0] if texts else ""))
    return urls

__all__ = [
    "AnchorData",
    "url_reconstructor",
    "extract_anchor_data"
]