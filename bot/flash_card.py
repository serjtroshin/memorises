from psycopg2.extras import NamedTupleCursor

from .database import CardsDB
from .database import get_connection
from .database import PhrasesDB
from .database import UsersDB
from .configs.settings import TIME_BEFORE_FIRST_SHOW
from .configs.settings import TIME_MULTIPLIER


class FlashCard:
    def __init__(
        self,
        word=None,
        translation=None,
        definition=None,
        synonyms=None,
        examples=None,
        chat_id=None,
        card_id=None,
        time_added=None,
        time_next_delta=None,
    ):
        self.word = word
        self.translation = translation
        self.definition = definition
        self.examples = examples
        self.synonyms = synonyms

        self.chat_id = chat_id
        self.card_id = card_id

        self.time_added = time_added
        self.time_next_delta = time_next_delta

    def __str__(self):
        definitions_strings = self.definition if self.definition is not None else ""
        examples_strings = (
            "Примеры:\n"
            + "".join([">> {} | {} \n".format(fr, to) for fr, to in self.examples])
            if self.examples
            else ""
        )
        synonym_strings = (
            "Синонимы:\n" + "".join([">> {}\n".format(syn) for syn in self.synonyms])
            if self.synonyms
            else ""
        )
        message = ""
        message += "{} | {}".format(self.word, self.translation) + "\n"
        message += definitions_strings + "\n"
        message += examples_strings
        message += synonym_strings
        return message

    def add_to_database(self):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
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
                    returning {PhrasesDB.phrase_id}
                """,
                    (
                        self.word,
                        self.translation,
                        self.definition,
                        self.synonyms,
                        self.examples,
                    ),
                )
                phrase_id = cur.fetchone()[0]

                cur.execute(
                    f"""
                        insert into {CardsDB.db_name}(
                            {CardsDB.phrase_id},
                            {CardsDB.time_next_delta}
                        ) values (
                            %s, %s
                        ) returning {CardsDB.card_id},
                        {CardsDB.time_added}, {CardsDB.time_next_delta}
                    """,
                    (phrase_id, TIME_BEFORE_FIRST_SHOW),
                )
                ret = cur.fetchone()
                self.card_id, self.time_added, self.time_next_delta = ret

                cur.execute(
                    f"""
                    insert into {UsersDB.db_name}(
                        {UsersDB.chat_id},
                        {UsersDB.card_id}
                    ) values (
                        %s, %s
                    )
                """,
                    (self.chat_id, self.card_id),
                )

    @staticmethod
    def _retrieve(ob, tp):
        if ob is None:
            return None
        if tp == "synonyms":
            return ob[1:-1].split(",")
        elif tp == "examples":
            ob = eval(ob)
            return {eval(i) for i in ob}
        return None

    def fill_from_database(self):
        with get_connection() as conn:
            with conn.cursor(cursor_factory=NamedTupleCursor) as cur:
                cur.execute(
                    f"""
                    select {PhrasesDB.db_name}.{PhrasesDB.phrase},
                           {PhrasesDB.db_name}.{PhrasesDB.translation},
                           {PhrasesDB.db_name}.{PhrasesDB.definition},
                           {PhrasesDB.db_name}.{PhrasesDB.synonyms},
                           {PhrasesDB.db_name}.{PhrasesDB.examples},
                           {CardsDB.db_name}.{CardsDB.time_added},
                           {CardsDB.db_name}.{CardsDB.time_next_delta},
                           {UsersDB.db_name}.{UsersDB.chat_id}
                    from {CardsDB.db_name} join {PhrasesDB.db_name}
                    on {PhrasesDB.db_name}.{PhrasesDB.phrase_id}=
                        {CardsDB.db_name}.{CardsDB.phrase_id}
                    join {UsersDB.db_name} on {CardsDB.db_name}.{CardsDB.card_id}=
                        {UsersDB.db_name}.{UsersDB.card_id}
                    where {CardsDB.db_name}.{CardsDB.card_id}=%s
                """,
                    (self.card_id,),
                )
                record = cur.fetchone()
                self.word = record.phrase
                self.translation = record.translation
                self.examples = FlashCard._retrieve(record.examples, "examples")
                self.synonyms = FlashCard._retrieve(record.synonyms, "synonyms")
                self.chat_id = record.chat_id
                self.time_added = record.time_added
                self.time_next_delta = record.time_next_delta

    def update(self):
        with get_connection() as conn:
            with conn.cursor(cursor_factory=NamedTupleCursor) as cur:
                cur.execute(
                    f"""
                    update {CardsDB.db_name}
                    set {CardsDB.time_next_delta}={CardsDB.time_next_delta}*%s
                    where {CardsDB.card_id}=%s
                    returning {CardsDB.time_next_delta}
                """,
                    (TIME_MULTIPLIER, self.card_id),
                )
                return cur.fetchone()[0]

    def chech_if_exist(self):
        with get_connection() as conn:
            with conn.cursor(cursor_factory=NamedTupleCursor) as cur:
                cur.execute(
                    f"""
                    select from {CardsDB.db_name} join {UsersDB.db_name}
                    on {UsersDB.db_name}.{UsersDB.card_id}=
                        {CardsDB.db_name}.{CardsDB.card_id}
                    join {PhrasesDB.db_name}
                    on {CardsDB.db_name}.{CardsDB.phrase_id}=
                        {PhrasesDB.db_name}.{PhrasesDB.phrase_id}
                    where {UsersDB.chat_id}=%s and {PhrasesDB.phrase}=%s and
                    {PhrasesDB.translation}=%s
                """,
                    (str(self.chat_id), self.word, self.translation),
                )
                return cur.fetchone() is not None

    @staticmethod
    def findall_in_database(word, chat_id):
        with get_connection() as conn:
            with conn.cursor(cursor_factory=NamedTupleCursor) as cur:
                cur.execute(
                    f"""
                    select {PhrasesDB.db_name}.{PhrasesDB.phrase},
                           {PhrasesDB.db_name}.{PhrasesDB.translation},
                           {UsersDB.db_name}.{UsersDB.chat_id},
                           {CardsDB.db_name}.{CardsDB.card_id}
                    from {CardsDB.db_name} join {PhrasesDB.db_name}
                    on {PhrasesDB.db_name}.{PhrasesDB.phrase_id}=
                        {CardsDB.db_name}.{CardsDB.phrase_id}
                    join {UsersDB.db_name} on {CardsDB.db_name}.{CardsDB.card_id}=
                        {UsersDB.db_name}.{UsersDB.card_id}
                    where {UsersDB.db_name}.{UsersDB.chat_id}=%s and
                    ({PhrasesDB.db_name}.{PhrasesDB.phrase}=%s or
                    {PhrasesDB.db_name}.{PhrasesDB.translation}=%s)
                """,
                    (chat_id, word, word),
                )
                return cur.fetchall()

    @staticmethod
    def delete(card_id):
        with get_connection() as conn:
            with conn.cursor(cursor_factory=NamedTupleCursor) as cur:
                cur.execute(
                    f"""
                    delete from {UsersDB.db_name} where {UsersDB.card_id}=%s
                """,
                    (card_id,),
                )
                cur.execute(
                    f"""
                    delete from {CardsDB.db_name} where {CardsDB.card_id}=%s
                """,
                    (card_id,),
                )
                return cur.rowcount


def get_all_flash_cards():
    with get_connection() as conn:
        with conn.cursor(cursor_factory=NamedTupleCursor) as cur:
            cur.execute(
                f"""
                select {CardsDB.card_id}, {CardsDB.time_added},
                    {CardsDB.time_next_delta}
                from {CardsDB.db_name}"""
            )  # todo add exceptions
            return cur.fetchall()


if __name__ == "__main__":
    flashCard = FlashCard(card_id="10")
    flashCard.fill_from_database()
    print(flashCard)
    print(flashCard.chat_id)
    print(FlashCard.findall_in_database("привет", "124669989"))
