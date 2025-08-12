import yaml
from vllm.config import (
    VllmConfig, ModelConfig, ObservabilityConfig, 
    ParallelConfig, DeviceConfig, CacheConfig
)
from dataclasses import asdict
import enum
import torch
from typing import Any

class ConfigParser:
    @classmethod
    def _serialize(cls, obj: object):
        if isinstance(obj, enum.Enum):
            return obj.value
        if isinstance(obj, torch.dtype):
            return str(obj)[6:]
        if isinstance(obj, dict):
            return {k: cls._serialize(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [cls._serialize(v) for v in obj]
        return obj
    @classmethod
    def _all_example_parse(cls, vllm_config: VllmConfig):
        config = {}
        model_config = vllm_config.model_config
        config.update(asdict(model_config))
        cache_config = vllm_config.cache_config
        config.update(asdict(cache_config))
        parallel_config = vllm_config.parallel_config
        config.update(asdict(parallel_config))
        scheduler_config = vllm_config.scheduler_config
        config.update(asdict(scheduler_config))
        device_config = vllm_config.device_config
        config.update(asdict(device_config))
        load_config = vllm_config.load_config
        config.update(asdict(load_config))
        lora_config = vllm_config.lora_config
        if lora_config: config.update(asdict(lora_config))
        speculative_config = vllm_config.speculative_config
        if speculative_config: config.update(asdict(speculative_config))
        decoding_config = vllm_config.decoding_config
        config.update(asdict(decoding_config))
        observability_config = vllm_config.observability_config
        if observability_config: config.update(asdict(observability_config))
        # quant_config = vllm_config.quant_config # In model config
        compilation_config = vllm_config.compilation_config
        if compilation_config: config.update(asdict(compilation_config))
        config: dict = cls._serialize(config)
        pop_keys = ["enabled_custom_ops", "disabled_custom_ops", "traced_files"]
        for key, value in config.items():
            if value is None:
                pop_keys.append(key)
        for pop_key in pop_keys:
            config.pop(pop_key)
        return config
    @classmethod
    def _all_example_parse_and_write(cls, vllm_config: VllmConfig, file_path: str = "config.yaml"):
        config = cls._all_example_parse(vllm_config)
        with open(file_path, 'w') as file:
            yaml.dump(config, file, default_flow_style=False, sort_keys=False)
    @classmethod
    def write(cls, config: dict[str, Any], file_path: str = "config.yaml"):
        config = cls._serialize(config)
        with open(file_path, 'w') as file:
            yaml.dump(config, file, default_flow_style=False, sort_keys=False)
    @classmethod
    def preset_1(cls) -> dict[str, Any]:
        return {
            "host": "127.0.0.1",
            "port": 8000,
            "model": "Qwen/Qwen3-0.6B",
            "dtype": torch.float16,
            "max_model_len": 4096,
            "enforce-eager": True,
            "max_lora_rank": 16,
            "max_loras": 1,
            "max_cpu_loras": 1,
            "gpu_memory_utilization": 0.9,
            "pipeline_parallel_size": 1,
            "tensor_parallel_size": 2,
            "data_parallel_size": 1,
            "data_parallel_backend": "mp",
            "worker_cls": "vllm.v1.worker.gpu_worker.Worker",
            "max_num_batched_tokens": 4096,
            "scheduler_cls": "vllm.core.scheduler.Scheduler",
        }
    @classmethod
    def change_model(cls, model_id: str, file_path: str = "config.yaml", tmp_path: str = "tmp.yaml"):
        with open(file_path, 'r') as file:
            config = yaml.safe_load(file)
        config["model"] = model_id
        with open(tmp_path, 'w') as file:
            yaml.dump(config, file, default_flow_style=False, sort_keys=False)