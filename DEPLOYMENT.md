# Deployment Guide for Render

## ✅ Changes Made for Cloud Deployment

### 1. **Cloud-Friendly Logging**
All Python modules now log to **stdout** (console) instead of files:
- ✅ `ai/recommender.py`
- ✅ `ai/analyst.py`
- ✅ `ai/utils/comparison.py`

**Why?** Cloud platforms like Render have read-only filesystems or restricted write permissions. Logging to stdout allows Render to capture logs in its dashboard.

**Before:**
```python
logging.basicConfig(filename="ai/logs/ai.log", level=logging.INFO, ...)
```

**After:**
```python
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]  # Logs to console
)
```

### 2. **Complete Dependencies**
Added missing packages to `requirements.txt`:
- ✅ `scikit-learn==1.5.1` (for cosine_similarity)
- ✅ `numpy==1.26.4` (for array operations)

### 3. **Render Configuration**
Created `render.yaml` with deployment settings:
- Python 3.12.3
- Auto-install dependencies
- Start command: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
- Free tier configuration

---

## 🚀 How to Deploy on Render

### Step 1: Push to GitHub
```bash
# Make sure all changes are committed
git add .
git commit -m "Cloud-friendly logging and deployment config"
git push origin main
```

### Step 2: Create Render Account
1. Go to https://render.com
2. Sign up with GitHub (free)
3. Connect your GitHub account

### Step 3: Deploy Backend
1. Click **"New +"** → **"Web Service"**
2. Connect your GitHub repository: `ai-business-analyst`
3. Configure settings:
   - **Name:** `ai-business-analyst-api`
   - **Region:** Choose closest to you (e.g., Oregon)
   - **Branch:** `main`
   - **Root Directory:** Leave blank
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type:** `Free`

4. **Environment Variables** (add these):
   - `PYTHON_VERSION` = `3.12.3`
   - Add any other secrets (JWT keys, etc.) if needed

5. Click **"Create Web Service"**

### Step 4: Wait for Build
- Render will install dependencies (~3-5 minutes)
- Watch logs in real-time on Render dashboard
- Look for: `Application startup complete`

### Step 5: Get Your API URL
Once deployed, Render gives you a URL like:
```
https://ai-business-analyst-api.onrender.com
```

---

## 📝 Update Frontend for Production

After deployment, update your frontend API base URL:

**File:** `src/lib/axios.ts`
```typescript
const instance = axios.create({
  // Change from localhost to your Render URL
  baseURL: process.env.VITE_API_URL || "https://ai-business-analyst-api.onrender.com",
  // ...existing config
});
```

**Create `.env` file:**
```bash
VITE_API_URL=https://ai-business-analyst-api.onrender.com
```

---

## 🔍 Viewing Logs on Render

After deployment, you can view logs:
1. Go to your service dashboard
2. Click **"Logs"** tab
3. You'll see all stdout logs from your application:
   ```
   2025-10-29 03:47:52 - ai.recommender - INFO - Successfully loaded ai_tools.csv
   2025-10-29 03:47:52 - ai.analyst - INFO - Generated SWOT for 'Technology'
   ```

---

## ⚠️ Important Notes

### Free Tier Limitations:
- **Spins down after 15 minutes of inactivity**
  - First request after inactivity takes ~30-60 seconds (cold start)
  - Solution: Upgrade to paid tier ($7/month) for always-on service
  
- **750 hours/month free**
  - Good for testing and small projects
  
- **No persistent disk**
  - Database changes are lost on restart
  - Use external database (PostgreSQL on Render is free!)

### AI Model Considerations:
- Sentence-transformers model downloads on first startup (~90MB)
- Takes ~1-2 minutes on first deployment
- Model is cached in memory afterward
- On free tier, memory is limited (512MB)

### Database:
Your SQLite database (`db/aitugo.db`) will work but:
- Changes are lost when service restarts
- **Recommendation:** Use Render's free PostgreSQL database for production
  - Update `db/connections.py` to use PostgreSQL connection string
  - Render provides free PostgreSQL (256MB storage)

---

## 🧪 Testing Your Deployment

After deployment, test these endpoints:

```bash
# Replace with your Render URL
API_URL="https://ai-business-analyst-api.onrender.com"

# 1. Health check
curl $API_URL/

# 2. Get recommendations
curl "$API_URL/api/recommend?query=email%20marketing&top_k=3"

# 3. Get SWOT analysis
curl "$API_URL/api/analyze?user_role=Technology"

# 4. Compare tools
curl "$API_URL/api/compare?tools=Monica,MagicTrips"
```

---

## 🛠️ Troubleshooting

### Issue: "Address already in use"
**Solution:** Render sets the PORT environment variable. Make sure `api/main.py` uses it:
```python
import os
port = int(os.getenv("PORT", 8000))
uvicorn.run(app, host="0.0.0.0", port=port)
```

### Issue: "Module not found"
**Solution:** Verify all dependencies are in `requirements.txt`:
```bash
pip freeze > requirements.txt
```

### Issue: Slow cold starts
**Solution:** 
- Free tier limitation - upgrade to paid tier
- Or keep service warm with uptime monitoring (like UptimeRobot)

### Issue: Logs not appearing
**Solution:** Already fixed! We changed logging to stdout instead of files.

---

## 📊 Monitoring

Render provides:
- **Real-time logs** - See all stdout output
- **Metrics** - CPU, Memory, Request count
- **Alerts** - Email notifications for errors

---

## 🎯 Next Steps After Deployment

1. **Deploy Frontend** (Vite/React):
   - Use Vercel, Netlify, or Render Static Site
   - Update API URL to your Render backend
   
2. **Setup PostgreSQL** (Recommended):
   - Free on Render
   - Persistent data storage
   - Better for production
   
3. **Add Environment Variables**:
   - JWT secret keys
   - Database URLs
   - API keys (if any)
   
4. **Custom Domain** (Optional):
   - Link your own domain (e.g., `api.yourdomain.com`)
   - Free SSL included

---

## 📚 Resources

- [Render Python Docs](https://render.com/docs/deploy-fastapi)
- [Render Free Tier Limits](https://render.com/docs/free)
- [FastAPI Deployment Guide](https://fastapi.tiangolo.com/deployment/render/)
