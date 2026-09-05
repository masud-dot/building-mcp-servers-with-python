-- Capstone schema. Two roles, and one table neither can read.
CREATE SCHEMA ops;

CREATE TABLE ops.services (
    name text PRIMARY KEY,
    team text NOT NULL,
    tier int  NOT NULL
);

CREATE TABLE ops.incidents (
    id              bigserial PRIMARY KEY,
    service         text NOT NULL REFERENCES ops.services(name),
    severity        int  NOT NULL,
    summary         text NOT NULL,
    status          text NOT NULL DEFAULT 'open',
    acknowledged_by text,
    opened_at       timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ops.deployments (
    id          bigserial PRIMARY KEY,
    service     text NOT NULL REFERENCES ops.services(name),
    version     text NOT NULL,
    deployed_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ops.scan_results (
    handle     text PRIMARY KEY,
    service    text NOT NULL,
    status     text NOT NULL,
    matches    bigint,
    expires_at timestamptz NOT NULL
);

-- Present on purpose and granted to nobody. If a bug ever
-- reaches this table, the grant is what stops it.
CREATE TABLE ops.oncall_pager_tokens (
    id text PRIMARY KEY, token text NOT NULL
);

INSERT INTO ops.services VALUES
  ('checkout','payments',1), ('search','discovery',2),
  ('billing','payments',1);
INSERT INTO ops.incidents (service,severity,summary) VALUES
  ('checkout',1,'Card authorisation failures spiking'),
  ('checkout',3,'Slow p95 on /cart'),
  ('search',2,'Index lag above threshold');
INSERT INTO ops.deployments (service,version) VALUES
  ('checkout','2026.9.1'), ('checkout','2026.9.2'),
  ('search','2026.8.14');
INSERT INTO ops.oncall_pager_tokens
  VALUES ('pd','pd_live_never_expose');

-- Reads four tables. Cannot write anything.
-- Local development passwords. Change these, and the matching
-- values in .env, for anything reachable beyond localhost.
CREATE ROLE aiops_reader LOGIN PASSWORD 'localdev';
GRANT CONNECT ON DATABASE aiops TO aiops_reader;
GRANT USAGE ON SCHEMA ops TO aiops_reader;
GRANT SELECT ON ops.services, ops.incidents, ops.deployments,
                ops.scan_results TO aiops_reader;

-- Writes exactly two things and nothing else.
CREATE ROLE aiops_writer LOGIN PASSWORD 'localdev';
GRANT CONNECT ON DATABASE aiops TO aiops_writer;
GRANT USAGE ON SCHEMA ops TO aiops_writer;
GRANT SELECT, UPDATE ON ops.incidents TO aiops_writer;
GRANT SELECT, INSERT, UPDATE ON ops.scan_results TO aiops_writer;
GRANT USAGE ON SEQUENCE ops.incidents_id_seq TO aiops_writer;
