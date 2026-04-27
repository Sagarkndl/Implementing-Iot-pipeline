# main.py — starts all three servers
import os, sys, time, socket, subprocess

def ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8",80)); v=s.getsockname()[0]; s.close(); return v
    except: return "192.168.x.x"

def run(script):
    e = os.environ.copy(); e["PYTHONUNBUFFERED"]="1"
    return subprocess.Popen([sys.executable, script], env=e)

if __name__ == "__main__":
    print("\n  Lindstorm Warehouse v3.0 — Voice + ML\n")
    local = ip()
    print("  Starting API (5001)..."); api = run("api_app.py"); time.sleep(1.5)
    print("  Starting ML  (5002)..."); ml  = run("ml_api.py");  time.sleep(1.0)
    print("  Starting Web (5000)..."); fe  = run("frontend_app.py"); time.sleep(1.2)
    print(f"""
  ─────────────────────────────────────────
  Chrome (PC):    http://localhost:5000
  Phone (WiFi):   http://{local}:5000

  worker1     / worker123
  worker2     / worker456
  supervisor1 / super123

  Supervisor → ML Insights tab
  Worker     → ? Help button
  ─────────────────────────────────────────
  Ctrl+C to stop
""")
    try:
        api.wait()
    except KeyboardInterrupt:
        print("\n  Stopping..."); api.terminate(); ml.terminate(); fe.terminate()
