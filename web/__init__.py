import os
import json
from flask import Flask, session
from flask_cors import CORS
from markupsafe import Markup

from web.config import Config
from web.extensions import db

def create_app(config_class=Config):
    app = Flask(__name__, 
                template_folder='../templates', 
                static_folder='../static')
    app.config.from_object(config_class)
    
    CORS(app, supports_credentials=True)
    
    # Initialize components that need the db
    from billing import init_billing
    init_billing(db)
    
    from admin import init_admin
    init_admin(db)
    
    # Register Context Processors
    @app.context_processor
    def inject_config():
        return dict(config=os.environ)

    @app.context_processor
    def inject_user():
        if session.get("authenticated") and session.get("user_id"):
            return dict(
                request={
                    "user": {
                        "uid": session.get("user_id"),
                        "email": session.get("email", ""),
                        "user_id": session.get("user_id"),
                    }
                }
            )
        return dict(request={"user": None})

    # Register Template Filters
    @app.template_filter("tojsonfilter")
    def to_json_filter(obj):
        return Markup(json.dumps(obj))

    # Import and register blueprints
    from web.blueprints.auth import auth_bp
    app.register_blueprint(auth_bp)
    
    from web.blueprints.views import views_bp
    app.register_blueprint(views_bp)
    
    from web.blueprints.api import api_bp
    app.register_blueprint(api_bp)
    
    from web.blueprints.billing import billing_bp
    app.register_blueprint(billing_bp)
    
    from web.blueprints.legacy_chat import legacy_chat_bp
    app.register_blueprint(legacy_chat_bp)
    
    return app
