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
