// src/api/admin-dashboard.ts
// Admin Dashboard API Service with TanStack Query Caching

import { useQuery } from "@tanstack/react-query";
import { instance } from "../lib/axios";

// ==================== TYPE DEFINITIONS ====================

export interface DashboardStats {
  total_users: number;
  active_users: number;
  total_revenue: number;
  system_uptime: string;
  recent_activity: {
    type: string;
    message: string;
    time: string;
  }[];
}

export interface ActivityItem {
  id: number;
  type: string;
  message: string;
  time: string;
  icon: string;
  color: string;
}

// ==================== API HOOKS ====================

/**
 * Hook to fetch admin dashboard stats
 * Cached for 2 minutes with background refetch
 */
export const useAdminDashboardStats = () => {
  return useQuery({
    queryKey: ["admin", "dashboard", "stats"],
    queryFn: async (): Promise<DashboardStats> => {
      const response = await instance.get<DashboardStats>("/api/admin/dashboard/stats");
      return response.data;
    },
    staleTime: 2 * 60 * 1000, // 2 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
    refetchOnWindowFocus: true,
    refetchInterval: 2 * 60 * 1000, // Auto-refresh every 2 minutes
  });
};

/**
 * Hook to fetch recent activity stream
 * Cached for 1 minute with background refetch for near real-time updates
 */
export const useAdminActivityStream = (limit = 10) => {
  return useQuery({
    queryKey: ["admin", "dashboard", "activity", limit],
    queryFn: async (): Promise<ActivityItem[]> => {
      const response = await instance.get<{ activities: ActivityItem[] }>(
        `/api/admin/activity-stream?limit=${limit}`
      );
      return response.data.activities || [];
    },
    staleTime: 1 * 60 * 1000, // 1 minute
    gcTime: 5 * 60 * 1000, // 5 minutes
    refetchOnWindowFocus: true,
    refetchInterval: 60 * 1000, // Auto-refresh every 1 minute
  });
};
