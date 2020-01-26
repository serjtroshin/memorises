from yoyo import step

steps = [
    step("alter table cards drop constraint cards_phrases_fkey",
         """alter table cards add constraint
          cards_phrases_fkey foreign key (phrase)
          references phrases(phrase)""",
          ignore_errors='apply'),
    step("alter table phrases drop constraint phrases_pkey",
         "alter table phrases add primary key (phrase)",
         ignore_errors='apply'),
    step("alter table phrases add column phrase_id serial primary key",
         "alter table phrases drop column phrase_id",
         ignore_errors='apply'),
]
