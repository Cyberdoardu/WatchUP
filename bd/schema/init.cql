CREATE KEYSPACE IF NOT EXISTS watchup
WITH replication = {
    'class': 'NetworkTopologyStrategy',
    'dc1' : 1
};

USE watchup;

CREATE TABLE IF NOT EXISTS usuarios (
    id UUID PRIMARY KEY,
    nome text,
    email text,
    senha text,
    username text,
    admin boolean
);

CREATE CUSTOM INDEX IF NOT EXISTS ON usuarios (email) USING 'org.apache.cassandra.index.sasi.SASIIndex';
CREATE CUSTOM INDEX IF NOT EXISTS ON usuarios (username) USING 'org.apache.cassandra.index.sasi.SASIIndEX';