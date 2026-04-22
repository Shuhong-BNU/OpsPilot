"""运行状态聚合服务."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.config import config
from app.core.milvus_client import milvus_manager
from app.services.database_service import database_service


class RuntimeStatusService:
    """汇总前端展示所需的系统状态。"""

    @staticmethod
    def _mask_secret(secret: str) -> str | None:
        if not secret:
            return None
        if len(secret) <= 8:
            return f"{secret[:2]}****"
        return f"{secret[:3]}****{secret[-4:]}"

    @staticmethod
    def _status_payload(healthy: bool, message: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = {
            "healthy": healthy,
            "status": "ready" if healthy else "unavailable",
            "message": message,
        }
        if extra:
            payload.update(extra)
        return payload

    def _probe_http_endpoint(self, url: str) -> dict[str, Any]:
        request = Request(url, headers={"Accept": "application/json"})
        try:
            with urlopen(request, timeout=1.5) as response:
                return self._status_payload(True, f"HTTP {response.status}", {"url": url})
        except HTTPError as exc:
            # 405/404 通常也表示服务已在线，只是方法或路径不匹配。
            healthy = exc.code < 500
            return self._status_payload(healthy, f"HTTP {exc.code}", {"url": url})
        except URLError as exc:
            return self._status_payload(False, str(exc.reason), {"url": url})
        except Exception as exc:  # pragma: no cover - 防御性兜底
            return self._status_payload(False, str(exc), {"url": url})

    def get_status(self) -> dict[str, Any]:
        dashscope_key = config.dashscope_api_key.strip()
        sqlite_ready = database_service.health_check()
        milvus_ready = milvus_manager.health_check()

        services = {
            "api": self._status_payload(True, "OpsPilot API 运行中", {"url": config.access_url}),
            "sqlite": self._status_payload(
                sqlite_ready,
                "SQLite 持久化可用" if sqlite_ready else "SQLite 不可用",
                {"path": str(Path(config.database_path))},
            ),
            "milvus": self._status_payload(
                milvus_ready,
                "Milvus 连接正常" if milvus_ready else "Milvus 未连接",
                {"address": f"{config.milvus_host}:{config.milvus_port}"},
            ),
            "mcp_cls": self._probe_http_endpoint(config.mcp_cls_url),
            "mcp_monitor": self._probe_http_endpoint(config.mcp_monitor_url),
        }

        return {
            "service": {
                "name": config.app_name,
                "title": config.app_title,
                "version": config.app_version,
                "mode": "开发" if config.debug else "生产",
            },
            "network": {
                "listen_url": config.listen_url,
                "access_url": config.access_url,
                "docs_url": config.docs_url,
            },
            "models": {
                "llm": config.dashscope_model,
                "embedding": config.dashscope_embedding_model,
                "rerank": config.dashscope_rerank_model,
                "rag": config.rag_model,
            },
            "providers": {
                "dashscope": {
                    "configured": bool(dashscope_key),
                    "masked_key": self._mask_secret(dashscope_key),
                }
            },
            "services": services,
            "logs": {
                "app": "logs/app_*.log",
                "cls": "logs/mcp_cls.log",
                "monitor": "logs/mcp_monitor.log",
            },
        }


runtime_status_service = RuntimeStatusService()
