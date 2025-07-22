from urllib.parse import urlparse
from .common import *
class BasicPriority(IPriority):
    def __init__(self, website: str):
        self.website = urlparse(website)
        self.netloc = self.website.netloc
        self.site = self.netloc.replace("www.", "")
        self.site_name = self.site.split(".")[0]
    def score(self, url: str, text: str):
        l_text = text.lower()
        priority_map = {
            "tuyển sinh": 100,
            "xét tuyển": 100,
            "đào tạo": 100,
            "chỉ tiêu": 100,
            "học phí": 100,
            "học bổng": 100,
            "số liệu": 50,
            "ba công khai": 150,
            "báo cáo thường niên": 150,
            "cơ cấu": 100,
            "bậc đại học": 100,
            "đào tạo đại học": 200,
            "đào tạo bậc đại học": 200,
            "đào tạo thạc sĩ": 30,
            "đào tạo tiến sĩ": 30,
            "đội ngũ": 90,
            "cán bộ": 90,
            "chế độ": 90,
            "thông tin": 50,
            "giới thiệu": 50,
            "khoa": 40
        }
        min_priority_list = [
            "ảnh",
            "video"
        ]
        for k, v in priority_map.items():
            if k in l_text:
                return v
        if self.netloc in url:
            return 10
        elif self.site in url:
            return 9
        elif self.site_name in url:
            return 8
        else:
            for p in min_priority_list:
                if p in l_text:
                    return 1
            else:
                return 2
    def priority(self, key: UrlKey):
        return (key.score / key.level if key.level != 0 else 0, key.index, key.retry)
    