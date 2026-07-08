from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import Settings
from app.database import init_db, make_engine, make_session_factory
from app.services.seed import seed_risk_rules


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    engine = make_engine(settings)
    init_db(engine, settings)
    session_factory = make_session_factory(engine)
    with session_factory() as session:
        seed_risk_rules(session)

    app = FastAPI(title=settings.app_name)
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)
    return app


app = create_app()
