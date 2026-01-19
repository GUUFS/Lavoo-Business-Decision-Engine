import { useQuery } from "@tanstack/react-query";

const API_BASE_URL = "http://localhost:8000";

// --- INTERFACES ---
export interface Alert {
  id: number;
  title: string;
  category: string;
  priority: "High" | "Medium" | "Low";
  score: number;
  time_remaining: string;
  why_act_now: string;
  potential_reward: string;
  action_required: string;
  is_pinned?: boolean; // Support for pinned alerts
}

export interface Insight {
  id: number;
  title: string;
  category: string;
  what_changed: string;
  why_it_matters: string;
  action_to_take: string;
  read_time: number;
}

export interface Review {
  id: number;
  business_name: string;
  rating: number;
  review_text: string;
  date_submitted: string;
}

export interface DashboardStats {
  total_revenue: number;
  active_alerts: number;
  new_alerts_today: number;
  total_insights: number;
  new_insights_today: number;
  average_rating: number;
  rating_change: number;
  total_chops: number;
  unattended_alerts: number;
  total_referrals: number;
  referrals_this_month: number;
  referral_chops: number;
}

// --- AUTH HELPERS ---
const getAuthHeaders = () => {
  const token =
    localStorage.getItem("access_token") ||
    localStorage.getItem("token") ||
    localStorage.getItem("authToken");
  return {
    "Content-Type": "application/json",
    Authorization: token ? `Bearer ${token}` : "",
  };
};

// --- API HOOKS ---

/**
 * Hook to fetch dashboard stats
 * Cached for 30 seconds, refetches in background every 30 seconds
 * Invalidates immediately when chops are earned
 */
export const useDashboardStats = (userId: number | null) => {
  return useQuery({
    queryKey: ["dashboard", "stats", userId],
    queryFn: async (): Promise<DashboardStats> => {
      if (!userId) throw new Error("User ID required");

      // Fetch user data for chops
      const userResponse = await fetch(`${API_BASE_URL}/users/me`, {
        headers: getAuthHeaders(),
        credentials: "include",
      });

      if (!userResponse.ok) {
        throw new Error(`HTTP ${userResponse.status}`);
      }

      const userData = await userResponse.json();

      // Fetch alerts count
      const alertsResponse = await fetch(`${API_BASE_URL}/api/alerts`, {
        headers: getAuthHeaders(),
      });

      if (!alertsResponse.ok) {
        throw new Error(`HTTP ${alertsResponse.status}`);
      }

      const alertsData = await alertsResponse.json();
      const activeAlerts = Array.isArray(alertsData) ? alertsData.length : 0;

      // Fetch insights/analyses stats
      const statsResponse = await fetch(`${API_BASE_URL}/api/user/stats`, {
        headers: getAuthHeaders(),
      });

      let totalAnalyses = 0;
      let avgConfidence = 0;
      if (statsResponse.ok) {
        const statsData = await statsResponse.json();
        totalAnalyses = statsData.total_analyses || 0;
        avgConfidence = statsData.avg_confidence || 0;
      }

      // Fetch reviews for average rating
      const reviewsResponse = await fetch(`${API_BASE_URL}/api/reviews`, {
        headers: getAuthHeaders(),
      });

      let avgRating = 0;
      if (reviewsResponse.ok) {
        const reviews = await reviewsResponse.json();
        const reviewsArray = Array.isArray(reviews) ? reviews : [];
        if (reviewsArray.length > 0) {
          const totalRating = reviewsArray.reduce((sum: number, r: any) => sum + (r.rating || 0), 0);
          avgRating = totalRating / reviewsArray.length;
        }
      }

      return {
        total_revenue: 0,
        active_alerts: activeAlerts,
        new_alerts_today: 0,
        total_insights: totalAnalyses, // This will be displayed as "Total Analyses"
        new_insights_today: 0,
        average_rating: avgRating,
        rating_change: 0,
        total_chops: userData.total_chops || userData.chops || 0,
        unattended_alerts: activeAlerts,
        total_referrals: userData.referral_count || 0,
        referrals_this_month: userData.referrals_this_month || 0,
        referral_chops: userData.referral_chops || 0,
      };
    },
    enabled: !!userId,
    staleTime: 5 * 60 * 1000, // 5 minutes - prevents reloads when switching tabs
    gcTime: 15 * 60 * 1000, // 15 minutes
    refetchOnWindowFocus: false, // Don't refetch on window focus to prevent reloads
    refetchInterval: false, // Disable auto-refresh to prevent constant reloads
  });
};

