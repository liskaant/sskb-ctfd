from flask import render_template, current_app as app

from CTFd.utils.decorators import admins_only

@app.route('/admin/bulk_import', methods=['GET'])
@admins_only
def view_admin_bulk_import():
	return render_template('sskb_bulk_import_admin.html')
