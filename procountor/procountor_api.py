import random
import string
from datetime import datetime, timedelta
from decimal import Decimal

import re

import requests
import logging

from membership.reference_numbers import normalize_reference

logger = logging.getLogger("ProcountorAPI")


class ProcountorAPIException(Exception):
    pass


SEPA_MESSAGE_PREFIXES = ("SEPA-MAKSU", "SEPA PIKASIIRTO")


def reference_from_sepa_message(message):
    """
    Find a payment reference in the message of a SEPA credit transfer.

    When the payer's bank does not pass the reference on as a reference
    payment, it arrives inside the message, which is laid out in
    fixed-width columns: payment type, reference or free text, the payer
    bank's BIC and sometimes a country code. For example:

    "SEPA-MAKSU                         1234 26011                         HANDSESSXXX                        FI"

    The digit groups of a reference are separated by single spaces and the
    columns by several, so the columns are split on runs of whitespace.

    Returns the reference in national form, or None if the message does not
    carry a valid one.
    """
    if not message:
        return None
    message = message.strip()
    for prefix in SEPA_MESSAGE_PREFIXES:
        if message.startswith(prefix):
            columns = re.split(r"\s{2,}", message[len(prefix):].strip())
            return normalize_reference(columns[0])
    return None


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
                self.events.append(ProcountorBankStatementEvent(event))


