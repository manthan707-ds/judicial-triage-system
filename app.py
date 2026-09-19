"""
Flask API for the judicial case triage system.

Endpoints:
  GET  /health
  GET  /options
  GET  /priority-list?limit=50&offset=0
  GET  /pending-all?limit=50&offset=0&bucket=Complex
  POST /predict
"""

import joblib
import pandas as pd
from flask import Flask, jsonify, request

BASE = r"C:\Users\manth\SIH PROJECT"

MODEL_PATH = f"{BASE}\\triage_model_lgbm.pkl"
ENCODERS_PATH = f"{BASE}\\feature_encoders.pkl"
PRIORITY_LIST_PATH = f"{BASE}\\priority_list.json"
PENDING_ALL_PATH = f"{BASE}\\pending_scored_all.json"

FEATURES = ['type_name_label', 'purpose_name_label', 'judge_position', 'dist_code', 'court_no']

app = Flask(__name__)


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response

print("Loading model and encoders...")
model = joblib.load(MODEL_PATH)
encoders = joblib.load(ENCODERS_PATH)
print("Model classes:", list(model.classes_))

try:
    priority_df = pd.read_json(PRIORITY_LIST_PATH)
    print(f"Loaded priority_list: {len(priority_df)} rows")
except Exception as e:
    priority_df = pd.DataFrame()
    print(f"WARNING: could not load priority_list.json: {e}")

try:
    pending_all_df = pd.read_json(PENDING_ALL_PATH)
    print(f"Loaded pending_scored_all: {len(pending_all_df)} rows")
except Exception as e:
    pending_all_df = pd.DataFrame()
    print(f"WARNING: could not load pending_scored_all.json: {e}")


def encode_features(payload: dict):
    row = {}
    for col in FEATURES:
        raw_val = str(payload.get(col, ""))
        le = encoders[col]
        known_classes = set(le.classes_)
        safe_val = raw_val if raw_val in known_classes else le.classes_[0]
        row[col] = le.transform([safe_val])[0]
    return pd.DataFrame([row], columns=FEATURES)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "model_classes": list(model.classes_),
        "priority_list_rows": len(priority_df),
        "pending_all_rows": len(pending_all_df),
    })


@app.route("/options", methods=["GET"])
def options():
    return jsonify({col: sorted(encoders[col].classes_.tolist()) for col in FEATURES})


@app.route("/priority-list", methods=["GET"])
def priority_list():
    limit = int(request.args.get("limit", 50))
    offset = int(request.args.get("offset", 0))
    if priority_df.empty:
        return jsonify({"total": 0, "results": []})
    page = priority_df.iloc[offset: offset + limit]
    return jsonify({
        "total": len(priority_df),
        "offset": offset,
        "limit": limit,
        "results": page.to_dict(orient="records"),
    })


@app.route("/pending-all", methods=["GET"])
def pending_all():
    limit = int(request.args.get("limit", 50))
    offset = int(request.args.get("offset", 0))
    bucket = request.args.get("bucket")
    df = pending_all_df
    if bucket:
        df = df[df["predicted_bucket"] == bucket]
    if df.empty:
        return jsonify({"total": 0, "results": []})
    page = df.iloc[offset: offset + limit]
    return jsonify({
        "total": len(df),
        "offset": offset,
        "limit": limit,
        "results": page.to_dict(orient="records"),
    })


@app.route("/predict", methods=["POST"])
def predict():
    payload = request.get_json(force=True)
    missing = [f for f in FEATURES if f not in payload]
    if missing:
        return jsonify({"error": f"Missing fields: {missing}"}), 400

    X = encode_features(payload)
    pred = model.predict(X)[0]
    proba = model.predict_proba(X)[0]
    class_probs = {cls: float(p) for cls, p in zip(model.classes_, proba)}
    complex_idx = list(model.classes_).index("Complex")

    return jsonify({
        "predicted_bucket": pred,
        "class_probabilities": class_probs,
        "complex_risk_score": float(proba[complex_idx]),
        "input_used": payload,
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)
