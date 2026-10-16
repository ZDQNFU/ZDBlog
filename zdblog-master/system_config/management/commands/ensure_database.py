from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create the configured PostgreSQL database when it does not exist."

    def handle(self, *args, **options):
        database = settings.DATABASES["default"]
        if database["ENGINE"] != "django.db.backends.postgresql":
            raise CommandError(
                "ensure_database currently supports PostgreSQL only; "
                f"configured engine is {database['ENGINE']!r}."
            )

        database_name = database["NAME"]
        if not database_name:
            raise CommandError("DB_NAME must be set before creating the database.")

        try:
            import psycopg
            from psycopg import sql
        except ImportError as exc:
            raise CommandError("Install psycopg to create the PostgreSQL database.") from exc

        options = database.get("OPTIONS", {})
        connection_options = {
            "dbname": options.get("maintenance_db", "postgres"),
            "host": database.get("HOST") or None,
            "port": database.get("PORT") or None,
            "user": database.get("USER") or None,
            "password": database.get("PASSWORD") or None,
            "connect_timeout": options.get("connect_timeout", 10),
        }
        connection_options.update(
            {
                key: value
                for key, value in options.items()
                if key not in {"maintenance_db", "connect_timeout"}
            }
        )

        try:
            with psycopg.connect(**connection_options, autocommit=True) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT pg_advisory_lock(hashtext(%s)::bigint)",
                        (database_name,),
                    )
                    cursor.execute(
                        "SELECT 1 FROM pg_database WHERE datname = %s",
                        (database_name,),
                    )
                    if cursor.fetchone():
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"Database {database_name!r} already exists."
                            )
                        )
                        return

                    cursor.execute(
                        sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name))
                    )
                    self.stdout.write(
                        self.style.SUCCESS(f"Created database {database_name!r}.")
                    )
        except psycopg.Error as exc:
            raise CommandError(
                f"Could not ensure database {database_name!r} exists. "
                "The configured PostgreSQL user must be allowed to create databases."
            ) from exc
