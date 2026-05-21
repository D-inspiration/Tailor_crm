"""Flask application factory with SQLAlchemy integration."""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, jsonify
from config import Config
from utils.extensions import db
from controllers.auth_controller import auth_bp
from controllers.event_controller import event_bp
from controllers.session_controller import session_bp
from controllers.webhook_controller import webhook_bp
from controllers.subscription_controller import subscription_bp


from utils.logger import get_logger

logger = get_logger("App")


def create_app(config_class=Config) -> Flask:
    """Application factory pattern."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(event_bp)
    app.register_blueprint(session_bp)
    app.register_blueprint(webhook_bp)
    app.register_blueprint(subscription_bp)
    
    # COMM PLATFORM MUST BE INSIDE FACTORY
    from comm_platform import init_comm_platform
    init_comm_platform(app)
    
    @app.get("/health")
    def health():
        return jsonify({"status": "ok", "service": "SBEAE"}), 200

    @app.errorhandler(404)
    def not_found(_e):
        return jsonify({"error": "not_found"}), 404

    @app.errorhandler(405)
    def method_not_allowed(_e):
        return jsonify({"error": "method_not_allowed"}), 405

    @app.errorhandler(500)
    def internal_error(_e):
        logger.exception("Unhandled exception")
        return jsonify({"error": "internal_server_error"}), 500

    with app.app_context():
        db.create_all()

    logger.info("SBEAE Flask app created, routes registered")
    return app
    



if __name__ == "__main__":
    app = create_app()
    app.run(host="127.0.0.1", port=5050, debug=False)
