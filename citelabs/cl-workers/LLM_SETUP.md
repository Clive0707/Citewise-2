# LLM Provider Setup Guide

CiteLabs supports multiple LLM backends:
- **Ollama** (default): Local, free, no API key needed
- **Gemini**: Cloud, Google's API, free tier available

Switch between them using the `LLM_PROVIDER` environment variable.

---

## 🚀 Quick Start

### Option 1: Ollama (Default - Local)

Ollama is used by default. Requires Ollama installed locally.

```bash
# .env file
LLM_PROVIDER=ollama
OLLAMA_MODEL=llama3.1
```

**Installation:**
```bash
# Install Ollama (macOS)
brew install ollama

# Or download from: https://ollama.ai/

# Pull the model
ollama pull llama3.1
```

**Pros:**
- ✅ 100% free
- ✅ Runs locally (private)
- ✅ No API keys needed
- ✅ No internet required (after model download)
- ✅ No rate limits

**Cons:**
- ❌ Requires ~5GB disk space per model
- ❌ Slower than cloud APIs (depends on hardware)
- ❌ Requires Ollama installation

---

### Option 2: Gemini (Cloud - Google API)

Google's Gemini API - fast, powerful, generous free tier.

#### Step 1: Get API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Click **"Get API Key"**
3. Create new API key or use existing project
4. Copy the API key

#### Step 2: Configure Environment

Update your `.env` file:

```bash
# LLM Provider
LLM_PROVIDER=gemini

# Gemini Config
GEMINI_API_KEY=your-api-key-here
GEMINI_MODEL=gemini-1.5-flash
```

#### Step 3: Restart Workers

```bash
cd /Users/chrisdias/Desktop/Java/Personal_Learning/CiteLabs_new/workers-py
source env/bin/activate
uvicorn app.main:app --reload --port 8001
```

**Pros:**
- ✅ Very fast (~1-2 seconds)
- ✅ No local resources needed
- ✅ Latest models from Google
- ✅ Generous free tier (60 req/min, 1500 req/day)
- ✅ No installation required

**Cons:**
- ❌ Requires internet
- ❌ Requires API key
- ❌ Rate limits (free tier)
- ❌ Data sent to Google

---

## 🔄 Switching Between Providers

Simply change the environment variable and restart:

```bash
# Use Ollama (local)
LLM_PROVIDER=ollama

# Use Gemini (cloud)
LLM_PROVIDER=gemini
```

No code changes needed! The abstraction layer handles everything.

---

## 🏗️ Architecture

```
app/llm.py
    ↓
llm_provider.get_llm_provider()
    ↓
    ├─→ llm_ollama.py     (if LLM_PROVIDER=ollama)
    │   └─→ subprocess → ollama run llama3.1
    │
    └─→ llm_gemini.py     (if LLM_PROVIDER=gemini)
        └─→ Google Gemini API
```

### Files Added:
- `app/llm_provider.py` - Abstract base class and factory
- `app/llm_ollama.py` - Ollama implementation (refactored)
- `app/llm_gemini.py` - Gemini implementation (new)

### Files Modified:
- `app/llm.py` - Uses abstraction instead of direct Ollama calls
- `requirements.txt` - Added `google-generativeai==0.8.3`
- `.env` - Added LLM provider configuration
- `.env.example` - Added LLM configuration documentation

### No Changes:
- `app/crawl.py` - Still calls `generate_llm_summary()` (unchanged API)
- `app/simulation.py` - Still calls `call_llm()` (unchanged API)
- `app/schema.py` - Unchanged

---

## 📊 Comparison

| Feature | Ollama | Gemini |
|---------|--------|--------|
| **Cost** | Free | Free tier (then paid) |
| **Speed** | Medium-Slow | Very Fast |
| **Privacy** | 100% local | Sent to Google |
| **Setup** | Requires install | Just API key |
| **Internet** | Not needed | Required |
| **Rate Limits** | None | 60/min, 1500/day |
| **Quality** | Good | Excellent |
| **Disk Space** | ~5GB | None |

---

## 🎯 Where LLM is Used

| Location | Function | Purpose |
|----------|----------|---------|
| `crawl.py` line 228 | `generate_llm_summary(text, short=False)` | Page purpose summary (2-3 sentences) |
| `crawl.py` line 235 | `generate_llm_summary(text, short=True)` | AI summary (18-40 words) |
| `simulation.py` line 248 | `call_llm(prompt)` | Explain ranking reasoning |
| `simulation.py` line 259 | `call_llm(prompt)` | Suggest SEO fixes |

---

## 🔧 Model Options

### Ollama Models

