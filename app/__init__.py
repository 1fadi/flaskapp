from flask import Flask, jsonify, request
from flask_bootstrap import Bootstrap
from flask_mail import Mail
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from config import config
from flask_login import LoginManager
from flask_pagedown import PageDown
from flask import url_for, redirect, flash, current_app
from flask_login.utils import login_url as make_login_url, make_next_param

bootstrap = Bootstrap()
mail = Mail()
moment = Moment()
db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'


@login_manager.unauthorized_handler
def unauthorized():
    if request.blueprint in login_manager.blueprint_login_views:
        login_view = login_manager.blueprint_login_views[request.blueprint]
    else:
        login_view = login_manager.login_view

    if not login_view:
        abort(401)

    if login_manager.login_message:
        if login_manager.localize_callback is not None:
            flash(
                login_manager.localize_callback(login_manager.login_message),
                category=login_manager.login_message_category,
            )
        else:
            flash(login_manager.login_message, category=login_manager.login_message_category)

    config = current_app.config
    if config.get("USE_SESSION_FOR_NEXT"):
        login_url = LoginManager.expand_login_view(login_view)
        session["_id"] = login_manager._session_identifier_generator()
        session["next"] = make_next_param(login_url, request.url)
        redirect_url = make_login_url(login_view)
    else:
        redirect_url = make_login_url(login_view, next_url=request.url)

    if request.is_json:
        return jsonify({'redirect': redirect_url})
    else:
        return redirect(redirect_url)


pagedown = PageDown()


def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    if app.config['SSL_REDIRECT']:
        from flask_sslify import SSLify
        sslify = SSLify(app)
    bootstrap.init_app(app)
    mail.init_app(app)
    moment.init_app(app)
    db.init_app(app)
    login_manager.init_app(app)
    pagedown.init_app(app)

    # attach routes
    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')
    
    from .api import api as api_blueprint
    app.register_blueprint(api_blueprint, url_prefix='/api/v1') 
    
    from .moderate import moderate as moderate_blueprint
    app.register_blueprint(moderate_blueprint, url_prefix='/moderate')

    return app