class ProcountorBankStatementEvent(object):
    """
    BankStatement event object
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
        700: 'maksuliikennepalvelu',
        701: 'toistuva maksuliikennepalvelu',
        702: 'Laksumaksupalvelu',
        703: 'Maksupäätemaksu',
        704: 'Suoramaksupalvelu',
        705: 'Viitesiirto',
        706: 'Maksupalvelu',
        710: 'Talletus',
        720: 'Nosto',
        721: 'Maksukorttimaksu',
        722: 'Shekki',
        730: 'Pankkimaksu',
        740: 'Korkomaksu',
        750: 'Luottokorkomaksu',
        760: 'Lainamaksu',
    }

    def __init__(self, row):
        self.id = row.get("id", 0)
        self.payDate = datetime.strptime(row.get("payDate", ""), "%Y-%m-%d")
        self.valueDate = row.get("valueDate", None)
        if self.valueDate:
            self.valueDate = datetime.strptime(self.valueDate, "%Y-%m-%d")
        self.sum = row.get("sum", 0)
        self.accountNumber = row.get("accountNumber", None)
        self.name = row.get("name", None) or ""  # Force name to be string
        self.explanationCode = row.get("explanationCode", 0)
        self.explanationDescription = self.EXPLANATIONCODES.get(self.explanationCode,
                                                                str(self.explanationCode))
        self.archiveCode = row.get("archiveCode", "")
        self.message = row.get("message", "") or ""  # Force message to be string
        self.reference = (row.get("reference", "") or "").replace(" ", "").lstrip("0")
        if not self.reference:
            # The reference may be inside the message of a SEPA payment
            self.reference = reference_from_sepa_message(self.message) or ""

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


class ProcountorReferencePayment(object):
    """
    Procountor Reference Payments
    """

    MAPPINGS = {
        'transaction': 'archiveId',
        'amount': 'sum',
        'date': 'paymentDate',
        'fromto': 'name',
        'reference': 'reference',
    }

    def __init__(self, row):
        self.id = row.get("id", 0)
        self.paymentDate = row.get("paymentDate", None)
        if self.paymentDate:
            self.paymentDate = datetime.strptime(self.paymentDate, "%Y-%m-%d")
        self.valueDate = row.get("valueDate", None)
        if self.valueDate:
            self.valueDate = datetime.strptime(self.valueDate, "%Y-%m-%d")
        self.sum = Decimal(row.get("sum", 0))
        self.accountNumber = row.get("accountNumber", None)
        self.name = row.get("name", None)
        self.reference = row.get("bankReference", "").replace(' ', '').lstrip('0')
        self.archiveId = row.get("archiveId", "")
        self.allocated = row.get("allocated", True)
        self.invoiceId = row.get("invoiceId", 0)
        self.event_type_description = "Viitesiirto"
        self.message = ""
        self.attachments = []

    def __getitem__(self, key):
        """
        This is a compatibility getter for csv bills processing
        ReferencePayment {
            id (integer, optional): Unique identifier of the reference payment. ,
            accountNumber (string, optional): Account number for which the reference payment is generated. ,
            valueDate (string, optional): Date when the event was registered in the counterpart bank. ,
            paymentDate (string, optional): Date when the payment was paid by the payer in his/her own bank. ,
            sum (number, optional): The total amount for the reference payment. ,
            name (string, optional): Name of the counterparty. ,
            bankReference (string, optional): A reference value for the bank. ,
            archiveId (string, optional): Archive code of the reference payment. Archive codes are unique in one bank
            but two events from different banks can share the same archive code. ,
            allocated (boolean, optional): Is the reference payment allocated to an invoice. If it is, the event must
            also have an invoice ID. ,
            invoiceId (integer, optional): Unique identifier of the invoice linked to the event. ,
            attachments (Array[Attachment], optional): A list of attachments added to the reference payment.
        }
        """

        if key in self.MAPPINGS:
            return getattr(self, self.MAPPINGS[key], None)
        return getattr(self, key, None)


class ProcountorAPIClient(object):
    def __init__(self, api, company_id, redirect_uri, client_id, client_secret, api_key):
        self.session = requests.Session()
        self.api = api.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.company_id = company_id
        self.api_key = api_key
        self._oauth_access_token = None
        self._oauth_expires = None
        self.state = "".join([random.choice(string.digits+string.ascii_letters) for x in range(16)])

    def _error_handler(self, url, parameters, response):
        if response.status_code >= 400:
            logger.debug(response.request.body)
            logger.debug(response.request.headers)
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

    def refresh_access_token(self):
        if self._oauth_access_token and self._oauth_expires > (datetime.now() + timedelta(seconds=60)):
            return

        params = {
            "grant_type": "client_credentials",
            "redirect_uri": self.redirect_uri,
            "api_key": self.api_key,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        headers = {"Content-type": "application/x-www-form-urlencoded"}

        res = self.post("oauth/token", body=params, headers=headers)

        if res.status_code != 200:
            raise ProcountorAPIException("Token fetch failed, wrong response status code %d", res.status_code)

        data = res.json()

        self._oauth_access_token = data["access_token"]
        self._oauth_expires = datetime.now() + timedelta(seconds=data["expires_in"])
        self.session.headers.update({"Authorization": "Bearer %s" % self._oauth_access_token})

    def get_referencepayments(self, start, end):
        """
        Get refence payments
        :param start:
        :param end:
        :return:
        """
        params = {
            "startDate": start.strftime("%Y-%m-%d"),
            "endDate": end.strftime("%Y-%m-%d"),
            "orderById": "asc",
        }
        out = []
        while True:
            res = self.get("referencepayments", params=params)
            result = res.json()
            meta = result.get("meta")
            out += [ProcountorReferencePayment(row) for row in result.get("results", [])]
            if meta.get("resultCount") == meta.get("pageSize"):
                params["previousId"] = str(out[-1].id)
            else:
                break
        return out

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
        params = {
            "startDate": start.strftime("%Y-%m-%d"),
            "endDate": end.strftime("%Y-%m-%d")
        }
        res = self.get("bankstatements", params=params)
        return [ProcountorBankStatement(x) for x in res.json().get("results", [])]

    def get_ledgerreceipts(self, start, end):

        params = {
            "startDate": start.strftime("%Y-%m-%d"),
            "endDate": end.strftime("%Y-%m-%d")
        }
        res = self.get("ledgerreceipts", params=params)
        return res.json()

    def get_invoices(self, start, end, status="PAID"):
        params = {
            "startDate": start.strftime("%Y-%m-%d"),
            "endDate": end.strftime("%Y-%m-%d"),
            "status": status,
        }
        res = self.get("invoices", params=params)
        return res.json()
