"""
输入验证模块 (Input Validation)
包含输入清理、文件验证、SQL注入防护等
"""

import re
import html
from typing import Optional, List, Any
from pathlib import Path
from pydantic import BaseModel, validator, Field
from loguru import logger

from src.core.config import settings


# ========== 输入清理 ==========


class InputSanitizer:
    """输入清理器"""

    # 危险字符模式
    SQL_INJECTION_PATTERNS = [
        r"(\bunion\b.*\bselect\b)",
        r"(\bselect\b.*\bfrom\b)",
        r"(\binsert\b.*\binto\b)",
        r"(\bupdate\b.*\bset\b)",
        r"(\bdelete\b.*\bfrom\b)",
        r"(\bdrop\b.*\btable\b)",
        r"(\bexec\b|\bexecute\b)",
        r"(;.*\bwaitfor\b)",
        r"(\bcast\b.*\bas\b)",
    ]

    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe[^>]*>",
        r"<embed[^>]*>",
        r"<object[^>]*>",
    ]

    @classmethod
    def sanitize_string(cls, value: str, max_length: Optional[int] = None) -> str:
        """
        清理字符串输入

        Args:
            value: 输入字符串
            max_length: 最大长度限制

        Returns:
            清理后的字符串
        """
        if not isinstance(value, str):
            return ""

        # 长度限制
        if max_length and len(value) > max_length:
            logger.warning(f"输入超长，截断到 {max_length} 字符")
            value = value[:max_length]

        # HTML 实体转义
        value = html.escape(value)

        # 移除控制字符
        value = re.sub(r"[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]", "", value)

        return value.strip()

    @classmethod
    def check_sql_injection(cls, value: str) -> bool:
        """
        检查 SQL 注入

        Args:
            value: 输入字符串

        Returns:
            True 表示检测到注入，False 表示安全
        """
        value_lower = value.lower()

        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, value_lower, re.IGNORECASE):
                logger.warning(f"检测到 SQL 注入尝试: {value[:50]}...")
                return True

        return False

    @classmethod
    def check_xss(cls, value: str) -> bool:
        """
        检查 XSS 攻击

        Args:
            value: 输入字符串

        Returns:
            True 表示检测到 XSS，False 表示安全
        """
        value_lower = value.lower()

        for pattern in cls.XSS_PATTERNS:
            if re.search(pattern, value_lower, re.IGNORECASE):
                logger.warning(f"检测到 XSS 攻击尝试: {value[:50]}...")
                return True

        return False

    @classmethod
    def sanitize_user_input(cls, value: str) -> tuple[str, bool]:
        """
        综合清理用户输入

        Args:
            value: 输入字符串

        Returns:
            (清理后的字符串, 是否检测到攻击)
        """
        is_dangerous = False

        # 检查 SQL 注入
        if cls.check_sql_injection(value):
            is_dangerous = True

        # 检查 XSS
        if cls.check_xss(value):
            is_dangerous = True

        # 清理字符串
        cleaned = cls.sanitize_string(
            value,
            max_length=settings.MAX_QUERY_LENGTH
        )

        return cleaned, is_dangerous


# ========== 文件验证 ==========


class FileValidator:
    """文件验证器"""

    ALLOWED_EXTENSIONS = set(settings.ALLOWED_FILE_EXTENSIONS)
    MAX_SIZE = settings.MAX_UPLOAD_SIZE

    # 危险文件扩展名（黑名单）
    DANGEROUS_EXTENSIONS = {
        ".exe", ".bat", ".cmd", ".sh", ".ps1",
        ".scr", ".pif", ".com", ".js", ".vbs",
        ".jar", ".app", ".deb", ".rpm",
    }

    # 文件类型签名（Magic Numbers）
    FILE_SIGNATURES = {
        b"\x25\x50\x44\x46": ".pdf",  # PDF
        b"\x50\x4b\x03\x04": ".docx",  # DOCX (also ZIP)
        b"\xd0\xcf\x11\xe0": ".doc",   # DOC
        b"\x50\x4b\x03\x04": ".xlsx",  # XLSX (also ZIP)
        b"\xd0\xcf\x11\xe0": ".xls",   # XLS
    }

    @classmethod
    def validate_extension(cls, filename: str) -> bool:
        """
        验证文件扩展名

        Args:
            filename: 文件名

        Returns:
            是否合法
        """
        ext = Path(filename).suffix.lower()

        # 检查黑名单
        if ext in cls.DANGEROUS_EXTENSIONS:
            logger.warning(f"检测到危险文件类型: {ext}")
            return False

        # 检查白名单
        return ext in cls.ALLOWED_EXTENSIONS

    @classmethod
    def validate_size(cls, file_size: int) -> bool:
        """
        验证文件大小

        Args:
            file_size: 文件大小（字节）

        Returns:
            是否合法
        """
        return file_size <= cls.MAX_SIZE

    @classmethod
    def validate_content_type(cls, content_type: str) -> bool:
        """
        验证 Content-Type

        Args:
            content_type: MIME 类型

        Returns:
            是否合法
        """
        allowed_types = [
            "application/pdf",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.ms-excel",
            "text/plain",
            "text/markdown",
        ]

        return content_type in allowed_types

    @classmethod
    async def validate_file(
        cls,
        filename: str,
        file_size: int,
        content_type: str,
        content: Optional[bytes] = None
    ) -> tuple[bool, str]:
        """
        综合验证文件

        Args:
            filename: 文件名
            file_size: 文件大小
            content_type: MIME 类型
            content: 文件内容（可选，用于深度验证）

        Returns:
            (是否合法, 错误信息)
        """
        # 验证扩展名
        if not cls.validate_extension(filename):
            return False, f"不支持的文件类型"

        # 验证大小
        if not cls.validate_size(file_size):
            return False, f"文件过大（最大 {cls.MAX_SIZE // 1024 // 1024}MB）"

        # 验证 Content-Type
        if not cls.validate_content_type(content_type):
            return False, f"不支持的 MIME 类型: {content_type}"

        # 深度验证（检查文件头）
        if content and len(content) >= 4:
            ext = Path(filename).suffix.lower()
            expected_sig = None

            for sig, sig_ext in cls.FILE_SIGNATURES.items():
                if sig_ext == ext:
                    expected_sig = sig
                    break

            if expected_sig and not content.startswith(expected_sig):
                logger.warning(f"文件签名不匹配: {filename}")
                return False, "文件内容与扩展名不匹配"

        return True, ""


