# encoding: utf-8
import json
import random
import string
import urlparse
from datetime import datetime, timedelta

import django
import requests
from django.conf import settings
import logging

logger = logging.getLogger("ProcountorAPI")


class ProcountorAPIException(Exception):
    pass


class ProcountorBankStatement(object):
    def __init__(self, row):
        self.id = row.get("id", None)
        self.accountNumber = row.get("accountNumber", None)
        self.startDate = datetime.strptime(row.get("startDate", None), "%Y-%m-%d")
        self.endDate = datetime.strptime(row.get("endDate", None), "%Y-%m-%d")
        self.currency = row.get("currency", None)
        self.numberOfDeposits = row.get("numberOfDeposits", None)
        self.depositSum = row.get("depositSum", 0)
        self.numberOfWithdrawals = row.get("numberOfWithdrawals", None)
        self.withdrawalSum = row.get("withdrawalSum", 0)
        self.startBalance = row.get("startBalance", 0)
        self.endBalance = row.get("endBalance", 0)
        self.events = []
        for potential_event in row.get("events", []):
            for event in potential_event.get("events", []) + [potential_event]:
                ProcountorBankStatementEvent(event)


class ProcountorBankStatementEvent(object):
    """
    BaknStatement event object
    """

    MAPPINGS = {
        'transaction': 'archiveCode',
        'amount': 'sum',
        'date': 'payDate',
        'event_type_description': 'explanationDescription',
        'fromto': 'name',
        'reference': 'reference',
    }

    # http://www.finanssiala.fi/maksujenvalitys/dokumentit/ISO20022_Account_Statement_Guide_V1_3.pdf pages 39-40
    EXPLANATIONCODES = {
        700: u'maksuliikennepalvelu',
        701: u'toistuva maksuliikennepalvelu',
        702: u'Laksumaksupalvelu',
        703: u'Maksupäätemaksu',
        704: u'Suoramaksupalvelu',
        705: u'Viitesiirto',
        706: u'Maksupalvelu',
        710: u'Talletus',
        720: u'Nosto',
        721: u'Maksukorttimaksu',
        722: u'Shekki',
        730: u'Pankkimaksu',
        740: u'Korkomaksu',
        750: u'Luottokorkomaksu',
        760: u'Lainamaksu',
    }

    def __init__(self, row):
        self.id = row.get("id", 0)
        self.payDate = datetime.strptime(row.get("payDate", ""), "%Y-%m-%d")
        self.valueDate = row.get("valueDate", None)
        if self.valueDate:
            self.valueDate = datetime.strptime(self.valueDate, "%Y-%m-%d")
        self.sum = row.get("sum", 0)
        self.accountNumber = row.get("accountNumber", None)
        self.name = row.get("name", None)
        self.explanationCode = row.get("explanationCode", 0)
        self.explanationDescription = self.EXPLANATIONCODES.get(self.explanationCode,
                                                                str(self.explanationCode))
        self.archiveCode = row.get("archiveCode", "")
        self.message = row.get("message", "")
        self.reference = row.get("reference", "")
        self.allocated = row.get("allocated", True)
        self.invoiceId = row.get("invoiceId", 0)
        self.productId = row.get("productId", 0)
        self.endToEndId = row.get("endToEndId", 0)
        self.attachments = []

    def __getitem__(self, key):
        """
        This is a compatibility getter for csv bills processing
        :param key:
        :return:
        """

        if key in self.MAPPINGS:
            return getattr(self, self.MAPPINGS[key], None)
        return getattr(self, key, None)


