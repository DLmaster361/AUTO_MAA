"""check_update 非强制检查一小时内复用结果, 强制检查绕过并刷新缓存。"""

import unittest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

from app.services.update import _UpdateHandler


def _version_info(version: str) -> dict:
    return {
        "data": {
            "version_name": version,
            "url": "https://example.invalid/pkg.zip",
            "release_note": '<!-- {"v9.9.9": {"新增功能": ["x"]}} -->',
        }
    }


class UpdateCheckCacheTest(unittest.IsolatedAsyncioTestCase):
    async def test_no_update_result_is_cached_within_one_hour(self) -> None:
        updater = _UpdateHandler()
        request = AsyncMock(return_value=_version_info("v1.0.0"))
        with patch.object(updater, "_request_version_info", request):
            first = await updater.check_update("v1.0.0")
            second = await updater.check_update("v1.0.0")

        self.assertEqual(first, (False, "v1.0.0", {}))
        self.assertEqual(second, first)
        self.assertEqual(request.await_count, 1)

    async def test_force_bypasses_and_refreshes_cache(self) -> None:
        updater = _UpdateHandler()
        request = AsyncMock(
            side_effect=[_version_info("v1.0.0"), _version_info("v9.9.9")]
        )
        with patch.object(updater, "_request_version_info", request):
            await updater.check_update("v1.0.0")
            forced = await updater.check_update("v1.0.0", if_force=True)
            cached = await updater.check_update("v1.0.0")

        self.assertEqual(request.await_count, 2)
        self.assertEqual(forced[:2], (True, "v9.9.9"))
        self.assertEqual(cached, forced)

    async def test_cache_expires_after_one_hour(self) -> None:
        updater = _UpdateHandler()
        request = AsyncMock(return_value=_version_info("v1.0.0"))
        with patch.object(updater, "_request_version_info", request):
            await updater.check_update("v1.0.0")
            version, result, _ = updater._check_cache
            updater._check_cache = (
                version,
                result,
                datetime.now() - timedelta(hours=1, seconds=1),
            )
            await updater.check_update("v1.0.0")

        self.assertEqual(request.await_count, 2)

    async def test_cache_is_keyed_by_current_version(self) -> None:
        updater = _UpdateHandler()
        request = AsyncMock(return_value=_version_info("v1.0.0"))
        with patch.object(updater, "_request_version_info", request):
            await updater.check_update("v1.0.0")
            await updater.check_update("v0.9.0")

        self.assertEqual(request.await_count, 2)
