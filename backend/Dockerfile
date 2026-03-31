# AI法务智能体系统 - 后端 Dockerfile

FROM python:3.11-bookworm

WORKDIR /app

# 使用阿里云 pip 镜像 (国内服务器加速)
ENV UV_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/ \
    UV_TRUSTED_HOST=mirrors.aliyun.com \
    UV_HTTP_TIMEOUT=300 \
    PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers

RUN pip install uv -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com

# ---- 第1层: Python 依赖 (仅 pyproject.toml 变动时重建) ----
COPY pyproject.toml README.md ./
RUN uv pip install --system -e .

# ---- 第2层: 源代码 (日常代码提交只重建这里，几秒完成) ----
COPY . .

RUN mkdir -p /app/data

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys, urllib.request; urllib.request.urlopen('http://127.0.0.1:8001/health', timeout=5); sys.exit(0)" || exit 1

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8001"]
