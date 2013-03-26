
create table attribute
(
	id	      int		auto_increment not null primary key,
	name	      varchar(255)	not null
) engine = innodb;

create table pos -- part of speech
(
	id	      int		auto_increment not null primary key,
	name	      varchar(255)	not null
) engine = innodb;

-- all the attributes defined for a part of speech (verb conjugations, etc)
create table pos_form
(
	pos_id		int	not null,
	attribute_id	int	not null,

	foreign key (attribute_id) references attribute(id) on delete cascade,
	foreign key (pos_id) references pos(id) on delete cascade
) engine = innodb;

-- dictionary entries ( words)
create table word
(
	id		int		auto_increment not null primary key,
	pos_id		int		not null,
	word		varchar(64)	not null,

	foreign key (pos_id) references pos(id) on delete cascade
) engine = innodb;

create table definition
(
	id		int		auto_increment not null primary key,
	definition	text		not null
) engine = innodb;

create table word_form
(
	id		int		auto_increment not null primary key,
	variant		varchar(64)	not null,
	word_id		int		not null,

	foreign key (word_id) references word(id) on delete cascade

) engine = innodb;

create table user
(
	id		int		auto_increment not null primary key,
	name		varchar(64)	not null,
	password	char(80)	not null,  -- 2 sha1 hashes
	access		enum('user', 'admin') not null
) engine = innodb;
