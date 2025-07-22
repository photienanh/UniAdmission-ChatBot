from .common import IFilter
class BasicFilter(IFilter):
    def __init__(self):
        pass
    def filter(self, recorded: set, url: str, text: str):
        black_lists = [
            "javascript",
            "youtube.com",
            "zalo.me",
            "tiktok.com",
            "twitter.com",
            "facebook.com",
            ".jpg",
            ".png",
            ".webp",
            ".avif",
            ".ico",
            ".pdf",
            ".txt"
        ]
        if len(url) < 200:
            for block in black_lists:
                if block in url:
                    return False
            return True
        return False