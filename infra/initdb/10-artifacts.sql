CREATE TABLE IF NOT EXISTS artifacts (
  artifact_key   text PRIMARY KEY,
  content_type   text NOT NULL,
  codec          text NOT NULL DEFAULT 'none',
  bytes          bytea,
  json           jsonb,
  meta           jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at     timestamptz NOT NULL DEFAULT now(),
  updated_at     timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS artifacts_content_type_idx ON artifacts(content_type);

-- Prefix LIKE 'run_id/%' を速くする（BTREE + text_pattern_ops）
CREATE INDEX IF NOT EXISTS artifacts_key_prefix_idx
ON artifacts (artifact_key text_pattern_ops);

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
