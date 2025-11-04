# Railway Deployment Guide

## Problem & Solution

### The Error You Encountered:
```
POST http://localhost:8000/login net::ERR_CONNECTION_REFUSED
```

**Cause**: Your frontend was trying to connect to `localhost:8000` (your local computer) instead of the Railway backend URL.

**Solution**: We've configured the app to use environment variables so it knows which backend to connect to.

---

## How It Works Now

### Local Development (Your Computer):
```
Frontend (localhost:3000) → Backend (localhost:8000)
```

### Production (Railway):
```
Frontend (Railway) → Backend (ai-business-analyst-api-production.up.railway.app)
```

---

## Railway Deployment Steps

### **Step 1: Set Environment Variables in Railway**

1. Go to your Railway project dashboard
2. Click on your **frontend service**
3. Go to **Variables** tab
4. Add this variable:

```
VITE_APP_API_BASE_URL=https://ai-business-analyst-api-production.up.railway.app
```

5. Click on your **backend service**
6. Go to **Variables** tab
7. Add this variable (already there probably):

```
DATABASE_URL=postgresql://neondb_owner:npg_0btB2HXYhFvf@ep-crimson-bush-abi04jqe-pooler.eu-west-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require
```

---

### **Step 2: Rebuild Your Frontend**

After setting environment variables:

1. In Railway dashboard, go to your **frontend service**
2. Click **Deployments** tab
3. Click the three dots (⋮) on the latest deployment
4. Click **Redeploy**

Or push a new commit:
```bash
git add .
git commit -m "fix: use environment variables for API URL"
git push
```

---

### **Step 3: Verify Deployment**

1. Wait for Railway to rebuild (takes 2-5 minutes)
2. Open your Railway frontend URL
3. Try logging in
4. Check browser console - should NOT see `localhost:8000` errors anymore

---

## Environment Variable Structure

### **Local Development** (`.env.local`):
```bash
VITE_APP_API_BASE_URL=http://localhost:8000
```

### **Production** (Railway Variables):
```bash
VITE_APP_API_BASE_URL=https://ai-business-analyst-api-production.up.railway.app
```

---

## Files We Fixed

1. **`src/api/authentication.ts`**
   - Changed: `fetch("http://localhost:8000/login")`
   - To: `fetch("${baseURL}/login")`
   - Now uses `VITE_APP_API_BASE_URL` environment variable

2. **`src/lib/fetch-helper.ts`**
   - Changed: `const BASE_URL = "http://localhost:8000"`
   - To: `const BASE_URL = import.meta.env.VITE_APP_API_BASE_URL`
   - Now uses environment variable

3. **`src/lib/axios.ts`**
   - Already correct! Uses `import.meta.env.VITE_APP_API_BASE_URL`

---

## How to Test Locally

```bash
# Terminal 1: Start backend
uvicorn api.main:app --reload --port 8000

# Terminal 2: Start frontend
npm run dev
```

Frontend will use `http://localhost:8000` automatically.

---

## How to Test Production Build Locally

```bash
# Build with production settings
npm run build

# Preview the build
npm run preview
```

This will use `.env.production` which points to Railway backend.

---

## Common Issues & Solutions

### Issue 1: CORS Errors
**Error**: `Access-Control-Allow-Origin`

**Solution**: Make sure your backend `api/main.py` has CORS enabled:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or specify your Railway frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

✅ Already configured in your code!

---

### Issue 2: 404 Not Found
**Error**: Routes return 404

**Solution**: Make sure Railway is serving the frontend correctly. Check `railway.toml` or build settings.

---

### Issue 3: Environment Variable Not Working
**Error**: Still connecting to localhost

**Solution**:
1. Clear browser cache
2. Rebuild in Railway (redeploy)
3. Make sure variable name is exactly: `VITE_APP_API_BASE_URL`

---

## Railway Setup Checklist

### Frontend Service:
- ✅ Environment variable: `VITE_APP_API_BASE_URL=https://ai-business-analyst-api-production.up.railway.app`
- ✅ Build command: `npm run build`
- ✅ Start command: `npm run preview` or serve the `dist` folder

### Backend Service:
- ✅ Environment variable: `DATABASE_URL` (Neon PostgreSQL)
- ✅ Start command: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
- ✅ Health check: `/health` endpoint

---

## Monitoring

### Check if services are running:

**Backend Health Check:**
```bash
curl https://ai-business-analyst-api-production.up.railway.app/health
```

Should return:
```json
{
  "status": "healthy",
  "timestamp": "...",
  "database": {
    "type": "postgresql",
    "connected": true
  }
}
```

**Frontend:**
Open in browser: `https://your-frontend-url.up.railway.app`

---

## Next Steps After Deployment

1. ✅ Test login functionality
2. ✅ Test signup functionality
3. ✅ Test AI analyzer features
4. ✅ Check database connections
5. ✅ Monitor logs in Railway dashboard

---

## For Collins

When you pull these changes:

```bash
# Install any new dependencies
npm install
pip install -r requirements.txt

# For local development, just run as usual:
uvicorn api.main:app --reload  # Backend
npm run dev                     # Frontend
```

The `.env.local` file will automatically use `localhost:8000` for local development!

---

## Questions?

If you see errors:
1. Check Railway logs (click on service → Logs)
2. Check browser console (F12)
3. Verify environment variables are set correctly
4. Make sure both services are deployed and running

**Current Railway URLs:**
- Backend: `https://ai-business-analyst-api-production.up.railway.app`
- Frontend: (You need to add this in Railway)

---

Good luck with deployment! 🚀
