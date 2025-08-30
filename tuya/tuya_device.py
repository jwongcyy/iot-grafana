import requests
import json
import time
import hashlib
import hmac
import os
import urllib.parse
from dotenv import load_dotenv
from typing import Dict, Any, Optional

# Load environment variables from .env file
load_dotenv()

class TuyaCloudAPI:
    def __init__(self):
        self.client_id = os.getenv('TUYA_ACCESS_ID')
        self.secret = os.getenv('TUYA_ACCESS_SECRET')
        self.region = os.getenv('REGION', 'tuyaus').lower()
        self.base_url = os.getenv('TUYA_BASE_URL', self._get_base_url_from_region())
        self.access_token = None
        self.token_expire_time = 0
        
        # Validate required environment variables
        if not self.client_id or not self.secret:
            raise ValueError("TUYA_ACCESS_ID and TUYA_ACCESS_SECRET must be set in .env file")
        
        print(f"Initialized with Client ID: {self.client_id}")
        print(f"Base URL: {self.base_url}")
        
    def _get_base_url_from_region(self) -> str:
        """Get base URL based on region"""
        region_urls = {
            'tuyacn': 'https://openapi.tuyacn.com',
            'tuyaus': 'https://openapi.tuyaus.com',
            'tuyaeu': 'https://openapi.tuyaeu.com',
            'tuyain': 'https://openapi.tuyain.com'
        }
        return region_urls.get(self.region, 'https://openapi.tuyaus.com')
    
    def _string_to_sign(self, query_params: Dict[str, str] = None, body: str = "", method: str = "GET", path: str = "") -> Dict[str, str]:
        """
        Generate the string to sign according to Tuya's algorithm
        """
        # Process query parameters
        arr = []
        param_map = {}
        url_path = path
        
        if query_params:
            for key, value in query_params.items():
                arr.append(key)
                param_map[key] = value
        
        # Sort parameters alphabetically
        arr.sort()
        
        # Build URL with query parameters
        if arr:
            query_str = "&".join([f"{key}={urllib.parse.quote(str(param_map[key]))}" for key in arr])
            url_path = f"{path}?{query_str}"
        else:
            url_path = path
        
        # Calculate SHA256 of body
        if body:
            body_sha256 = hashlib.sha256(body.encode('utf-8')).hexdigest()
        else:
            body_sha256 = hashlib.sha256(b'').hexdigest()
        
        # For device API calls, we don't use Signature-Headers, so headers_str is empty
        headers_str = ""
        
        # Build the sign URL string
        sign_url = f"{method}\n{body_sha256}\n{headers_str}\n{url_path}"
        
        return {
            "signUrl": sign_url,
            "url": url_path
        }
    
    def _calc_sign(self, client_id: str, access_token: str, timestamp: str, nonce: str, sign_str: str, secret: str) -> str:
        """
        Calculate the HMAC-SHA256 signature
        """
        # Build the string to sign
        str_to_sign = client_id + access_token + timestamp + nonce + sign_str
        
        # Calculate HMAC-SHA256
        signature = hmac.new(
            secret.encode('utf-8'),
            str_to_sign.encode('utf-8'),
            hashlib.sha256
        ).hexdigest().upper()
        
        return signature
    
    def get_access_token(self) -> str:
        """Get access token from Tuya Cloud"""
        if self.access_token and time.time() < self.token_expire_time:
            return self.access_token
            
        # For token endpoint, we need to include grant_type parameter
        query_params = {
            'grant_type': '1'
        }
        
        endpoint = "/v1.0/token"
        full_url = f"{self.base_url}{endpoint}"
        timestamp = str(int(time.time() * 1000))
        method = "GET"
        nonce = ""  # Empty nonce for token request
        
        # Generate string to sign with query parameters
        sign_map = self._string_to_sign(query_params=query_params, method=method, path=endpoint)
        sign_str = sign_map["signUrl"]
        
        # Calculate signature (no access token for token request)
        access_token_for_sign = ""
        sign = self._calc_sign(self.client_id, access_token_for_sign, timestamp, nonce, sign_str, self.secret)
        
        headers = {
            'client_id': self.client_id,
            'sign': sign,
            't': timestamp,
            'sign_method': 'HMAC-SHA256',
            'Content-Type': 'application/json'
        }
        
        # Build URL with query parameters
        request_url = f"{full_url}?grant_type=1"
        
        try:
            print(f"Getting access token from: {request_url}")
            print(f"Timestamp: {timestamp}")
            print(f"String to sign: {repr(sign_str)}")
            print(f"Signature: {sign}")
            
            response = requests.get(request_url, headers=headers, timeout=10)
            response.raise_for_status()
            result = response.json()
            
            print(f"Token response: {json.dumps(result, indent=2)}")
            
            if result['success']:
                self.access_token = result['result']['access_token']
                self.token_expire_time = time.time() + result['result']['expire_time'] - 300
                print(f"Access token obtained successfully: {self.access_token[:20]}...")
                return self.access_token
            else:
                raise Exception(f"Failed to get access token: {result.get('msg', 'Unknown error')}")
                
        except requests.exceptions.RequestException as e:
            raise Exception(f"Network error: {e}")
    
    def get_device_info(self, device_id: Optional[str] = None) -> Dict[str, Any]:
        """
        GET {{url}}/v1.0/devices/{{device_id}}
        Get detailed device information
        """
        # Use device_id from parameter or environment variable
        target_device_id = device_id or os.getenv('TUYA_DEVICE_ID')
        if not target_device_id:
            raise ValueError("Device ID must be provided either as parameter or in TUYA_DEVICE_ID environment variable")
        
        access_token = self.get_access_token()
        endpoint = f"/v1.0/devices/{target_device_id}"
        full_url = f"{self.base_url}{endpoint}"
        timestamp = str(int(time.time() * 1000))
        method = "GET"
        nonce = ""  # Empty nonce for device API
        body = ""   # Empty body for GET request
        
        # Generate string to sign
        sign_map = self._string_to_sign(method=method, path=endpoint)
        sign_str = sign_map["signUrl"]
        
        # Calculate signature
        sign = self._calc_sign(self.client_id, access_token, timestamp, nonce, sign_str, self.secret)
        
        headers = {
            'client_id': self.client_id,
            'access_token': access_token,
            'sign': sign,
            't': timestamp,
            'sign_method': 'HMAC-SHA256',
            'Content-Type': 'application/json'
        }
        
        print(f"\nGetting device info from: {full_url}")
        print(f"Timestamp: {timestamp}")
        print(f"String to sign: {repr(sign_str)}")
        print(f"Signature: {sign}")
        print(f"Access Token: {access_token[:20]}...")
        
        try:
            response = requests.get(full_url, headers=headers, timeout=10)
            print(f"Response status: {response.status_code}")
            
            result = response.json()
            print(f"Device info response: {json.dumps(result, indent=2)}")
            
            return result
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to get device info: {e}")
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse JSON response: {e}")
    
    def get_device_status(self, device_id: Optional[str] = None) -> Dict[str, Any]:
        """
        GET {{url}}/v1.0/devices/{{device_id}}/status
        Get device status
        """
        target_device_id = device_id or os.getenv('TUYA_DEVICE_ID')
        if not target_device_id:
            raise ValueError("Device ID must be provided")
        
        access_token = self.get_access_token()
        endpoint = f"/v1.0/devices/{target_device_id}/status"
        full_url = f"{self.base_url}{endpoint}"
        timestamp = str(int(time.time() * 1000))
        method = "GET"
        nonce = ""  # Empty nonce for device API
        body = ""   # Empty body for GET request
        
        # Generate string to sign
        sign_map = self._string_to_sign(method=method, path=endpoint)
        sign_str = sign_map["signUrl"]
        
        # Calculate signature
        sign = self._calc_sign(self.client_id, access_token, timestamp, nonce, sign_str, self.secret)
        
        headers = {
            'client_id': self.client_id,
            'access_token': access_token,
            'sign': sign,
            't': timestamp,
            'sign_method': 'HMAC-SHA256',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.get(full_url, headers=headers, timeout=10)
            return response.json()
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to get device status: {e}")

# Alternative method using POST request for token
class TuyaCloudAPIPost:
    def __init__(self):
        self.client_id = os.getenv('TUYA_ACCESS_ID')
        self.secret = os.getenv('TUYA_ACCESS_SECRET')
        self.base_url = os.getenv('TUYA_BASE_URL', 'https://openapi.tuyaus.com')
        
    def get_access_token_post(self):
        """Get access token using POST request"""
        url = f"{self.base_url}/v1.0/token"
        timestamp = str(int(time.time() * 1000))
        
        # Generate signature
        sign_message = self.client_id + timestamp
        sign = hmac.new(
            self.secret.encode('utf-8'),
            sign_message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest().upper()
        
        headers = {
            'client_id': self.client_id,
            'sign': sign,
            't': timestamp,
            'sign_method': 'HMAC-SHA256',
            'Content-Type': 'application/json'
        }
        
        # POST body with grant_type
        data = {
            'grant_type': 1
        }
        
        response = requests.post(url, headers=headers, json=data)
        return response.json()

# Usage example
if __name__ == "__main__":
    try:
        print("Testing Tuya Cloud API...")
        
        # Try the main method first
        print("Trying main method with query parameters...")
        tuya_api = TuyaCloudAPI()
        device_id = os.getenv('TUYA_DEVICE_ID')
        
        if not device_id:
            print("ERROR: TUYA_DEVICE_ID not found in environment variables")
        else:
            print(f"Device ID: {device_id}")
            device_info = tuya_api.get_device_info(device_id)
            
            if device_info.get('success'):
                print("✅ SUCCESS: Device information retrieved!")
                print(f"Device Name: {device_info['result'].get('name', 'N/A')}")
                print(f"Online Status: {device_info['result'].get('online', 'N/A')}")
                print(f"Category: {device_info['result'].get('category', 'N/A')}")
            else:
                print(f"❌ ERROR: {device_info.get('msg', 'Unknown error')}")
                print(f"Error Code: {device_info.get('code', 'N/A')}")
                
                # If main method fails, try POST method
                if device_info.get('code') == 1004 or 'grant_type' in device_info.get('msg', '').lower():
                    print("\nTrying POST method as fallback...")
                    post_api = TuyaCloudAPIPost()
                    post_result = post_api.get_access_token_post()
                    print(f"POST method result: {json.dumps(post_result, indent=2)}")
            
    except ValueError as e:
        print(f"Configuration error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()