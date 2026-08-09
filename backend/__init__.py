from pathlib import Path

from flask import Flask

from config import Config


def create_app():
    """
    Application Factory
    """

    app = Flask(
        __name__,
        template_folder="../frontend/templates",
        static_folder="../frontend/static",
    )
    app.config.from_object(Config)

    from backend.routes.home import home_bp
    from backend.routes.students import students_bp
    from backend.routes.cohort import cohort_bp

    app.register_blueprint(home_bp)
    app.register_blueprint(students_bp)
    app.register_blueprint(cohort_bp)

    # Load the bundled simulated dataset into the in-memory store at startup
    # (FR1) so the app is immediately usable without requiring an upload first.
    from backend.data.store import data_store

    sample_path = Path(__file__).parent / "data" / "sample_data.csv"
    data_store.load_from_csv(str(sample_path))

    return app
