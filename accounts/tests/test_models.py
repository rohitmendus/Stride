from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

# Test fixture, not an application credential.
PASSWORD = "Forest-Trail!7294"


class UserModelTests(TestCase):
    def test_email_identity_is_normalized_unique_and_password_is_hashed(self):
        User = get_user_model()
        self.assertEqual(User.USERNAME_FIELD, "email")
        user = User.objects.create_user("  ALEX@Example.COM  ", PASSWORD)
        self.assertEqual(user.email, "alex@example.com")
        self.assertTrue(user.check_password(PASSWORD))
        self.assertNotEqual(user.password, PASSWORD)
        self.assertFalse(user.is_staff or user.is_superuser)
        self.assertEqual(User.objects.get_by_natural_key("ALEX@EXAMPLE.COM"), user)
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create(email="ALEX@EXAMPLE.COM", password="not-used")

    def test_superuser_manager_and_admin_forms_use_email_and_safe_passwords(self):
        User = get_user_model()
        with self.assertRaises(ValueError):
            User.objects.create_user("", PASSWORD)
        with self.assertRaises(ValueError):
            User.objects.create_superuser("admin@example.com", PASSWORD, is_staff=False)
        admin = User.objects.create_superuser("admin@example.com", PASSWORD)
        self.assertTrue(admin.is_staff and admin.is_superuser and admin.is_active)
        self.client.force_login(admin)
        response = self.client.get("/admin/accounts/user/add/")
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'name="username"')
        response = self.client.post(
            "/admin/accounts/user/add/",
            {
                "email": "MEMBER@EXAMPLE.COM",
                "first_name": "New",
                "last_name": "Member",
                "password1": PASSWORD,
                "password2": PASSWORD,
                "_save": "Save",
            },
        )
        self.assertEqual(response.status_code, 302)
        member = User.objects.get(email="member@example.com")
        self.assertTrue(member.check_password(PASSWORD))
        self.assertFalse(member.is_staff or member.is_superuser)
