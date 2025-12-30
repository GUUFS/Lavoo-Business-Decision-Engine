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

      // Fetch insights count
      const insightsResponse = await fetch(`${API_BASE_URL}/api/insights`, {
        headers: getAuthHeaders(),
      });

      if (!insightsResponse.ok) {
        throw new Error(`HTTP ${insightsResponse.status}`);
      }

      const insightsData = await insightsResponse.json();
      const totalInsights = insightsData.total_insights || insightsData.insights?.length || 0;

      // Fetch reviews for average rating
      const reviewsResponse = await fetch(`${API_BASE_URL}/api/reviews`, {
        headers: getAuthHeaders(),
      });

      let averageRating = 0;
      if (reviewsResponse.ok) {
        const reviewsData = await reviewsResponse.json();
        const reviews = Array.isArray(reviewsData) ? reviewsData : [];
        if (reviews.length > 0) {
          averageRating =
            reviews.reduce((sum: number, r: Review) => sum + r.rating, 0) /
            reviews.length;
        }
      }

      return {
        total_revenue: 0,
        active_alerts: activeAlerts,
        new_alerts_today: 0,
        total_insights: totalInsights,
        new_insights_today: 0,
        average_rating: averageRating,
        rating_change: 0,
        total_chops: userData.total_chops || userData.chops || 0,
        unattended_alerts: activeAlerts,
        total_referrals: userData.referral_count || 0,
        referrals_this_month: userData.referrals_this_month || 0,
        referral_chops: userData.referral_chops || 0,
      };
    },
    enabled: !!userId,
    staleTime: 30 * 1000, // 30 seconds
    gcTime: 5 * 60 * 1000, // 5 minutes
    refetchOnWindowFocus: true,
    refetchInterval: 30 * 1000, // Auto-refresh every 30 seconds in background
  });
};

/**
 * Hook to fetch urgent alerts
 * Shows the same 3 alerts as the opportunity alerts tab (no re-sorting)
 * Cached for 1 minute, refetches in background every 1 minute
 */
export const useUrgentAlerts = (userId: number | null, limit = 3) => {
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

      // Return the first N alerts in the same order as the alerts tab
      // (already sorted by pinned first, then by created_at desc from the API)
      return alertsArray.slice(0, limit);
    },
    enabled: !!userId,
    staleTime: 1 * 60 * 1000, // 1 minute
    gcTime: 5 * 60 * 1000, // 5 minutes
    refetchOnWindowFocus: false,
    refetchInterval: 1 * 60 * 1000, // Auto-refresh every 1 minute
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
    gcTime: 15 * 60 * 1000, // 15 minutes
    refetchOnWindowFocus: false,
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
    gcTime: 15 * 60 * 1000, // 15 minutes
    refetchOnWindowFocus: false,
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
