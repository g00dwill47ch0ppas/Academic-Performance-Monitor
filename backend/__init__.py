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
    from backend.routes.modules import module_bp

    app.register_blueprint(home_bp)
    app.register_blueprint(students_bp)
    app.register_blueprint(cohort_bp)
    app.register_blueprint(module_bp)

    # Seed the bundled simulated dataset as a demo module at startup (FR1) so
    # the app is immediately usable without requiring an upload first.
    from backend.data.loader import load_dataframe
    from backend.data.store import data_store

    if not data_store.modules:
        sample_path = Path(__file__).parent / "data" / "sample_data.csv"
        sample_df = load_dataframe(str(sample_path), filename="sample_data.csv")
        sample_module = data_store.build_module_from_df(
            "CS101", "Sample module (simulated data)", sample_df
        )
        data_store.modules[sample_module.code] = sample_module
        data_store.active_module_code = sample_module.code

    @app.context_processor
    def inject_module_nav():
        return {
            "nav_active_module": data_store.active_module,
            "nav_module_items": [
                {"code": m.code, "name": m.name, "label": m.label}
                for m in data_store.module_list()
            ],
        }

    return app
