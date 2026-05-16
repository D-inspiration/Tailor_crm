import requests
import base64
from django.conf import settings

MONNIFY_BASE_URL = getattr(settings, 'MONNIFY_BASE_URL', 'https://sandbox.monnify.com')
MONNIFY_API_KEY = getattr(settings, 'MONNIFY_API_KEY', '')
MONNIFY_SECRET_KEY = getattr(settings, 'MONNIFY_SECRET_KEY', '')
MONNIFY_CONTRACT_CODE = getattr(settings, 'MONNIFY_CONTRACT_CODE', '')

class MonnifyClient:
    def __init__(self):
        self.base_url = MONNIFY_BASE_URL.rstrip('/')
        self.api_key = MONNIFY_API_KEY
        self.secret_key = MONNIFY_SECRET_KEY
        self.contract_code = MONNIFY_CONTRACT_CODE
        self.access_token = None
        
        print(f"[MONNIFY INIT] base_url={self.base_url}")
        print(f"[MONNIFY INIT] api_key={self.api_key}")
        print(f"[MONNIFY INIT] secret_key={self.secret_key[:10]}...")
        print(f"[MONNIFY INIT] contract={self.contract_code}")
    

    def _get_auth_token(self):
        credentials = base64.b64encode(f"{self.api_key}:{self.secret_key}".encode()).decode()
        print(f"[MONNIFY DEBUG] API Key: {self.api_key[:10]}...")
        print(f"[MONNIFY DEBUG] Auth URL: {self.base_url}/api/v1/auth/login")
        print(f"[MONNIFY DEBUG] Credentials (first 20 chars): {credentials[:20]}...")
        
        res = requests.post(
            f"{self.base_url}/api/v1/auth/login",
            headers={'Authorization': f'Basic {credentials}'},
            timeout=10
        )
        print(f"[MONNIFY DEBUG] Status: {res.status_code}")
        print(f"[MONNIFY DEBUG] Response: {res.text}")
        
        if res.status_code == 200:
            data = res.json()
            self.access_token = data['responseBody']['accessToken']
            return self.access_token
        raise Exception(f"Monnify auth failed: {res.text}")
    

    def _headers(self):
        if not self.access_token:
            self._get_auth_token()
        return {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }

    def initialize_transaction(self, amount, customer_email, customer_name, 
                               payment_reference, payment_description,
                               redirect_url, meta_data=None):
        payload = {
            "amount": amount,
            "customerName": customer_name,
            "customerEmail": customer_email,
            "paymentReference": payment_reference,
            "paymentDescription": payment_description,
            "currencyCode": "NGN",
            "contractCode": self.contract_code,
            "redirectUrl": redirect_url,
            "paymentMethods": ["CARD", "ACCOUNT_TRANSFER"],
            "metaData": meta_data or {}
        }
        
        print(f"[MONNIFY INIT] payload={payload}")
        
        res = requests.post(
            f"{self.base_url}/api/v1/merchant/transactions/init-transaction",
            headers=self._headers(),
            json=payload,
            timeout=10
        )
        
        print(f"[MONNIFY INIT] status={res.status_code}")
        print(f"[MONNIFY INIT] response={res.text[:500]}")
        
        if res.status_code == 200:
            return res.json()['responseBody']
        raise Exception(f"Monnify init failed: {res.text}")

    def verify_transaction(self, transaction_reference):
        url = f"{self.base_url}/api/v2/transactions/{transaction_reference}"
        print(f"[MONNIFY VERIFY] URL={url}")
        print(f"[MONNIFY VERIFY] tx_ref={transaction_reference}")
        
        res = requests.get(
            url,
            headers=self._headers(),
            timeout=10
        )
        
        print(f"[MONNIFY VERIFY] status={res.status_code}")
        print(f"[MONNIFY VERIFY] response={res.text[:1000]}")
        
        if res.status_code == 200:
            data = res.json()
            print(f"[MONNIFY VERIFY] parsed={data}")
            return data.get('responseBody', {})
        
        print(f"[MONNIFY VERIFY] FAILED: {res.text}")
        raise Exception(f"Monnify verify failed: {res.text}")

    def get_transaction_by_reference(self, payment_reference):
        """Search transaction by payment reference when tx_ref not provided in redirect."""
        url = f"{self.base_url}/api/v1/merchant/transactions/query"
        params = {"paymentReference": payment_reference}
        
        print(f"[MONNIFY QUERY] URL={url}")
        print(f"[MONNIFY QUERY] params={params}")
        
        res = requests.get(
            url,
            headers=self._headers(),
            params=params,
            timeout=10
        )
        
        print(f"[MONNIFY QUERY] status={res.status_code}")
        print(f"[MONNIFY QUERY] response={res.text[:1000]}")
        
        if res.status_code == 200:
            data = res.json()
            print(f"[MONNIFY QUERY] parsed={data}")
            
            # FIX: Monnify query returns transaction directly in responseBody, not in content array
            response_body = data.get('responseBody', {})
            
            # Check if responseBody is a dict (single transaction) or has content array
            if isinstance(response_body, dict):
                # Check if it's a paginated response with content
                if 'content' in response_body and isinstance(response_body['content'], list):
                    transactions = response_body['content']
                    if transactions:
                        tx = transactions[0]
                        print(f"[MONNIFY QUERY] found tx from content array={tx}")
                        return tx
                # Otherwise, responseBody IS the transaction itself
                elif 'paymentStatus' in response_body:
                    print(f"[MONNIFY QUERY] found tx directly in responseBody={response_body}")
                    return response_body
            
            print(f"[MONNIFY QUERY] no transactions found, responseBody={response_body}")
            return {}
        
        print(f"[MONNIFY QUERY] FAILED: {res.text}")
        raise Exception(f"Monnify query failed: {res.text}")
    