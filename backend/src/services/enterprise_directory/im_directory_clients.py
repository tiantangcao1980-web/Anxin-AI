# -*- coding: utf-8 -*-
"""
飞书 / 钉钉 / 企业微信 通讯录同步客户端

设计动机（deploy/enterprise-onprem/LDAP_SYNC.md §8 路线图 P3）：
    复用 LdapClient 协议 ——
    每家 IM 平台都暴露"获取部门树 + 获取用户列表"的 API，
    把它们映射到统一的 ``LdapDeptRecord`` / ``LdapUserRecord`` 后，
    既有的 ``LdapSyncService`` 就能直接消费，零修改。

实装策略：
    - 所有 HTTP 走 ``httpx``（已在依赖中）
    - access_token 内部缓存，到期前 60s 主动刷新
    - 出错抛 ``ImDirectoryUnavailable`` —— 调用方按 LDAP fail-closed 处理
    - 接口形态保持同步（不返回 Awaitable），方便嵌入 ``LdapSyncService``；
      内部用 ``httpx.Client`` (sync) —— LdapSyncService 在 worker 里跑，
      不阻塞 event loop。

API 文档参考：
    - 飞书 OpenAPI：https://open.feishu.cn/document/server-docs/contact-v3
    - 钉钉 OpenAPI：https://open.dingtalk.com/document/orgapp/contacts-api
    - 企业微信通讯录：https://developer.work.weixin.qq.com/document/path/90208
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

from src.services.enterprise_directory.ldap_sync import (
    LdapDeptRecord,
    LdapUserRecord,
)

logger = logging.getLogger(__name__)


class ImDirectoryUnavailable(RuntimeError):
    """IM 平台 API 不可达 / 鉴权失败。"""


# ---------------------------------------------------------------------------
# 通用 token 缓存
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class _TokenCache:
    """access_token 缓存。"""

    token: str = ""
    expires_at: float = 0.0  # epoch sec

    def is_valid(self, *, leeway_sec: int = 60) -> bool:
        return bool(self.token) and time.time() + leeway_sec < self.expires_at


# ---------------------------------------------------------------------------
# 飞书
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class FeishuConfig:
    app_id: str
    app_secret: str
    base_url: str = "https://open.feishu.cn"
    timeout: float = 10.0


class FeishuDirectoryClient:
    """飞书通讯录同步客户端 —— 实现 ``LdapClient`` 协议。

    DN 编码：
        - 部门 DN：``feishu:dept:{open_department_id}``
        - 用户 DN：``feishu:user:{open_id}``
    parent_dn：父部门同样编码，根部门（dept_id="0"）→ None
    """

    EXT_PREFIX = "feishu"

    def __init__(self, config: FeishuConfig) -> None:
        if not config.app_id or not config.app_secret:
            raise ImDirectoryUnavailable("飞书配置缺 app_id / app_secret")
        self.config = config
        self._token = _TokenCache()
        self._http: Any = None

    # --- LdapClient 协议 ---

    def fetch_departments(self) -> list[LdapDeptRecord]:
        token = self._get_token()
        deps: list[LdapDeptRecord] = []
        # 飞书：递归子部门 fetch_child(department_id, page_token)
        # 入口部门 id="0"
        for dept in self._iter_departments(token, parent_id="0"):
            dept_id = str(dept.get("department_id") or dept.get("open_department_id") or "")
            if not dept_id:
                continue
            parent_id = str(dept.get("parent_department_id") or "")
            parent_dn = (
                f"{self.EXT_PREFIX}:dept:{parent_id}"
                if parent_id and parent_id != "0"
                else None
            )
            deps.append(
                LdapDeptRecord(
                    dn=f"{self.EXT_PREFIX}:dept:{dept_id}",
                    name=dept.get("name") or dept_id,
                    parent_dn=parent_dn,
                    code=str(dept.get("department_id_legacy") or "") or None,
                )
            )
        return deps

    def fetch_users(self) -> list[LdapUserRecord]:
        token = self._get_token()
        users: list[LdapUserRecord] = []
        # 飞书：按部门列出成员；先拿部门再 sweep
        for dept in self._iter_departments(token, parent_id="0"):
            dept_id = str(dept.get("department_id") or dept.get("open_department_id") or "")
            if not dept_id:
                continue
            dept_dn = f"{self.EXT_PREFIX}:dept:{dept_id}"
            for user in self._iter_users_in_dept(token, dept_id):
                email = (user.get("email") or user.get("enterprise_email") or "").strip()
                if not email:
                    continue
                open_id = str(user.get("open_id") or user.get("user_id") or "")
                users.append(
                    LdapUserRecord(
                        dn=f"{self.EXT_PREFIX}:user:{open_id}",
                        email=email.lower(),
                        name=user.get("name") or email.split("@")[0],
                        external_id=open_id,
                        department_dn=dept_dn,
                    )
                )
        return users

    # --- 内部：HTTP ---

    def _http_client(self):
        if self._http is None:
            try:
                import httpx
            except ImportError as exc:
                raise ImDirectoryUnavailable("需要 httpx") from exc
            self._http = httpx.Client(
                base_url=self.config.base_url,
                timeout=self.config.timeout,
            )
        return self._http

    def _get_token(self) -> str:
        if self._token.is_valid():
            return self._token.token
        try:
            resp = self._http_client().post(
                "/open-apis/auth/v3/tenant_access_token/internal",
                json={"app_id": self.config.app_id, "app_secret": self.config.app_secret},
            )
            data = resp.json()
            if resp.status_code != 200 or data.get("code") != 0:
                raise ImDirectoryUnavailable(f"飞书 token 失败 resp={data}")
        except Exception as exc:
            raise ImDirectoryUnavailable(f"飞书 token 拉取失败: {exc}") from exc
        self._token = _TokenCache(
            token=data["tenant_access_token"],
            expires_at=time.time() + int(data.get("expire", 7200)),
        )
        return self._token.token

    def _iter_departments(self, token: str, *, parent_id: str):
        """递归遍历部门树。注意：飞书 API 返回子部门，不含自己。"""
        seen: set[str] = set()
        stack: list[str] = [parent_id]
        while stack:
            pid = stack.pop()
            if pid in seen:
                continue
            seen.add(pid)
            page_token = None
            while True:
                params = {"parent_department_id": pid, "page_size": 50}
                if page_token:
                    params["page_token"] = page_token
                try:
                    resp = self._http_client().get(
                        "/open-apis/contact/v3/departments",
                        params=params,
                        headers={"Authorization": f"Bearer {token}"},
                    )
                    body = resp.json()
                except Exception as exc:
                    raise ImDirectoryUnavailable(f"飞书 list_departments: {exc}") from exc
                if body.get("code") != 0:
                    raise ImDirectoryUnavailable(f"飞书 list_departments resp={body}")
                items = (body.get("data") or {}).get("items", [])
                for item in items:
                    yield item
                    child_id = str(item.get("department_id") or "")
                    if child_id:
                        stack.append(child_id)
                page_token = (body.get("data") or {}).get("page_token")
                if not page_token:
                    break

    def _iter_users_in_dept(self, token: str, dept_id: str):
        page_token = None
        while True:
            params = {"department_id": dept_id, "page_size": 50}
            if page_token:
                params["page_token"] = page_token
            try:
                resp = self._http_client().get(
                    "/open-apis/contact/v3/users/find_by_department",
                    params=params,
                    headers={"Authorization": f"Bearer {token}"},
                )
                body = resp.json()
            except Exception as exc:
                raise ImDirectoryUnavailable(f"飞书 list_users: {exc}") from exc
            if body.get("code") != 0:
                raise ImDirectoryUnavailable(f"飞书 list_users resp={body}")
            yield from (body.get("data") or {}).get("items", [])
            page_token = (body.get("data") or {}).get("page_token")
            if not page_token:
                break


# ---------------------------------------------------------------------------
# 钉钉
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class DingtalkConfig:
    app_key: str
    app_secret: str
    base_url: str = "https://oapi.dingtalk.com"
    timeout: float = 10.0


class DingtalkDirectoryClient:
    """钉钉通讯录客户端 —— 实现 LdapClient。

    DN 编码同飞书风格：``dingtalk:dept:{id}`` / ``dingtalk:user:{userid}``
    """

    EXT_PREFIX = "dingtalk"

    def __init__(self, config: DingtalkConfig) -> None:
        if not config.app_key or not config.app_secret:
            raise ImDirectoryUnavailable("钉钉配置缺 app_key / app_secret")
        self.config = config
        self._token = _TokenCache()
        self._http: Any = None

    def fetch_departments(self) -> list[LdapDeptRecord]:
        token = self._get_token()
        out: list[LdapDeptRecord] = []
        for d in self._iter_departments(token):
            dept_id = str(d.get("dept_id") or d.get("id"))
            parent_id = str(d.get("parent_id") or "1")  # 钉钉根 id=1
            parent_dn = (
                f"{self.EXT_PREFIX}:dept:{parent_id}"
                if parent_id and parent_id != "1"
                else None
            )
            out.append(
                LdapDeptRecord(
                    dn=f"{self.EXT_PREFIX}:dept:{dept_id}",
                    name=d.get("name") or dept_id,
                    parent_dn=parent_dn,
                )
            )
        return out

    def fetch_users(self) -> list[LdapUserRecord]:
        token = self._get_token()
        users: list[LdapUserRecord] = []
        for d in self._iter_departments(token):
            dept_id = str(d.get("dept_id") or d.get("id"))
            dept_dn = f"{self.EXT_PREFIX}:dept:{dept_id}"
            for u in self._iter_users_in_dept(token, dept_id):
                email = (u.get("email") or u.get("org_email") or "").strip()
                if not email:
                    continue
                userid = str(u.get("userid") or "")
                users.append(
                    LdapUserRecord(
                        dn=f"{self.EXT_PREFIX}:user:{userid}",
                        email=email.lower(),
                        name=u.get("name") or email.split("@")[0],
                        external_id=userid,
                        department_dn=dept_dn,
                    )
                )
        return users

    # --- 内部 ---

    def _http_client(self):
        if self._http is None:
            try:
                import httpx
            except ImportError as exc:
                raise ImDirectoryUnavailable("需要 httpx") from exc
            self._http = httpx.Client(
                base_url=self.config.base_url,
                timeout=self.config.timeout,
            )
        return self._http

    def _get_token(self) -> str:
        if self._token.is_valid():
            return self._token.token
        try:
            resp = self._http_client().get(
                "/gettoken",
                params={
                    "appkey": self.config.app_key,
                    "appsecret": self.config.app_secret,
                },
            )
            data = resp.json()
            if resp.status_code != 200 or data.get("errcode") not in (0, None):
                raise ImDirectoryUnavailable(f"钉钉 token 失败 resp={data}")
        except Exception as exc:
            raise ImDirectoryUnavailable(f"钉钉 token 拉取失败: {exc}") from exc
        self._token = _TokenCache(
            token=data["access_token"],
            expires_at=time.time() + int(data.get("expires_in", 7200)),
        )
        return self._token.token

    def _iter_departments(self, token: str):
        """钉钉 list_sub 递归（dept_id=1 是根）"""
        seen: set[str] = set()
        stack: list[str] = ["1"]
        while stack:
            pid = stack.pop()
            if pid in seen:
                continue
            seen.add(pid)
            try:
                resp = self._http_client().post(
                    "/topapi/v2/department/listsub",
                    params={"access_token": token},
                    json={"dept_id": int(pid)},
                )
                body = resp.json()
            except Exception as exc:
                raise ImDirectoryUnavailable(f"钉钉 listsub: {exc}") from exc
            if body.get("errcode") != 0:
                raise ImDirectoryUnavailable(f"钉钉 listsub resp={body}")
            for item in body.get("result") or []:
                yield item
                child_id = str(item.get("dept_id") or item.get("id") or "")
                if child_id:
                    stack.append(child_id)

    def _iter_users_in_dept(self, token: str, dept_id: str):
        cursor = 0
        while True:
            try:
                resp = self._http_client().post(
                    "/topapi/v2/user/list",
                    params={"access_token": token},
                    json={"dept_id": int(dept_id), "cursor": cursor, "size": 50},
                )
                body = resp.json()
            except Exception as exc:
                raise ImDirectoryUnavailable(f"钉钉 user/list: {exc}") from exc
            if body.get("errcode") != 0:
                raise ImDirectoryUnavailable(f"钉钉 user/list resp={body}")
            result = body.get("result") or {}
            yield from result.get("list") or []
            if not result.get("has_more"):
                break
            cursor = result.get("next_cursor", 0)


# ---------------------------------------------------------------------------
# 企业微信（WeCom）
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class WecomConfig:
    corp_id: str
    contacts_secret: str  # 通讯录 secret（区分应用 secret）
    base_url: str = "https://qyapi.weixin.qq.com"
    timeout: float = 10.0


class WecomDirectoryClient:
    """企业微信通讯录客户端 —— 实现 LdapClient。

    DN 编码：``wecom:dept:{id}`` / ``wecom:user:{userid}``
    """

    EXT_PREFIX = "wecom"

    def __init__(self, config: WecomConfig) -> None:
        if not config.corp_id or not config.contacts_secret:
            raise ImDirectoryUnavailable("企业微信配置缺 corp_id / contacts_secret")
        self.config = config
        self._token = _TokenCache()
        self._http: Any = None

    def fetch_departments(self) -> list[LdapDeptRecord]:
        token = self._get_token()
        try:
            resp = self._http_client().get(
                "/cgi-bin/department/list",
                params={"access_token": token},
            )
            body = resp.json()
        except Exception as exc:
            raise ImDirectoryUnavailable(f"企业微信 department/list: {exc}") from exc
        if body.get("errcode") != 0:
            raise ImDirectoryUnavailable(f"企业微信 department/list resp={body}")
        out: list[LdapDeptRecord] = []
        for d in body.get("department") or []:
            did = str(d.get("id"))
            parent_id = str(d.get("parentid") or "")
            parent_dn = (
                f"{self.EXT_PREFIX}:dept:{parent_id}"
                if parent_id and parent_id != "0"
                else None
            )
            out.append(
                LdapDeptRecord(
                    dn=f"{self.EXT_PREFIX}:dept:{did}",
                    name=d.get("name") or did,
                    parent_dn=parent_dn,
                )
            )
        return out

    def fetch_users(self) -> list[LdapUserRecord]:
        token = self._get_token()
        users: list[LdapUserRecord] = []
        for d in self.fetch_departments():
            dept_id = d.dn.split(":")[-1]
            try:
                resp = self._http_client().get(
                    "/cgi-bin/user/list",
                    params={
                        "access_token": token,
                        "department_id": dept_id,
                        "fetch_child": 0,
                    },
                )
                body = resp.json()
            except Exception as exc:
                raise ImDirectoryUnavailable(f"企业微信 user/list: {exc}") from exc
            if body.get("errcode") != 0:
                raise ImDirectoryUnavailable(f"企业微信 user/list resp={body}")
            for u in body.get("userlist") or []:
                email = (u.get("email") or u.get("biz_mail") or "").strip()
                if not email:
                    continue
                userid = str(u.get("userid") or "")
                users.append(
                    LdapUserRecord(
                        dn=f"{self.EXT_PREFIX}:user:{userid}",
                        email=email.lower(),
                        name=u.get("name") or email.split("@")[0],
                        external_id=userid,
                        department_dn=d.dn,
                    )
                )
        return users

    # --- 内部 ---

    def _http_client(self):
        if self._http is None:
            try:
                import httpx
            except ImportError as exc:
                raise ImDirectoryUnavailable("需要 httpx") from exc
            self._http = httpx.Client(
                base_url=self.config.base_url,
                timeout=self.config.timeout,
            )
        return self._http

    def _get_token(self) -> str:
        if self._token.is_valid():
            return self._token.token
        try:
            resp = self._http_client().get(
                "/cgi-bin/gettoken",
                params={
                    "corpid": self.config.corp_id,
                    "corpsecret": self.config.contacts_secret,
                },
            )
            data = resp.json()
            if resp.status_code != 200 or data.get("errcode") != 0:
                raise ImDirectoryUnavailable(f"企业微信 token 失败 resp={data}")
        except Exception as exc:
            raise ImDirectoryUnavailable(f"企业微信 token 拉取失败: {exc}") from exc
        self._token = _TokenCache(
            token=data["access_token"],
            expires_at=time.time() + int(data.get("expires_in", 7200)),
        )
        return self._token.token


__all__ = [
    "DingtalkConfig",
    "DingtalkDirectoryClient",
    "FeishuConfig",
    "FeishuDirectoryClient",
    "ImDirectoryUnavailable",
    "WecomConfig",
    "WecomDirectoryClient",
]
