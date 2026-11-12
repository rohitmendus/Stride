from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from accounts.forms import RegistrationForm

from .test_models import PASSWORD


class AuthenticationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            "alex@example.com", PASSWORD, first_name="Alex"
        )

    def test_login_session_and_post_logout(self):
        self.assertRedirects(
            self.client.get("/"), "/login/?next=/", fetch_redirect_response=False
        )
        page = self.client.get("/login/")
        self.assertEqual(page.status_code, 200)
        self.assertTemplateUsed(page, "accounts/login.html")
        response = self.client.post(
            "/login/", {"username": " ALEX@EXAMPLE.COM ", "password": PASSWORD}
        )
        self.assertRedirects(response, "/dashboard/")
        self.assertTrue(response.cookies[settings.SESSION_COOKIE_NAME]["httponly"])
        home = self.client.get("/")
        self.assertContains(home, "alex@example.com")
        self.assertIn("no-store", home.headers["Cache-Control"])
        self.assertEqual(self.client.get("/logout/").status_code, 405)
        self.assertIn("_auth_user_id", self.client.session)
        self.assertRedirects(self.client.post("/logout/"), "/login/")
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertRedirects(
            self.client.get("/"), "/login/?next=/", fetch_redirect_response=False
        )

    def test_registration_creates_a_regular_user_and_starts_a_session(self):
        page = self.client.get("/register/")
        self.assertEqual(page.status_code, 200)
        self.assertTemplateUsed(page, "accounts/register.html")
        response = self.client.post(
            "/register/",
            {
                "first_name": "Sam",
                "email": " SAM@EXAMPLE.COM ",
                "password1": PASSWORD,
                "password2": PASSWORD,
                "is_staff": "true",
                "is_superuser": "true",
            },
        )
        self.assertRedirects(response, "/")
        user = get_user_model().objects.get(email="sam@example.com")
        self.assertTrue(user.check_password(PASSWORD))
        self.assertFalse(user.is_staff or user.is_superuser)
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)
        self.assertContains(self.client.get("/"), "sam@example.com")
        self.assertRedirects(self.client.get("/register/"), "/")
        self.assertRedirects(self.client.get("/login/"), "/dashboard/")

    def test_invalid_registration_does_not_create_or_sign_in_a_user(self):
        valid = {
            "first_name": "Sam",
            "email": "sam@example.com",
            "password1": PASSWORD,
            "password2": PASSWORD,
        }
        for changes in (
            {"email": "ALEX@EXAMPLE.COM"},
            {"password2": "different"},
            {"password1": "short", "password2": "short"},
            {"first_name": "   "},
        ):
            with self.subTest(changes=changes):
                response = self.client.post("/register/", valid | changes)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context["form"].errors)
                self.assertEqual(get_user_model().objects.count(), 1)
                self.assertNotIn("_auth_user_id", self.client.session)

    def test_invalid_credentials_and_inactive_accounts_cannot_sign_in(self):
        for email, password in (
            ("alex@example.com", "wrong"),
            ("unknown@example.com", PASSWORD),
        ):
            response = self.client.post(
                "/login/", {"username": email, "password": password}
            )
            self.assertContains(response, "Email or password is incorrect.")
            self.assertNotIn("_auth_user_id", self.client.session)
        self.user.is_active = False
        self.user.save()
        response = self.client.post(
            "/login/", {"username": self.user.email, "password": PASSWORD}
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_rejects_external_redirect_targets(self):
        for target in ("https://evil.example/", "//evil.example/"):
            self.assertRedirects(
                self.client.post(
                    "/login/",
                    {"username": self.user.email, "password": PASSWORD, "next": target},
                ),
                "/dashboard/",
            )
            self.client.logout()

    def test_csrf_is_required_for_registration_login_and_logout(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(
            client.post("/register/", {"email": "sam@example.com"}).status_code, 403
        )
        credentials = {"username": self.user.email, "password": PASSWORD}
        self.assertEqual(client.post("/login/", credentials).status_code, 403)
        client.get("/login/")
        token = client.cookies[settings.CSRF_COOKIE_NAME].value
        self.assertEqual(
            client.post(
                "/login/",
                credentials | {"csrfmiddlewaretoken": token},
                HTTP_ORIGIN="https://evil.example",
            ).status_code,
            403,
        )
        self.assertRedirects(
            client.post("/login/", credentials | {"csrfmiddlewaretoken": token}),
            "/dashboard/",
        )
        self.assertEqual(client.post("/logout/").status_code, 403)
        self.assertIn("_auth_user_id", client.session)
        self.assertRedirects(
            client.post(
                "/logout/",
                {
                    "csrfmiddlewaretoken": client.cookies[
                        settings.CSRF_COOKIE_NAME
                    ].value
                },
            ),
            "/login/",
        )

    def test_duplicate_email_created_during_registration_returns_a_form_error(self):
        original = RegistrationForm.is_valid

        def competing_registration(form):
            valid = original(form)
            get_user_model().objects.create_user("sam@example.com", PASSWORD)
            return valid

        with patch.object(RegistrationForm, "is_valid", competing_registration):
            response = self.client.post(
                "/register/",
                {
                    "first_name": "Sam",
                    "email": "sam@example.com",
                    "password1": PASSWORD,
                    "password2": PASSWORD,
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertIn("email", response.context["form"].errors)
        self.assertEqual(
            get_user_model().objects.filter(email="sam@example.com").count(), 1
        )
        self.assertNotIn("_auth_user_id", self.client.session)
