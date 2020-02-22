from yoyo import step

__depends__ = {'0003-cards-drop-phrase-column'}

steps = [
    step("""create index if not exists phrases_phrase_idx on
            phrases(lower(phrases.phrase))""",
         "drop index phrases_phrase_idx"),
    step("""create index if not exists phrases_translation_idx on
            phrases(lower(phrases.translation))""",
         "drop index phrases_translation_idx"),
]
