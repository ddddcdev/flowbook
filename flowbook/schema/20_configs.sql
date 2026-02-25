CREATE TABLE IF NOT EXISTS configs (
  config_id    uuid PRIMARY KEY,
  kind         text NOT NULL,
  name         text NOT NULL,
  spec         jsonb NOT NULL DEFAULT '{}'::jsonb,
  meta         jsonb NOT NULL DEFAULT '{}'::jsonb,
  is_active    boolean NOT NULL DEFAULT true,
  created_at   timestamptz NOT NULL DEFAULT now(),
  updated_at   timestamptz NOT NULL DEFAULT now(),
  UNIQUE(kind, name)
);

CREATE INDEX IF NOT EXISTS configs_kind_idx ON configs(kind);

DROP TRIGGER IF EXISTS configs_set_updated_at ON configs;

CREATE TRIGGER configs_set_updated_at
BEFORE UPDATE ON configs
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();
