"""HTTP layer: one blueprint per functional area."""
from routes.alerts import bp as alerts_bp
from routes.analysis import bp as analysis_bp
from routes.auth import bp as auth_bp
from routes.dashboard import bp as dashboard_bp
from routes.data_management import bp as data_bp
from routes.insights import bp as insights_bp
from routes.rules import bp as rules_bp
from routes.simulator import bp as simulator_bp
from routes.transactions import bp as transactions_bp

ALL_BLUEPRINTS = (
    auth_bp,
    dashboard_bp,
    transactions_bp,
    alerts_bp,
    rules_bp,
    analysis_bp,
    insights_bp,
    data_bp,
    simulator_bp,
)


def register_blueprints(app):
    for blueprint in ALL_BLUEPRINTS:
        app.register_blueprint(blueprint)
