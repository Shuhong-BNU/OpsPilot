"""轻量监控接口."""

from fastapi import APIRouter, Query, Response

from app.services.metrics_service import metrics_service

router = APIRouter()


@router.get("/metrics")
async def get_metrics(format: str = Query(default="json")):
    """返回结构化指标，支持简易 Prometheus 格式."""
    if format == "prometheus":
        return Response(
            content=metrics_service.render_prometheus(),
            media_type="text/plain; version=0.0.4",
        )

    return {
        "code": 200,
        "message": "success",
        "data": metrics_service.snapshot(),
    }
