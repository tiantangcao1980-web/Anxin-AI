from fastapi import Response

from src.api.main import add_security_headers, root


async def _empty_response(_request: object) -> Response:
    return Response()


async def test_root_returns_service_metadata() -> None:
    assert await root() == {
        "name": "Anxin Smart Assistant",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs",
    }


async def test_add_security_headers_sets_default_browser_guards() -> None:
    response = await add_security_headers(object(), _empty_response)

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-XSS-Protection"] == "1; mode=block"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
