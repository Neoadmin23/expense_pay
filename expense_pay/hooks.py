from . import __version__ as app_version

app_name = "expense_pay"
app_title = "Expense Pay"
app_publisher = "Kishan Panchal"
app_description = "multiple entries in payment entry"
app_email = "k.d.panchalofc@gmail.com"
app_license = "MIT"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/expense_pay/css/expense_pay.css"
# app_include_js = "/assets/expense_pay/js/expense_pay.js"

# include js, css files in header of web template
# web_include_css = "/assets/expense_pay/css/expense_pay.css"
# web_include_js = "/assets/expense_pay/js/expense_pay.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "expense_pay/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"Expenses Entry" : "public/js/expenses_entry.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
#	"methods": "expense_pay.utils.jinja_methods",
#	"filters": "expense_pay.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "expense_pay.install.before_install"
# after_install = "expense_pay.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "expense_pay.uninstall.before_uninstall"
# after_uninstall = "expense_pay.uninstall.after_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "expense_pay.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
#	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
#	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
#	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
#	"*": {
#		"on_update": "method",
#		"on_cancel": "method",
#		"on_trash": "method"
#	}
# }

doc_events = {
    "Expenses Entry": {
        "on_submit": "expense_pay.create_gl_entry.create_gl_entries",
        "on_cancel": "expense_pay.create_gl_entry.cancel_gl_entries",
        "on_trash": "expense_pay.create_gl_entry.delete_gl_entries"
    }
    # "Sales Invoice": {
    #     "before_insert": "expense_pay.utils.api.sales_invoice_set_draft_series",
    #     "before_submit": "expense_pay.utils.api.sales_invoice_set_final_series",
    # }
}
# Scheduled Tasks
# ---------------

# scheduler_events = {
#	"all": [
#		"expense_pay.tasks.all"
#	],
#	"daily": [
#		"expense_pay.tasks.daily"
#	],
#	"hourly": [
#		"expense_pay.tasks.hourly"
#	],
#	"weekly": [
#		"expense_pay.tasks.weekly"
#	],
#	"monthly": [
#		"expense_pay.tasks.monthly"
#	],
# }

# Testing
# -------

# before_tests = "expense_pay.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
#	"frappe.desk.doctype.event.event.get_events": "expense_pay.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
#	"Task": "expense_pay.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["expense_pay.utils.before_request"]
# after_request = ["expense_pay.utils.after_request"]

# Job Events
# ----------
# before_job = ["expense_pay.utils.before_job"]
# after_job = ["expense_pay.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
#	{
#		"doctype": "{doctype_1}",
#		"filter_by": "{filter_by}",
#		"redact_fields": ["{field_1}", "{field_2}"],
#		"partial": 1,
#	},
#	{
#		"doctype": "{doctype_2}",
#		"filter_by": "{filter_by}",
#		"partial": 1,
#	},
#	{
#		"doctype": "{doctype_3}",
#		"strict": False,
#	},
#	{
#		"doctype": "{doctype_4}"
#	}
# ]
after_migrate = ["expense_pay.utils.sar_symbol.set_new_saudi_riyal_symbol"]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
#	"expense_pay.auth.validate"
# ]
