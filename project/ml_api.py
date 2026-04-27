# ml_api.py  —  ML prediction endpoints  (port 5002)
from flask import Flask, jsonify
from ml_engine import predict_location_demand, score_worker_performance, seed_demo_pick_log

app = Flask(__name__)

@app.get("/ml/demand-forecast")
def demand():
    try:
        return jsonify({"ok":True,"predictions":predict_location_demand()})
    except Exception as e:
        return jsonify({"ok":False,"error":str(e),"predictions":[]})

@app.get("/ml/worker-performance")
def perf():
    try:
        return jsonify({"ok":True,"scores":score_worker_performance()})
    except Exception as e:
        return jsonify({"ok":False,"error":str(e),"scores":[]})

@app.get("/ml/health")
def health():
    return jsonify({"ok":True})

if __name__ == "__main__":
    seed_demo_pick_log()
    print("ML API on port 5002")
    app.run(host="0.0.0.0", port=5002, debug=False)
