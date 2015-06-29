from datetime import timedelta, datetime

from flask import Flask, request, redirect
from flask.ext.bootstrap import Bootstrap
from flask_wtf.csrf import CsrfProtect
from dmutils import apiclient, init_app, flask_featureflags, formats
from dmutils.content_loader import ContentLoader

from config import configs


bootstrap = Bootstrap()
data_api_client = apiclient.DataAPIClient()
csrf = CsrfProtect()
feature_flags = flask_featureflags.FeatureFlag()

service_content = ContentLoader(
    "app/section_order.yml", "app/content/g6/"
)


def create_app(config_name):

    application = Flask(__name__,
                        static_folder='static/',
                        static_url_path=configs[config_name].STATIC_URL_PATH)

    init_app(
        application,
        configs[config_name],
        bootstrap=bootstrap,
        data_api_client=data_api_client,
        feature_flags=feature_flags
    )
    # Should be incorporated into digitalmarketplace-utils as well
    csrf.init_app(application)

    from .main import main as main_blueprint
    from .status import status as status_blueprint

    if application.config['AUTHENTICATION']:
        from .main.helpers.auth import requires_auth
        application.permanent_session_lifetime = timedelta(minutes=60)
        main_blueprint.before_request(requires_auth)

    application.register_blueprint(status_blueprint, url_prefix='/admin')
    application.register_blueprint(main_blueprint, url_prefix='/admin')
    main_blueprint.config = application.config.copy()

    @application.before_request
    def remove_trailing_slash():
        if request.path != '/' and request.path.endswith('/'):
            return redirect(request.path[:-1], code=301)

    @application.template_filter('timeformat')
    def timeformat(value):
        return datetime.strptime(
            value, formats.DATETIME_FORMAT).strftime('%H:%M:%S')

    @application.template_filter('dateformat')
    def dateformat(value):
        return datetime.strptime(
            value, formats.DATETIME_FORMAT).strftime('%d/%m/%Y')

    @application.template_filter('displaydateformat')
    def display_date_format(value):
        return value.strftime('%d/%m/%Y')

    return application
