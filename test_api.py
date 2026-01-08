
import httpx
import json
import socket

def check_port(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.settimeout(1)
            s.connect((host, port))
            return True
        except:
            return False

def test_login():
    host = "127.0.0.1"
    port = 8000
    print(f"Checking if port {port} is open on {host}...")
    if not check_port(host, port):
        print("Port is CLOSED!")
        return

    print("Port is OPEN.")

    try:
        with httpx.Client(timeout=5.0) as client:
            print("Testing health...")
            r = client.get("http://localhost:8000/health")
            print(f"Health: {r.status_code} - {r.text}")

            print("\nTesting login...")
            login_url = "http://localhost:8000/api/v1/auth/login"
            payload = {"username": "admin", "password": "admin123"}
            print(f"Sending POST to {login_url}...")
            r = client.post(login_url, json=payload)
            print(f"Login Response Status: {r.status_code}")
            print(f"Login Response Body: {r.text}")
    except httpx.TimeoutException:
        print("Request timed out!")
    except Exception as e:
        print(f"An error occurred: {type(e).__name__}: {e}")

if __name__ == "__main__":
    test_login()
