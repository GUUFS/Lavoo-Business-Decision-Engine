# Platform Configuration Files

This directory contains deployment configuration examples for various cloud platforms.

## Available Platforms

- **Railway** → `railway.toml`
- **DigitalOcean** → `digitalocean.yaml`
- **Render** → `render.yaml`
- **Heroku** → `Procfile` and `runtime.txt`

## Usage

1. Choose your platform
2. Copy the relevant file(s) to the project root
3. Customize as needed
4. Deploy!

**Example:**
```bash
# For Railway
cp .platform-configs/railway.toml .

# For Render
cp .platform-configs/render.yaml .

# For Heroku
cp .platform-configs/Procfile .
cp .platform-configs/runtime.txt .
```

## Platform Comparison

| Platform | Setup Complexity | Free Tier | Best For |
|----------|------------------|-----------|----------|
| Railway | ⭐⭐ Easy | $5 credit/mo | Quick deploys |
| DigitalOcean | ⭐⭐⭐ Medium | $200 (60d) | Production apps |
| Render | ⭐ Easiest | ✅ Free | Testing/Dev |
| Heroku | ⭐⭐ Easy | ✅ Free Eco | Classic deployments |

See `DEPLOYMENT.md` for full deployment guides.
