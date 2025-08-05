import logging

class PingAccessLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool | logging.LogRecord:
        return "/request" not in record.getMessage()
    
def set_ping_filter():
    uvicorn_logger = logging.getLogger("uvicorn.access")
    uvicorn_logger.addFilter(PingAccessLogFilter())