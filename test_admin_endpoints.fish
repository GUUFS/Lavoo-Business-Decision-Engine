#!/usr/bin/env fish

# Admin Backend API Testing Script (Fish Shell Compatible)
# Tests all 11 admin endpoints

set BASE_URL "http://localhost:8000"
echo "🚀 Testing Admin Backend API Endpoints"
echo "========================================"
echo ""

# Login credentials
set ADMIN_EMAIL "admin@gmail.com"
echo "📝 Using admin account: $ADMIN_EMAIL"
echo "Enter admin password:"
read -s ADMIN_PASSWORD

# Step 1: Get JWT token
echo ""
echo "Getting admin JWT token..."
set LOGIN_RESPONSE (curl -s -X POST "$BASE_URL/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$ADMIN_EMAIL\",\"password\":\"$ADMIN_PASSWORD\"}")

set TOKEN (echo $LOGIN_RESPONSE | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

if test -z "$TOKEN"
    echo "❌ Failed to get admin token. Response:"
    echo "$LOGIN_RESPONSE"
    exit 1
end

echo "✅ Admin token obtained: "(string sub -l 20 $TOKEN)"..."
echo ""

# ============================================
# CONTENT MANAGEMENT ENDPOINTS (6 endpoints)
# ============================================
echo "📊 Testing Content Management Endpoints"
echo "----------------------------------------"

# Test 1: Create Insight
echo "1️⃣  POST /admin/content/insights"
set CREATE_INSIGHT (curl -s -X POST "$BASE_URL/admin/content/insights" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Insight - GPT-5 Breakthrough",
    "category": "AI Research",
    "read_time": "3 min",
    "what_changed": "OpenAI announces GPT-5 with revolutionary reasoning capabilities",
    "why_it_matters": "This exceeds human performance on complex tasks and could transform how we use AI",
    "action_to_take": "Explore GPT-5 API and test it for your business use cases",
    "source": "Admin Test",
    "date": "2025-12-11"
  }')

if echo "$CREATE_INSIGHT" | grep -q '"id"'
    set INSIGHT_ID (echo $CREATE_INSIGHT | grep -o '"id":[0-9]*' | cut -d':' -f2)
    echo "   ✅ Created insight ID: $INSIGHT_ID"
else
    echo "   ❌ Failed: $CREATE_INSIGHT"
end
echo ""

# Test 2: Create Alert
echo "2️⃣  POST /admin/content/alerts"
set CREATE_ALERT (curl -s -X POST "$BASE_URL/admin/content/alerts" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Alert - New Feature Released",
    "category": "Product Update",
    "priority": "high",
    "score": 85,
    "time_remaining": "24 hours",
    "why_act_now": "Early adopters get priority support and exclusive tutorials",
    "potential_reward": "2x efficiency gain in business analysis workflows",
    "action_required": "Upgrade to premium and try bulk analysis feature",
    "source": "Admin Test",
    "date": "2025-12-11"
  }')

if echo "$CREATE_ALERT" | grep -q '"id"'
    set ALERT_ID (echo $CREATE_ALERT | grep -o '"id":[0-9]*' | cut -d':' -f2)
    echo "   ✅ Created alert ID: $ALERT_ID"
else
    echo "   ❌ Failed: $CREATE_ALERT"
end
echo ""

# Test 3: Create Trend
echo "3️⃣  POST /admin/content/trends"
set CREATE_TREND (curl -s -X POST "$BASE_URL/admin/content/trends" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Trend - AI Video Editing Explosion",
    "industry": "Content Creation",
    "description": "AI-powered video editing tools are seeing 300% growth in adoption among content creators. Tools like Runway and Descript leading the charge.",
    "engagement": "25000",
    "growth": "300.5%",
    "viral_score": 92,
    "search_volume": "75000",
    "peak_time": "2025-12",
    "competition": "medium",
    "opportunity": "high",
    "nature": "growing",
    "hashtags": ["AIvideo", "VideoAI", "AutoEdit"],
    "platforms": ["TikTok", "Instagram", "YouTube"],
    "action_items": "1. Research top AI video tools\n2. Create comparison guide\n3. Test free tier options"
  }')

if echo "$CREATE_TREND" | grep -q '"id"'
    set TREND_ID (echo $CREATE_TREND | grep -o '"id":[0-9]*' | cut -d':' -f2)
    echo "   ✅ Created trend ID: $TREND_ID"
else
    echo "   ❌ Failed: $CREATE_TREND"
end
echo ""

# Test 4: Get Recent Insights
echo "4️⃣  GET /admin/content/insights?limit=5"
set GET_INSIGHTS (curl -s -X GET "$BASE_URL/admin/content/insights?limit=5" \
  -H "Authorization: Bearer $TOKEN")

if echo "$GET_INSIGHTS" | grep -q '"insights"'
    set INSIGHT_COUNT (echo $GET_INSIGHTS | grep -o '"id":[0-9]*' | wc -l)
    echo "   ✅ Retrieved $INSIGHT_COUNT insight(s)"
else
    echo "   ❌ Failed: $GET_INSIGHTS"
end
echo ""

# Test 5: Get Recent Alerts
echo "5️⃣  GET /admin/content/alerts?limit=5"
set GET_ALERTS (curl -s -X GET "$BASE_URL/admin/content/alerts?limit=5" \
  -H "Authorization: Bearer $TOKEN")

if echo "$GET_ALERTS" | grep -q '"alerts"'
    set ALERT_COUNT (echo $GET_ALERTS | grep -o '"id":[0-9]*' | wc -l)
    echo "   ✅ Retrieved $ALERT_COUNT alert(s)"
else
    echo "   ❌ Failed: $GET_ALERTS"
end
echo ""

# Test 6: Get Recent Trends
echo "6️⃣  GET /admin/content/trends?limit=5"
set GET_TRENDS (curl -s -X GET "$BASE_URL/admin/content/trends?limit=5" \
  -H "Authorization: Bearer $TOKEN")

if echo "$GET_TRENDS" | grep -q '"trends"'
    set TREND_COUNT (echo $GET_TRENDS | grep -o '"id":[0-9]*' | wc -l)
    echo "   ✅ Retrieved $TREND_COUNT trend(s)"
else
    echo "   ❌ Failed: $GET_TRENDS"
end
echo ""

# ============================================
# AI ANALYSIS MONITORING ENDPOINTS (3 endpoints)
# ============================================
echo "🧠 Testing AI Analysis Monitoring Endpoints"
echo "--------------------------------------------"

# Test 7: Get Analyses with Pagination
echo "7️⃣  GET /admin/analyses?page=1&limit=5&status=all&type=all"
set GET_ANALYSES (curl -s -X GET "$BASE_URL/admin/analyses?page=1&limit=5&status=all&type=all" \
  -H "Authorization: Bearer $TOKEN")

if echo "$GET_ANALYSES" | grep -q '"analyses"'
    set TOTAL_ANALYSES (echo $GET_ANALYSES | grep -o '"total":[0-9]*' | cut -d':' -f2)
    set COMPLETION_RATE (echo $GET_ANALYSES | grep -o '"avg_confidence":[0-9.]*' | cut -d':' -f2)
    echo "   ✅ Retrieved analyses. Total in DB: $TOTAL_ANALYSES"
    echo "   Avg Confidence: $COMPLETION_RATE"
else
    echo "   ❌ Failed: $GET_ANALYSES"
end
echo ""

# Test 8: Get Analysis Types
echo "8️⃣  GET /admin/analysis-types"
set GET_TYPES (curl -s -X GET "$BASE_URL/admin/analysis-types" \
  -H "Authorization: Bearer $TOKEN")

if echo "$GET_TYPES" | grep -q '"types"'
    set TYPE_COUNT (echo $GET_TYPES | grep -o '"analysis_type"' | wc -l)
    echo "   ✅ Retrieved $TYPE_COUNT analysis type(s)"
else
    echo "   ❌ Failed: $GET_TYPES"
end
echo ""

# Test 9: Get Analysis Detail (if we have analyses)
if test -n "$TOTAL_ANALYSES"; and test "$TOTAL_ANALYSES" -gt 0
    set FIRST_ANALYSIS_ID (echo $GET_ANALYSES | grep -o '"id":[0-9]*' | head -1 | cut -d':' -f2)
    echo "9️⃣  GET /admin/analyses/$FIRST_ANALYSIS_ID"
    set GET_DETAIL (curl -s -X GET "$BASE_URL/admin/analyses/$FIRST_ANALYSIS_ID" \
      -H "Authorization: Bearer $TOKEN")

    if echo "$GET_DETAIL" | grep -q '"id"'
        echo "   ✅ Retrieved analysis detail for ID: $FIRST_ANALYSIS_ID"
    else
        echo "   ❌ Failed: $GET_DETAIL"
    end
else
    echo "9️⃣  GET /admin/analyses/{id}"
    echo "   ⚠️  Skipped (no analyses in database)"
end
echo ""

# ============================================
# ANALYTICS DASHBOARD ENDPOINTS (2 endpoints)
# ============================================
echo "📈 Testing Analytics Dashboard Endpoints"
echo "-----------------------------------------"

# Test 10: Get Analytics Metrics
echo "🔟 GET /admin/analytics?timeRange=7d"
set GET_ANALYTICS (curl -s -X GET "$BASE_URL/admin/analytics?timeRange=7d" \
  -H "Authorization: Bearer $TOKEN")

if echo "$GET_ANALYTICS" | grep -q '"metrics"'
    set TOTAL_COUNT (echo $GET_ANALYTICS | grep -o '"totalAnalyses":[0-9]*' | cut -d':' -f2)
    set COMPLETION (echo $GET_ANALYTICS | grep -o '"completionRate":[0-9.]*' | cut -d':' -f2)
    echo "   ✅ Analytics retrieved:"
    echo "      - Total Analyses (7d): $TOTAL_COUNT"
    echo "      - Completion Rate: $COMPLETION%"
    set CHART_POINTS (echo $GET_ANALYTICS | grep -o '"date"' | wc -l)
    echo "      - Chart Data Points: $CHART_POINTS"
else
    echo "   ❌ Failed: $GET_ANALYTICS"
end
echo ""

# Test 11: Get Activity Stream
echo "1️⃣1️⃣  GET /admin/activity-stream?limit=10"
set GET_ACTIVITY (curl -s -X GET "$BASE_URL/admin/activity-stream?limit=10" \
  -H "Authorization: Bearer $TOKEN")

if echo "$GET_ACTIVITY" | grep -q '"activities"'
    set ACTIVITY_COUNT (echo $GET_ACTIVITY | grep -o '"type":"[^"]*"' | wc -l)
    echo "   ✅ Retrieved $ACTIVITY_COUNT recent activities"
else
    echo "   ❌ Failed: $GET_ACTIVITY"
end
echo ""

# ============================================
# SUMMARY
# ============================================
echo "========================================"
echo "✅ Testing Complete!"
echo ""
echo "Summary:"
echo "  - Content Management: 6 endpoints tested"
echo "  - AI Analysis Monitoring: 3 endpoints tested"
echo "  - Analytics Dashboard: 2 endpoints tested"
echo "  - Total: 11 admin endpoints"
echo ""
echo "Check above for any ❌ failures."
echo "========================================"
