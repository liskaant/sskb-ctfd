from sqlalchemy import and_

from CTFd.models import UserFieldEntries, Fields
from CTFd.utils.user import get_current_user
from CTFd.utils.modes import get_model
from CTFd.models import Users

def filter_standings(standings, category: str):
	new_standings = []

	for standing in standings:
		standing_category = (
			UserFieldEntries.query.join(Fields, and_(
				Fields.id == UserFieldEntries.field_id,
				Fields.name == 'Category'
			))
			.filter(UserFieldEntries.user_id == standing.account_id)
			.first()
		).value

		if standing_category == category:
			new_standings.append(standing)

	return new_standings

def current_user_category():
	current_user = get_current_user();
	current_category = None
	if current_user != None:
		for field in current_user.fields:
			if field.name == 'Category':
				current_category = field.value
				break
	return current_category

def fetch_categories():
	if get_model() != Users:
		return []

	return list(set([v.value for v in (
		UserFieldEntries.query
		.join(Fields, and_(
			Fields.id == UserFieldEntries.field_id,
			Fields.name == 'Category'
		))
		.all()
	)]))

def category_tabs(current):
	tabs = [ {
		"category": "All",
		"url": "",
		"active": current is None,
	} ]

	for category in fetch_categories():
		tabs.append({
			"category": category,
			"url": f"/{category}",
			"active": current == category,
		})

	return tabs
