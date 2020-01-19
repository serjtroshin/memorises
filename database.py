import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import json
import logging
from Config import Config
import os
from yoyo import read_migrations
from yoyo import get_backend
from argparse import ArgumentParser

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)


class Config:
    database_url = os.environ.get("DATABASE_URL")
    if database_url is None:
        _config = Config.get_config()["database"]

        dbname = _config["dbname"]
        initial_dbname = _config["initial_dbname"]
        user = _config["user"]
        password = _config["password"]
        host = _config["host"]
        port = _config["port"]
        timeout = _config["timeout"]


def get_connection():
    if Config.database_url is not None:
        conn = psycopg2.connect(Config.database_url, sslmode='require')
    else:
        conn = psycopg2.connect(
            dbname=Config.dbname,
            user=Config.user,
            password=Config.password,
            host=Config.host,
            port=Config.port
        )
    return conn


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


def create_database(recreate=False):
    if recreate:
        drop_database()

    exists = False

    if Config.database_url is None:
        conn = psycopg2.connect(
            dbname=Config.initial_dbname,
            user=Config.user,
            password=Config.password,
            host=Config.host,
            port=Config.port,
        )

        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "select 1 from pg_catalog.pg_database "
                    f"where datname = '{Config.dbname}'"
                )
                exists = cur.fetchone()
                if not exists:
                    logger.info(f"Creating database {Config.dbname}")
                    cur.execute(f"create database {Config.dbname}")
        conn.close()

    if not exists:
        with get_connection() as conn:
            with conn.cursor() as cur:
                # Creating tables
                cur.execute(f"""
                    create table if not exists {UsersDB.db_name}(
                        {UsersDB.chat_id} varchar(100),
                        {UsersDB.card_id} integer primary key
                    )
                """)
                cur.execute(f"""
                    create table if not exists {CardsDB.db_name}(
                        {CardsDB.card_id} serial primary key,
                        {CardsDB.phrase_id} integer not null,
                        {CardsDB.time_added} timestamp default current_timestamp,
                        {CardsDB.time_next_delta} integer not null default 3600
                    )
                """)
                cur.execute(f"""
                    create table if not exists {PhrasesDB.db_name}(
                        {PhrasesDB.phrase_id} serial primary key,
                        {PhrasesDB.phrase} varchar(4096),
                        {PhrasesDB.translation} text not null,
                        {PhrasesDB.definition} text,
                        {PhrasesDB.synonyms} text,
                        {PhrasesDB.examples} text
                    )
                """)

                # Constraints
                cur.execute(f"""
                    alter table {UsersDB.db_name} drop constraint
                    if exists users_cards_fkey
                """)
                cur.execute(f"""
                    alter table {UsersDB.db_name} add constraint
                    users_cards_fkey foreign key ({UsersDB.card_id})
                    references {CardsDB.db_name}({CardsDB.card_id})
                """)
                cur.execute(f"""
                    alter table {CardsDB.db_name} drop constraint
                    if exists cards_phrases_fkey
                """)
                cur.execute(f"""
                    alter table {CardsDB.db_name} add constraint
                    cards_phrases_fkey foreign key ({CardsDB.phrase_id})
                    references {PhrasesDB.db_name}({PhrasesDB.phrase_id})
                """)

                # Indexes
                cur.execute(f"""
                    create index if not exists user_chat_id_idx on
                    {UsersDB.db_name}({UsersDB.chat_id})
                """)


def drop_database():
    conn = psycopg2.connect(
        dbname=Config.initial_dbname,
        user=Config.user,
        password=Config.password,
        host=Config.host,
        port=Config.port,
    )

    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

    with conn:
        with conn.cursor() as cur:
            logger.info(f"Dropping database {Config.dbname}")
            cur.execute(f"drop database if exists {Config.dbname}")
    conn.commit()
    conn.close()


def apply_migrations():
    if Config.database_url is None:
        backend = get_backend(f'postgres://{Config.user}:{Config.password}@{Config.host}:{Config.port}/{Config.dbname}')
    else:
        backend = get_backend(Config.database_url)
    migrations = read_migrations('migrations/')
    with backend.lock():
        backend.apply_migrations(backend.to_apply(migrations))


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument('--recreate', action='store_true')

    args = parser.parse_args()

    create_database(recreate=args.recreate)
    apply_migrations()

