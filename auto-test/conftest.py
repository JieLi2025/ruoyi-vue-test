# -*- coding: utf-8 -*-
"""接口自动化测试公共配置与 fixture"""
import os
import uuid

import pytest
import requests

BASE_URL = os.getenv("RUOYI_BASE_URL", "http://localhost:8080")
USERNAME = os.getenv("RUOYI_USERNAME", "admin")
PASSWORD = os.getenv("RUOYI_PASSWORD", "admin123")
TIMEOUT = 10

# 测试凭证：需先用管理员账号在「系统管理 → 参数设置」中把 sys.account.captchaEnabled 置为 false
# 否则每次登录都需要人工识别验证码，无法自动化


class Api(object):
    """轻量接口客户端，统一拼接 baseUrl 与超时"""

    def __init__(self, base_url, token=None):
        self.base_url = base_url
        self.session = requests.Session()
        if token:
            self.session.headers.update({"Authorization": "Bearer " + token})

    def get(self, path, **kwargs):
        kwargs.setdefault("timeout", TIMEOUT)
        return self.session.get(self.base_url + path, **kwargs)

    def post(self, path, **kwargs):
        kwargs.setdefault("timeout", TIMEOUT)
        return self.session.post(self.base_url + path, **kwargs)

    def put(self, path, **kwargs):
        kwargs.setdefault("timeout", TIMEOUT)
        return self.session.put(self.base_url + path, **kwargs)

    def delete(self, path, **kwargs):
        kwargs.setdefault("timeout", TIMEOUT)
        return self.session.delete(self.base_url + path, **kwargs)


def do_login(username=USERNAME, password=PASSWORD):
    """调用登录接口，返回 (response, json_body)"""
    resp = requests.post(
        BASE_URL + "/login",
        json={"username": username, "password": password, "code": "", "uuid": ""},
        timeout=TIMEOUT,
    )
    return resp, resp.json()


@pytest.fixture(scope="session")
def base_url():
    return BASE_URL


@pytest.fixture(scope="session")
def token():
    """登录一次，全用例复用同一个 token"""
    resp, data = do_login()
    if data.get("code") != 200:
        pytest.fail(
            "登录失败，请确认后端已启动、账号正确，且已在参数设置中关闭验证码。返回：%s" % data
        )
    return data["token"]


@pytest.fixture(scope="session")
def api(base_url, token):
    return Api(base_url, token)


@pytest.fixture
def anonymous_api(base_url):
    """不带 token 的客户端，用于鉴权负向用例"""
    return Api(base_url)


@pytest.fixture
def created_user(api):
    """创建一条测试用户，用例结束后自动清理，返回 userId 与 userName"""
    user_name = "autotest" + uuid.uuid4().hex[:6]
    payload = {
        "userName": user_name,
        "nickName": "自动化测试用户",
        "deptId": 100,
        "password": "Test@123456",
        "phonenumber": "13800138000",
        "email": "autotest@example.com",
        "sex": "0",
        "status": "0",
        "postIds": [1],
        "roleIds": [2],
        "remark": "pytest 自动化创建，用例结束后自动删除",
    }
    resp = api.post("/system/user", json=payload)
    assert resp.json()["code"] == 200, "创建测试用户失败：%s" % resp.text

    resp = api.get("/system/user/list",
                   params={"pageNum": 1, "pageSize": 10, "userName": user_name})
    rows = resp.json().get("rows", [])
    assert rows, "创建后未查询到用户：%s" % user_name
    user_id = rows[0]["userId"]

    yield {"userId": user_id, "userName": user_name}

    api.delete("/system/user/%s" % user_id)
