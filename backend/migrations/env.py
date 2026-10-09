from alembic import context

from app import models  # noqa: F401
from app.chaos import models as chaos_models  # noqa: F401
from app.config import Settings
from app.db import Base, database
from app.investigation import models as investigation_models  # noqa: F401
from app.monitoring import models as monitoring_models  # noqa: F401
from app.repairs import models as repair_models  # noqa: F401

config = Settings()
if context.is_offline_mode():
    context.configure(url=config.database_url, target_metadata=Base.metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    engine, _ = database(config.database_url)
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=Base.metadata,
            render_as_batch=engine.dialect.name == "sqlite",
        )
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()
