# syntax=docker/dockerfile:1
# AI法务智能体系统 - 后端 Dockerfile

FROM python:3.11-bookworm

WORKDIR /app

# 使用阿里云 pip 镜像 (国内服务器加速)
ENV UV_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/ \
    UV_TRUSTED_HOST=mirrors.aliyun.com \
    UV_HTTP_TIMEOUT=300 \
    PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers

RUN pip install uv -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com

# ---- 第1层: Playwright 浏览器 (独立缓存，极少变动) ----
# --mount=type=cache 让 pip/apt 的下载缓存持久化，即使层重建也不用重新下载
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=cache,target=/root/.cache/pip \
    --mount=type=cache,target=/var/cache/apt,sharing=locked \
    uv pip install --system playwright && \
    playwright install --with-deps chromium

# ---- 第2层: Python 依赖 (仅 pyproject.toml 变动时重建) ----
COPY pyproject.toml README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=cache,target=/root/.cache/pip \
    uv pip install --system -e .

# ---- 第3层: 源代码 (日常代码提交只重建这里，几秒完成) ----
COPY . .

RUN mkdir -p /app/data

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8001"]
