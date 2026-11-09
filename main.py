"""Root launcher to run Sentinel AI backend and frontend."""
import subprocess
import sys
import time

def main():
    print("==================================================")
    print("   Starting SENTINEL AI Multi-Market Platform     ")
    print("==================================================")
    
    # 1. Start FastAPI backend
    print("Starting FastAPI backend on port 8000...")
    backend = subprocess.Popen([sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8000"])
    
    time.sleep(2)
    
    # 2. Start Streamlit frontend
    print("Starting Streamlit Dashboard on port 8501...")
    frontend = subprocess.Popen([sys.executable, "-m", "streamlit", "run", "frontend/app.py", "--server.port", "8501"])

    try:
        backend.wait()
        frontend.wait()
    except KeyboardInterrupt:
        print("\nStopping Sentinel AI services...")
        backend.terminate()
        frontend.terminate()

if __name__ == "__main__":
    main()
