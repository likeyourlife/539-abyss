#!/bin/bash
# 今彩539 Dashboard 启动脚本
# 用法: ./start.sh [--no-server] [--port PORT]

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
PYTHON="/Users/ioorule/.workbuddy/binaries/python/envs/default/bin/python3"
PORT=5390

# 解析参数
NO_SERVER=false
while [[ $# -gt 0 ]]; do
  case $1 in
    --no-server) NO_SERVER=true; shift ;;
    --port) PORT="$2"; shift 2 ;;
    *) shift ;;
  esac
done

echo "✦ 今彩539 Dashboard"
echo "   项目路径: $PROJECT_ROOT"
echo ""

# 1. 更新数据（可选）
# echo "1. 采集最新数据..."
# cd "$PROJECT_ROOT" && $PYTHON scripts/daily_push.py

# 2. 生成Dashboard数据
echo "1. 生成Dashboard数据..."
cd "$PROJECT_ROOT" && $PYTHON scripts/generate_dashboard_data.py

# 3. 复制数据到前端目录
cp "$PROJECT_ROOT/reports/dashboard_data.json" "$PROJECT_ROOT/frontend/dashboard_data.json"
cp "$PROJECT_ROOT/data/backtest_history.json" "$PROJECT_ROOT/frontend/backtest_history.json" 2>/dev/null

if [ "$NO_SERVER" = true ]; then
  echo ""
  echo "   静态模式：数据已更新，可用浏览器打开 frontend/index.html"
  echo "   或部署到 GitHub Pages（自动通过 GitHub Actions）"
  exit 0
fi

# 4. 启动Flask服务
echo "2. 启动Flask服务(端口 $PORT)..."
cd "$PROJECT_ROOT" && $PYTHON frontend/app.py --port $PORT 2>/dev/null || \
cd "$PROJECT_ROOT" && $PYTHON -c "
import sys, os
sys.path.insert(0, '$PROJECT_ROOT')
os.environ['PORT'] = '$PORT'
# 动态修改端口
import importlib
app_mod = import_module('frontend.app')
app_mod.app.run(host='0.0.0.0', port=$PORT, debug=False)
"

echo ""
echo "   访问地址: http://localhost:$PORT"
echo "   按 Ctrl+C 停止服务"
