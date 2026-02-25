-- entities: entity_key is the scoping key (opaque string, exact-match only)
CREATE TABLE IF NOT EXISTS entities (
  entity_key text PRIMARY KEY,
  meta_json  text
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

-- entity_runs: canonical result per (run_id, entity_key)
-- result_artifacts_json: JSON array of {path, label}. When plan has no result_artifacts,
-- last step's first output is stored as [{"path": "step/key", "label": null}].
CREATE TABLE IF NOT EXISTS entity_runs (
  run_id      text NOT NULL REFERENCES runs(run_id),
  entity_key  text NOT NULL,
  result_artifacts_json text,
  status      text NOT NULL,
  config_json  text,
  created_at  timestamptz NOT NULL DEFAULT now(),
  updated_at  timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (run_id, entity_key)
);

ALTER TABLE entity_runs DROP COLUMN IF EXISTS summary_json;
ALTER TABLE entity_runs DROP COLUMN IF EXISTS path;
ALTER TABLE entity_runs ADD COLUMN IF NOT EXISTS result_artifacts_json text;
ALTER TABLE entity_runs ADD COLUMN IF NOT EXISTS config_json text;
-- Migrate artifact_path -> result_artifacts_json, then drop artifact_path (for existing DBs)
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=current_schema() AND table_name='entity_runs' AND column_name='artifact_path') THEN
    UPDATE entity_runs SET result_artifacts_json = json_build_array(json_build_object('path', artifact_path, 'label', null))::text
      WHERE artifact_path IS NOT NULL AND (result_artifacts_json IS NULL OR result_artifacts_json = '');
    ALTER TABLE entity_runs DROP COLUMN artifact_path;
  END IF;
END $$;

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

DROP TRIGGER IF EXISTS entity_runs_set_updated_at ON entity_runs;
CREATE TRIGGER entity_runs_set_updated_at
BEFORE UPDATE ON entity_runs
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();
