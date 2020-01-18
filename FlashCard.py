from time import time
from database import get_connection, UsersDB, CardsDB, PhrasesDB
from psycopg2.extras import NamedTupleCursor

class FlashCard:
    def __init__(self, word=None, translation=None, definition=None, synonyms=None, examples=None, chat_id=None):
        self.word = word
        self.translation = translation
        self.definition = definition
        self.examples = examples
        self.synonyms = synonyms

        self.chat_id = chat_id
        self.card_id = None

    def __str__(self):
        definitions_strings = "\n".join(list(
                      map(str, list(filter(lambda x: x is not None, [
                           self.definition]
                    )))))
        examples_strings = "Примеры:\n" + "".join([">> {} | {} \n".format(fr, to) for fr, to in self.examples]) \
            if not self.examples is None else ""
        synonym_strings = "Синонимы:\n" + "".join([">>: {}\n".format(syn) for syn in self.synonyms]) \
            if not self.synonyms is None else ""
        message = ""
        message += "{} | {}".format(self.word, self.translation) + '\n'
        message += definitions_strings + "\n"
        if not self.examples is None:
            message += examples_strings
        if not self.synonyms is None:
            message += synonym_strings
        return message

    def add_to_database(self):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(f"""
                    insert into {PhrasesDB.db_name}(
                        {PhrasesDB.phrase},
                        {PhrasesDB.translation},
                        {PhrasesDB.definition},
                        {PhrasesDB.synonyms},
                        {PhrasesDB.examples}
                    )
                    values (
                        %s, %s, %s, %s, %s
                    )
                    on conflict do nothing
                """, (self.word, self.translation, self.definition, self.synonyms, self.examples))

                cur.execute(f"""
                        insert into {CardsDB.db_name}(
                            {CardsDB.phrase}
                        ) values (
                            %s
                        ) returning {CardsDB.card_id}
                    """, (self.word,)
                )

                self.card_id = cur.fetchone()[0]

                cur.execute(f"""
                    insert into {UsersDB.db_name}(
                        {UsersDB.chat_id},
                        {UsersDB.card_id}
                    ) values (
                        %s, %s
                    )
                """, (self.chat_id, self.card_id))

    def get_from_database(self):
        with get_connection() as conn:
            with conn.cursor(cursor_factory=NamedTupleCursor) as cur:
                cur.execute(f"""
                    select * from {CardsDB.db_name}
                    where {CardsDB.card_id}=%s
                """, (self.card_id,))
                return cur.fetchone()

    def update(self):
        with get_connection() as conn:
            with conn.cursor(cursor_factory=NamedTupleCursor) as cur:
                cur.execute(f"""
                    update {CardsDB.db_name}
                    set {CardsDB.time_next_delta}={CardsDB.time_next_delta}*10
                    where {CardsDB.card_id}=%s
                    returning {CardsDB.time_next_delta}
                """, (self.card_id,))
                return cur.fetchone()[0]

    def chech_if_exist(self):
        with get_connection() as conn:
            with conn.cursor(cursor_factory=NamedTupleCursor) as cur:
                cur.execute(f"""
                                    select from
                                        {CardsDB.db_name} inner join {UsersDB.db_name}
                                        on {UsersDB.db_name}.{UsersDB.card_id}={CardsDB.db_name}.{CardsDB.card_id}
                                    where {UsersDB.chat_id}=%s and {CardsDB.phrase}=%s
                                """, (str(self.chat_id), self.word))
                return cur.fetchone() is not None
