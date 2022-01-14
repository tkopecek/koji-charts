CREATE TABLE channels (
  id int(11) PRIMARY NOT NULL,
  name varchar(128) DEFAULT NULL,
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

CREATE TABLE task (
  id int(11) PRIMARY KEY NOT NULL,
  state int(11) DEFAULT NULL,
  create_time datetime DEFAULT NULL,
  start_time datetime DEFAULT NULL,
  completion_time datetime DEFAULT NULL,
  channel_id int(11) DEFAULT NULL,
  host_id int(11) DEFAULT NULL,
  parent int(11) DEFAULT NULL,
  owner int(11) DEFAULT NULL,
  method varchar(30) DEFAULT NULL,
  arch varchar(10) DEFAULT NULL,
  KEY arch (arch),
  KEY method (method),
  KEY create_time (create_time),
  KEY start_time (start_time),
  KEY completion_time (completion_time),
  KEY state (state),
  KEY channel_id (channel_id),
  KEY host_id (host_id),
  KEY parent (parent),
  KEY owner (owner)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 PAGE_COMPRESSED=1;

CREATE TABLE users (
  id int(11) PRIMARY NOT NULL,
  name varchar(255) DEFAULT NULL,
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

CREATE TABLE build (
    id int(11) PRIMARY KEY,
    pkg_id INTEGER NOT NULL,
    start_time TIMESTAMP,
    completion_time TIMESTAMP,
    state INTEGER NOT NULL,
    task_id INTEGER,
    owner INTEGER NOT NULL REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 PAGE_COMPRESSED=1;
