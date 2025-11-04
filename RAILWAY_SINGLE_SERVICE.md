# 🚂 Railway Single-Service Deployment Guide

## Your Deployment Setup

You deployed the **entire repository as ONE service** on Railway.

This means:
- ✅ Frontend (React) and Backend (FastAPI) run together
- ✅ Backend serves the built React app
- ✅ Backend also handles API requests
- ✅ Only ONE Railway service (not two separate ones)

## ⚠️ Build Error Fixed

**The Error You Saw:**
```
sh: 1: npm: not found
ERROR: failed to build
```

**What It Meant:** Railway was using Python environment but needed Node.js to build React.

**What We Fixed:** Created configuration files so Railway installs **both** Node.js and Python

---

## 🎯 What You Need to Do in Railway Dashboard

### **Step 1: Find Your Service URL**

1. Go to **Railway Dashboard**: https://railway.app/dashboard
2. Click on your project
3. Click on your **service** (the one you deployed)
4. Click **"Settings"** tab
5. Scroll to **"Domains"** section
6. You should see a URL like:
   ```
   https://ai-business-analyst-production-xxxx.up.railway.app
   ```
7. **Copy this URL** (you'll need it in Step 2)

---

### **Step 2: Set Environment Variables**

Still in your service, click **"Variables"** tab and add these:

#### **Variable 1: Frontend API URL**
```
Name:  VITE_APP_API_BASE_URL
Value: https://YOUR-RAILWAY-URL.up.railway.app
```
⚠️ **Replace** `YOUR-RAILWAY-URL.up.railway.app` with the URL you copied in Step 1!

**Example:**
```
VITE_APP_API_BASE_URL=https://ai-business-analyst-production-a1b2.up.railway.app
```

#### **Variable 2: Database URL** (if not already set)
```
Name:  DATABASE_URL
Value: postgresql://neondb_owner:npg_0btB2HXYhFvf@ep-crimson-bush-abi04jqe-pooler.eu-west-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require
```

---

### **Step 3: Configure Build Settings**

Click **"Settings"** tab and scroll down:

#### **Build Command:**
```bash
npm install && npm run build && pip install -r requirements.txt
```

Or use our custom script:
```bash
./railway-build.sh
```

#### **Start Command:**
```bash
uvicorn api.main:app --host 0.0.0.0 --port $PORT
```

⚠️ **Important:** Make sure to use `$PORT` (Railway's dynamic port variable)

---

### **Step 4: Trigger Redeploy**

After setting variables and build commands:

**Option A: Push to GitHub**
```bash
git add .
git commit -m "fix: configure for Railway single-service deployment"
git push
```

Railway will auto-deploy when it detects the push.

**Option B: Manual Redeploy**
1. Click **"Deployments"** tab
2. Click the three dots (⋮) on latest deployment
3. Click **"Redeploy"**

---

### **Step 5: Monitor Deployment**

1. Stay on **"Deployments"** tab
2. Click on the **running deployment**
3. Click **"View Logs"**
4. You should see:
   ```
   📦 Installing Node.js dependencies...
   ✅ Node dependencies installed

   🎨 Building React frontend...
   ✅ Frontend built to web/ directory

   🐍 Installing Python dependencies...
   ✅ Python dependencies installed

   INFO:     Application startup complete.
   ```

---

## 📊 How It Works

### **Build Phase:**
```
1. Railway clones your GitHub repo
2. Runs build command:
   - npm install (installs React dependencies)
   - npm run build (builds React → web/ folder)
   - pip install (installs Python dependencies)
```

### **Runtime Phase:**
```
3. Runs start command:
   - uvicorn starts FastAPI server
   - FastAPI serves:
     ✓ API endpoints (/api/*, /login, /signup, etc.)
     ✓ Static React app (from web/ directory)
```

### **Request Flow:**
```
User visits: https://your-railway-url.up.railway.app
  ↓
FastAPI receives request
  ↓
Routes to:
  - /api/* → API endpoints
  - /login → Login endpoint
  - /signup → Signup endpoint
  - /* → React app (index.html)
```

---

## ✅ Testing Your Deployment

### **Test 1: Health Check**

Visit in browser:
```
https://YOUR-RAILWAY-URL.up.railway.app/health
```

Should return:
```json
{
  "status": "healthy",
  "timestamp": "2025-11-04T...",
  "database": {
    "type": "postgresql",
    "connected": true
  },
  "version": "1.0.0"
}
```

✅ If you see this, backend is working!

---

### **Test 2: Frontend**

Visit in browser:
```
https://YOUR-RAILWAY-URL.up.railway.app
```

Should show your React app homepage.

✅ If you see your app, frontend is working!

---

### **Test 3: Login (The Critical One)**

1. Visit your Railway URL
2. Go to login page
3. **Open Browser Console (F12)**
4. **Click Network tab**
5. Try to login

**What you should see:**
```
✅ POST https://YOUR-RAILWAY-URL.up.railway.app/login
   Status: 200
```

**What you should NOT see:**
```
❌ POST http://localhost:8000/login
   ERR_CONNECTION_REFUSED
```

---

## 🐛 Troubleshooting

### **Issue 1: Still seeing localhost:8000 errors**

**Cause:** Frontend wasn't rebuilt with new environment variable

**Solution:**
1. Make sure `VITE_APP_API_BASE_URL` is set in Railway
2. Redeploy (Railway needs to rebuild frontend with new variable)
3. Clear browser cache
4. Hard refresh (Ctrl + Shift + R)

---

### **Issue 2: 404 Not Found on routes**

**Cause:** React router not configured properly

**Solution:**
Your `api/routes/index.py` already handles this - it serves React app for all routes.
Should work automatically.

---

### **Issue 3: Build fails**

**Check logs for:**

**"npm: command not found"**
- Railway can't find Node.js
- Make sure you have `package.json` in root

**"pip: command not found"**
- Railway can't find Python
- Make sure you have `requirements.txt` in root

**"No module named 'fastapi'"**
- Python packages not installed
- Check if `requirements.txt` exists

---

### **Issue 4: Port binding error**

**Error:** `Address already in use`

**Solution:**
Make sure start command uses `$PORT`:
```bash
uvicorn api.main:app --host 0.0.0.0 --port $PORT
```

NOT:
```bash
uvicorn api.main:app --port 8000  # ❌ Wrong for Railway
```

---

## 📋 Railway Dashboard Checklist

- [ ] Found my Railway URL
- [ ] Set `VITE_APP_API_BASE_URL` variable
- [ ] Set `DATABASE_URL` variable
- [ ] Configured build command
- [ ] Configured start command
- [ ] Triggered redeploy
- [ ] Checked deployment logs
- [ ] Tested /health endpoint
- [ ] Tested frontend loads
- [ ] Tested login (no localhost errors)
- [ ] Checked browser console (F12)

---

## 🎯 Expected Railway Variables

After configuration, your Variables tab should show:

```
┌────────────────────────────────────────────────────┐
│  Variables                                 + New   │
├────────────────────────────────────────────────────┤
│                                                    │
│  VITE_APP_API_BASE_URL                            │
│  https://ai-business-analyst-production-...       │
│                                                    │
│  DATABASE_URL                                      │
│  postgresql://neondb_owner:npg_0btB2...           │
│                                                    │
│  PORT (auto-set by Railway)                       │
│  $PORT                                             │
│                                                    │
└────────────────────────────────────────────────────┘
```

---

## 🚀 After Successful Deployment

Your app structure on Railway:

```
Your Railway URL (e.g., https://xyz.up.railway.app)
│
├── / → React App (homepage)
├── /login → React Login Page
├── /signup → React Signup Page
├── /analyze → React Analyzer Page
│
├── /api/recommend → AI Recommendations API
├── /api/analyze → Business Analysis API
├── /api/compare → Tool Comparison API
│
├── /health → Backend Health Check
└── /docs → FastAPI Auto-docs (Swagger)
```

---

## 📞 Need Help?

If deployment fails:

1. **Check Railway Logs**
   - Deployments → Click deployment → View Logs
   - Look for red error messages

2. **Check Browser Console**
   - F12 → Console tab
   - Look for errors

3. **Test Health Endpoint**
   - Visit `/health` endpoint
   - Should return healthy status

4. **Check Environment Variables**
   - Variables tab
   - Make sure `VITE_APP_API_BASE_URL` is correct

---

## 🎉 Success!

When everything works:
- ✅ `/health` returns healthy status
- ✅ Frontend loads at root URL
- ✅ Login works without localhost errors
- ✅ API endpoints respond correctly
- ✅ Database connection successful

---

**You're deploying ONE service that does EVERYTHING!** 🚂✨
