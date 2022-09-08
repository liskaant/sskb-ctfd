import os
from flask import Blueprint
from flask_restx import Api
from CTFd.plugins import register_plugin_assets_directory, register_admin_plugin_script
from CTFd.utils.plugins import override_template

from .views import view_split_scoreboard

def load(app):
	# get plugin location
	dir_path = os.path.dirname(os.path.realpath(__file__))
	dir_name = os.path.basename(dir_path)

	register_plugin_assets_directory(app, base_path="/plugins/"+dir_name+"/assets/", endpoint="split_scoreboard_assets")

	# Team settings page override
	override_template('scoreboard.html', open(os.path.join(dir_path, 'assets/scoreboard.html')).read())

	# Team Modals
	app.view_functions['scoreboard.listing'] = view_split_scoreboard

	# Blueprint used to access the static_folder directory.
	blueprint = Blueprint(
		"split_scores", __name__, template_folder="templates", static_folder="assets"
	)