/**
 * Hook to fetch urgent alerts
 * Shows first 5 alerts for free users, first 3 for dashboard widget
 * Matches behavior of alerts tab exactly
 * Cached for 5 minutes to prevent constant reloads
 */
export const useUrgentAlerts = (userId: number | null, limit = 5) => {
  return useQuery({
    queryKey: ["dashboard", "urgent-alerts", userId, limit],
    queryFn: async (): Promise<Alert[]> => {
      if (!userId) throw new Error("User ID required");

      const response = await fetch(`${API_BASE_URL}/api/alerts`, {
        headers: getAuthHeaders(),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const alerts = await response.json();
      const alertsArray = Array.isArray(alerts) ? alerts : [];

      // Sort: pinned first, then by score (matches alerts page behavior)
      const sortedAlerts = alertsArray.sort((a: Alert, b: Alert) => {
        if (a.is_pinned && !b.is_pinned) return -1;
        if (!a.is_pinned && b.is_pinned) return 1;
        return b.score - a.score;
      });

      // Return first N alerts (5 for free users to match alerts page, 3 for dashboard widget)
      return sortedAlerts.slice(0, limit);
    },
    enabled: !!userId,
    staleTime: 5 * 60 * 1000, // 5 minutes (matches alerts list cache)
    gcTime: 10 * 60 * 1000, // 10 minutes
    refetchOnWindowFocus: false, // Don't refetch on focus
    refetchInterval: false, // Disable auto-refresh
  });
};

/**
 * Hook to fetch top insights
 * Cached for 5 minutes
 */
export const useTopInsights = (limit = 3) => {
  return useQuery({
    queryKey: ["dashboard", "top-insights", limit],
    queryFn: async (): Promise<Insight[]> => {
      const response = await fetch(`${API_BASE_URL}/api/insights`, {
        headers: getAuthHeaders(),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      const insightsArray = data.insights || [];
      return insightsArray.slice(0, limit);
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
    refetchOnWindowFocus: false,
    refetchInterval: false, // Disable auto-refresh
  });
};

/**
 * Hook to fetch recent reviews
 * Cached for 5 minutes
 */
export const useRecentReviews = (limit = 3) => {
  return useQuery({
    queryKey: ["dashboard", "recent-reviews", limit],
    queryFn: async (): Promise<Review[]> => {
      const response = await fetch(`${API_BASE_URL}/api/reviews`, {
        headers: getAuthHeaders(),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const reviews = await response.json();
      const reviewsArray = Array.isArray(reviews) ? reviews : [];
      return reviewsArray.slice(0, limit);
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
    refetchOnWindowFocus: false,
    refetchInterval: false, // Disable auto-refresh
  });
};

/**
 * Hook to fetch all alerts (for opportunity alerts page)
 * Cached for 1 minute, refetches in background every 1 minute
 */
export const useAllAlerts = () => {
  return useQuery({
    queryKey: ["alerts", "all"],
    queryFn: async (): Promise<Alert[]> => {
      const response = await fetch(`${API_BASE_URL}/api/alerts`, {
        headers: getAuthHeaders(),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const alerts = await response.json();
      return Array.isArray(alerts) ? alerts : [];
    },
    staleTime: 1 * 60 * 1000, // 1 minute
    gcTime: 5 * 60 * 1000, // 5 minutes
    refetchOnWindowFocus: false,
    refetchInterval: 1 * 60 * 1000, // Auto-refresh every 1 minute
  });
};

/**
 * Hook to fetch all insights (for insights page)
 * Cached for 5 minutes
 */
export const useAllInsights = () => {
  return useQuery({
    queryKey: ["insights", "all"],
    queryFn: async (): Promise<Insight[]> => {
      const response = await fetch(`${API_BASE_URL}/api/insights`, {
        headers: getAuthHeaders(),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      return data.insights || [];
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 15 * 60 * 1000, // 15 minutes
    refetchOnWindowFocus: false,
  });
};
