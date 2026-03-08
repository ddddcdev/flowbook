CREATE TABLE IF NOT EXISTS configs (
  config_id    uuid PRIMARY KEY,
  config_type  text NOT NULL,
  config_name  text NOT NULL,
  spec         jsonb NOT NULL DEFAULT '{}'::jsonb,
  spec_text    text DEFAULT '',
  meta         jsonb NOT NULL DEFAULT '{}'::jsonb,
  is_active    boolean NOT NULL DEFAULT true,
  created_at   timestamptz NOT NULL DEFAULT now(),
  updated_at   timestamptz NOT NULL DEFAULT now(),
  UNIQUE(config_type, config_name)
);

CREATE INDEX IF NOT EXISTS configs_config_type_idx ON configs(config_type);

DROP TRIGGER IF EXISTS configs_set_updated_at ON configs;

CREATE TRIGGER configs_set_updated_at
BEFORE UPDATE ON configs
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();
