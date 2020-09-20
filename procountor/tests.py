from datetime import datetime

from django.test import TestCase
import requests_mock

from procountor.models import APIToken
from procountor.procountor_api import ProcountorAPIClient

class ProcountorLoginTests(TestCase):
    fixtures = ['test_user.json']

    def test_login_redirect_requires_auth(self):
        response = self.client.get('/procountor/')
        self.assertRedirects(response, '/login/?next=/procountor/')

    def test_login_redirect(self):
        expected_url = 'https://invalid.url/keylogin?response_type=code&client_id=test&' \
                        'redirect_uri=redirect-uri-placeholder'
        login = self.client.login(username='admin', password='dhtn')
        self.assertTrue(login, 'Could not log in')
        with self.settings(PROCOUNTOR_KEYLOGIN_URL='https://invalid.url/keylogin', PROCOUNTOR_CLIENT_ID="test",
                           PROCOUNTOR_REDIRECT_URL="redirect-uri-placeholder"):
            response = self.client.get('/procountor/')
        self.assertRedirects(response, expected_url, fetch_redirect_response=False)

    def test_login_return(self):
        response_data = {
            "api_key": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJodHRwczovL2FwaS10ZXN0LnByb2NvdW50b3IuY29tIiwiY"
                       "XVkIjoiY2xpZW50X2lkIiwic3ViIjoyNjUzNSwiY2lkIjoxNDE1OSwiaWF0IjoxNjA3OTYyNDgwLCJqdGkiOiI3ZDQ0NDg"
                       "0MC05ZGMwLTExZDEtYjI0NS01ZmZkY2U3NGZhZDIifQ.PZegXEcIDzJcOqlJEK-KKkvoQ0TgACABtZjaWQEvzOU"
        }
        login = self.client.login(username='admin', password='dhtn')
        self.assertTrue(login, 'Could not log in')
        with self.settings(PROCOUNTOR_API_URL='https://invalid.url/api'):
            with requests_mock.Mocker() as m:
                m.post('https://invalid.url/api/oauth/key', json=response_data)
                response = self.client.get('/procountor/auth/?code=abc123&expires_in=300')
            self.assertEquals(response.status_code, 200, "Return failed")

        self.assertIsNotNone(APIToken.objects.first())
        token = APIToken.objects.first()
        self.assertEqual(token.api_key, response_data["api_key"])
        self.assertEqual(APIToken.objects.count(), 1)


class ProcountorAPIClientTests(TestCase):

    def test_refresh_access_token(self):
        response_data = {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJodHRwczovL2FwaS10ZXN0LnByb2NvdW50b3IuY29t"
                            "IiwiYXVkIjoiY2xpZW50X2lkIiwic3ViIjoyNjUzNSwiY2lkIjoxNDE1OSwianRpIjoiN2Q0NDQ4NDAtOWRjMC0xM"
                            "WQxLWIyNDUtNWZmZGNlNzRmYWQyIiwiYXV0aF90aW1lIjoxNjA3OTYyNDc5LCJpYXQiOjE2MDc5NjI0ODAsImV4cCI"
                            "6MTYwNzk2NjA4MCwic2NvcGUiOiJtMm0ifQ.D8FNTcN8RzHP30rtv1cJ5Elsk9lYQ-NIS0cDyWB4hmg",
            "expires_in": 3600
        }
        with requests_mock.Mocker() as m:
            m.post('https://invalid.url/api/oauth/token?grant_type=client_credentials'
                   '&redirect_uri=redirect-url-placeholder&api_key=foobar&client_id=abc123&client_secret=abc1234',
                   json=response_data)
            client = ProcountorAPIClient(api='https://invalid.url/api', company_id=1,
                                         redirect_uri="redirect-url-placeholder", client_id="abc123",
                                         client_secret="abc1234", api_key="foobar")

            client.refresh_access_token()

            self.assertEqual(client._oauth_access_token, response_data["access_token"])
            self.assertTrue(client._oauth_expires > datetime.now())
