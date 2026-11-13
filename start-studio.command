#!/bin/zsh
set -eu
cd "${0:A:h}"
if [[ ! -d frontend/node_modules ]]; then
  npm ci --prefix frontend --no-audit --no-fund
fi
npm run build --prefix frontend
rag_studio_python="${RAG_STUDIO_PYTHON:-/opt/anaconda3/envs/agent/bin/python}"
if [[ ! -x "$rag_studio_python" ]]; then
  rag_studio_python="$(command -v python3)"
fi
rag_studio_port="${RAG_STUDIO_PORT:-8021}"
echo "Knowledge Studio: http://127.0.0.1:${rag_studio_port}/studio/"
echo "保持此终端开启；Ctrl+C 停止服务。"
exec "$rag_studio_python" -m uvicorn app.api:app --host 127.0.0.1 --port "$rag_studio_port"
