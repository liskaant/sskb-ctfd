import os
from flask_restx import Namespace, Api, Resource
from flask import Blueprint, request

from CTFd.utils.decorators import admins_only
from CTFd.models import db, Users, Fields
from CTFd.schemas.users import UserSchema
from CTFd.cache import clear_standings
from CTFd.api.v1.users import UserPublic
from CTFd.utils.plugins import override_template

from . import views

api_namespace = Namespace('bulk import')

@api_namespace.route('')
class BulkImport(Resource):
	@admins_only
	def get(self):
		return {
			'success': True,
			'users': [{
				'name': user.name,
				'email': user.email,
				'fields': {v.name:v.value for v in user.fields},
			} for user in Users.query.filter_by(type='user').all()],
		}

	@admins_only
	def post(self):
		req = request.get_json()

		if 'users' not in req or type(req['users']) != list:
			return {'success': False, 'errors': 'Invalid input format'}, 400

		created_users = []
		for user in req['users']:
			if 'email' in user and user['email']:
				Users.query.filter_by(email=user['email']).delete()

			fields = []

			if 'fields' in user and type(user['fields']) == dict:
				for k, v in user['fields'].items():
					field = Fields.query.filter_by(name=k).first()
					if field:
						fields.append({
							'field_id': field.id,
							'value': v,
						})

			schema = UserSchema()
			user = schema.load({
				'name': user['name'] if 'name' in user else None,
				'email': user['email'] if 'email' in user else None,
				'password': user['password'] if 'password' in user else None,
				'fields': fields,
			})

			if user.errors:
				return {'success': False, 'errors': user.errors}, 400

			db.session.add(user.data)
			created_users.append(schema.dump(user.data))

		db.session.commit()
		clear_standings()

		return { 'success': True }

def load(app):
	dir_path = os.path.dirname(os.path.realpath(__file__))
	override_template('sskb_bulk_import_admin.html', open(os.path.join(dir_path, 'sskb_bulk_import_admin.html')).read())

	api = Blueprint('bulk_import_api', __name__, url_prefix='/api/v1')
	BulkImportApi = Api(api, version='v1', doc=app.config.get('SWAGGER_UI'))
	BulkImportApi.add_namespace(api_namespace, '/bulk_import')
	app.register_blueprint(api)
