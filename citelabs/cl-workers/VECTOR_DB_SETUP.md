# Vector Database Setup Guide

CiteLabs supports two vector database backends:
- **FAISS** (default): Local, in-memory, no persistence
- **Supabase**: Cloud, persistent, with caching

Switch between them using the `VECTOR_DB_PROVIDER` environment variable.

---

## 🚀 Quick Start

### Option 1: FAISS (Default - No Setup Required)

FAISS is used by default. No configuration needed!

```bash
# .env file (or leave empty)
VECTOR_DB_PROVIDER=faiss
```

**Pros:**
- ✅ Zero setup
- ✅ No external dependencies
- ✅ Fast for small datasets
- ✅ Free

**Cons:**
- ❌ No persistence (rebuilds every query)
- ❌ In-memory only
- ❌ Not suitable for production at scale

---

### Option 2: Supabase (Persistent, Cloud-Based)

#### Step 1: Create Supabase Project

1. Go to [https://supabase.com](https://supabase.com)
2. Sign up / Log in
3. Click **"New Project"**
4. Choose:
   - **Organization**: Personal or create new
   - **Project Name**: `citelabs` (or your choice)
   - **Database Password**: Generate strong password (save it!)
   - **Region**: Choose closest to you
   - **Pricing Plan**: Free tier is fine

#### Step 2: Run SQL Setup Script

1. Open your Supabase project dashboard
2. Go to **SQL Editor** (left sidebar)
3. Click **"New Query"**
4. Copy entire contents of `setup_supabase.sql`
5. Paste and click **"Run"**
6. Verify success (should see "Success. No rows returned")

#### Step 3: Get API Credentials

1. In Supabase dashboard, go to **Settings** → **API**
2. Copy:
   - **Project URL** (e.g., `https://xxxxx.supabase.co`)
   - **anon/public key** (long JWT token)

#### Step 4: Configure Environment

Update your `.env` file:

```bash
# Vector Database
VECTOR_DB_PROVIDER=supabase

# Supabase Credentials
SUPABASE_URL=https://teojilugekycknjzwghi.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### Step 5: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs `supabase==2.3.4` (already added to requirements.txt).

#### Step 6: Test It!

Restart your worker server:

```bash
uvicorn app.main:app --reload --port 8001
```

Run a simulation - vectors will now persist in Supabase!

---

## 🔄 Switching Between Backends

Simply change the environment variable:

```bash
# Use local FAISS
VECTOR_DB_PROVIDER=faiss

# Use cloud Supabase
VECTOR_DB_PROVIDER=supabase
```

No code changes needed! The abstraction layer handles everything.

---

## 🏗️ Architecture

```
simulation.py
    ↓
vector_store.py (abstraction)
    ↓
    ├─→ vector_faiss.py     (if VECTOR_DB_PROVIDER=faiss)
    └─→ vector_supabase.py  (if VECTOR_DB_PROVIDER=supabase)
```

### Files Added:
- `app/vector_store.py` - Abstract base class and factory
- `app/vector_faiss.py` - FAISS implementation (refactored)
- `app/vector_supabase.py` - Supabase implementation (new)
- `setup_supabase.sql` - Database schema and functions
- `.env.example` - Configuration template

### Files Modified:
- `app/simulation.py` - Uses abstraction instead of direct FAISS
- `requirements.txt` - Added `supabase==2.3.4`

---

## 📊 Comparison

| Feature | FAISS | Supabase |
|---------|-------|----------|
| **Setup** | None | 5 minutes |
| **Cost** | Free | Free (up to 500MB) |
| **Speed** | Very fast | Fast (~100ms) |
| **Persistence** | ❌ No | ✅ Yes |
| **Caching** | ❌ No | ✅ Yes |
| **Production Ready** | Small scale | ✅ Yes |
| **Requires Internet** | ❌ No | ✅ Yes |
| **Vector Limit** | RAM-limited | ~1M vectors (free) |

---

## 🧪 Testing

### Test FAISS

```bash
# .env
VECTOR_DB_PROVIDER=faiss

# Start server
uvicorn app.main:app --reload --port 8001

# Run simulation from frontend
# Check logs: "Using FAISS vector store (in-memory)"
```

### Test Supabase

```bash
# .env
VECTOR_DB_PROVIDER=supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-key-here

# Start server
uvicorn app.main:app --reload --port 8001

# Run simulation from frontend
# Check logs: "Using Supabase vector store"

# Verify in Supabase:
# Go to Table Editor → citelabs_pages
# Should see rows inserted!
```

---

## 🐛 Troubleshooting

### "SUPABASE_URL and SUPABASE_KEY environment variables must be set"

**Solution**: 
- Make sure `.env` file exists
- Check variables are set correctly
- Restart worker server after changing `.env`

### "relation 'citelabs_pages' does not exist"

**Solution**: 
- Run `setup_supabase.sql` in Supabase SQL Editor
- Verify table exists in **Table Editor**

### "function match_pages does not exist"

**Solution**: 
- Rerun `setup_supabase.sql` (safe to run multiple times)
- Check **Database** → **Functions** for `match_pages`

### Slow Supabase queries

**Solution**: 
- Check index exists: `idx_citelabs_pages_embedding`
- May take time to build index on first run
- HNSW index builds incrementally

### "Connection refused" to Supabase

**Solution**: 
- Check internet connection
- Verify `SUPABASE_URL` is correct (should include https://)
- Check Supabase project is not paused (free tier auto-pauses after inactivity)

---

## 🔒 Security Notes

1. **API Key**: We use `anon` key (safe for client-side)
   - Row Level Security (RLS) not enabled by default
   - For production, enable RLS on `citelabs_pages` table

2. **.env File**: Never commit to Git!
   - Already in `.gitignore`
   - Use `.env.example` as template

3. **Supabase Free Tier**:
   - 500MB database storage
   - Plenty for embeddings (1M vectors ≈ 1.5GB theoretical)
   - Project pauses after 1 week inactivity

---

## 📈 Performance Tips

### FAISS
- Fast for < 10,000 vectors
- Rebuilds index on every query (acceptable for small datasets)
- No network latency

### Supabase
- Slightly slower first query (cold start)
- Much faster subsequent queries (caching)
- Best for persistent data / production
- Enable connection pooling for high traffic

---

## 🚀 Next Steps

### Optional Enhancements

1. **Add TTL (Time to Live)**
   - Delete old vectors after X days
   - Prevent stale data

2. **Add Deduplication**
   - Check if URL already crawled recently
   - Skip re-crawling if content fresh

3. **Add Hybrid Search**
   - Combine vector search + keyword search
   - Better accuracy

4. **Add Batch Operations**
   - Insert multiple vectors in single transaction
   - Better performance

5. **Add Monitoring**
   - Track vector store performance
   - Log query times

---

## 📚 Resources

- [Supabase Vector Search Docs](https://supabase.com/docs/guides/ai/vector-columns)
- [pgvector GitHub](https://github.com/pgvector/pgvector)
- [FAISS Documentation](https://github.com/facebookresearch/faiss/wiki)
- [SentenceTransformers Models](https://www.sbert.net/docs/pretrained_models.html)

---

## ❓ Questions?

If you encounter issues:
1. Check logs in worker terminal
2. Verify `.env` configuration
3. Test SQL queries in Supabase SQL Editor
4. Check this guide's troubleshooting section

Happy vector searching! 🎯




