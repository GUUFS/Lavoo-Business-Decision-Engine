/**
 * Analysis API Hooks
 * TanStack Query hooks for analysis history, opportunity alerts, and AI insights pages
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import Cookies from "js-cookie";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

// --- INTERFACES ---
export interface Bottleneck {
  id: number;
  title: string;
  description: string;
  priority: "HIGH" | "MEDIUM" | "LOW";
  impact: string;
}

export interface BusinessStrategy {
  id: number;
  bottleneckId: number;
  title: string;
  description: string;
  features: string[];
}

export interface AITool {
  id: number;
  bottleneckId: number;
  title: string;
  description: string;
  price: string;
  rating: string;
  features: string[];
  pros: string[];
  cons: string[];
  website: string;
  comparison: {
    pricing: string;
    easeOfUse: string;
    learningCurve: string;
    integration: string;
  };
  implementation: {
    timeframe: string;
    difficulty: string;
    steps: string[];
    requirements: string[];
  };
}

export interface RoadmapStage {
  step: number;
  title: string;
  timeline: string;
  difficulty: string;
  description: string;
}

export interface ROIMetrics {
  monthly_revenue_increase: number;
  monthly_cost_savings: number;
  implementation_cost: number;
  twelve_month_projected_gain: number;
  break_even_months: number;
  time_savings_per_week: number;
  efficiency_gain_percent: number;
}

export interface BusinessAnalysis {
  analysis_id: number;
  business_goal: string;
  bottlenecks: Bottleneck[];
  business_strategies: BusinessStrategy[];
  ai_tools: AITool[];
  roadmap: RoadmapStage[];
  roi_metrics: ROIMetrics;
  ai_confidence_score: number;
  created_at: string;
  objective: string;
}

export interface TransformedAnalysis {
  id: number;
  title: string;
  date: string;
  description: string;
  bottlenecks: number;
  solutions: number;
  confidence: string;
  status: string;
  industry: string;
  created_at: string;
  raw: BusinessAnalysis;
}

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
  created_at?: string;
}

// --- AUTH HELPERS ---
const getAuthConfig = () => {
  const token = Cookies.get("access_token") ||
                localStorage.getItem("access_token") ||
                localStorage.getItem("token");

  return {
    headers: {
      "Content-Type": "application/json",
      Authorization: token ? `Bearer ${token}` : "",
    },
    withCredentials: true,
  };
};

const getAuthHeaders = () => {
  const token = Cookies.get("access_token") ||
                localStorage.getItem("access_token") ||
                localStorage.getItem("token");
  return {
    "Content-Type": "application/json",
    Authorization: token ? `Bearer ${token}` : "",
  };
};

// ====================
// ANALYSIS HISTORY HOOKS
// ====================

/**
 * Transform backend analysis data to UI format
 */
const transformAnalysis = (analysis: BusinessAnalysis): TransformedAnalysis => ({
  id: analysis.analysis_id,
  title: `Business Analysis - ${new Date(analysis.created_at).toLocaleDateString('en-US', {
    month: '2-digit',
    day: '2-digit',
    year: 'numeric'
  })}`,
  date: new Date(analysis.created_at).toLocaleDateString('en-US', {
    month: '2-digit',
    day: '2-digit',
    year: 'numeric'
  }),
  description: analysis.objective || analysis.business_goal || 'Business analysis report',
  bottlenecks: analysis.bottlenecks?.length || 0,
  solutions: (analysis.business_strategies?.length || 0) + (analysis.ai_tools?.length || 0),
  confidence: `${analysis.ai_confidence_score || 85}%`,
  status: 'completed',
  industry: 'Business',
  created_at: analysis.created_at,
  raw: analysis,
});

/**
 * Hook to fetch user's analysis history
 * Cached for 5 minutes - good balance for historical data
 */
export const useAnalysisHistory = (limit: number = 50) => {
  return useQuery({
    queryKey: ["analysis", "history", limit],
    queryFn: async (): Promise<TransformedAnalysis[]> => {
      const response = await axios.get(
        `${API_BASE_URL}/api/business/analyses?limit=${limit}`,
        getAuthConfig()
      );

      if (response.data.success) {
        const analyses = response.data.data || [];
        return analyses.map(transformAnalysis);
      }
      throw new Error("Failed to fetch analyses");
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 15 * 60 * 1000, // 15 minutes
    refetchOnWindowFocus: false,
  });
};

/**
 * Hook to fetch a single analysis by ID
 * Cached for 10 minutes - analysis data doesn't change
 */
export const useAnalysisById = (analysisId: number | null) => {
  return useQuery({
    queryKey: ["analysis", "detail", analysisId],
    queryFn: async (): Promise<BusinessAnalysis> => {
      if (!analysisId) throw new Error("Analysis ID required");

      const response = await axios.get(
        `${API_BASE_URL}/api/business/analyses/${analysisId}`,
        getAuthConfig()
      );

      if (response.data.success) {
        return response.data.data;
      }
      throw new Error("Failed to fetch analysis");
    },
    enabled: !!analysisId,
    staleTime: 10 * 60 * 1000, // 10 minutes
    gcTime: 30 * 60 * 1000, // 30 minutes
    refetchOnWindowFocus: false,
  });
};

/**
 * Hook to submit a new business analysis
 * Invalidates analysis history cache on success
 */
export const useAnalyzeBusinessGoal = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (businessGoal: string): Promise<BusinessAnalysis> => {
      const response = await axios.post(
        `${API_BASE_URL}/api/business/analyze`,
        { business_goal: businessGoal },
        getAuthConfig()
      );

      if (response.data.success) {
        return response.data.data;
      }
      throw new Error(response.data.message || "Analysis failed");
    },
    onSuccess: () => {
      // Invalidate and refetch analysis history
      queryClient.invalidateQueries({ queryKey: ["analysis", "history"] });
    },
  });
};

