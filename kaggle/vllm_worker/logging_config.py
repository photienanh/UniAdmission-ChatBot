"""
Cấu hình logging cho vLLM worker để tắt các log INFO không cần thiết
"""
import logging
import warnings
import os

def setup_logging():
    """
    Thiết lập logging để chỉ hiện ERROR, tắt hết WARNING và INFO
    """
    # Thiết lập biến môi trường để tắt log
    os.environ["VLLM_LOG_LEVEL"] = "ERROR"
    os.environ["VLLM_LOGGING_LEVEL"] = "ERROR"
    os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
    os.environ["TF_CPP_MIN_VLOG_LEVEL"] = "0"
    # Tắt tất cả warnings trước
    warnings.filterwarnings("ignore")
    warnings.filterwarnings("ignore", category=UserWarning)
    warnings.filterwarnings("ignore", category=FutureWarning)
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
    warnings.filterwarnings("ignore", message=".*")
    
    # Danh sách các logger cần tắt
    loggers_to_suppress = [
        "vllm",
        "vllm.engine", 
        "vllm.worker",
        "vllm.model_runner",
        "vllm.executor", 
        "vllm.executor.ray_utils",
        "vllm.executor_base",
        "vllm.config",
        "vllm.core",
        "vllm.core.scheduler",
        "vllm.engine.async_llm_engine",
        "vllm.engine.llm_engine", 
        "vllm.logger",
        "vllm.entrypoints",
        "vllm.entrypoints.api_server",
        "vllm.utils",
        "vllm.distributed",
        "ray",
        "ray.serve",
        "transformers",
        "torch.distributed",
        "torch.nn.parallel.distributed",
        "uvicorn.access",
        "uvicorn.error",
        "uvicorn",
        "tensorflow",
        "tf"
    ]
    
    # Thiết lập root logger chỉ hiện ERROR trước
    logging.basicConfig(
        level=logging.ERROR,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        force=True
    )
    
    # Thiết lập level ERROR cho tất cả các logger
    for logger_name in loggers_to_suppress:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.ERROR)
        logger.propagate = False
    
    # Thiết lập logging filter để block warnings
    class ErrorOnlyFilter(logging.Filter):
        def filter(self, record):
            # Chỉ cho phép ERROR và CRITICAL levels
            return record.levelno >= logging.ERROR
    
    # Áp dụng filter cho root logger
    root_logger = logging.getLogger()
    root_logger.addFilter(ErrorOnlyFilter())
    root_logger.setLevel(logging.ERROR)