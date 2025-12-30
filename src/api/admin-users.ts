// src/api/admin-users.ts
// Admin User Management API Service

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { instance } from "../lib/axios";

// ==================== TYPE DEFINITIONS ====================

export interface User {
  id: number;
  name: string;
  email: string;
  plan: string;
  status: 'active' | 'suspended' | 'inactive';
  joinDate: string;
  lastActive: string;
  analyses: number;
  avatar: string;
}

export interface UserDetails extends User {
  subscription_status: string;
  subscription_plan: string;
  total_chops: number;
  referral_chops: number;
  alert_reading_chops: number;
  insight_reading_chops: number;
  referral_count: number;
  referrals: string[];
  insight_sharing_chops: number;
  alert_sharing_chops: number;
  days_remaining: number;
  referral_code: string;
  is_active: boolean;
}

export interface UserStats {
  total: number;
  pro: number;
  free: number;
  deactivated: number;
  inactive: number;
  active?: number;
}

export interface GetUsersResponse {
  users: User[];
  total: number;
  totalPages: number;
}

// ==================== API HOOKS ====================

/**
 * Hook to fetch user stats
 * Cached for 2 minutes
 */
export const useUserStats = () => {
  return useQuery({
    queryKey: ["admin", "users", "stats"],
    queryFn: async (): Promise<UserStats> => {
      const response = await instance.get<UserStats>("/api/control/users/stats");
      return response.data;
    },
    staleTime: 2 * 60 * 1000, // 2 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
    refetchOnWindowFocus: true,
  });
};

/**
 * Get paginated users with filters (admin only)
 * Hook with 2-minute cache for user management data
 */
export const useUsers = (params: {
  page?: number;
  limit?: number;
  status?: string;
  search?: string;
}) => {
  const { page = 1, limit = 10, status = "all", search = "" } = params;

  return useQuery({
    queryKey: ["admin", "users", "list", page, limit, status, search],
    queryFn: async (): Promise<GetUsersResponse> => {
      const queryParams = new URLSearchParams({
        page: page.toString(),
        limit: limit.toString(),
        search,
        status
      });
      const response = await instance.get<GetUsersResponse>(
        `/api/control/users?${queryParams}`
      );
      return response.data;
    },
    staleTime: 2 * 60 * 1000, // 2 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
    refetchOnWindowFocus: true,
  });
};

/**
 * Get detailed user information (admin only)
 * Hook with 3-minute cache for user details
 */
export const useUserDetail = (userId: number | null) => {
  return useQuery({
    queryKey: ["admin", "user-detail", userId],
    queryFn: async (): Promise<UserDetails> => {
      const response = await instance.get<UserDetails>(`/api/control/users/${userId}`);
      return response.data;
    },
    staleTime: 3 * 60 * 1000, // 3 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
    enabled: !!userId, // Only fetch if userId is provided
  });
};

/**
 * Toggle user status (admin only)
 * Mutation hook with automatic cache invalidation
 */
export const useToggleUserStatus = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (userId: number): Promise<{ is_active: boolean }> => {
      const response = await instance.patch(`/api/control/users/${userId}/status`);
      return response.data;
    },
    onSuccess: (_, userId) => {
      // Invalidate user list cache to refetch with updated data
      queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
      // Invalidate specific user detail cache
      queryClient.invalidateQueries({ queryKey: ["admin", "user-detail", userId] });
    },
  });
};
