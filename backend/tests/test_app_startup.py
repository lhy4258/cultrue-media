import asyncio
import unittest
from unittest.mock import patch

import app.main as main


class StartupTests(unittest.TestCase):
    def test_database_schema_failure_does_not_block_application_startup(self):
        class FailingRepository:
            def __init__(self, database_url):
                self.database_url = database_url

            async def ensure_schema(self):
                raise RuntimeError("database unavailable")

        with patch.object(main, "PostgresReviewRepository", FailingRepository):
            asyncio.run(main.ensure_database_schema())


if __name__ == "__main__":
    unittest.main()