class ProcountorAPIClient(object):
    def __init__(self, api, company_id, redirect_uri, client_id, client_secret):
        self.session = requests.Session()
        self.api = api.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.company_id = company_id
        self._oauth_access_token = None
        self._oauth_refresh_token = None
        self._oauth_expires = None
        self.state = "".join([random.choice(string.digits+string.ascii_letters) for x in range(16)])

    def _error_handler(self, url, parameters, response):
        if response.status_code >= 400:
            print(response.request.body)
            print(response.request.headers)
            raise ProcountorAPIException("GET %s params %s failed with error (%d) %s" % (url, parameters,
                                                                                         response.status_code,
                                                                                         response.content))
        return response

    def get(self, path, headers=None, params=None):
        url = "%s/%s" % (self.api, path)
        if not params:
            params = {}
        response = self.session.get(url, params=params, headers=headers, allow_redirects=False)
        return self._error_handler(url, params, response)

    def post(self, path, body=None, headers=None, params=None):
        if not headers:
            headers = {}
        if not params:
            params = {}
        url = "%s/%s" % (self.api, path)
        response = self.session.post(url, data=body, params=params, headers=headers, allow_redirects=False)
        return self._error_handler(url, params, response)

    def oauth_authz(self, username, password):
        body = {
            "response_type": "code",
            "username": username,
            "password": password,
            "company": self.company_id,
            "redirect_uri": self.redirect_uri
        }
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "state": self.state,
        }
        headers = {"Content-type": "application/x-www-form-urlencoded"}
        res = self.post("/oauth/authz", body=body, params=params, headers=headers)
        if res.status_code != 302:
            raise ProcountorAPIException("Authentication failed, wrong response status code %d", res.status_code)
        target = self.session.get_redirect_target(res)

        parsed = urlparse.urlparse(target)
        target_parameters = dict(urlparse.parse_qsl(parsed.query))

        return target_parameters["code"]

    def oauth_token(self, code):
        params = {
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri,
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        headers = {"Content-type": "application/x-www-form-urlencoded"}

        res = self.post("/oauth/token", params=params, headers=headers)

        if res.status_code != 200:
            raise ProcountorAPIException("Token fetch failed, wrong response status code %d", res.status_code)

        return res.json()

    def authenticate_2phase(self, authorization_code):
        tokens = self.oauth_token(authorization_code)

        self._oauth_access_token = tokens.get("access_token", None)
        self._oauth_refresh_token = tokens.get("refresh_token", None)
        self._oauth_expires = datetime.now() + timedelta(seconds=tokens.get("expires_in", -1))

        if self._oauth_access_token:
            self.session.headers.update({"Authorization": "Bearer %s" % self._oauth_access_token})

        return True

    def authenticate(self, username, password):
        authorization_code = self.oauth_authz(username, password)

        logger.debug("Oauth phase 1 success, token: %s" % (authorization_code,))

        return self.authenticate_2phase(authorization_code=authorization_code)

    def get_invoices(self, status="PAID"):
        res = r.get("invoices", params={"status": status})
        return res.json()

    def get_bankstatements(self, start, end):
        """
        TODO: Fetch all pages!!!
        {
          "bankStatements": [
            {
              "id": 0,
              "accountNumber": "string",
              "startDate": "2018-06-02",
              "endDate": "2018-06-02",
              "currency": "EUR",
              "numberOfDeposits": 0,
              "depositSum": 0,
              "numberOfWithdrawals": 0,
              "withdrawalSum": 0,
              "startBalance": 0,
              "endBalance": 0,
              "events": [
                {
                  "id": 0,
                  "payDate": "2018-06-02",
                  "valueDate": "2018-06-02",
                  "sum": 0,
                  "accountNumber": "string",
                  "name": "string",
                  "explanationCode": 0,
                  "archiveCode": "string",
                  "message": "string",
                  "reference": "string",
                  "allocated": true,
                  "invoiceId": 0,
                  "productId": 0,
                  "endToEndId": 0,
                  "attachments": [
                    {
                      "id": 0,
                      "name": "Picture.jpg",
                      "referenceType": "INVOICE",
                      "referenceId": 0,
                      "mimeType": "string"
                    }
                  ]
                }
              ]
            }
          ]
        }
        """
        params={
            "startDate": start.strftime("%Y-%m-%d"),
            "endDate": end.strftime("%Y-%m-%d")
        }
        res = self.get("bankstatements", params=params)
        print(json.dumps(res.json(), indent=4))
        return [ProcountorBankStatement(x) for x in res.json().get("bankStatements", [])]

    def get_ledgerreceipts(self, start, end):

        params = {
            "startDate": start.strftime("%Y-%m-%d"),
            "endDate": end.strftime("%Y-%m-%d")
        }
        res = r.get("ledgerreceipts", params=params)
        return res.json()

    def get_invoices(self, start, end):
        params = {
            "startDate": start.strftime("%Y-%m-%d"),
            "endDate": end.strftime("%Y-%m-%d")
        }
        res = r.get("invoices", params=params)
        return res.json()


if __name__ == '__main__':
    django.setup()
    r = ProcountorAPIClient(api=settings.PROCOUNTOR_API_URL,
                            company_id=settings.PROCOUNTOR_COMPANY_ID,
                            redirect_uri=settings.PROCOUNTOR_REDIRECT_URL,
                            client_id=settings.PROCOUNTOR_CLIENT_ID,
                            client_secret=settings.PROCOUNTOR_CLIENT_SECRET,
                            )
    r.authenticate(settings.PROCOUNTOR_USER, settings.PROCOUNTOR_PASSWORD)

    res = r.get_ledgerreceipts(datetime.now() - timedelta(days=3), datetime.now())
    print(json.dumps(res, indent=4))

    """
    res = r.get_invoices(status='PAID')
    print(res)
    res = r.get_invoices(status='MARKED_PAID')
    print(res)
    res = r.get_bankstatements(start=datetime.now() - timedelta(days=365), end=datetime.now())
    print(res)
    """
