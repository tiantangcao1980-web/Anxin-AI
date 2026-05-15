"""
TokenStore — Fernet 加密的 token 持久化工具（P4-A）

职责
----
- 把明文 token 加密成 ``bytes`` 后写入 ``app_tokens.encrypted_*`` 字段；
- 读时解密成明文字符串；
- 支持 key rotation：通过环境变量传多 key（逗号分隔），用 ``MultiFernet``
  自动按顺序尝试解密、加密永远用第一个 key。

使用方式
--------
::

    store = TokenStore.from_settings()
    blob = store.encrypt("ya29.a0AfH6...")
    plain = store.decrypt(blob)

key 生成
--------
::

    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

把生成的 base64-urlsafe 字符串放进环境变量 ``OAUTH_TOKEN_ENCRYPTION_KEY``。
"""

from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken, MultiFernet


class TokenStoreConfigError(RuntimeError):
    """配置错误（key 缺失 / 格式非法）。"""


class TokenStore:
    """Fernet 对称加密的 token 存储工具（无状态，可单例复用）。

    参数
    ----
    keys : list[str]
        Fernet base64-urlsafe key 列表。
        - 长度 = 1 时单 key 模式；
        - 长度 > 1 时启用 ``MultiFernet`` —— 加密永远用 ``keys[0]``，
          解密会按顺序尝试所有 key（key rotation 期间新老 key 共存）。
    """

    def __init__(self, keys: list[str]) -> None:
        if not keys:
            raise TokenStoreConfigError(
                "TokenStore 需要至少一个 Fernet key（OAUTH_TOKEN_ENCRYPTION_KEY 未配置）"
            )

        fernets: list[Fernet] = []
        for idx, key in enumerate(keys):
            if not key:
                raise TokenStoreConfigError(f"第 {idx} 个 OAUTH_TOKEN_ENCRYPTION_KEY 为空")
            try:
                fernets.append(Fernet(key.encode() if isinstance(key, str) else key))
            except (ValueError, TypeError) as e:
                raise TokenStoreConfigError(
                    f"第 {idx} 个 OAUTH_TOKEN_ENCRYPTION_KEY 不是合法的 Fernet key: {e}"
                ) from e

        self._fernet: Fernet | MultiFernet
        if len(fernets) == 1:
            self._fernet = fernets[0]
        else:
            self._fernet = MultiFernet(fernets)

        self._key_count = len(fernets)

    # ------------------------------------------------------------------
    # 工厂
    # ------------------------------------------------------------------
    @classmethod
    def from_settings(cls) -> TokenStore:
        """从 ``core.config.settings`` 读取 key 并构造实例。

        支持单 key 或多 key（逗号分隔，用于 key rotation）。
        """
        # 局部导入避免循环引用
        from src.core.config import settings

        raw_key = (settings.OAUTH_TOKEN_ENCRYPTION_KEY or "").strip()
        if not raw_key:
            raise TokenStoreConfigError(
                "settings.OAUTH_TOKEN_ENCRYPTION_KEY 未配置；"
                "请用 `python -c 'from cryptography.fernet import Fernet; "
                "print(Fernet.generate_key().decode())'` 生成后注入环境变量。"
            )
        keys = [k.strip() for k in raw_key.split(",") if k.strip()]
        return cls(keys=keys)

    # ------------------------------------------------------------------
    # 核心 API
    # ------------------------------------------------------------------
    def encrypt(self, token: str) -> bytes:
        """加密明文 token，返回密文 bytes。"""
        if not isinstance(token, str):
            raise TypeError(f"encrypt 入参必须是 str，得到 {type(token).__name__}")
        return self._fernet.encrypt(token.encode("utf-8"))

    def decrypt(self, blob: bytes) -> str:
        """解密密文 bytes，返回明文 token。

        若 key 不匹配会抛 ``InvalidToken``，调用方应捕获并标记
        AppAuthorization.status = error。
        """
        if not isinstance(blob, (bytes, bytearray, memoryview)):
            raise TypeError(f"decrypt 入参必须是 bytes-like，得到 {type(blob).__name__}")
        return self._fernet.decrypt(bytes(blob)).decode("utf-8")

    def encrypt_optional(self, token: str | None) -> bytes | None:
        """便捷方法：None 透传，str 加密。"""
        if token is None:
            return None
        return self.encrypt(token)

    def decrypt_optional(self, blob: bytes | None) -> str | None:
        """便捷方法：None 透传，bytes 解密。"""
        if blob is None:
            return None
        return self.decrypt(blob)

    @property
    def key_count(self) -> int:
        """当前生效的 key 数量（>1 表示处于 rotation 期间）。"""
        return self._key_count


__all__ = ["TokenStore", "TokenStoreConfigError", "InvalidToken"]
