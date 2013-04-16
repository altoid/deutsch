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
