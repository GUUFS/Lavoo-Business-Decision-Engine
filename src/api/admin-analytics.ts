// src/api/admin-analytics.ts
// Admin Analytics Dashboard API Service

import { useQuery } from "@tanstack/react-query";
import { instance } from "../lib/axios";

// ==================== TYPE DEFINITIONS ====================

export interface AnalyticsMetrics {
  totalAnalyses: number;
  completionRate: number;
  avgProcessingTime: number;
  userSatisfaction: number;
}

export interface ChartDataPoint {
  date: string;
  analyses: number;
  users: number;
}

export interface TopAnalysisType {
  type: string;
  count: number;
  percentage: number;
}

export interface PerformanceMetric {
  metric: string;
  value: string;
  change: string;
  trend: "up" | "down";
}

export interface GetAnalyticsResponse {
  metrics: AnalyticsMetrics;
  chartData: ChartDataPoint[];
  topAnalysisTypes: TopAnalysisType[];
  performanceMetrics: PerformanceMetric[];
}

export interface Activity {
  type: "analysis_started" | "analysis_completed" | "analysis_failed";
  message: string;
  timestamp: string;
  timeAgo: string;
  icon: string;
  color: "blue" | "green" | "red";
  user: string;
}

export interface GetActivityStreamResponse {
  activities: Activity[];
}

// ==================== API FUNCTIONS ====================

/**
 * Get platform analytics metrics (admin only)
 * Hook with 3-minute cache for moderately changing data
 * @param timeRange - Time range filter: "24h" | "7d" | "30d" | "90d"
 */
export const useAnalytics = (timeRange: "24h" | "7d" | "30d" | "90d" = "7d") => {
  return useQuery({
    queryKey: ["admin", "analytics", timeRange],
    queryFn: async (): Promise<GetAnalyticsResponse> => {
      const response = await instance.get<GetAnalyticsResponse>(
        `/admin/analytics?timeRange=${timeRange}`
      );
      return response.data;
    },
    // 3-minute cache for analytics data
    staleTime: 3 * 60 * 1000, // 3 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
  });
};

/**
 * Legacy function - kept for backward compatibility
 * @deprecated Use useAnalytics hook instead
 */
export const getAnalytics = async (
  timeRange: "24h" | "7d" | "30d" | "90d" = "7d"
): Promise<GetAnalyticsResponse> => {
  const response = await instance.get<GetAnalyticsResponse>(
    `/admin/analytics?timeRange=${timeRange}`
  );
  return response.data;
};

/**
 * Get recent platform activity for real-time feed (admin only)
 * Hook with automatic 14-second refetch for real-time updates
 */
export const useActivityStream = (limit = 10) => {
  return useQuery({
    queryKey: ["admin", "activity-stream", limit],
    queryFn: async (): Promise<GetActivityStreamResponse> => {
      const response = await instance.get<GetActivityStreamResponse>(
        `/admin/activity-stream?limit=${limit}`
      );
      return response.data;
    },
    // Shorter cache for real-time data
    staleTime: 14 * 1000, // 14 seconds (matches old polling interval)
    gcTime: 1 * 60 * 1000, // 1 minute
    refetchInterval: 14 * 1000, // Auto-refetch every 14 seconds
    refetchIntervalInBackground: false, // Stop polling when tab inactive
  });
};

/**
 * Legacy function - kept for backward compatibility
 * @deprecated Use useActivityStream hook instead
 */
export const getActivityStream = async (limit = 10): Promise<GetActivityStreamResponse> => {
  const response = await instance.get<GetActivityStreamResponse>(
    `/admin/activity-stream?limit=${limit}`
  );
  return response.data;
};
