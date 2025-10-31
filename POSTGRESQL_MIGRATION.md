# PostgreSQL Migration Guide

## 🎯 Overview

This guide walks you through migrating from CSV/SQLite to PostgreSQL for production deployment.

---

## 📋 What Was Changed

### **New Files Created:**

1. **`db/pg_connections.py`** - PostgreSQL database connections
   - Auto-detects DATABASE_URL environment variable
   - Falls back to SQLite for local development
   - Handles connection pooling and lifecycle

2. **`db/pg_models.py`** - Database models
   - `User` model (migrated from old models.py)
   - `AITool` model (replaces CSV storage)
   - Pydantic models for API validation

3. **`ai/recommender_db.py`** - Database-powered recommender
   - Loads tools from PostgreSQL instead of CSV
   - Caches embeddings in memory
   - Singleton pattern for efficiency

4. **`ai/analyst_db.py`** - Database-powered SWOT analysis
   - Queries tools from database
   - Flexible search across multiple columns

5. **`ai/utils/comparison_db.py`** - Database-powered comparison
   - Compares tools from database
   - Feature inference from database fields

6. **`api/routes/ai_db.py`** - New API routes using database
   - All endpoints now query PostgreSQL
   - Added new endpoints: `/tools/search`, `/tools/{id}`

7. **`scripts/migrate_csv_to_db.py`** - Migration script
   - Imports CSV data into PostgreSQL
   - Handles data validation and transformation

### **Modified Files:**

1. **`api/main.py`**
   - Auto-detects PostgreSQL availability
   - Falls back to old CSV routes if PostgreSQL not available
   - Initializes database on startup

2. **`requirements.txt`**
   - Added `psycopg2-binary==2.9.9` for PostgreSQL

---

## 🚀 Migration Steps

### **Step 1: Install PostgreSQL Driver**

```bash
pip install psycopg2-binary==2.9.9
```

### **Step 2: Set Up PostgreSQL (Local Testing)**

#### **Option A: Using Render (Recommended for Production)**

1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click "New +" → "PostgreSQL"
3. Configure:
   - Name: `ai-business-analyst-db`
   - Database: `aitools`
   - User: `aitools_user`
   - Region: Same as your web service
   - Instance Type: Free
4. Click "Create Database"
5. Copy the "External Database URL" - looks like:
   ```
   postgresql://user:password@host:5432/database
   ```

#### **Option B: Local PostgreSQL (For Development)**

```bash
# Install PostgreSQL
sudo apt-get install postgresql postgresql-contrib  # Ubuntu/Debian
brew install postgresql  # macOS

# Start PostgreSQL
sudo service postgresql start  # Linux
brew services start postgresql  # macOS

# Create database
sudo -u postgres createdb aitools

# Create user
sudo -u postgres psql -c "CREATE USER aitools_user WITH PASSWORD 'your_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE aitools TO aitools_user;"
```

### **Step 3: Set Environment Variable**

```bash
# Create .env file
echo 'DATABASE_URL=postgresql://aitools_user:your_password@localhost:5432/aitools' > .env

# Or export directly
export DATABASE_URL=postgresql://aitools_user:your_password@localhost:5432/aitools
```

### **Step 4: Run Migration Script**

```bash
# Make script executable
chmod +x scripts/migrate_csv_to_db.py

# Run migration
python scripts/migrate_csv_to_db.py
```

**Expected Output:**
```
======================================================================
🚀 AI Tools CSV to PostgreSQL Migration
======================================================================

📊 Database: postgresql
   Connection: localhost:5432/aitools

📂 Loading CSV from: /path/to/ai/data/ai_tools.csv
✓ Loaded 136 tools from CSV
  Columns: main_category, sub_category, url, name, ...

🔨 Creating database tables...
✓ Database tables created successfully

🔄 Importing tools to database...
  ✓ Committed 50 tools...
  ✓ Committed 100 tools...

✅ Import complete!
   Imported: 136 tools
   Skipped: 0 tools (already exist)

🔍 Verifying import...
  Tools in database: 136
  ✅ Verification passed!

📋 Sample tools:
  • MagicTrips (AI Productivity Tools) - Rating: 0.0
  • Monica (AI Productivity Tools) - Rating: 3.86
  • You (AI Productivity Tools) - Rating: 0.0
  • Jigso (AI Productivity Tools) - Rating: 4.6
  • SoBrief (AI Productivity Tools) - Rating: 5.0

======================================================================
✅ Migration completed successfully!
======================================================================
```

### **Step 5: Test the Application**

```bash
# Start the server
uvicorn api.main:app --reload --port 8000
```

**Check startup logs:**
```
INFO:     Started server process
INFO:root:✓ Database initialized: postgresql
INFO:root:✓ Using PostgreSQL-based AI routes
INFO:     Application startup complete.
```

**Test endpoints:**
```bash
# Test recommendations
curl "http://localhost:8000/api/recommend?query=travel&top_k=3"

# Test SWOT analysis
curl "http://localhost:8000/api/analyze?user_role=entrepreneur"

# Test comparison
curl "http://localhost:8000/api/compare?tools=Monica,MagicTrips"

# Test search (new endpoint!)
curl "http://localhost:8000/api/tools/search?query=travel&limit=5"
```

