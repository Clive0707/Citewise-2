-- Chat Sessions
CREATE TABLE IF NOT EXISTS "chat_sessions" (
  "id" TEXT PRIMARY KEY,
  "user_id" TEXT NOT NULL,
  "title" TEXT,
  "scope" TEXT NOT NULL,
  "run_id" TEXT,
  "created_at" TIMESTAMP(3) DEFAULT CURRENT_TIMESTAMP,
  "updated_at" TIMESTAMP(3) DEFAULT CURRENT_TIMESTAMP,
  "deleted_at" TIMESTAMP(3)
);

CREATE INDEX IF NOT EXISTS "chat_sessions_user_id_deleted_at_idx"
ON "chat_sessions" ("user_id", "deleted_at");

-- Chat Messages
CREATE TABLE IF NOT EXISTS "chat_messages" (
  "id" TEXT PRIMARY KEY,
  "session_id" TEXT NOT NULL,
  "role" TEXT NOT NULL,
  "content" TEXT NOT NULL,
  "tokens_in" INTEGER,
  "tokens_out" INTEGER,
  "model_used" TEXT,
  "latency_ms" INTEGER,
  "created_at" TIMESTAMP(3) DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS "chat_messages_session_id_created_at_idx"
ON "chat_messages" ("session_id", "created_at");

-- Chat Citations
CREATE TABLE IF NOT EXISTS "chat_citations" (
  "id" TEXT PRIMARY KEY,
  "message_id" TEXT NOT NULL,
  "url" TEXT NOT NULL,
  "domain_type" TEXT,
  "chunk_id" INTEGER,
  "relevance_score" DOUBLE PRECISION,
  "created_at" TIMESTAMP(3) DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS "chat_citations_message_id_idx"
ON "chat_citations" ("message_id");

-- Usage Logs (billing)
CREATE TABLE IF NOT EXISTS "usage_logs" (
  "id" TEXT PRIMARY KEY,
  "user_id" TEXT NOT NULL,
  "date" DATE NOT NULL,
  "tokens_used" INTEGER DEFAULT 0,
  "messages_count" INTEGER DEFAULT 0,
  "created_at" TIMESTAMP(3) DEFAULT CURRENT_TIMESTAMP,
  "updated_at" TIMESTAMP(3) DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS "usage_logs_user_id_date_key"
ON "usage_logs" ("user_id", "date");

CREATE INDEX IF NOT EXISTS "usage_logs_user_id_date_idx"
ON "usage_logs" ("user_id", "date");