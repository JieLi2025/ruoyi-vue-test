# -*- coding: utf-8 -*-
"""
用户管理接口用例

覆盖：列表查询、新增、按条件查询、详情回显、唯一性校验、
密码重置、删除清理，以及已知缺陷的回归标记（xfail）。
"""
import pytest


class TestUserQuery(object):
    def test_user_list(self, api):
        """正向：用户列表分页查询返回正确结构"""
        data = api.get("/system/user/list",
                       params={"pageNum": 1, "pageSize": 10}).json()
        assert data["code"] == 200
        assert isinstance(data["rows"], list)
        assert data["total"] > 0

    def test_user_list_by_name(self, api):
        """正向：按用户名模糊查询只返回匹配记录"""
        data = api.get("/system/user/list",
                       params={"pageNum": 1, "pageSize": 10, "userName": "adm"}).json()
        assert data["code"] == 200
        assert all("adm" in row["userName"] for row in data["rows"])

    def test_user_list_paging(self, api):
        """边界：切换每页条数，返回条数不超过 pageSize"""
        data = api.get("/system/user/list",
                       params={"pageNum": 1, "pageSize": 5}).json()
        assert data["code"] == 200
        assert len(data["rows"]) <= 5


class TestUserCrud(object):
    def test_create_user(self, created_user):
        """正向：新增用户成功，且可按用户名查回"""
        assert created_user["userId"] > 0
        assert created_user["userName"].startswith("autotest")

    def test_user_detail(self, api, created_user):
        """正向：详情接口回显与新增时一致，角色关联未丢失"""
        data = api.get("/system/user/%s" % created_user["userId"]).json()
        assert data["code"] == 200
        assert data["data"]["userName"] == created_user["userName"]
        assert isinstance(data["roleIds"], list) and data["roleIds"], "角色关联丢失"

    def test_duplicate_username_rejected(self, api, created_user):
        """反向：重复登录账号新增应被拦截"""
        payload = {
            "userName": created_user["userName"],
            "nickName": "重复账号测试",
            "deptId": 100,
            "password": "Test@123456",
        }
        data = api.post("/system/user", json=payload).json()
        assert data["code"] != 200
        assert "已存在" in data.get("msg", "")

    def test_reset_password(self, api, created_user):
        """正向：重置密码接口调用成功"""
        data = api.put("/system/user/resetPwd",
                       json={"userId": created_user["userId"],
                             "password": "Test@654321"}).json()
        assert data["code"] == 200

    def test_delete_user(self, api, created_user):
        """正向：删除用户后列表中不再出现"""
        data = api.delete("/system/user/%s" % created_user["userId"]).json()
        assert data["code"] == 200
        check = api.get("/system/user/list",
                        params={"pageNum": 1, "pageSize": 10,
                                "userName": created_user["userName"]}).json()
        assert all(row["userId"] != created_user["userId"] for row in check["rows"])


class TestUserValidation(object):
    @pytest.mark.xfail(reason="已知缺陷 BUG-003：手机号格式仅前端校验，后端仅校验长度，接口层可传入非法规格")
    def test_phonenumber_format_should_be_rejected(self, api):
        """缺陷回归：后端应独立校验手机号格式，非法号码应被拒绝

        当前实际结果：接口返回 200，非法手机号可入库。
        注意：系统对手机号有唯一性校验，因此这里使用随机生成的非法号段号码，
        避免因「手机号码已存在」被拦截而误判为缺陷已修复。
        """
        import uuid
        import random
        name = "autotest" + uuid.uuid4().hex[:6]
        # 11 位、以 12 开头（号段非法），后 9 位随机，规避唯一性校验干扰
        phone = "12" + str(random.randint(100000000, 999999999))
        payload = {
            "userName": name,
            "nickName": "非法手机号测试",
            "deptId": 100,
            "password": "Test@123456",
            "phonenumber": phone,
            "status": "0",
        }
        body = api.post("/system/user", json=payload).json()

        created_id = None
        if body.get("code") == 200:
            rows = api.get("/system/user/list",
                           params={"pageNum": 1, "pageSize": 10,
                                   "userName": name}).json().get("rows", [])
            if rows:
                created_id = rows[0]["userId"]
        try:
            assert body["code"] != 200, "后端未拦截非法手机号，缺陷成立"
        finally:
            if created_id:
                api.delete("/system/user/%s" % created_id)

    @pytest.mark.xfail(reason="已知缺陷 BUG-004：用户名称首尾空格未做 trim 规范化")
    def test_username_should_be_trimmed(self, api):
        """缺陷回归：用户名首尾空格应被去除或拦截

        当前实际结果：带空格的用户名可保存成功。
        用例结束后自动清理创建出的账号，避免残留脏数据。
        """
        import uuid
        name = "  at" + uuid.uuid4().hex[:6] + "  "
        payload = {
            "userName": name,
            "nickName": "空格测试",
            "deptId": 100,
            "password": "Test@123456",
            "status": "0",
        }
        body = api.post("/system/user", json=payload).json()

        created_id = None
        if body.get("code") == 200:
            rows = api.get("/system/user/list",
                           params={"pageNum": 1, "pageSize": 10,
                                   "userName": name.strip()}).json().get("rows", [])
            for row in rows:
                if row["userName"] == name:
                    created_id = row["userId"]
                    break
        try:
            assert body["code"] != 200, "带空格的用户名被接受，缺陷成立"
        finally:
            if created_id:
                api.delete("/system/user/%s" % created_id)
