CREATE SCHEMA analytics;

CREATE TABLE analytics.customers (
    id         bigserial PRIMARY KEY,
    name       text NOT NULL,
    country    text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE analytics.orders (
    id          bigserial PRIMARY KEY,
    customer_id bigint NOT NULL REFERENCES analytics.customers(id),
    total_pence bigint NOT NULL,
    status      text NOT NULL,
    placed_at   timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE analytics.pipeline_runs (
    id           bigserial PRIMARY KEY,
    pipeline     text NOT NULL,
    status       text NOT NULL,
    rows_written bigint,
    started_at   timestamptz NOT NULL DEFAULT now()
);

-- Present on purpose, and never exposed by the server.
CREATE TABLE analytics.api_credentials (
    id      bigserial PRIMARY KEY,
    service text NOT NULL,
    token   text NOT NULL
);

INSERT INTO analytics.customers (name, country) VALUES
  ('Acme Ltd','GB'), ('Bourne Co','US'), ('Corvid PLC','GB');
INSERT INTO analytics.orders (customer_id, total_pence, status) VALUES
  (1, 12050, 'paid'), (1, 3400, 'refunded'), (2, 89900, 'paid'),
  (3, 1500, 'pending'), (2, 25000, 'paid');
INSERT INTO analytics.pipeline_runs
  (pipeline, status, rows_written) VALUES
  ('orders_daily','succeeded',5),
  ('customers_sync','failed',NULL),
  ('orders_daily','succeeded',12);
INSERT INTO analytics.api_credentials (service, token) VALUES
  ('stripe','sk_live_do_not_expose');

-- The server connects as this role. It can read three tables
-- and write nothing.
-- Local development passwords. Change these, and the matching
-- values in .env, for anything reachable beyond localhost.
CREATE ROLE mcp_reader LOGIN PASSWORD 'localdev';
GRANT CONNECT ON DATABASE warehouse TO mcp_reader;
GRANT USAGE ON SCHEMA analytics TO mcp_reader;
GRANT SELECT ON analytics.customers, analytics.orders,
                analytics.pipeline_runs TO mcp_reader;

-- Chapter 18: a second role, able to delete from exactly one
-- table and nothing else. The read path never uses it.
CREATE ROLE mcp_writer LOGIN PASSWORD 'localdev';
GRANT CONNECT ON DATABASE warehouse TO mcp_writer;
GRANT USAGE ON SCHEMA analytics TO mcp_writer;
GRANT SELECT, DELETE ON analytics.pipeline_runs TO mcp_writer;

-- Chapter 26: work that outlives a request lives here, not in
-- any instance's memory.
CREATE TABLE analytics.scan_results (
    handle      text PRIMARY KEY,
    table_name  text NOT NULL,
    status      text NOT NULL,
    rows_seen   bigint,
    null_counts jsonb,
    created_at  timestamptz NOT NULL DEFAULT now(),
    expires_at  timestamptz NOT NULL
);
GRANT SELECT, INSERT, UPDATE ON analytics.scan_results
    TO mcp_writer;
GRANT SELECT ON analytics.scan_results TO mcp_reader;
