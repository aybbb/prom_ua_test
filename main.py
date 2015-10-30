from flask import Flask
from promua_test_app.views import *
from flask_wtf import CsrfProtect

import __config as config

app = Flask(__name__)
# configure app
app.config.from_object(config)
# setup extensions
csrf_protect = CsrfProtect()
# init extensions
csrf_protect.init_app(app)
login_manager.init_app(app)
# setup static and templates
app.template_folder = "promua_test_app/templates"
app.static_folder = "promua_test_app/static"
# register handlers
app.before_request(before_request)
app.teardown_appcontext(teardown_app_context)
# register views
IndexView.register(app)
UserView.register(app)

if __name__ == '__main__':
    app.run(host="176.110.58.145", port=7114)
