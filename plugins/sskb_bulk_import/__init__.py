import os, traceback, json
from flask_restx import Namespace, Api, Resource
from flask import Blueprint, request

from CTFd.utils.decorators import admins_only
from CTFd.models import db, Users, Fields
from CTFd.schemas.users import UserSchema
from CTFd.cache import clear_standings
from CTFd.utils.plugins import override_template

from . import views

api_namespace = Namespace('bulk_import')

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
			return {'success': False, 'message': 'Invalid input format, expected array of users'}, 400

		row_hint = "Hint: Row #0 is the header, first record is Row #1"

		created_users = 0
		for i, row in enumerate(req['users']):
			try:
				if 'email' in row and row['email']:
					Users.query.filter_by(email=row['email']).delete()
				else:
					return { "success": False, "message": f"Error processing Row #{i + 1}: Email is required\n{row_hint}\nRow dump: {json.dumps(row, indent=4)}" }, 400

				fields = []

				if 'fields' in row and type(row['fields']) == dict:
					for k, v in row['fields'].items():
						field = Fields.query.filter_by(name=k).first()
						if field:
							fields.append({
								'field_id': field.id,
								'value': v,
							})

				schema = UserSchema()
				user = schema.load({
					'name': row['name'] if 'name' in row else None,
					'email': row['email'] if 'email' in row else None,
					'password': row['password'] if 'password' in row else None,
					'fields': fields,
				})

				if user.errors:
					db.session.rollback()
					return {'success': False, 'message': f"Error processing Row #{i + 1}\n{row_hint}\nError: {json.dumps(user.errors, indent=4)}\nRow dump: {json.dumps(row, indent=4)}" }, 400

				db.session.add(user.data)
				created_users += 1
			except:
				db.session.rollback()
				return { 'success': False, 'message': f"Error processing Row #{i + 1}\nHint: Row #0 is the header, first record is Row #1\nError: " + traceback.format_exc() + f"\nRow dump: {json.dumps(row, indent=4)}" }, 400

		try:
			db.session.commit()
			clear_standings()
		except:
			db.session.rollback()
			return { 'success': False, 'message': f"Error commiting changes, please try again\nError: " + traceback.format_exc() }, 400

		return { 'success': True, 'message': f'Ok: Created or updated {created_users} users' }

def load(app):
	dir_path = os.path.dirname(os.path.realpath(__file__))
	override_template('sskb_bulk_import_admin.html', open(os.path.join(dir_path, 'templates/sskb_bulk_import.html')).read())
	override_template('admin/scoreboard.html', open(os.path.join(dir_path, 'templates/admin_scoreboard.html')).read())
	override_template('admin/scoreboard/standings.html', open(os.path.join(dir_path, 'templates/admin_scoreboard_standings.html')).read())

	api = Blueprint('bulk_import_api', __name__, url_prefix='/api/v1')
	BulkImportApi = Api(api, version='v1', doc=app.config.get('SWAGGER_UI'))
	BulkImportApi.add_namespace(api_namespace, '/bulk_import')
	app.register_blueprint(api)
