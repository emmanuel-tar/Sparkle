#!/usr/bin/env python
"""
Server subprocess wrapper - keeps server running in background.
"""
import subprocess
import sys
import time
import os

def start_server():
    """Start and maintain server process."""
    print("🚀 Starting RetailPro ERP Server...")
    print("📍 Server URL: http://127.0.0.1:8001")
    print("🔗 Health check: http://127.0.0.1:8001/health")
    print("\nPress Ctrl+C to stop the server\n")
    
    # Change to server directory
    server_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(server_dir)
    
    # Start uvicorn
    cmd = [
        sys.executable,
        "-m", "uvicorn",
        "app.main:app",
        "--port", "8001",
        "--host", "127.0.0.1",
    ]
    
    try:
        process = subprocess.Popen(cmd)
        process.wait()
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down server...")
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        print("✓ Server stopped")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    start_server()
