from unittest import TestCase

from django.db import connection
from django.test import Client, SimpleTestCase


class TemplateTests(SimpleTestCase):
    def test_home_uses_the_shared_layout_and_brand_partial(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/home.html")
        self.assertTemplateUsed(response, "base.html")
        self.assertTemplateUsed(response, "components/brand.html")
        self.assertContains(response, "Project foundation")


class HealthTests(TestCase):
    def test_health_and_htmx_fragment_query_postgresql(self):
        queries = []

        def record_query(execute, sql, params, many, context):
            queries.append(sql)
            return execute(sql, params, many, context)

        with connection.execute_wrapper(record_query):
            response = Client().get("/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "database": "connected"})
        self.assertIn("SELECT 1", queries)
        fragment = Client().get("/connection/", HTTP_HX_REQUEST="true")
        self.assertEqual(fragment.status_code, 200)
        self.assertIn(b'id="connection-status"', fragment.content)
        self.assertIn(b"PostgreSQL connected", fragment.content)
        self.assertNotIn(b"<!doctype", fragment.content)

    def test_unavailable_database_returns_sanitized_status(self):
        from unittest.mock import patch

        from django.db import OperationalError

        with patch(
            "core.views.connection.cursor",
            side_effect=OperationalError("private connection details"),
        ):
            response = Client().get("/health/")
            fragment = Client().get("/connection/", HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json(), {"status": "error", "database": "unavailable"}
        )
        self.assertNotIn(b"private connection details", response.content)
        self.assertIn(b"PostgreSQL unavailable", fragment.content)
