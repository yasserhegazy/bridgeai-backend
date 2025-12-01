import requests
import sys
import time

def test_echo():
    base_url = "http://localhost:8000"
    
    # Check health
    try:
        print(f"Checking health at {base_url}/")
        resp = requests.get(f"{base_url}/", timeout=5)
        print(f"Health check status: {resp.status_code}")
    except Exception as e:
        print(f"Health check failed: {e}")
        sys.exit(1)

    url = f"{base_url}/api/ai/echo"
    payload = {"user_input": "hello world"}
    try:
        print(f"Sending POST request to {url} with payload: {payload}")
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        print(f"Status Code: {response.status_code}")
        print(f"Response: {data}")
        
        expected_output = "Echo: hello world"
        if data.get("output") == expected_output:
             print("Test PASSED")
        else:
             print(f"Test FAILED: Expected output '{expected_output}', got '{data.get('output')}'")
             sys.exit(1)
    except Exception as e:
        print(f"Test FAILED: {e}")
        if 'response' in locals():
            print(f"Response content: {response.text}")
        sys.exit(1)

if __name__ == "__main__":
    test_echo()
