-- entities: entity_key is the scoping key (slash-separated hierarchy allowed)
-- meta: jsonb for display_name, description, etc.
CREATE TABLE IF NOT EXISTS entities (
  entity_key   text PRIMARY KEY,
  meta         jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at   timestamptz NOT NULL DEFAULT now(),
  updated_at   timestamptz NOT NULL DEFAULT now()
);

-- runs: already exists conceptually
CREATE TABLE IF NOT EXISTS runs (
  run_id     text PRIMARY KEY,
  status     text NOT NULL,
  config_json text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE runs ADD COLUMN IF NOT EXISTS config_json text;

-- results: canonical result per (run_id, entity_key)
-- result_artifacts_json: JSON array of {path, label}. When plan has no result_artifacts,
-- last step's first output is stored as [{"path": "step/key", "label": null}].
CREATE TABLE IF NOT EXISTS results (
  run_id      text NOT NULL REFERENCES runs(run_id),
  entity_key  text NOT NULL,
  result_artifacts_json text,
  status      text NOT NULL,
  config_json  text,
  created_at  timestamptz NOT NULL DEFAULT now(),
  updated_at  timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (run_id, entity_key)
);

-- artifacts: composite PK (run_id, entity_key, artifact_path)
-- key format: {run_id}/{entity_key}/{artifact_path}
-- inputs: entity_key = '' (empty), artifact_path = 'input/{name}'
-- outputs: entity_key = entity, artifact_path = '{step}/{out}'
CREATE TABLE IF NOT EXISTS artifacts (
  run_id       text NOT NULL,
  entity_key   text NOT NULL,
  artifact_path text NOT NULL,
  content_type text NOT NULL,
  codec        text NOT NULL DEFAULT 'none',
  bytes        bytea,
  json         jsonb,
  meta         jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at   timestamptz DEFAULT now(),
  updated_at   timestamptz DEFAULT now(),
  PRIMARY KEY (run_id, entity_key, artifact_path)
);

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=current_schema() AND table_name='artifacts' AND column_name='path') THEN
    ALTER TABLE artifacts RENAME COLUMN path TO artifact_path;
  END IF;
END $$;
CREATE INDEX IF NOT EXISTS artifacts_content_type_idx ON artifacts(content_type);
CREATE INDEX IF NOT EXISTS artifacts_run_id_idx ON artifacts(run_id);
CREATE INDEX IF NOT EXISTS artifacts_run_entity_idx ON artifacts(run_id, entity_key);

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS trigger AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS artifacts_set_updated_at ON artifacts;
CREATE TRIGGER artifacts_set_updated_at
BEFORE UPDATE ON artifacts
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS results_set_updated_at ON results;
CREATE TRIGGER results_set_updated_at
BEFORE UPDATE ON results
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS entities_set_updated_at ON entities;
CREATE TRIGGER entities_set_updated_at
BEFORE UPDATE ON entities
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

-- Seed initial entities
INSERT INTO entities (entity_key, meta, created_at, updated_at)
VALUES
  ('demo', '{"display_name": "Demo", "desc": "Top-level demo scope"}'::jsonb, now(), now()),
  ('demo/excel', '{"display_name": "Demo Excel", "desc": "Excel import/export demo"}'::jsonb, now(), now())
ON CONFLICT (entity_key) DO NOTHING;
