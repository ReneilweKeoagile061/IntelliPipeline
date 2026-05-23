# api/app.py
import os
import sys
from pathlib import Path

_api_dir = Path(__file__).resolve().parent
if str(_api_dir) not in sys.path:
    sys.path.insert(0, str(_api_dir))

from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS

load_dotenv(_api_dir.parent / ".env")

from routes.drift import drift_bp
from routes.explain import explain_bp
from routes.models import models_bp
from routes.query import query_bp
from routes.analytics import analytics_bp  # NEW: Import analytics blueprint

app = Flask(__name__)
CORS(app, origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","))

app.register_blueprint(models_bp)
app.register_blueprint(drift_bp)
app.register_blueprint(explain_bp)
app.register_blueprint(query_bp)
app.register_blueprint(analytics_bp)  # NEW: Register analytics blueprint


@app.route("/health")
def health():
    return {"status": "ok", "service": "intellipipeline-api"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("API_PORT", "5000")), debug=True)