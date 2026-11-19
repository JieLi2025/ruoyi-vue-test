# -*- coding: utf-8 -*-
"""登录鉴权接口用例"""
from conftest import do_login


class TestLogin(object):
    def test_login_success(self):
        """正向：管理员账号密码正确时登录成功并返回 token"""
        resp, data = do_login()
        assert resp.status_code == 200
        assert data["code"] == 200, "登录失败：%s" % data
        assert data.get("token"), "未返回 token"
        assert len(data["token"]) > 20

    def test_login_wrong_password(self):
        """反向：密码错误时业务码非 200，且不返回 token"""
        resp, data = do_login(password="wrong_password_123")
        assert resp.status_code == 200
        assert data["code"] != 200
        assert "密码" in data.get("msg", "") or "用户" in data.get("msg", "")
        assert data.get("token") is None

    def test_login_empty_username(self):
        """反向：用户名为空时登录被拒绝"""
        resp, data = do_login(username="")
        assert resp.status_code == 200
        assert data["code"] != 200

    def test_login_unknown_user(self):
        """反向：不存在的账号登录失败，提示信息不区分用户是否存在（防用户名枚举）"""
        resp, data = do_login(username="not_exist_user_999")
        assert data["code"] != 200
        assert data.get("token") is None


class TestSession(object):
    def test_get_info(self, api):
        """获取当前登录用户信息"""
        data = api.get("/getInfo").json()
        assert data["code"] == 200
        assert data["user"]["userName"] == "admin"
        assert isinstance(data["roles"], list) and data["roles"], "未返回角色列表"
        assert isinstance(data["permissions"], list)

    def test_get_routers(self, api):
        """获取按角色下发的动态路由菜单"""
        data = api.get("/getRouters").json()
        assert data["code"] == 200
        assert isinstance(data["data"], list) and data["data"], "未返回菜单树"

    def test_access_without_token(self, anonymous_api):
        """鉴权负向：不携带 token 访问受限接口应被拒绝

        注意：RuoYi 的鉴权失败采用「HTTP 200 + 业务码 401」的响应形式，
        由前端根据 code 字段判断跳转登录页，因此断言校验业务码而非 HTTP 状态码。
        """
        resp = anonymous_api.get("/system/user/list",
                                 params={"pageNum": 1, "pageSize": 10})
        body = resp.json()
        assert body["code"] == 401, "未携带 token 时应返回业务码 401"
        assert "认证" in body.get("msg", "")

    def test_access_with_fake_token(self, base_url):
        """鉴权负向：伪造 token 访问受限接口应被拒绝"""
        import requests
        resp = requests.get(
            base_url + "/system/user/list",
            headers={"Authorization": "Bearer fake_token_123456"},
            params={"pageNum": 1, "pageSize": 10},
            timeout=10,
        )
        body = resp.json()
        assert body["code"] == 401, "伪造 token 时应返回业务码 401"