# ========== Pydantic 验证模型 ==========


class BaseValidationModel(BaseModel):
    """基础验证模型"""

    class Config:
        # 任何额外的字段都会导致验证错误
        extra = "forbid"
        # 允许别名
        allow_population_by_field_name = True


class UserInputModel(BaseValidationModel):
    """用户输入验证模型"""

    query: str = Field(..., min_length=1, max_length=1000)

    @validator("query")
    def sanitize_query(cls, v):
        """清理查询字符串"""
        sanitized, is_dangerous = InputSanitizer.sanitize_user_input(v)

        if is_dangerous:
            raise ValueError("检测到非法输入")

        return sanitized


class ChatMessageModel(BaseValidationModel):
    """聊天消息验证模型"""

    message: str = Field(..., min_length=1, max_length=5000)
    session_id: Optional[str] = None

    @validator("message")
    def sanitize_message(cls, v):
        """清理消息内容"""
        sanitized, is_dangerous = InputSanitizer.sanitize_user_input(v)

        if is_dangerous:
            raise ValueError("检测到非法输入")

        return sanitized


class FileUploadModel(BaseValidationModel):
    """文件上传验证模型"""

    filename: str
    file_size: int
    content_type: str

    @validator("filename")
    def validate_filename(cls, v):
        """验证文件名"""
        # 检查路径遍历攻击
        if ".." in v or v.startswith("/"):
            raise ValueError("非法文件名")

        # 检查扩展名
        if not FileValidator.validate_extension(v):
            raise ValueError(f"不支持的文件类型: {Path(v).suffix}")

        return v

    @validator("file_size")
    def validate_file_size(cls, v):
        """验证文件大小"""
        if not FileValidator.validate_size(v):
            raise ValueError("文件过大")

        return v


# ========== 路径验证 ==========


def validate_path_traversal(path: str) -> bool:
    """
    检查路径遍历攻击

    Args:
        path: 路径字符串

    Returns:
        True 表示检测到攻击，False 表示安全
    """
    dangerous_patterns = ["..", "~/", "/etc/", "/sys/", "/proc/"]

    for pattern in dangerous_patterns:
        if pattern in path:
            logger.warning(f"检测到路径遍历尝试: {path}")
            return True

    return False


# ========== 命令注入验证 ==========


def validate_command_injection(input_str: str) -> bool:
    """
    检查命令注入

    Args:
        input_str: 输入字符串

    Returns:
        True 表示检测到注入，False 表示安全
    """
    dangerous_chars = [";", "&", "|", "$", "`", "\n", "\r", "(", ")"]

    for char in dangerous_chars:
        if char in input_str:
            logger.warning(f"检测到命令注入尝试: {input_str[:50]}...")
            return True

    return False


# ========== Email 验证 ==========


def validate_email(email: str) -> bool:
    """
    验证 Email 格式

    Args:
        email: Email 地址

    Returns:
        是否合法
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


# ========== 手机号验证 ==========


def validate_phone(phone: str) -> bool:
    """
    验证手机号格式（中国）

    Args:
        phone: 手机号

    Returns:
        是否合法
    """
    pattern = r'^1[3-9]\d{9}$'
    return re.match(pattern, phone) is not None
