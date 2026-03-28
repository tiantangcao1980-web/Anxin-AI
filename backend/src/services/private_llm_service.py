# -*- coding: utf-8 -*-
"""私有 LLM 检测与配置服务"""

from typing import List, Dict, Any, Optional

import httpx
from loguru import logger


class PrivateLLMService:
    """私有 LLM 检测与配置服务

    支持自动检测本地运行的 LLM 服务（Ollama / vLLM / LocalAI / LM Studio），
    并提供连接测试、推荐模型和部署指南。
    """

    LOCAL_PROVIDERS: Dict[str, Dict[str, Any]] = {
        "ollama": {"port": 11434, "health": "/api/tags", "name": "Ollama"},
        "vllm": {"port": 8000, "health": "/health", "name": "vLLM"},
        "localai": {"port": 8080, "health": "/readyz", "name": "LocalAI"},
        "lmstudio": {"port": 1234, "health": "/v1/models", "name": "LM Studio"},
    }

    # ------------------------------------------------------------------
    # 检测
    # ------------------------------------------------------------------

    async def detect_local_llm(self) -> List[Dict[str, Any]]:
        """
        扫描本地端口检测运行中的 LLM 服务。

        Returns:
            [{ provider, endpoint, status, models }]
        """
        detected: List[Dict[str, Any]] = []

        async with httpx.AsyncClient(timeout=3) as client:
            for provider_key, info in self.LOCAL_PROVIDERS.items():
                endpoint = f"http://127.0.0.1:{info['port']}"
                health_url = f"{endpoint}{info['health']}"
                try:
                    resp = await client.get(health_url)
                    if resp.status_code < 400:
                        models = self._extract_models(provider_key, resp)
                        detected.append({
                            "provider": provider_key,
                            "name": info["name"],
                            "endpoint": endpoint,
                            "status": "running",
                            "models": models,
                        })
                except httpx.ConnectError:
                    pass
                except Exception as e:
                    logger.debug(f"检测 {info['name']} 失败: {e}")

        return detected

    # ------------------------------------------------------------------
    # 连接测试
    # ------------------------------------------------------------------

    async def test_connection(
        self, endpoint: str, model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        测试连接 + 简单推理测试。

        Returns:
            { success, latency_ms, model_info, error? }
        """
        import time

        endpoint = endpoint.rstrip("/")
        # 先测试 /v1/models
        models_url = f"{endpoint}/v1/models"
        model_info: dict = {}

        async with httpx.AsyncClient(timeout=10) as client:
            try:
                resp = await client.get(models_url)
                if resp.status_code < 400:
                    data = resp.json()
                    models_list = data.get("data", [])
                    model_info = {
                        "available_models": [
                            m.get("id", m.get("name", "unknown"))
                            for m in models_list[:20]
                        ]
                    }
            except Exception:
                pass

            # 简单推理测试
            infer_model = model or (
                model_info.get("available_models", [None])[0]
                if model_info.get("available_models")
                else None
            )
            if not infer_model:
                return {
                    "success": False,
                    "latency_ms": 0,
                    "model_info": model_info,
                    "error": "未找到可用模型",
                }

            chat_url = f"{endpoint}/v1/chat/completions"
            payload = {
                "model": infer_model,
                "messages": [{"role": "user", "content": "你好"}],
                "max_tokens": 16,
            }

            try:
                start = time.monotonic()
                resp = await client.post(chat_url, json=payload, timeout=30)
                latency_ms = int((time.monotonic() - start) * 1000)
                resp.raise_for_status()
                return {
                    "success": True,
                    "latency_ms": latency_ms,
                    "model_info": model_info,
                }
            except Exception as e:
                return {
                    "success": False,
                    "latency_ms": 0,
                    "model_info": model_info,
                    "error": str(e),
                }

    # ------------------------------------------------------------------
    # 推荐模型
    # ------------------------------------------------------------------

    def get_recommended_models(self) -> List[Dict[str, Any]]:
        """返回法律场景推荐模型列表"""
        return [
            {
                "name": "Qwen2.5-7B-Instruct",
                "size": "7B",
                "description": "通义千问 7B，中文法律理解能力优秀，资源占用低",
                "min_vram_gb": 6,
                "provider": "ollama",
                "command": "ollama pull qwen2.5:7b-instruct",
            },
            {
                "name": "Qwen2.5-14B-Instruct",
                "size": "14B",
                "description": "通义千问 14B，法律推理和合同审查能力显著提升",
                "min_vram_gb": 12,
                "provider": "ollama",
                "command": "ollama pull qwen2.5:14b-instruct",
            },
            {
                "name": "GLM-4-9B-Chat",
                "size": "9B",
                "description": "智谱 GLM-4 9B，中文法律文书写作能力强",
                "min_vram_gb": 8,
                "provider": "ollama",
                "command": "ollama pull glm4:9b-chat",
            },
            {
                "name": "Yi-34B-Chat",
                "size": "34B",
                "description": "零一万物 34B，深度法律分析和长文本处理能力",
                "min_vram_gb": 24,
                "provider": "ollama",
                "command": "ollama pull yi:34b-chat",
            },
            {
                "name": "DeepSeek-V2-Chat",
                "size": "MoE-236B",
                "description": "DeepSeek MoE 架构，性价比极高，法律推理能力强",
                "min_vram_gb": 16,
                "provider": "vllm",
                "command": "vllm serve deepseek-ai/DeepSeek-V2-Lite-Chat",
            },
            {
                "name": "Llama-3-8B-Instruct",
                "size": "8B",
                "description": "Meta Llama 3，英文法律场景通用基座",
                "min_vram_gb": 6,
                "provider": "ollama",
                "command": "ollama pull llama3:8b-instruct",
            },
        ]

    # ------------------------------------------------------------------
    # 部署指南
    # ------------------------------------------------------------------

    def get_deployment_guide(self, provider: str) -> Dict[str, Any]:
        """返回指定提供商的部署指南"""
        guides: Dict[str, Dict[str, Any]] = {
            "ollama": {
                "provider": "ollama",
                "title": "Ollama 本地部署指南",
                "requirements": {
                    "os": "macOS / Linux / Windows (WSL2)",
                    "ram": ">=16GB 推荐",
                    "vram": ">=6GB (GPU 加速)",
                },
                "steps": [
                    {
                        "title": "安装 Ollama",
                        "command": "curl -fsSL https://ollama.ai/install.sh | sh",
                        "description": "一键安装 Ollama，macOS 也可通过 brew install ollama",
                    },
                    {
                        "title": "启动服务",
                        "command": "ollama serve",
                        "description": "启动 Ollama 服务，默认监听 127.0.0.1:11434",
                    },
                    {
                        "title": "下载推荐模型",
                        "command": "ollama pull qwen2.5:7b-instruct",
                        "description": "下载通义千问 7B 模型（适合法律场景）",
                    },
                    {
                        "title": "验证运行",
                        "command": 'ollama run qwen2.5:7b-instruct "你好"',
                        "description": "验证模型可以正常运行",
                    },
                ],
            },
            "vllm": {
                "provider": "vllm",
                "title": "vLLM 高性能推理部署指南",
                "requirements": {
                    "os": "Linux (CUDA 11.8+)",
                    "ram": ">=32GB 推荐",
                    "vram": ">=16GB (A100/4090 推荐)",
                },
                "steps": [
                    {
                        "title": "安装 vLLM",
                        "command": "pip install vllm",
                        "description": "安装 vLLM，需要 CUDA 环境",
                    },
                    {
                        "title": "启动服务",
                        "command": "python -m vllm.entrypoints.openai.api_server --model Qwen/Qwen2.5-14B-Instruct --port 8000",
                        "description": "以 OpenAI 兼容接口启动 vLLM 服务",
                    },
                ],
            },
            "localai": {
                "provider": "localai",
                "title": "LocalAI 部署指南",
                "requirements": {
                    "os": "macOS / Linux / Windows",
                    "ram": ">=8GB",
                    "docker": "推荐使用 Docker 部署",
                },
                "steps": [
                    {
                        "title": "Docker 部署",
                        "command": "docker run -p 8080:8080 localai/localai:latest",
                        "description": "使用 Docker 一键启动 LocalAI",
                    },
                    {
                        "title": "安装模型",
                        "command": "curl http://localhost:8080/models/apply -H 'Content-Type: application/json' -d '{\"url\": \"github:mudler/LocalAI/gallery/qwen2.5-7b-instruct.yaml\"}'",
                        "description": "通过 API 安装模型",
                    },
                ],
            },
            "lmstudio": {
                "provider": "lmstudio",
                "title": "LM Studio 桌面部署指南",
                "requirements": {
                    "os": "macOS / Windows / Linux",
                    "ram": ">=16GB 推荐",
                    "vram": ">=6GB (GPU 加速，可选)",
                },
                "steps": [
                    {
                        "title": "下载安装",
                        "command": "https://lmstudio.ai/download",
                        "description": "从官网下载 LM Studio 桌面应用",
                    },
                    {
                        "title": "搜索并下载模型",
                        "command": "在应用内搜索 Qwen2.5-7B-Instruct 并点击下载",
                        "description": "通过图形界面搜索和下载模型",
                    },
                    {
                        "title": "启动本地服务器",
                        "command": "在 Local Server 标签页点击 Start Server",
                        "description": "启动 OpenAI 兼容 API 服务，默认端口 1234",
                    },
                ],
            },
        }

        guide = guides.get(provider)
        if not guide:
            return {
                "provider": provider,
                "title": f"未知提供商: {provider}",
                "requirements": {},
                "steps": [],
                "error": f"不支持的提供商，可选: {', '.join(guides.keys())}",
            }
        return guide

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_models(
        provider_key: str, resp: httpx.Response
    ) -> List[str]:
        """从健康检查响应中提取模型列表"""
        try:
            data = resp.json()
        except Exception:
            return []

        if provider_key == "ollama":
            # /api/tags 返回 { models: [{ name, ... }] }
            return [m.get("name", "") for m in data.get("models", [])]
        elif provider_key in ("lmstudio", "vllm", "localai"):
            # /v1/models 返回 { data: [{ id, ... }] }
            return [
                m.get("id", m.get("name", ""))
                for m in data.get("data", [])
            ]
        return []
