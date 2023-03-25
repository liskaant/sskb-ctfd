import os
from flask import Blueprint
from flask_restx import Api
from CTFd.plugins import register_plugin_assets_directory
from CTFd.utils.plugins import override_template

from .views import scoreboard as scoreboard_view_blueprint, view_scoreboard
from .api import scoreboard as scoreboard_api_namespace

def load(app):
	# get plugin location
	dir_path = os.path.dirname(os.path.realpath(__file__))
	dir_name = os.path.basename(dir_path)

	register_plugin_assets_directory(app, base_path=f"/plugins/{dir_name}/assets/", endpoint="sskb_category_scoreboard_assets")

	# Team settings page override
	override_template('scoreboard.html', open(os.path.join(dir_path, 'templates/scoreboard.html')).read())

	# View functions
	app.view_functions['scoreboard.listing'] = view_scoreboard
	app.register_blueprint(scoreboard_view_blueprint)

	# Api anedpoint
	api = Blueprint("scoreboard_api", __name__, url_prefix="/api/v1")
	scoreboard_api = Api(api, version="v1", doc=app.config.get("SWAGGER_UI"))
	scoreboard_api.add_namespace(scoreboard_api_namespace, "/scoreboard")
	app.register_blueprint(api)
