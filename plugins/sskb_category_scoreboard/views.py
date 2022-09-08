from flask import Blueprint, render_template
import json

from CTFd.utils import config
from CTFd.utils.config.visibility import scores_visible
from CTFd.utils.decorators.visibility import check_score_visibility
from CTFd.utils.helpers import get_infos
from CTFd.utils.scores import get_standings
from CTFd.utils.user import is_admin

from CTFd.cache import cache
from sqlalchemy import or_, and_
from CTFd.utils.modes import get_model
from CTFd.models import Users, UserFieldEntries, Fields, Solves, Awards
from CTFd.utils import get_config
from CTFd.utils.dates import isoformat, unix_time_to_utc
from collections import defaultdict
from CTFd.utils.user import get_current_user

scoreboard = Blueprint("scoreboard", __name__)

def filter_standings(standings, filter):
	new_standings = []

	for standing in standings:
		category = (
			UserFieldEntries.query.join(Fields, and_(
				Fields.id == UserFieldEntries.field_id,
				Fields.name == 'Category'
			))
			.filter(UserFieldEntries.user_id == standing.account_id)
			.first()
		).value

		if category == filter:
			new_standings.append(standing)

	return new_standings

def graph_data(standings):
	response = {}

	team_ids = [team.account_id for team in standings]

	solves = Solves.query.filter(Solves.account_id.in_(team_ids))
	awards = Awards.query.filter(Awards.account_id.in_(team_ids))

	freeze = get_config("freeze")

	if freeze:
		solves = solves.filter(Solves.date < unix_time_to_utc(freeze))
		awards = awards.filter(Awards.date < unix_time_to_utc(freeze))

	solves = solves.all()
	awards = awards.all()

	# Build a mapping of accounts to their solves and awards
	solves_mapper = defaultdict(list)
	for solve in solves:
		solves_mapper[solve.account_id].append(
			{
				"challenge_id": solve.challenge_id,
				"account_id": solve.account_id,
				"team_id": solve.team_id,
				"user_id": solve.user_id,
				"value": solve.challenge.value,
				"date": isoformat(solve.date),
			}
		)

	for award in awards:
		solves_mapper[award.account_id].append(
			{
				"challenge_id": None,
				"account_id": award.account_id,
				"team_id": award.team_id,
				"user_id": award.user_id,
				"value": award.value,
				"date": isoformat(award.date),
			}
		)

	# Sort all solves by date
	for team_id in solves_mapper:
		solves_mapper[team_id] = sorted(
			solves_mapper[team_id], key=lambda k: k["date"]
		)

	for i, _team in enumerate(team_ids):
		response[i + 1] = {
			"id": standings[i].account_id,
			"name": standings[i].name,
			"solves": solves_mapper.get(standings[i].account_id, []),
		}

	return response

@scoreboard.route("/scoreboard")
@check_score_visibility
def view_split_scoreboard():
	infos = get_infos()

	if config.is_scoreboard_frozen():
		infos.append("Scoreboard has been frozen")

	if is_admin() is True and scores_visible() is False:
		infos.append("Scores are not currently visible to users")

	standings = get_standings()

	categories = []
	if get_model() == Users:
		current_user = get_current_user();
		current_category = None
		if current_user != None:
			for field in current_user.fields:
				if field.name == 'Category':
					current_category = field.value
					break

		categories = list(set([v.value for v in (
			UserFieldEntries.query
			.join(Fields, and_(
				Fields.id == UserFieldEntries.field_id,
				Fields.name == 'Category'
			))
			.all()
		)]))

		tabs = []
		for v in categories:
			filtered_standings = filter_standings(standings, v)
			tabs.append({
				'category': v,
				'standings': filtered_standings,
				'graph': json.dumps(graph_data(filtered_standings)),
				'active': current_category == v,
			})

		tabs.append({
			'category': 'All',
			'standings': standings,
			'graph': json.dumps(graph_data(standings)),
			'active': current_category == None,
		})

		return render_template("scoreboard.html", tabs=tabs, infos=infos)
	else:
		return render_template("scoreboard.html", tabs=[{
			'category': '',
			'standings': standings,
			'graph': json.dumps(graph_data(standings)),
			'active': True,
		}], infos=infos)
