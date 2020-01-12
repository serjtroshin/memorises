import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import json
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)


class Config:
    _config = json.load(open("config.json", "r"))["database"]

    dbname = _config["dbname"]
    initial_dbname = _config["initial_dbname"]
    user = _config["user"]
    password = _config["password"]
    host = _config["host"]
    port = _config["port"]
    timeout = _config["timeout"]


def get_connection():
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
    phrase = "phrase"
    time_added = "time_added"
    time_next_delta = "time_next_delta"


class PhrasesDB:
    db_name = "phrases"
    phrase = "phrase"
    translation = "translation"
    definition = "definition"
    synonyms = "synonyms"
    examples = "examples"


def create_database(recreate=False):
    if recreate:
        drop_database()

    conn = psycopg2.connect(
        dbname=Config.initial_dbname,
        user=Config.user,
        password=Config.password,
        host=Config.host,
        port=Config.port,
    )

    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

    exists = True

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
                        {CardsDB.phrase} varchar(4096),
                        {CardsDB.time_added} timestamp default current_timestamp,
                        {CardsDB.time_next_delta} integer not null default 100
                    )
                """)
                cur.execute(f"""
                    create table if not exists {PhrasesDB.db_name}(
                        {PhrasesDB.phrase} varchar(4096) primary key,
                        {PhrasesDB.translation} text not null,
                        {PhrasesDB.definition} text,
                        {PhrasesDB.synonyms} text,
                        {PhrasesDB.examples} text
                    )
                """)

                # Constraints
                cur.execute(f"""
                    alter table {UsersDB.db_name} add constraint
                    users_cards_fkey foreign key ({UsersDB.card_id})
                    references {CardsDB.db_name}({CardsDB.card_id})
                """)
                cur.execute(f"""
                    alter table {CardsDB.db_name} add constraint
                    cards_phrases_fkey foreign key ({CardsDB.phrase})
                    references {PhrasesDB.db_name}({PhrasesDB.phrase})
                """)

                # Indexes
                cur.execute(f"""
                    create index user_chat_id_idx on
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


if __name__ == "__main__":
    create_database(recreate=True)
