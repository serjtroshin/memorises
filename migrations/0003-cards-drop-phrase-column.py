from yoyo import step

__depends__ = {'0002-cards-add-phrases-foreign-key'}

steps = [
    step("",
         """update cards set phrase=phrases.phrase
            from phrases where cards.phrase_id=phrases.phrase_id""",
         ignore_errors='apply'),
    step("alter table cards drop column phrase",
         "alter table cards add column phrase varchar(4096)",
         ignore_errors='apply'),
]
