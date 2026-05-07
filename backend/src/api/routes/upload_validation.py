"""Shared upload validation helpers for API routes."""

from fastapi import HTTPException, UploadFile, status

from src.core.validators import FileValidator


async def read_validated_upload_file(file: UploadFile) -> tuple[bytes, str, str]:
    """Read an UploadFile and enforce the shared file validation policy."""
    content = await file.read()
    filename = file.filename or "未命名文件"
    content_type = file.content_type or "application/octet-stream"

    is_valid, validation_error = await FileValidator.validate_file(
        filename=filename,
        file_size=len(content),
        content_type=content_type,
        content=content,
    )
    if not is_valid:
        status_code_ = (
            status.HTTP_413_CONTENT_TOO_LARGE
            if not FileValidator.validate_size(len(content))
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=status_code_, detail=validation_error)

    return content, filename, FileValidator.normalize_content_type(content_type)
