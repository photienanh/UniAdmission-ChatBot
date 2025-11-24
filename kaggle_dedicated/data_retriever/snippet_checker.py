"""
Snippet Sufficiency Checker
Kiểm tra snippet từ search results có đủ thông tin để trả lời câu hỏi không
"""
from typing import Protocol
from .schema import SearchResult
from server import GenerationParams


class SnippetCheckerProtocol(Protocol):
    """Protocol cho snippet checker"""
    async def is_sufficient(
        self, 
        snippet: str, 
        title: str, 
        query: str,
        url: str,
        params: GenerationParams
    ) -> bool:
        """Kiểm tra snippet có đủ thông tin không"""
        ...


class HeuristicSnippetChecker:
    """
    Heuristic-based checker: nhanh, không cần LLM
    CHỈ dùng snippet cho các câu hỏi DỄ (địa chỉ, số điện thoại, email)
    Các câu hỏi khác (học phí, chương trình, ...) → luôn crawl
    """
    
    def __init__(
        self,
        min_snippet_length: int = 100,
        min_keyword_match_ratio: float = 0.5
    ):
        self.min_snippet_length = min_snippet_length
        self.min_keyword_match_ratio = min_keyword_match_ratio
        
        # Whitelist: Chỉ các query type này mới dùng snippet
        # Các query khác → luôn crawl
        self.snippet_suitable_queries = {
            # Địa chỉ
            "địa chỉ", "ở đâu", "tại đâu", "địa điểm", "nơi",
            # Số điện thoại
            "số điện thoại", "điện thoại", "phone", "hotline", "liên hệ",
            # Email
            "email", "mail", "thư điện tử", "e-mail",
            # Website
            "website", "trang web", "web", "url"
        }
    
    def _extract_keywords(self, text: str) -> set[str]:
        """Trích xuất keywords từ text, loại bỏ stop words"""
        stop_words = {
            "là", "của", "và", "cho", "với", "từ", "trong", "đến", "theo", 
            "năm", "2025", "2024", "các", "một", "những", "được", "có", 
            "không", "nào", "để", "về", "sẽ", "đã", "ai", "gì", "như",
            "số", "điện", "thoại", "email", "mail", "địa", "chỉ", "ở", "đâu"
        }
        words = set(text.lower().split())
        # Loại bỏ stop words và từ quá ngắn
        keywords = {w for w in words if w not in stop_words and len(w) > 2}
        return keywords
    
    def _check_relevance(self, title: str, url: str, query: str) -> bool:
        """
        Kiểm tra title/URL có liên quan đến query không
        Ví dụ: Query "Số điện thoại UET" → title/URL phải có "UET" hoặc "Đại học Công nghệ"
        """
        query_keywords = self._extract_keywords(query)
        if len(query_keywords) == 0:
            return True  # Query quá ngắn, coi như relevant
        
        # Combine title + URL để check
        combined = f"{title} {url}".lower()
        combined_keywords = self._extract_keywords(combined)
        
        # Kiểm tra có keyword nào từ query xuất hiện trong title/URL không
        matched = query_keywords.intersection(combined_keywords)
        match_ratio = len(matched) / len(query_keywords) if len(query_keywords) > 0 else 0
        
        # Nếu match >= 30% keywords → relevant
        return match_ratio >= 0.3
    
    
    def _is_snippet_suitable_query(self, query: str) -> bool:
        """
        Kiểm tra query có phải loại "dễ" (địa chỉ, số điện thoại, email) không
        Chỉ những query này mới dùng snippet, còn lại → luôn crawl
        """
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in self.snippet_suitable_queries)
    
    async def is_sufficient(
        self,
        snippet: str,
        title: str,
        query: str,
        url: str,
        params: GenerationParams
    ) -> bool:
        """
        Kiểm tra snippet có đủ thông tin để trả lời query không
        
        Logic:
        1. CHỈ check snippet cho các query "dễ" (địa chỉ, số điện thoại, email)
        2. Các query khác → luôn return False (phải crawl)
        3. Với query "dễ": 
           - Kiểm tra snippet có chứa thông tin cụ thể không
           - Kiểm tra title/URL có liên quan đến query không (quan trọng!)
        """
        # Bước 1: Kiểm tra query có phải loại "dễ" không
        if not self._is_snippet_suitable_query(query):
            # Query không phải loại "dễ" → luôn crawl
            return False
        
        # Bước 2: Chỉ check snippet cho query "dễ"
        combined_text = f"{title} {snippet}".strip()
        combined_lower = combined_text.lower()
        
        # 2.1. Kiểm tra error/placeholder messages
        error_indicators = [
            "truy cập bị chặn", "error", "not found", "404", "403",
            "click here", "xem thêm", "đọc tiếp", "xem chi tiết",
            "bấm vào đây", "tìm hiểu thêm"
        ]
        if any(indicator in combined_lower for indicator in error_indicators):
            return False
        
        # 2.2. Kiểm tra title/URL có liên quan đến query không (QUAN TRỌNG!)
        is_relevant = self._check_relevance(title, url, query)
        if not is_relevant:
            # Title/URL không liên quan đến query → không đủ
            return False
        
        # 2.3. Kiểm tra có thông tin cụ thể trong snippet
        query_lower = query.lower()
        import re
        
        # Địa chỉ
        if any(word in query_lower for word in ["địa chỉ", "ở đâu", "tại đâu", "địa điểm"]):
            address_indicators = ["đường", "phố", "quận", "huyện", "tỉnh", "thành phố", "tại", "ở"]
            if any(indicator in combined_lower for indicator in address_indicators):
                # Có từ khóa địa chỉ → kiểm tra có số nhà/đường không
                if re.search(r'\d+', combined_text):  # Có số (số nhà, số đường)
                    return True
                # Hoặc có đủ dài
                if len(combined_text) > self.min_snippet_length:
                    return True
            return False
        
        # Số điện thoại
        if any(word in query_lower for word in ["số điện thoại", "điện thoại", "phone", "hotline", "liên hệ"]):
            # Pattern số điện thoại Việt Nam: 0xxx-xxx-xxx hoặc 0xxxxxxxxx
            phone_patterns = [
                r'0\d{9,10}',  # 0123456789 hoặc 01234567890
                r'0\d{3}[-.\s]?\d{3}[-.\s]?\d{4}',  # 0123-456-7890
                r'\(\d{3,4}\)\s?\d{3}[-.\s]?\d{4}',  # (024) 3754-7461
            ]
            for pattern in phone_patterns:
                if re.search(pattern, combined_text):
                    # Có số điện thoại + title/URL relevant → đủ
                    return True
            return False
        
        # Email
        if any(word in query_lower for word in ["email", "mail", "thư điện tử", "e-mail"]):
            # Pattern email: xxx@xxx.xxx
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            if re.search(email_pattern, combined_text):
                # Có email + title/URL relevant → đủ
                return True
            return False
        
        # Website
        if any(word in query_lower for word in ["website", "trang web", "web", "url"]):
            # Pattern URL: http:// hoặc https:// hoặc www.
            url_pattern = r'(https?://|www\.)[^\s]+'
            if re.search(url_pattern, combined_text, re.IGNORECASE):
                return True
            # Hoặc có đủ dài
            if len(combined_text) > self.min_snippet_length:
                return True
            return False
        
        # Nếu không match bất kỳ loại nào → không đủ
        return False


class LLMSnippetChecker:
    """
    LLM-based checker: chính xác hơn nhưng chậm hơn
    Dùng LLM để đánh giá snippet có đủ thông tin không
    """
    
    def __init__(self, llm_model):
        self.llm_model = llm_model
    
    async def is_sufficient(
        self,
        snippet: str,
        title: str,
        query: str,
        url: str,
        params: GenerationParams
    ) -> bool:
        """
        Dùng LLM để kiểm tra snippet có đủ thông tin không
        """
        prompt = f"""Bạn là trợ lý đánh giá thông tin. Hãy kiểm tra xem snippet sau có đủ thông tin để trả lời câu hỏi không.

Câu hỏi: {query}

Tiêu đề: {title}
URL: {url}
Snippet: {snippet}

Trả lời chỉ bằng "CÓ" nếu snippet đủ thông tin, hoặc "KHÔNG" nếu cần đọc thêm trang web."""

        # Gọi LLM (cần implement theo model protocol của bạn)
        # Ví dụ:
        # response = await self.llm_model.generate(prompt, max_tokens=10)
        # return "CÓ" in response.upper()
        
        # Tạm thời fallback về heuristic
        checker = HeuristicSnippetChecker()
        return await checker.is_sufficient(snippet, title, query, url, params)

