import django
import requests
from django.conf import settings


class ProcountorAPIException(Exception):
    pass


class ProcountorAPIClient(object):
    def __init__(self, api, company_id, redirect_uri, client_id, client_secret):
        self.session = requests.Session()
        self.api = api.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.company_id = company_id

    def _error_handler(self, url, parameters, response):
        if response.status_code >= 400:
            raise ProcountorAPIException("GET %s params %s failed with error (%d) %s" % (url, parameters,
                                                                                         response.status_code,
                                                                                         response.content))
        return response

    def get(self, path, headers=None, **parameters):
        url = "%s/%s" % (self.api, path)
        response = self.session.get(url, parameters=parameters, allow_redirects=False)
        return self._error_handler(url, parameters, response)

    def post(self, path, body, headers=None, **parameters):
        if not headers:
            headers = {}
        url = "%s/%s" % (self.api, path)
        response = self.session.post(url, body=body, parameters=parameters, headers=headers, allow_redirects=False)
        return self._error_handler(url, parameters, response)

    def authenticate(self, username, password):
        body = {
            "response_type": "code",
            "username": username,
            "password": password,
            "company": self.company_id,
            "redirect_uri": self.redirect_uri
        }
        res = self.post("/oauth/authz", body=body, headers={"Content-type": "application/x-www-form-urlencoded"})
        if res.status_code != 302:
            raise ProcountorAPIException("Authentication failed, wrong resonse status code %d", res.status_code)
        target = self.session.get_redirect_target(res)
        print(target)


if __name__ == '__main__':
    django.setup()
    r = ProcountorAPIClient("https://api-test.procountor.com/api",
                            company_id=settings.PROCOUNTOR_COMPANY_ID,
                            redirect_uri=settings.PROCOUNTOR_REDIRECT_URL,
                            client_id=settings.PROCOUNTOR_CLIENT_ID,
                            client_secret=settings.PROCOUNTOR_CLIENT_SECRET,
                            )
    r.authenticate(settings.PROCOUNTOR_USER, settings.PROCOUNTOR_PASSWORD)
    r.get("/invoices")
