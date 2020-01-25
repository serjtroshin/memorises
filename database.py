import logging
import os
from argparse import ArgumentParser

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from yoyo import get_backend
from yoyo import read_migrations

from config import Config
from settings import TIME_BEFORE_FIRST_SHOW

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


class DatabaseConfig:
    url = os.environ.get("DATABASE_URL")

    if url is None:
        _config = Config.get_config()["database"]

        dbname = _config["dbname"]
        initial_dbname = _config["initial_dbname"]
        user = _config["user"]
        password = _config["password"]
        host = _config["host"]
        port = _config["port"]
        timeout = _config["timeout"]


class UsersDB:
    db_name = "users"
    chat_id = "chat_id"
    card_id = "card_id"


class CardsDB:
    db_name = "cards"
    card_id = "card_id"
    phrase_id = "phrase_id"
    time_added = "time_added"
    time_next_delta = "time_next_delta"


class PhrasesDB:
    db_name = "phrases"
    phrase_id = "phrase_id"
    phrase = "phrase"
    translation = "translation"
    definition = "definition"
    synonyms = "synonyms"
    examples = "examples"


def get_connection():
    if DatabaseConfig.url is not None:
        conn = psycopg2.connect(DatabaseConfig.url, sslmode="require")
    else:
        conn = psycopg2.connect(
            dbname=DatabaseConfig.dbname,
            user=DatabaseConfig.user,
            password=DatabaseConfig.password,
            host=DatabaseConfig.host,
            port=DatabaseConfig.port,
        )
    return conn


def create_database(recreate=False):
    if recreate:
        drop_database()

    exists = False

    if DatabaseConfig.url is None:
        conn = psycopg2.connect(
            dbname=DatabaseConfig.initial_dbname,
            user=DatabaseConfig.user,
            password=DatabaseConfig.password,
            host=DatabaseConfig.host,
            port=DatabaseConfig.port,
        )

        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "select 1 from pg_catalog.pg_database "
                    f"where datname = '{DatabaseConfig.dbname}'"
                )
                exists = cur.fetchone()
                if not exists:
                    logger.info(f"Creating database {DatabaseConfig.dbname}")
                    cur.execute(f"create database {DatabaseConfig.dbname}")
        conn.close()
    else:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select exists(
                      select * from information_schema.tables where table_name=%s
                    )
                """,
                    ("_created",),
                )
                exists = cur.fetchone()[0]

    if not exists:
        with get_connection() as conn:
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

            with conn.cursor() as cur:
                cur.execute(
                    """
                    create table _created()
                """
                )

                # Creating tables
                cur.execute(
                    f"""
                    create table if not exists {UsersDB.db_name}(
                        {UsersDB.chat_id} varchar(100),
                        {UsersDB.card_id} integer primary key
                    )
                """
                )
                cur.execute(
                    f"""
                    create table if not exists {CardsDB.db_name}(
                        {CardsDB.card_id} serial primary key,
                        {CardsDB.phrase_id} integer not null,
                        {CardsDB.time_added} timestamp default current_timestamp,
                        {CardsDB.time_next_delta} integer not null default %s
                    )
                """,
                    (TIME_BEFORE_FIRST_SHOW,),
                )
                cur.execute(
                    f"""
                    create table if not exists {PhrasesDB.db_name}(
                        {PhrasesDB.phrase_id} serial primary key,
                        {PhrasesDB.phrase} varchar(4096),
                        {PhrasesDB.translation} text not null,
                        {PhrasesDB.definition} text,
                        {PhrasesDB.synonyms} text,
                        {PhrasesDB.examples} text
                    )
                """
                )

                # Constraints
                cur.execute(
                    f"""
                    alter table {UsersDB.db_name} drop constraint
                    if exists users_cards_fkey
                """
                )
                cur.execute(
                    f"""
                    alter table {UsersDB.db_name} add constraint
                    users_cards_fkey foreign key ({UsersDB.card_id})
                    references {CardsDB.db_name}({CardsDB.card_id})
                """
                )
                cur.execute(
                    f"""
                    alter table {CardsDB.db_name} drop constraint
                    if exists cards_phrases_fkey
                """
                )
                cur.execute(
                    f"""
                    alter table {CardsDB.db_name} add constraint
                    cards_phrases_fkey foreign key ({CardsDB.phrase_id})
                    references {PhrasesDB.db_name}({PhrasesDB.phrase_id})
                """
                )

                # Indexes
                cur.execute(
                    f"""
                    create index if not exists user_chat_id_idx on
                    {UsersDB.db_name}({UsersDB.chat_id})
                """
                )


def drop_database():
    conn = psycopg2.connect(
        dbname=DatabaseConfig.initial_dbname,
        user=DatabaseConfig.user,
        password=DatabaseConfig.password,
        host=DatabaseConfig.host,
        port=DatabaseConfig.port,
    )

    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

    with conn:
        with conn.cursor() as cur:
            logger.info(f"Dropping database {DatabaseConfig.dbname}")
            cur.execute(f"drop database if exists {DatabaseConfig.dbname}")
    conn.commit()
    conn.close()


def apply_migrations():
    if DatabaseConfig.url is None:
        backend = get_backend(
            f"postgres://{DatabaseConfig.user}:{DatabaseConfig.password}"
            f"@{DatabaseConfig.host}:{DatabaseConfig.port}/{DatabaseConfig.dbname}"
        )
    else:
        backend = get_backend(DatabaseConfig.url)
    migrations = read_migrations("migrations/")
    with backend.lock():
        backend.apply_migrations(backend.to_apply(migrations))


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--recreate", action="store_true")

    args = parser.parse_args()

    create_database(recreate=args.recreate)
    apply_migrations()
