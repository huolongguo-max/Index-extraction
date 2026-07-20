#!/usr/bin/env bash
# ============================================================
# Index-extraction 一键启动脚本
# 用法: chmod +x start.sh && ./start.sh
# ============================================================
set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

BACKEND_PORT=18000
FRONTEND_PORT=15173

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'

cleanup() {
    echo ""
    echo -e "${YELLOW}正在停止所有服务...${NC}"
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    kill $WINDOW_PID 2>/dev/null
    wait $BACKEND_PID 2>/dev/null
    wait $FRONTEND_PID 2>/dev/null
    wait $WINDOW_PID 2>/dev/null
    echo -e "${GREEN}所有服务已停止${NC}"
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

echo "============================================"
echo -e "${CYAN}  Index-extraction 启动中...${NC}"
echo "============================================"

# ---- 1. 检查 Python ----
if ! command -v python3 &>/dev/null; then
    echo -e "${RED}错误: 未找到 python3，请先安装 Python 3.10+${NC}"
    exit 1
fi

# ---- 2. 自动安装 Python 依赖 ----
echo -e "${CYAN}[1/5] 检查 Python 依赖...${NC}"
MISSING=""
python3 -c "import fastapi" 2>/dev/null || MISSING="$MISSING fastapi"
python3 -c "import uvicorn" 2>/dev/null || MISSING="$MISSING uvicorn"
python3 -c "import pydantic" 2>/dev/null || MISSING="$MISSING pydantic"
python3 -c "import dotenv" 2>/dev/null || MISSING="$MISSING python-dotenv"
python3 -c "import loguru" 2>/dev/null || MISSING="$MISSING loguru"
python3 -c "import httpx" 2>/dev/null || MISSING="$MISSING httpx"
if [ -n "$MISSING" ]; then
    echo -e "${YELLOW}  安装缺失依赖: $MISSING${NC}"
    pip3 install -q $MISSING
fi

# Selenium + PyQt6 可选
python3 -c "import selenium" 2>/dev/null || \
    echo -e "${YELLOW}  提示: 采集引擎未安装，运行 pip install selenium webdriver-manager${NC}"
python3 -c "from PyQt6.QtWidgets import QApplication" 2>/dev/null || \
    echo -e "${YELLOW}  提示: 悬浮窗未安装，运行 pip install PyQt6${NC}"
echo -e "${GREEN}  Python 依赖就绪${NC}"

# ---- 3. 自动安装前端依赖 ----
echo -e "${CYAN}[2/5] 检查前端依赖...${NC}"
if [ ! -d "frontend/node_modules" ]; then
    echo -e "${YELLOW}  正在安装前端依赖（仅首次需要）...${NC}"
    cd frontend && npm install --silent 2>/dev/null && cd ..
fi
echo -e "${GREEN}  前端依赖就绪${NC}"

# ---- 4. 启动后端 ----
echo -e "${CYAN}[3/5] 启动后端 API（端口 $BACKEND_PORT）...${NC}"
python3 -c "
import sys; sys.path.insert(0, '.')
from backend.app import app
import uvicorn
uvicorn.run(app, host='0.0.0.0', port=$BACKEND_PORT, log_level='warning')
" &
BACKEND_PID=$!
sleep 2

if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo -e "${RED}错误: 后端启动失败${NC}"
    exit 1
fi
echo -e "${GREEN}  后端已启动 → http://localhost:${BACKEND_PORT}${NC}"

# ---- 5. 启动前端 ----
echo -e "${CYAN}[4/5] 启动前端页面（端口 $FRONTEND_PORT）...${NC}"
cd frontend
VITE_API_BASE_URL="http://localhost:$BACKEND_PORT" \
    npx vite --port $FRONTEND_PORT --host --strictPort 2>/dev/null &
FRONTEND_PID=$!
cd "$ROOT_DIR"
sleep 2

if ! kill -0 $FRONTEND_PID 2>/dev/null; then
    echo -e "${RED}错误: 前端启动失败${NC}"
    exit 1
fi
echo -e "${GREEN}  前端已启动 → http://localhost:${FRONTEND_PORT}${NC}"

# ---- 6. 启动悬浮窗（可选） ----
echo -e "${CYAN}[5/5] 启动桌面悬浮窗...${NC}"
HAS_PYQT6=0
python3 -c "from PyQt6.QtWidgets import QApplication" 2>/dev/null && HAS_PYQT6=1

if [ "$HAS_PYQT6" = "1" ]; then
    python3 window/main.py &
    WINDOW_PID=$!
    sleep 2
    if kill -0 $WINDOW_PID 2>/dev/null; then
        echo -e "${GREEN}  悬浮窗已启动（关闭窗口将隐藏到托盘）${NC}"
    else
        echo -e "${YELLOW}  悬浮窗启动失败（可能无图形桌面）${NC}"
    fi
else
    echo -e "${YELLOW}  跳过（PyQt6 未安装）${NC}"
fi

# ---- 完成 ----
echo ""
echo "============================================"
echo -e "${GREEN} ✅  Index-extraction 已就绪${NC}"
echo ""
echo -e "  Web 管理后台:  ${CYAN}http://localhost:${FRONTEND_PORT}${NC}"
echo -e "  API 接口文档:  ${CYAN}http://localhost:${BACKEND_PORT}/docs${NC}"
echo "============================================"
echo -e "${YELLOW}按 Ctrl+C 停止所有服务${NC}"
echo ""

# 自动打开浏览器
if command -v open &>/dev/null; then
    sleep 1 && open "http://localhost:$FRONTEND_PORT" 2>/dev/null &
elif command -v xdg-open &>/dev/null; then
    sleep 1 && xdg-open "http://localhost:$FRONTEND_PORT" 2>/dev/null &
fi

# 保持运行
wait
