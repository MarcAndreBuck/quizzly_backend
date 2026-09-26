from django.contrib.auth.models import User
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase
from auth_app.models import RevokedAccessToken


class RegistrationTests(APITestCase):
    """Test user registration and input validation."""

    def setUp(self):
        self.url = reverse('register')
        self.data = {
            'username': 'marc',
            'email': 'marc@example.com',
            'password': 'SecurePass123!',
            'confirmed_password': 'SecurePass123!',
        }

    def test_register_creates_user_with_hashed_password(self):
        response = self.client.post(self.url, self.data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['detail'], 'User created successfully!')
        user = User.objects.get(username='marc')
        self.assertEqual(user.email, 'marc@example.com')
        self.assertTrue(user.check_password('SecurePass123!'))

    def test_register_rejects_duplicate_email(self):
        User.objects.create_user(
            username='existing', email='marc@example.com',
            password='SecurePass123!'
        )

        response = self.client.post(self.url, self.data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)
        self.assertEqual(User.objects.count(), 1)

    def test_register_rejects_password_mismatch(self):
        self.data['confirmed_password'] = 'DifferentPass123!'

        response = self.client.post(self.url, self.data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data)
        self.assertFalse(User.objects.filter(username='marc').exists())


class AuthenticationTests(APITestCase):
    """Test login, logout, and token refresh through cookies."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='marc',
            email='marc@example.com',
            password='SecurePass123!',
        )
        self.credentials = {
            'username': 'marc',
            'password': 'SecurePass123!',
        }

    def login(self):
        """Log in with the test user's credentials."""
        return self.client.post(
            reverse('login'), self.credentials, format='json'
        )

    def test_login_sets_http_only_token_cookies(self):
        response = self.login()
        self.assertEqual(response.data['detail'], 'Login successfully!')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user']['id'], self.user.id)
        self.assertEqual(response.data['user']['email'], self.user.email)
        for name in ('access_token', 'refresh_token'):
            self.assertTrue(response.cookies[name].value)
            self.assertTrue(response.cookies[name]['httponly'])

    def test_login_rejects_wrong_password(self):
        self.credentials['password'] = 'wrong-password'

        response = self.login()

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotIn('access_token', response.cookies)
        self.assertNotIn('refresh_token', response.cookies)

    def test_logout_requires_authentication(self):
        response = self.client.post(reverse('logout'))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_deletes_cookies_and_blacklists_refresh_token(self):
        self.login()
        old_refresh_token = self.client.cookies['refresh_token'].value

        response = self.client.post(reverse('logout'))
        self.assertEqual(
            response.data['detail'],
            'Log-Out successfully! All Tokens will be deleted. '
            'Refresh token is now invalid.',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.cookies['access_token'].value, '')
        self.assertEqual(response.cookies['refresh_token'].value, '')
        self.client.cookies['refresh_token'] = old_refresh_token
        retry = self.client.post(reverse('token_refresh'))
        self.assertEqual(retry.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_sets_new_http_only_access_cookie(self):
        self.login()

        response = self.client.post(reverse('token_refresh'))
        self.assertEqual(response.data['detail'], 'Token refreshed')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.cookies['access_token'].value)
        self.assertTrue(response.cookies['access_token']['httponly'])

    def test_refresh_rejects_missing_cookie(self):
        response = self.client.post(reverse('token_refresh'))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_rejects_invalid_token(self):
        self.client.cookies['refresh_token'] = 'invalid-token'

        response = self.client.post(reverse('token_refresh'))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_without_refresh_cookie(self):
        self.login()
        del self.client.cookies['refresh_token']

        response = self.client.post(reverse('logout'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.cookies['access_token'].value, '')

    def test_login_rejects_missing_password(self):
        response = self.client.post(
            reverse('login'), {'username': 'marc'}, format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)

    def test_logout_invalidates_old_access_token(self):
        self.login()
        old_access_token = self.client.cookies['access_token'].value
        self.client.post(reverse('logout'))
        self.client.cookies['access_token'] = old_access_token

        response = self.client.post(reverse('logout'))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_revoked_token_displays_its_identifier(self):
        self.login()
        self.client.post(reverse('logout'))

        revoked_token = RevokedAccessToken.objects.get()
        self.assertEqual(str(revoked_token), revoked_token.jti)
