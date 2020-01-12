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
        message = "-----Карточка---\n"
        message += "{} | {}".format(self.word, self.translation)
        message += "\n".join(list(
                      map(str, list(filter(lambda x: x is not None, [
                           self.definition]
                    ))))) + "\n"
        if not self.examples is None:
            message += "".join([">> {} | {} \n".format(fr, to) for fr, to in self.examples])
        message += "--------------\n"
        # message = self.word + "\n" + collinsAPI.get_url(self.word) + "\n"
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
