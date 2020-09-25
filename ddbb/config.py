import alembic.config

import settings


def get_db_url():
    return "postgresql://{}:{}@{}:{}/{}".format(
        settings.DB_USERNAME,
        settings.DB_PASSWORD,
        settings.DB_HOST,
        settings.DB_PORT,
        settings.DB_DATABASE,
    )


def run_db_migrations():
    alembic_args = [
        '--raiseerr',
        'upgrade', 'head',
    ]
    alembic.config.main(argv=alembic_args)
