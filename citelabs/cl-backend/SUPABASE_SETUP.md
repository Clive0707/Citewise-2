# Backend Supabase Setup Guide

This backend now uses **Supabase (PostgreSQL)** instead of local SQLite!

---

## 🔧 Setup Steps

### **1. Get Your Supabase Connection String**

Go to your Supabase Dashboard:
- **Dashboard → Settings → Database → Connection String**
- Select **"Connection Pooling"** (recommended for serverless/API usage)
- Copy the **PostgreSQL connection string**

It should look like:
```
postgresql://postgres.teojilugekycknjzwghi:[YOUR-PASSWORD]@aws-0-us-west-1.pooler.supabase.com:6543/postgres
```

**Important:** Replace `[YOUR-PASSWORD]` with your actual database password.

If you don't have your password, you can reset it in **Settings → Database → Database Password**.

---

### **2. Create `.env` File**

Create a file named `.env` in the `backend-ts/` directory:

```bash
cd backend-ts
cp env.example .env
```

Then edit `.env` and replace `[YOUR-PASSWORD]` with your actual password:

```env
DATABASE_URL="postgresql://postgres.teojilugekycknjzwghi:YOUR_ACTUAL_PASSWORD@aws-0-us-west-1.pooler.supabase.com:6543/postgres"
PYTHON_WORKERS_URL="http://localhost:8000"
```

---

### **3. Install Dependencies**

```bash
npm install
```

---

### **4. Generate Prisma Client**

This generates TypeScript types from your database schema:

```bash
npm run prisma:generate
```

---

### **5. Run Database Migration**

This will create the `PageRecord` table in your Supabase database:

```bash
npm run prisma:migrate
```

**Note:** The `citelabs_pages` table already exists (created by the Python workers), so Prisma will just add the additional `PageRecord` table if you want to use it for extra metadata.

---

### **6. Start the Backend**

```bash
npm run dev
```

The backend will now:
- ✅ Connect to Supabase (not local SQLite)
- ✅ Share the same database as the Python workers
- ✅ Have type-safe database access via Prisma

---

## 📊 Database Models

### **CitelabsPage Model**
Maps to the existing `citelabs_pages` table created by Python workers.
Used for vector embeddings and AI summaries.

### **PageRecord Model** (Optional)
Additional table for storing extra metadata like:
- SEO data (metaDescription, keywords)
- Structured headings
- Page purpose summaries

---

## 🔍 Testing the Connection

You can test if Prisma is connected by running:

```bash
npx prisma studio
```

This will open a web UI where you can browse your Supabase tables!

---

## 🚀 Next Steps

You can now use Prisma in any route:

```typescript
import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

// Type-safe queries!
const page = await prisma.pageRecord.findUnique({
  where: { url: 'https://example.com' }
})
```

Or use the pre-configured `pageStore` service:

```typescript
import { pageStore } from './services/pageStore'

const page = await pageStore.findByUrl('https://example.com')
```

---

## 🎯 Benefits

✅ **Single Database** - Backend and Workers share Supabase
✅ **Type Safety** - Full TypeScript autocomplete
✅ **Migrations** - Version-controlled schema changes
✅ **Production Ready** - No local SQLite files to worry about



Steps:

npx prisma db pull
npx prisma migrate deploy
npx prisma generate 
npm run dev