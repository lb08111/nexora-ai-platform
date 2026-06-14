# -*- coding: utf-8 -*-
"""
Jotaduo AIops 平台 100 用户并发压力测试
模拟真实用户操作：登录 → 列表查询 → 聊天 → 审计 → 审批
区分 admin / operator 角色权限，operator 只访问已授权智能体
"""

import random
import string
import uuid

from locust import HttpUser, task, between

ADMIN_USER = "admin"

USER_AGENT_MAP = {
    "huangmizhi": ["default", "Test-bot", "AI-ops", "test"],
    "liming": ["default", "Test-bot", "AI-ops"],
    "liuyang": ["default", "Test-bot", "AI-ops", "test"],
    "luwenxing": ["default", "Test-bot", "AI-ops", "test"],
    "luyankun": ["default", "Test-bot", "AI-ops", "test"],
    "wangshengquan": ["default", "Test-bot", "AI-ops", "test"],
    "zhangjiahe": ["default", "Test-bot", "AI-ops", "test"],
    "zhangming": ["AI-minitor", "test"],
    "zouyumeng": ["default", "Test-bot", "AI-ops", "test"],
}
OPERATOR_USERS = list(USER_AGENT_MAP.keys())
ALL_AGENTS = ["test", "default", "AI-ops", "Test-bot", "AI-minitor"]
PASSWORD = "Test@2025"


class AIOpsUser(HttpUser):
    wait_time = between(1, 3)
    host = "http://127.0.0.1:8088"

    def on_start(self):
        if random.random() < 0.1:
            self.username = ADMIN_USER
            self.is_admin = True
            self.my_agents = ALL_AGENTS
        else:
            self.username = random.choice(OPERATOR_USERS)
            self.is_admin = False
            self.my_agents = USER_AGENT_MAP[self.username]
        self.token = None
        self.agent_id = random.choice(self.my_agents)
        self.session_id = str(uuid.uuid4())
        self.do_login()

    def do_login(self):
        resp = self.client.post(
            "/api/auth/login",
            json={"username": self.username, "password": PASSWORD},
            name="/api/auth/login",
        )
        if resp.status_code == 200:
            data = resp.json()
            self.token = data.get("token") or data.get("access_token")

    @property
    def headers(self):
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}

    # ── 通用接口（所有用户） ──

    @task(5)
    def list_agents(self):
        self.client.get(
            "/api/agents",
            headers=self.headers,
            name="/api/agents",
        )

    @task(5)
    def list_skills(self):
        self.client.get(
            "/api/skills",
            headers=self.headers,
            name="/api/skills",
        )

    @task(3)
    def list_chats(self):
        self.client.get(
            f"/api/agents/{self.agent_id}/chats",
            headers=self.headers,
            name="/api/agents/{id}/chats [GET]",
        )

    @task(4)
    def send_chat(self):
        msg = "".join(random.choices(string.ascii_letters + " ", k=50))
        self.client.post(
            f"/api/agents/{self.agent_id}/chats",
            headers=self.headers,
            json={
                "session_id": self.session_id,
                "user_id": self.username,
                "message": msg,
            },
            name="/api/agents/{id}/chats [POST]",
        )

    @task(1)
    def spa_page(self):
        self.client.get(
            random.choice(["/", "/login", "/chat", "/agent", "/settings"]),
            name="/[SPA pages]",
        )

    @task(1)
    def static_asset(self):
        self.client.get("/logo-icon.svg", name="/logo-icon.svg")

    # ── 管理员接口 ──

    @task(3)
    def admin_audit_events(self):
        if not self.is_admin:
            return
        self.client.get(
            "/api/jotaduo/audit/events",
            headers=self.headers,
            params={"limit": 20, "offset": 0},
            name="/api/jotaduo/audit/events",
        )

    @task(2)
    def admin_approval_requests(self):
        if not self.is_admin:
            return
        self.client.get(
            "/api/jotaduo/approval-requests",
            headers=self.headers,
            params={"limit": 10},
            name="/api/jotaduo/approval-requests",
        )

    @task(2)
    def admin_governance_policies(self):
        if not self.is_admin:
            return
        self.client.get(
            "/api/jotaduo/governance/policies",
            headers=self.headers,
            name="/api/jotaduo/governance/policies",
        )

    @task(2)
    def admin_list_users(self):
        if not self.is_admin:
            return
        self.client.get(
            "/api/auth/users",
            headers=self.headers,
            name="/api/auth/users",
        )

    @task(1)
    def admin_agent_grants(self):
        if not self.is_admin:
            return
        self.client.get(
            f"/api/jotaduo/agent-grants/{random.choice(ALL_AGENTS)}",
            headers=self.headers,
            name="/api/jotaduo/agent-grants/{id}",
        )
