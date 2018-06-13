from datetime import timedelta

from dmcontent.errors import ContentNotFoundError
from flask import Flask, request, redirect, session
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

import dmapiclient
from dmutils import init_app, flask_featureflags, formats
from dmutils.user import User
from dmcontent.content_loader import ContentLoader

from config import configs


csrf = CSRFProtect()
data_api_client = dmapiclient.DataAPIClient()
feature_flags = flask_featureflags.FeatureFlag()
login_manager = LoginManager()

content_loader = ContentLoader('app/content')


from app.main.helpers.service import parse_document_upload_time


def create_app(config_name):

    application = Flask(__name__,
                        static_folder='static/',
                        static_url_path=configs[config_name].STATIC_URL_PATH)

    init_app(
        application,
        configs[config_name],
        data_api_client=data_api_client,
        feature_flags=feature_flags,
        login_manager=login_manager
    )

    for framework_data in data_api_client.find_frameworks().get('frameworks'):
        try:
            content_loader.load_manifest(framework_data['slug'], 'services', 'edit_service_as_admin')
        except ContentNotFoundError:
            # Not all frameworks have this, so no need to panic (e.g. G-Cloud 4, G-Cloud 5)
            application.logger.info(
                "Could not load edit_service_as_admin manifest for {}".format(framework_data['slug'])
            )
        try:
            content_loader.load_manifest(framework_data['slug'], 'declaration', 'declaration')
        except ContentNotFoundError:
            # Not all frameworks have this, so no need to panic (e.g. G-Cloud 4, G-Cloud 5, G-Cloud-6)
            application.logger.info(
                "Could not load declaration manifest for {}".format(framework_data['slug'])
            )

    # Should be incorporated into digitalmarketplace-utils as well
    csrf.init_app(application)

    from .main import main as main_blueprint
    from .main import public as public_blueprint
    from .status import status as status_blueprint
    from dmutils.external import external as external_blueprint

    application.register_blueprint(status_blueprint, url_prefix='/admin')
    application.register_blueprint(main_blueprint, url_prefix='/admin')
    application.register_blueprint(public_blueprint, url_prefix='/admin')

    # Must be registered last so that any routes declared in the app are registered first (i.e. take precedence over
    # the external NotImplemented routes in the dm-utils external blueprint).
    application.register_blueprint(external_blueprint)

    login_manager.login_view = '/user/login'
    main_blueprint.config = application.config.copy()

    @application.before_request
    def remove_trailing_slash():
        if request.path != '/' and request.path.endswith('/'):
            return redirect(request.path[:-1], code=301)

    @application.before_request
    def refresh_session():
        session.permanent = True
        session.modified = True

    application.add_template_filter(parse_document_upload_time)

    return application


@login_manager.user_loader
def load_user(user_id):
    return User.load_user(data_api_client, user_id)
