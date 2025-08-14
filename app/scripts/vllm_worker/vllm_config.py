from vllm.config import (
    VllmConfig, ModelConfig, ObservabilityConfig, 
    ParallelConfig, DeviceConfig, CacheConfig, LoRAConfig
)
from vllm.lora.request import LoRARequest

# a = LoRARequest(
    
# )
class Config:
    @classmethod
    def get_vllm(cls, model_id: str):
        model_config = ModelConfig(
            model=model_id,
            # max_model_len=8192, # Auto with model config file
            # max_seq_len_to_capture=16384,
            # enforce_eager=True
        )
        # if "qwen3" in model_id.lower():
        #     model_config.rope_scaling = {
        #             "rope_type": "yarn",
        #             "factor" : 4.0,
        #             "original_max_position_embedding": 32768
        #         }
        observability_config = ObservabilityConfig(
            
        )
        parallel_config = ParallelConfig(
            worker_cls="vllm.worker.worker.Worker",
            tensor_parallel_size=2,
            distributed_executor_backend="mp"
        )
        device_config = DeviceConfig(
            
        )
        cache_config = CacheConfig(
            gpu_memory_utilization=0.9
        )
        lora_config = LoRAConfig(
            max_lora_rank=16,
            max_loras=1,
        )
        vllm_config = VllmConfig(
            model_config=model_config,
            observability_config=observability_config,
            parallel_config=parallel_config,
            device_config=device_config,
            cache_config=cache_config,
            lora_config=lora_config
        )
        return vllm_config