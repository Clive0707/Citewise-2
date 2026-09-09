-- CreateTable
CREATE TABLE "citelabs_pages" (
    "id" BIGSERIAL NOT NULL,
    "url" TEXT NOT NULL,
    "content" TEXT,
    "ai_summary" TEXT,
    "page_type" TEXT,
    "is_client" BOOLEAN NOT NULL DEFAULT false,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "citelabs_pages_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "PageRecord" (
    "id" TEXT NOT NULL,
    "url" TEXT NOT NULL,
    "pageType" TEXT,
    "title" TEXT,
    "metaDescription" TEXT,
    "headings" TEXT,
    "mainContent" TEXT,
    "lastModified" TEXT,
    "pagePurposeSummary" TEXT,
    "primaryKeywordGuess" TEXT,
    "aiSummary" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "PageRecord_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "sandbox_runs" (
    "id" TEXT NOT NULL,
    "sandbox_url" TEXT NOT NULL,
    "status" TEXT NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "sandbox_runs_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "sandbox_pages" (
    "id" TEXT NOT NULL,
    "run_id" TEXT NOT NULL,
    "url" TEXT NOT NULL,
    "title" TEXT,
    "h1" TEXT,
    "intent" TEXT,
    "page_summary" TEXT,
    "aiSummary" TEXT,
    "full_text" TEXT,
    "is_client" BOOLEAN NOT NULL DEFAULT true,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "sandbox_brand_name" TEXT,

    CONSTRAINT "sandbox_pages_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "answer_metrics" (
    "id" TEXT NOT NULL,
    "answer_id" TEXT NOT NULL,
    "brand_mention_count" INTEGER NOT NULL DEFAULT 0,
    "competitor_mention_count" INTEGER NOT NULL DEFAULT 0,
    "is_brand_mentioned" BOOLEAN NOT NULL DEFAULT false,
    "is_brand_cited" BOOLEAN NOT NULL DEFAULT false,
    "brand_cited_first" BOOLEAN NOT NULL DEFAULT false,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "answer_metrics_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "sandbox_questions" (
    "id" TEXT NOT NULL,
    "run_id" TEXT NOT NULL,
    "type" TEXT NOT NULL,
    "question" TEXT NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "sandbox_questions_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "sandbox_competitors" (
    "id" TEXT NOT NULL,
    "run_id" TEXT NOT NULL,
    "url" TEXT NOT NULL,
    "domain" TEXT NOT NULL,
    "title" TEXT,
    "h1" TEXT,
    "aiSummary" TEXT,
    "full_text" TEXT,
    "source_type" TEXT NOT NULL DEFAULT 'competitor',
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "domain_type" TEXT DEFAULT 'editorial',

    CONSTRAINT "sandbox_competitors_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "sandbox_chunks" (
    "id" TEXT NOT NULL,
    "run_id" TEXT NOT NULL,
    "url" TEXT NOT NULL,
    "chunk_id" INTEGER NOT NULL,
    "text" TEXT NOT NULL,
    "summary" TEXT,
    "is_client" BOOLEAN NOT NULL DEFAULT false,
    "domain" TEXT,
    "source_type" TEXT NOT NULL DEFAULT 'competitor',
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "domain_type" TEXT DEFAULT 'editorial',

    CONSTRAINT "sandbox_chunks_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "sandbox_rag_results" (
    "id" TEXT NOT NULL,
    "run_id" TEXT NOT NULL,
    "question_id" TEXT NOT NULL,
    "question" TEXT NOT NULL,
    "answer" TEXT NOT NULL,
    "did_sandbox_appear" BOOLEAN NOT NULL DEFAULT false,
    "chunks_used" INTEGER NOT NULL DEFAULT 0,
    "confidence" DOUBLE PRECISION,
    "competitor_citations" TEXT[],
    "sandbox_citations" TEXT[],
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "business_competitor_citations" TEXT[],
    "authority_source_citations" TEXT[],

    CONSTRAINT "sandbox_rag_results_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "sandbox_scores" (
    "id" TEXT NOT NULL,
    "run_id" TEXT NOT NULL,
    "geo_score" DOUBLE PRECISION NOT NULL,
    "aeo_score" DOUBLE PRECISION NOT NULL,
    "citation_rate" DOUBLE PRECISION NOT NULL,
    "coverage" DOUBLE PRECISION,
    "competitor_dominance" DOUBLE PRECISION,
    "missing_content" TEXT[],
    "schema_gaps" TEXT[],
    "structured_data_ops" TEXT[],
    "recommendations" TEXT[],
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "sandbox_scores_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "job_events" (
    "id" TEXT NOT NULL,
    "event_id" TEXT NOT NULL,
    "run_id" TEXT NOT NULL,
    "step" TEXT NOT NULL,
    "status" TEXT NOT NULL,
    "payload" JSONB,
    "timestamp" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "job_events_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "PageRecord_url_key" ON "PageRecord"("url");

-- CreateIndex
CREATE UNIQUE INDEX "answer_metrics_answer_id_key" ON "answer_metrics"("answer_id");

-- CreateIndex
CREATE UNIQUE INDEX "sandbox_chunks_run_id_url_chunk_id_key" ON "sandbox_chunks"("run_id", "url", "chunk_id");

-- CreateIndex
CREATE UNIQUE INDEX "sandbox_scores_run_id_key" ON "sandbox_scores"("run_id");

-- CreateIndex
CREATE UNIQUE INDEX "job_events_event_id_key" ON "job_events"("event_id");

-- CreateIndex
CREATE INDEX "job_events_run_id_idx" ON "job_events"("run_id");

-- CreateIndex
CREATE INDEX "job_events_event_id_idx" ON "job_events"("event_id");

