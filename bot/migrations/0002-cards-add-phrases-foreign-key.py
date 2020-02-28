from yoyo import step

__depends__ = {"0001-phrases-add-serial-column"}

steps = [
    step(
        "alter table cards add column phrase_id integer",
        "alter table cards drop column phrase_id",
        ignore_errors="apply",
    ),
    step(
        """alter table cards add constraint
            cards_phrases_fkey foreign key (phrase_id)
            references phrases(phrase_id)""",
        "alter table cards drop constraint cards_phrases_fkey",
        ignore_errors="apply",
    ),
    step(
        """update cards set phrase_id=phrases.phrase_id
            from phrases where cards.phrase=phrases.phrase""",
        ignore_errors="apply",
    ),
    step(
        "alter table cards alter column phrase_id set not null",
        "alter table cards alter column phrase_id drop not null",
        ignore_errors="apply",
    ),
]
