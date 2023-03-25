from flask import Blueprint, render_template

from CTFd.utils import config
from CTFd.utils.config.visibility import scores_visible
from CTFd.utils.decorators.visibility import check_score_visibility, check_account_visibility
from CTFd.utils.helpers import get_infos
from CTFd.utils.scores import get_standings
from CTFd.utils.user import is_admin

from .util import category_tabs, filter_standings

scoreboard = Blueprint("category_scoreboard", __name__)

@scoreboard.route("/scoreboard")
@scoreboard.route("/scoreboard/<category>")
@check_account_visibility
@check_score_visibility
def view_scoreboard(category = None):
	infos = get_infos()

	if config.is_scoreboard_frozen():
		infos.append("Scoreboard has been frozen")

	if is_admin() is True and scores_visible() is False:
		infos.append("Scores are not currently visible to users")

	standings = get_standings() if category is None else filter_standings(get_standings(), category)
	return render_template("scoreboard.html", standings=standings, infos=infos, tabs=category_tabs(category), cache_id=str(category))
