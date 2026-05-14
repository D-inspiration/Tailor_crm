"""app.py — SBEAE Flask application factory."""
import sys
import os

# Make all subpackages importable without install
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, jsonify
from config import Config
from controllers.controllers import auth_bp, event_bp, session_bp, webhook_bp
from utils.logger import get_logger

logger = get_logger("App")


def create_app(config_class=Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)

    # ── Blueprints ─────────────────────────────────────────────────────────
    app.register_blueprint(auth_bp)
    app.register_blueprint(event_bp)
    app.register_blueprint(session_bp)
    app.register_blueprint(webhook_bp)

    # ── Health endpoint ────────────────────────────────────────────────────
    @app.get("/health")
    def health():
        return jsonify({"status": "ok", "service": "SBEAE"}), 200

    # ── Global error handlers ──────────────────────────────────────────────
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "not_found"}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"error": "method_not_allowed"}), 405

    @app.errorhandler(500)
    def internal_error(e):
        logger.exception("Unhandled exception")
        return jsonify({"error": "internal_server_error"}), 500

    logger.info("SBEAE Flask app created, routes registered")
    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="127.0.0.1", port=5050, debug=False)
