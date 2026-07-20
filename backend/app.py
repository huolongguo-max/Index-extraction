"""
Index-extraction FastAPI 主入口
- 自动生成 Swagger 接口文档: /docs
- 自动生成 ReDoc 文档: /redoc
- SSE 实时数据流端点: /api/sse/stream
- 严格 Restful 规范
"""

import sys
from pathlib import Path

# 项目根目录
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

import traceback

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.core.config import APP_NAME, APP_ENV, DEBUG, BACKEND_HOST, BACKEND_PORT
from backend.core.response import resp

# ---- 新版路由 ----
from backend.api.rules import router as rules_router
from backend.api.data import router as data_router
from backend.api.control import router as control_router
from backend.api.sse import router as sse_router

from utils.log_utils import setup_logger, get_logger

# ==================== 初始化日志 ====================
setup_logger(name="api")
logger = get_logger()

# ==================== 创建 FastAPI 应用 ====================
app = FastAPI(
    title=APP_NAME,
    description=(
        "基于 XPath 行列交叉定位的网页表格 RPA 数据提取、桌面悬浮实时展示工具。"
        "支持规则管理、自动采集、SSE 实时推送。"
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ==================== CORS 中间件（前后端分离） ====================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:*", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== 全局异常捕获 — 统一返回格式，绝不裸露 500 ====================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """捕获所有未处理的异常，返回标准化错误响应"""
    tb = traceback.format_exc()
    logger.error(
        f"[UNHANDLED] {request.method} {request.url.path} — "
        f"{type(exc).__name__}: {exc}\n{tb}"
    )
    return JSONResponse(
        status_code=500,
        content={
            "code": 500,
            "msg": f"内部服务异常: {type(exc).__name__}" if DEBUG else "内部服务异常，请稍后重试",
            "data": {"detail": str(exc)} if DEBUG else None,
        },
    )

# ==================== 注册路由 ====================
app.include_router(rules_router)      # /api/rules/*
app.include_router(data_router)       # /api/data/*
app.include_router(control_router)    # /api/control/*
app.include_router(sse_router)        # /api/sse/*


# ==================== 根路径 ====================
@app.get("/", summary="API 根路径")
async def root():
    """返回 API 基本信息"""
    return resp.success(
        data={
            "app": APP_NAME,
            "env": APP_ENV,
            "version": "1.0.0",
            "docs": "/docs",
            "redoc": "/redoc",
            "endpoints": {
                "rules": "/api/rules",
                "data": "/api/data",
                "control": "/api/control",
                "sse": "/api/sse/stream",
            },
        },
        msg=f"欢迎使用 {APP_NAME} API",
    )


@app.get("/api/health", summary="健康检查")
async def health_check():
    """服务健康检查端点"""
    return resp.success(data={"status": "ok"}, msg="服务运行正常")


# ==================== 启动入口 ====================
if __name__ == "__main__":
    import uvicorn

    logger.info(f"启动 {APP_NAME} 服务 | 环境: {APP_ENV} | 调试: {DEBUG}")
    logger.info(f"接口文档: http://{BACKEND_HOST}:{BACKEND_PORT}/docs")

    uvicorn.run(
        "backend.app:app",
        host=BACKEND_HOST,
        port=BACKEND_PORT,
        reload=DEBUG,
        workers=1 if DEBUG else 4,
        log_level="info",
    )
