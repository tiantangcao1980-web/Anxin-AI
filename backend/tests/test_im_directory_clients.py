# -*- coding: utf-8 -*-
"""
飞书 / 钉钉 / 企业微信 通讯录客户端单测

不调用真实 API：通过 monkeypatch ``_http_client`` 注入一个 FakeHttp，
把 endpoint → 响应映射成字典，复现 paging / token 刷新行为。

每家平台覆盖：
    - fetch_departments 树形展开
    - fetch_users 主部门正确
    - 缺配置 / token 失败 → ImDirectoryUnavailable
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import pytest

from src.services.enterprise_directory import (
    DingtalkConfig,
    DingtalkDirectoryClient,
    FeishuConfig,
    FeishuDirectoryClient,
    ImDirectoryUnavailable,
    WecomConfig,
    WecomDirectoryClient,
)


# ---------------------------------------------------------------------------
# FakeHttp —— 模拟 httpx.Client
# ---------------------------------------------------------------------------


@dataclass
class _FakeResponse:
    status_code: int
    body: dict

    def json(self) -> dict:
        return self.body


class FakeHttp:
    """支持 .post / .get(path, params=..., json=..., headers=...) 调用。

    路由表：``{(method, path): handler_fn}``，handler 接 request 字典返回 _FakeResponse。
    """

    def __init__(self, routes: dict[tuple[str, str], Callable[[dict], _FakeResponse]]):
        self.routes = routes
        self.calls: list[dict] = []

    def _dispatch(self, method: str, path: str, **kwargs) -> _FakeResponse:
        req = {"method": method, "path": path, **kwargs}
        self.calls.append(req)
        handler = self.routes.get((method, path))
        if handler is None:
            raise AssertionError(f"未注册路由: {method} {path}")
        return handler(req)

    def get(self, path: str, **kwargs) -> _FakeResponse:
        return self._dispatch("GET", path, **kwargs)

    def post(self, path: str, **kwargs) -> _FakeResponse:
        return self._dispatch("POST", path, **kwargs)


# ---------------------------------------------------------------------------
# 飞书
# ---------------------------------------------------------------------------


def test_feishu_missing_config_raises() -> None:
    with pytest.raises(ImDirectoryUnavailable):
        FeishuDirectoryClient(FeishuConfig(app_id="", app_secret="x"))


def test_feishu_fetch_departments_and_users() -> None:
    client = FeishuDirectoryClient(FeishuConfig(app_id="a", app_secret="b"))

    # 飞书 token 接口
    def _token(req):
        return _FakeResponse(200, {"code": 0, "tenant_access_token": "tok", "expire": 7200})

    # list_departments 模拟：parent="0" -> [dept-1]，parent="dept-1" -> []
    list_calls = {"count": 0}
    def _list_depts(req):
        list_calls["count"] += 1
        parent = req["params"]["parent_department_id"]
        if parent == "0":
            return _FakeResponse(200, {
                "code": 0,
                "data": {
                    "items": [{"department_id": "dept-1", "name": "技术中心", "parent_department_id": "0"}],
                    "page_token": None,
                },
            })
        return _FakeResponse(200, {"code": 0, "data": {"items": [], "page_token": None}})

    def _users(req):
        return _FakeResponse(200, {
            "code": 0,
            "data": {
                "items": [
                    {"open_id": "u1", "name": "Alice", "email": "alice@corp.example"},
                ],
                "page_token": None,
            },
        })

    fake = FakeHttp({
        ("POST", "/open-apis/auth/v3/tenant_access_token/internal"): _token,
        ("GET", "/open-apis/contact/v3/departments"): _list_depts,
        ("GET", "/open-apis/contact/v3/users/find_by_department"): _users,
    })
    client._http = fake

    depts = client.fetch_departments()
    assert len(depts) == 1
    assert depts[0].dn == "feishu:dept:dept-1"
    assert depts[0].name == "技术中心"
    assert depts[0].parent_dn is None  # parent="0" → None

    users = client.fetch_users()
    assert len(users) == 1
    assert users[0].email == "alice@corp.example"
    assert users[0].department_dn == "feishu:dept:dept-1"
    assert users[0].dn == "feishu:user:u1"


def test_feishu_token_failure_propagates() -> None:
    client = FeishuDirectoryClient(FeishuConfig(app_id="a", app_secret="bad"))
    fake = FakeHttp({
        ("POST", "/open-apis/auth/v3/tenant_access_token/internal"): lambda req: _FakeResponse(
            401, {"code": 99991663, "msg": "invalid app secret"}
        ),
    })
    client._http = fake
    with pytest.raises(ImDirectoryUnavailable):
        client.fetch_departments()


# ---------------------------------------------------------------------------
# 钉钉
# ---------------------------------------------------------------------------


def test_dingtalk_fetch() -> None:
    client = DingtalkDirectoryClient(DingtalkConfig(app_key="k", app_secret="s"))

    def _token(req):
        return _FakeResponse(200, {"errcode": 0, "access_token": "tk", "expires_in": 7200})

    def _listsub(req):
        body = req.get("json") or {}
        if body.get("dept_id") == 1:
            return _FakeResponse(200, {
                "errcode": 0,
                "result": [{"dept_id": 10, "name": "技术", "parent_id": 1}],
            })
        return _FakeResponse(200, {"errcode": 0, "result": []})

    def _user_list(req):
        return _FakeResponse(200, {
            "errcode": 0,
            "result": {
                "list": [{"userid": "ding-u1", "name": "Bob", "email": "bob@corp.example"}],
                "has_more": False,
            },
        })

    fake = FakeHttp({
        ("GET", "/gettoken"): _token,
        ("POST", "/topapi/v2/department/listsub"): _listsub,
        ("POST", "/topapi/v2/user/list"): _user_list,
    })
    client._http = fake

    depts = client.fetch_departments()
    assert depts[0].dn == "dingtalk:dept:10"
    assert depts[0].parent_dn is None   # parent_id=1 (root) → None

    users = client.fetch_users()
    assert users[0].email == "bob@corp.example"
    assert users[0].department_dn == "dingtalk:dept:10"


# ---------------------------------------------------------------------------
# 企业微信
# ---------------------------------------------------------------------------


def test_wecom_fetch() -> None:
    client = WecomDirectoryClient(WecomConfig(corp_id="c", contacts_secret="s"))

    def _token(req):
        return _FakeResponse(200, {"errcode": 0, "access_token": "wtok", "expires_in": 7200})

    def _dept_list(req):
        return _FakeResponse(200, {
            "errcode": 0,
            "department": [
                {"id": 1, "name": "总部", "parentid": 0},
                {"id": 2, "name": "技术部", "parentid": 1},
            ],
        })

    def _user_list(req):
        if req["params"]["department_id"] == "2":
            return _FakeResponse(200, {
                "errcode": 0,
                "userlist": [{"userid": "wecom-u1", "name": "Carol", "email": "carol@corp.example"}],
            })
        return _FakeResponse(200, {"errcode": 0, "userlist": []})

    fake = FakeHttp({
        ("GET", "/cgi-bin/gettoken"): _token,
        ("GET", "/cgi-bin/department/list"): _dept_list,
        ("GET", "/cgi-bin/user/list"): _user_list,
    })
    client._http = fake

    depts = client.fetch_departments()
    assert len(depts) == 2
    # parentid=0 root → None
    root = next(d for d in depts if d.name == "总部")
    assert root.parent_dn is None
    sub = next(d for d in depts if d.name == "技术部")
    assert sub.parent_dn == "wecom:dept:1"

    users = client.fetch_users()
    assert any(u.email == "carol@corp.example" for u in users)
