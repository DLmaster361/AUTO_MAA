import unittest
from unittest.mock import AsyncMock, patch

from app.services.system import System


class SetPowerExecutionTest(unittest.IsolatedAsyncioTestCase):
    async def test_system_power_action_executes_without_frontend_close(self):
        # 前端退出会连带结束后端进程，系统电源动作不得依赖前端关闭（issue #611）
        with (
            patch.object(
                System, "_request_frontend_close", new_callable=AsyncMock
            ) as request_frontend_close,
            patch(
                "app.services.system.power.execute", new_callable=AsyncMock
            ) as execute,
        ):
            await System.set_power("ShutdownForce")

        execute.assert_awaited_once_with("ShutdownForce")
        request_frontend_close.assert_not_awaited()

    async def test_kill_self_still_requests_frontend_close(self):
        # KillSelf 是后端自行退出，保留先请求前端退出的既有行为
        server = type("Server", (), {"should_exit": False})()
        with (
            patch.object(System, "_request_frontend_close", new_callable=AsyncMock) as request_frontend_close,
            patch("app.core.config.Config.server", server),
        ):
            await System.set_power("KillSelf")

        request_frontend_close.assert_awaited_once()
        self.assertTrue(server.should_exit)


if __name__ == "__main__":
    unittest.main()
