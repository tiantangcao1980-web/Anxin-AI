# Anxin AI 安心智能助手 - 后端 Dockerfile

# 固定 minor 版本 + slim 变体（构建可重复 / 攻击面更小）
# 升级前需同步更新 .github/workflows 中的 python-version
FROM python:3.11.10-slim-bookworm

WORKDIR /app

# 使用阿里云 pip 镜像 (国内服务器加速)
ENV UV_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/ \
    UV_TRUSTED_HOST=mirrors.aliyun.com \
    UV_HTTP_TIMEOUT=300 \
    PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# slim 镜像缺少 build-essential / curl，按需补齐
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com

# ---- 第1层: Python 依赖 (仅 pyproject.toml 变动时重建) ----
COPY pyproject.toml README.md ./
RUN uv pip install --system -e .

# ---- 第2层: 源代码 (日常代码提交只重建这里，几秒完成) ----
COPY . .

# [SEC] 非 root 运行
RUN groupadd --system --gid 10001 app && \
    useradd --system --uid 10001 --gid app --home-dir /app --shell /sbin/nologin app && \
    mkdir -p /app/data && \
    chown -R app:app /app
USER app

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl --fail --silent http://127.0.0.1:8001/health || exit 1

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8001"]
