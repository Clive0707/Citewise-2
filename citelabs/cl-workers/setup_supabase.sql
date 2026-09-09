-- ============================================
-- CiteLabs Supabase Vector Database Setup
-- ============================================
-- Run this SQL script in your Supabase SQL Editor:
-- https://supabase.com/dashboard/project/_/sql
--
-- This script will:
-- 1. Enable pgvector extension
-- 2. Create pages table with vector column
-- 3. Create vector similarity search function
-- 4. Create indexes for fast queries
-- ============================================

-- Step 1: Enable pgvector extension
-- This adds vector data type support to PostgreSQL
CREATE EXTENSION IF NOT EXISTS vector;

-- Step 2: Create the pages table
CREATE TABLE IF NOT EXISTS citelabs_pages (
    id BIGSERIAL PRIMARY KEY,
    url TEXT NOT NULL,
    content TEXT,
    ai_summary TEXT,
    page_type TEXT,
    is_client BOOLEAN DEFAULT false,
    embedding VECTOR(384),  -- 384 dimensions for bge-small-en-v1.5
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Step 3: Create index on URL for faster lookups
CREATE INDEX IF NOT EXISTS idx_citelabs_pages_url 
ON citelabs_pages(url);

-- Step 4: Create index on is_client for filtering
CREATE INDEX IF NOT EXISTS idx_citelabs_pages_is_client 
ON citelabs_pages(is_client);

-- Step 5: Create vector similarity index (HNSW for fast approximate search)
-- This dramatically speeds up vector similarity searches
CREATE INDEX IF NOT EXISTS idx_citelabs_pages_embedding 
ON citelabs_pages 
USING hnsw (embedding vector_cosine_ops);

-- Alternative: IVFFlat index (comment above and uncomment below if preferred)
-- IVFFlat is faster to build but slower to query than HNSW
-- CREATE INDEX IF NOT EXISTS idx_citelabs_pages_embedding 
-- ON citelabs_pages 
-- USING ivfflat (embedding vector_cosine_ops)
-- WITH (lists = 100);

-- Step 6: Create vector similarity search function
-- This function performs cosine similarity search
CREATE OR REPLACE FUNCTION match_pages(
    query_embedding VECTOR(384),
    match_threshold FLOAT DEFAULT 0.0,
    match_count INT DEFAULT 10
)
RETURNS TABLE (
    id BIGINT,
    url TEXT,
    content TEXT,
    ai_summary TEXT,
    page_type TEXT,
    is_client BOOLEAN,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        citelabs_pages.id,
        citelabs_pages.url,
        citelabs_pages.content,
        citelabs_pages.ai_summary,
        citelabs_pages.page_type,
        citelabs_pages.is_client,
        1 - (citelabs_pages.embedding <=> query_embedding) AS similarity
    FROM citelabs_pages
    WHERE 1 - (citelabs_pages.embedding <=> query_embedding) > match_threshold
    ORDER BY citelabs_pages.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Step 7: Create function to auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Step 8: Create trigger to auto-update updated_at
CREATE TRIGGER update_citelabs_pages_updated_at
    BEFORE UPDATE ON citelabs_pages
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- Verification Queries (optional - run to check)
-- ============================================

-- Check if pgvector extension is enabled
-- SELECT * FROM pg_extension WHERE extname = 'vector';

-- Check table structure
-- \d citelabs_pages;

-- Check indexes
-- SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'citelabs_pages';

-- Check if function exists
-- SELECT routine_name FROM information_schema.routines WHERE routine_name = 'match_pages';

-- ============================================
-- Test Query (after inserting data)
-- ============================================

-- Test vector search with a dummy embedding (384 dimensions of 0.1)
-- SELECT * FROM match_pages(
--     ARRAY[0.1,0.1,0.1,...]::vector(384),  -- Replace with actual embedding
--     0.0,  -- No threshold
--     5     -- Top 5 results
-- );

-- ============================================
-- Cleanup (DANGER - deletes all data!)
-- ============================================

-- Uncomment to drop everything (use with caution!)
-- DROP TRIGGER IF EXISTS update_citelabs_pages_updated_at ON citelabs_pages;
-- DROP FUNCTION IF EXISTS update_updated_at_column();
-- DROP FUNCTION IF EXISTS match_pages(VECTOR, FLOAT, INT);
-- DROP TABLE IF EXISTS citelabs_pages;
-- DROP EXTENSION IF EXISTS vector;

-- ============================================
-- Notes
-- ============================================
-- 1. Vector dimension (384) matches bge-small-en-v1.5 model
--    If you change embedding model, update dimension here
--
-- 2. HNSW index provides ~90% recall with 10x speed improvement
--    Adjust ef_construction and M parameters for speed/accuracy tradeoff
--
-- 3. Cosine similarity: 1 = identical, 0 = perpendicular, -1 = opposite
--    We use (1 - distance) to get similarity score
--
-- 4. Free tier limits:
--    - Supabase Free: 500MB database (plenty for embeddings)
--    - ~1M vectors of 384 dimensions = ~1.5GB
-- ============================================