---

## 🔄 How It Works

### **Automatic Fallback System:**

The code automatically detects which database to use:

```python
# In api/main.py
try:
    from db.pg_connections import engine  # Try PostgreSQL
    from api.routes import ai_db as ai
    logger.info("✓ Using PostgreSQL")
except ImportError:
    from db.connections import engine  # Fallback to SQLite
    from api.routes import ai
    logger.info("⚠️ Using CSV/SQLite (fallback)")
```

### **Development vs Production:**

| Environment | Database | Data Source | Config |
|------------|----------|-------------|--------|
| **Local** (no DATABASE_URL) | SQLite | CSV files | Auto |
| **Local** (with DATABASE_URL) | PostgreSQL | Database | Manual |
| **Render** (with DATABASE_URL) | PostgreSQL | Database | Auto |

---

## 📊 Database Schema

### **Users Table:**
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    confirm_password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);
```

### **AI Tools Table:**
```sql
CREATE TABLE ai_tools (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    url VARCHAR(500),
    description TEXT NOT NULL,
    summary TEXT,
    main_category VARCHAR(255),
    sub_category VARCHAR(255),
    ai_categories TEXT,
    pricing TEXT,
    ratings FLOAT DEFAULT 0.0,
    key_features TEXT,
    pros TEXT,
    cons TEXT,
    who_should_use TEXT,
    compatibility_integration TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Indexes for performance
CREATE INDEX idx_ai_tools_name ON ai_tools(name);
CREATE INDEX idx_ai_tools_category ON ai_tools(main_category);
CREATE INDEX idx_ai_tools_subcategory ON ai_tools(sub_category);
```

---

## 🚀 Deploying to Render

### **Step 1: Create PostgreSQL Database on Render**

1. Dashboard → New + → PostgreSQL
2. Free tier settings
3. Copy "External Database URL"

### **Step 2: Add Environment Variable to Web Service**

1. Go to your web service settings
2. Environment → Add Environment Variable
3. Key: `DATABASE_URL`
4. Value: `postgresql://user:pass@host:5432/db` (from Step 1)
5. Save Changes

### **Step 3: Deploy**

Render will automatically:
1. Install `psycopg2-binary`
2. Detect `DATABASE_URL`
3. Use PostgreSQL routes
4. Initialize database tables

### **Step 4: Migrate Data**

**Option A: Run migration via Render Shell**
```bash
# In Render dashboard → Shell
python scripts/migrate_csv_to_db.py
```

**Option B: Run locally against Render database**
```bash
# Set Render's DATABASE_URL locally
export DATABASE_URL="postgresql://user:pass@host.render.com:5432/db"

# Run migration
python scripts/migrate_csv_to_db.py
```

---

## ✅ Verification Checklist

After migration, verify:

- [ ] Database tables created (`users`, `ai_tools`)
- [ ] 136 tools imported from CSV
- [ ] API endpoints return data from database
- [ ] Recommendations work (embeddings generated)
- [ ] SWOT analysis works
- [ ] Tool comparison works
- [ ] User authentication works
- [ ] Frontend connects successfully

---

## 🔧 Troubleshooting

### **Issue: "No tools found in database"**

**Solution:** Run migration script
```bash
python scripts/migrate_csv_to_db.py
```

### **Issue: "ModuleNotFoundError: No module named 'psycopg2'"**

**Solution:** Install PostgreSQL driver
```bash
pip install psycopg2-binary
```

### **Issue: "Connection refused" on Render**

**Solution:** Check DATABASE_URL format
- Render provides: `postgres://...`
- Code auto-converts to: `postgresql://...`
- Verify environment variable is set

### **Issue: "Embeddings not loading"**

**Solution:** Recommender caches embeddings on first request
- First request takes ~30 seconds (downloads model)
- Subsequent requests are fast
- On Render free tier, memory resets after inactivity

---

## 🎯 Benefits of PostgreSQL Migration

### **Before (CSV):**
- ❌ Can't update tools without redeploying
- ❌ No user-generated data (favorites, history)
- ❌ Slower search (loads entire CSV)
- ❌ No data relationships

### **After (PostgreSQL):**
- ✅ Update tools via API or admin panel
- ✅ Store user favorites, search history
- ✅ Fast indexed searches
- ✅ Relationships (users ↔ favorite tools)
- ✅ Production-ready scalability
- ✅ Free 256MB database on Render

---

## 📝 Next Steps

1. **Add Admin Panel** - Manage tools via web interface
2. **User Features** - Save favorites, search history
3. **Analytics** - Track popular tools, searches
4. **Caching** - Redis for faster responses
5. **Full-Text Search** - PostgreSQL's text search

---

## 🆘 Need Help?

- Check logs: Render Dashboard → Logs
- Test locally first with SQLite
- Run migration in stages (10 tools at a time)
- Contact support with error logs

---

**Migration Complete! Your app now uses PostgreSQL! 🎉**
