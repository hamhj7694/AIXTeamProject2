from __future__ import annotations

import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from general_api.app.domains.cases.mysql_repository import MySqlCaseRepository


class MySqlConfigurationTest(unittest.IsolatedAsyncioTestCase):
    async def test_csr_connection_defaults_are_used(self) -> None:
        pool = MagicMock()
        pool.close = MagicMock()
        pool.wait_closed = AsyncMock()

        with patch.dict(os.environ, {}, clear=True):
            with patch(
                "general_api.app.domains.cases.mysql_repository.aiomysql.create_pool",
                new=AsyncMock(return_value=pool),
            ) as create_pool:
                repository = MySqlCaseRepository()
                self.assertIs(await repository._get_pool(), pool)
                create_pool.assert_awaited_once_with(
                    host="127.0.0.1",
                    port=3306,
                    user="ham",
                    password="",
                    db="csr",
                    charset="utf8mb4",
                    connect_timeout=10,
                    autocommit=False,
                    init_command="SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED",
                    minsize=1,
                    maxsize=5,
                )
                await repository.close()

        pool.close.assert_called_once_with()
        pool.wait_closed.assert_awaited_once_with()

    async def test_environment_overrides_are_forwarded_to_pool(self) -> None:
        pool = MagicMock()
        environment = {
            "MYSQL_HOST": "csr.example.internal",
            "MYSQL_PORT": "3307",
            "MYSQL_USER": "service_user",
            "MYSQL_PASSWORD": "secret-from-runtime",
            "MYSQL_DATABASE": "csr_prod",
            "MYSQL_CONNECT_TIMEOUT_SECONDS": "7",
        }

        with patch.dict(os.environ, environment, clear=True):
            with patch(
                "general_api.app.domains.cases.mysql_repository.aiomysql.create_pool",
                new=AsyncMock(return_value=pool),
            ) as create_pool:
                repository = MySqlCaseRepository()
                await repository._get_pool()

        options = create_pool.await_args.kwargs
        self.assertEqual(options["host"], "csr.example.internal")
        self.assertEqual(options["port"], 3307)
        self.assertEqual(options["user"], "service_user")
        self.assertEqual(options["password"], "secret-from-runtime")
        self.assertEqual(options["db"], "csr_prod")
        self.assertEqual(options["connect_timeout"], 7)


if __name__ == "__main__":
    unittest.main()