// ====================
// OPPORTUNITY ALERTS HOOKS
// ====================

/**
 * Hook to fetch all opportunity alerts
 * Cached for 2 minutes - alerts can change frequently
 */
export const useOpportunityAlerts = () => {
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
    staleTime: 2 * 60 * 1000, // 2 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
    refetchOnWindowFocus: false,
    refetchInterval: 2 * 60 * 1000, // Auto-refresh every 2 minutes
  });
};

/**
 * Hook to fetch alerts by priority
 * Cached for 2 minutes
 */
export const useAlertsByPriority = (priority: "High" | "Medium" | "Low") => {
  return useQuery({
    queryKey: ["alerts", "priority", priority],
    queryFn: async (): Promise<Alert[]> => {
      const response = await fetch(`${API_BASE_URL}/api/alerts`, {
        headers: getAuthHeaders(),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const alerts = await response.json();
      const alertsArray = Array.isArray(alerts) ? alerts : [];
      return alertsArray.filter((a: Alert) => a.priority === priority);
    },
    staleTime: 2 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
    refetchOnWindowFocus: false,
  });
};

/**
 * Hook to fetch alerts by category
 * Cached for 2 minutes
 */
export const useAlertsByCategory = (category: string) => {
  return useQuery({
    queryKey: ["alerts", "category", category],
    queryFn: async (): Promise<Alert[]> => {
      const response = await fetch(`${API_BASE_URL}/api/alerts`, {
        headers: getAuthHeaders(),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const alerts = await response.json();
      const alertsArray = Array.isArray(alerts) ? alerts : [];

      if (category === "all") return alertsArray;
      return alertsArray.filter((a: Alert) => a.category === category);
    },
    staleTime: 2 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
    refetchOnWindowFocus: false,
  });
};

// ====================
// AI INSIGHTS HOOKS
// ====================

/**
 * Hook to fetch all AI insights with pagination
 * Cached for 5 minutes
 */
export const useAIInsights = (page: number = 1, perPage: number = 10) => {
  return useQuery({
    queryKey: ["insights", "all", page, perPage],
    queryFn: async (): Promise<{
      insights: Insight[];
      total_insights: number;
      current_page: number;
      total_pages: number;
      is_pro: boolean;
    }> => {
      const response = await fetch(
        `${API_BASE_URL}/api/insights?page=${page}&per_page=${perPage}`,
        {
          headers: getAuthHeaders(),
        }
      );

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      return {
        insights: data.insights || [],
        total_insights: data.total_insights || 0,
        current_page: data.current_page || 1,
        total_pages: data.total_pages || 1,
        is_pro: data.is_pro || false,
      };
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 15 * 60 * 1000, // 15 minutes
    refetchOnWindowFocus: false,
  });
};

/**
 * Hook to fetch insights by category
 * Cached for 5 minutes
 */
export const useInsightsByCategory = (category: string) => {
  return useQuery({
    queryKey: ["insights", "category", category],
    queryFn: async (): Promise<Insight[]> => {
      const response = await fetch(`${API_BASE_URL}/api/insights`, {
        headers: getAuthHeaders(),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      const insights = data.insights || [];

      if (category === "all") return insights;
      return insights.filter((i: Insight) => i.category === category);
    },
    staleTime: 5 * 60 * 1000,
    gcTime: 15 * 60 * 1000,
    refetchOnWindowFocus: false,
  });
};

/**
 * Hook to search insights
 * Cached for 3 minutes
 */
export const useSearchInsights = (searchTerm: string) => {
  return useQuery({
    queryKey: ["insights", "search", searchTerm],
    queryFn: async (): Promise<Insight[]> => {
      const response = await fetch(`${API_BASE_URL}/api/insights`, {
        headers: getAuthHeaders(),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      const insights = data.insights || [];

      if (!searchTerm) return insights;

      const term = searchTerm.toLowerCase();
      return insights.filter((i: Insight) =>
        i.title.toLowerCase().includes(term) ||
        i.category.toLowerCase().includes(term) ||
        i.what_changed?.toLowerCase().includes(term) ||
        i.why_it_matters?.toLowerCase().includes(term)
      );
    },
    enabled: searchTerm.length >= 2, // Only search with 2+ characters
    staleTime: 3 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
    refetchOnWindowFocus: false,
  });
};

// ====================
// CACHE UTILITIES
// ====================

/**
 * Hook to get query client for manual cache operations
 */
export const useInvalidateAnalysisCache = () => {
  const queryClient = useQueryClient();

  return {
    invalidateHistory: () =>
      queryClient.invalidateQueries({ queryKey: ["analysis", "history"] }),
    invalidateAlerts: () =>
      queryClient.invalidateQueries({ queryKey: ["alerts"] }),
    invalidateInsights: () =>
      queryClient.invalidateQueries({ queryKey: ["insights"] }),
    invalidateAll: () => {
      queryClient.invalidateQueries({ queryKey: ["analysis"] });
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
      queryClient.invalidateQueries({ queryKey: ["insights"] });
    },
    prefetchHistory: async () => {
      await queryClient.prefetchQuery({
        queryKey: ["analysis", "history", 50],
        queryFn: async () => {
          const response = await axios.get(
            `${API_BASE_URL}/api/business/analyses?limit=50`,
            getAuthConfig()
          );
          if (response.data.success) {
            return (response.data.data || []).map(transformAnalysis);
          }
          return [];
        },
      });
    },
  };
};