```bash
# List available models
ollama list

# Pull different models
ollama pull llama3.2        # Latest Llama
ollama pull mistral         # Mistral 7B
ollama pull codellama       # Code-focused
ollama pull mixtral         # Mixtral 8x7B
```

Update `.env`:
```bash
OLLAMA_MODEL=llama3.2
```

### Gemini Models

Available models:
- **`gemini-1.5-flash`** (recommended): Fast, cheap, good quality
- **`gemini-1.5-pro`**: More capable, slower, more expensive
- **`gemini-2.0-flash-exp`**: Latest experimental (may be unstable)

Update `.env`:
```bash
GEMINI_MODEL=gemini-1.5-pro
```

---

## 🧪 Testing

### Test Ollama

```bash
# 1. Ensure Ollama is running
ollama list

# 2. Set environment
# .env: LLM_PROVIDER=ollama

# 3. Start workers
uvicorn app.main:app --reload --port 8001

# 4. Check logs
# Should see: "Using Ollama LLM provider (local)"
```

### Test Gemini

```bash
# 1. Set environment
# .env: LLM_PROVIDER=gemini

# 2. Start workers
uvicorn app.main:app --reload --port 8001

# 3. Check logs
# Should see: "Using Gemini LLM provider"
# Should see: "Initialized Gemini provider with model: gemini-1.5-flash"
```

### Test from Frontend

1. Start all services (workers, backend, frontend)
2. Go to http://localhost:3001
3. Crawl a URL - check if AI summaries are generated
4. Run simulation - check if reasoning and fixes are provided

---

## 🐛 Troubleshooting

### Ollama Issues

**Error: "command not found: ollama"**
- **Solution**: Install Ollama: `brew install ollama` or download from https://ollama.ai/

**Error: "model 'llama3.1' not found"**
- **Solution**: Pull the model: `ollama pull llama3.1`

**Error: "connection refused"**
- **Solution**: Start Ollama service: `ollama serve`

### Gemini Issues

**Error: "GEMINI_API_KEY environment variable must be set"**
- **Solution**: Add API key to `.env` file

**Error: "403 Forbidden" or "API key not valid"**
- **Solution**: 
  - Get new API key from https://makersuite.google.com/app/apikey
  - Check for typos in `.env` file
  - Restart workers after updating `.env`

**Error: "429 Resource Exhausted"**
- **Solution**: Rate limit exceeded
  - Free tier: 60 requests/minute
  - Wait 1 minute or upgrade to paid tier

**Error: "Invalid model name"**
- **Solution**: Use valid model name:
  - `gemini-1.5-flash` (recommended)
  - `gemini-1.5-pro`
  - `gemini-2.0-flash-exp`

---

## 💰 Pricing

### Ollama
- **Cost**: $0 (free forever)
- **Hardware**: Uses your computer's CPU/GPU
- **Models**: All free (llama, mistral, etc.)

### Gemini
- **Free Tier**: 
  - 60 requests/minute
  - 1,500 requests/day
  - Generous for development

- **Paid Tier** (if you exceed free tier):
  - `gemini-1.5-flash`: $0.075 per 1M input tokens, $0.30 per 1M output tokens
  - `gemini-1.5-pro`: $1.25 per 1M input tokens, $5.00 per 1M output tokens

**Estimated Cost for CiteLabs:**
- Average crawl: ~4-6 API calls (2 summaries in crawl + 2-4 in simulation)
- ~250-375 crawls per day on free tier
- Very affordable even on paid tier

---

## 🚀 Adding More Providers (Future)

The abstraction makes it easy to add more providers:

### Examples:
- **OpenAI GPT-4** - Add `llm_openai.py`
- **Anthropic Claude** - Add `llm_anthropic.py`
- **AWS Bedrock** - Add `llm_bedrock.py`
- **Azure OpenAI** - Add `llm_azure.py`

Just implement the `LLMProvider` interface!

---

## 📝 Environment Variables Reference

```bash
# LLM Provider Selection
LLM_PROVIDER=ollama              # or "gemini"

# Ollama Config (if provider=ollama)
OLLAMA_MODEL=llama3.1            # Model name

# Gemini Config (if provider=gemini)
GEMINI_API_KEY=your-api-key      # Get from Google AI Studio
GEMINI_MODEL=gemini-1.5-flash    # Model name

# General Settings (all providers)
LLM_MAX_CONTENT_CHARS=6000       # Max input length
```

---

## ✨ Summary

- ✅ **Ollama**: Free, local, private (default)
- ✅ **Gemini**: Fast, cloud, generous free tier
- ✅ **Easy switching**: Just change environment variable
- ✅ **Extensible**: Easy to add more providers
- ✅ **No breaking changes**: Existing code unchanged

**Your Gemini API key is already configured!**  
Just change `LLM_PROVIDER=gemini` to test it! 🚀





