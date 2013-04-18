create table if not exists quiz
(
        id            int               auto_increment not null primary key,
        name          varchar(64)       not null unique
) engine = innodb;

create table if not exists quiz_structure
(
        quiz_id                 int                     not null,
        pos_id                  int                     not null,
        attribute_id            int                     not null,

        foreign key (quiz_id) references quiz(id) on delete cascade,
        foreign key (attribute_id) references attribute(id) on delete cascade,
        foreign key (pos_id) references pos(id) on delete cascade,

	unique  key (quiz_id, pos_id, attribute_id)

) engine = innodb;

create table if not exists quiz_score
(
        quiz_id                 int                     not null,
        word_id                 int                     not null,
        attribute_id            int                     not null,
        presentation_count      int                     not null,
        correct_count           int                     not null,

        -- specifying no qualifiers on the first timestamp column
        -- defaults to both DEFAULT CURRENT TIMESTAMP and ON UPDATE
        -- CURRENT TIMESTAMP.
        last_presentation       timestamp,

        foreign key (quiz_id) references quiz(id) on delete cascade,
        foreign key (attribute_id) references attribute(id) on delete cascade,
        foreign key (word_id) references word(id) on delete cascade,

        primary key (quiz_id, word_id, attribute_id)

) engine = innodb;

-- this view shows the number of attributes defined for each word defined
-- in the structure of a quiz.  helps us catch things like not all values
-- being present for a verb conjugation.
-- this view is not updatable because of the group by clause
-- but it will correctly show changes to underlying tables
create view quiz_attr_counts as
select qs.*, w.id word_id, count(*) attrcount
from word w, quiz_structure qs, word_attributes wa
where w.pos_id = qs.pos_id
and wa.word_id = w.id
and wa.attribute_id = qs.attribute_id
group by quiz_id, word_id
;


-- this view shows the number of attributes defined for each part of speech in a quiz structure
create view quiz_attr_count as
select distinct quiz.id quiz_id, qs.pos_id, qs.attribute_id, count(*) attrcount
from quiz
inner join quiz_structure qs on quiz.id = qs.quiz_id
group by quiz.id, qs.pos_id
;
