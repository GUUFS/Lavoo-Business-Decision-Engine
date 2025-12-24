// src/api/admin-users.ts
// Admin User Management API Service

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { instance } from "../lib/axios";

// ==================== TYPE DEFINITIONS ====================

export interface UserItem {
  id: number;
  name: string;
  email: string;
  plan: string;
  status: string;
  isAdmin: boolean;
  joinDate: string;
  lastActive: string;
  analyses: number;
  totalChops: number;
  avatar: string;
}

export interface UserStats {
  total: number;
  active: number;
  inactive: number;
}

export interface GetUsersResponse {
  users: UserItem[];
  total: number;
  stats: UserStats;
  pagination: {
    currentPage: number;
    totalPages: number;
    hasNext: boolean;
    hasPrev: boolean;
  };
}

export interface UserDetailResponse extends UserItem {
  referralCount: number;
}

// ==================== API FUNCTIONS ====================

/**
 * Get paginated users with filters (admin only)
 * Hook with 3-minute cache for user management data
 */
export const useUsers = (params: {
  page?: number;
  limit?: number;
  status?: string;
  search?: string;
}) => {
  const { page = 1, limit = 10, status = "all", search = "" } = params;

  return useQuery({
    queryKey: ["admin", "users", page, limit, status, search],
    queryFn: async (): Promise<GetUsersResponse> => {
      const response = await instance.get<GetUsersResponse>(
        `/admin/users?page=${page}&limit=${limit}&status=${status}&search=${encodeURIComponent(search)}`
      );
      return response.data;
    },
    // 3-minute cache for user data (changes moderately)
    staleTime: 3 * 60 * 1000, // 3 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
  });
};

/**
 * Legacy function - kept for backward compatibility
 * @deprecated Use useUsers hook instead
 */
export const getUsers = async (params: {
  page?: number;
  limit?: number;
  status?: string;
  search?: string;
}): Promise<GetUsersResponse> => {
  const { page = 1, limit = 10, status = "all", search = "" } = params;

  const response = await instance.get<GetUsersResponse>(
    `/admin/users?page=${page}&limit=${limit}&status=${status}&search=${encodeURIComponent(search)}`
  );
  return response.data;
};

/**
 * Get detailed user information (admin only)
 * Hook with 5-minute cache for user details
 */
export const useUserDetail = (userId: number) => {
  return useQuery({
    queryKey: ["admin", "user-detail", userId],
    queryFn: async (): Promise<UserDetailResponse> => {
      const response = await instance.get<UserDetailResponse>(`/admin/users/${userId}`);
      return response.data;
    },
    // 5-minute cache for user details (rarely changes)
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 15 * 60 * 1000, // 15 minutes
    enabled: !!userId, // Only fetch if userId is provided
  });
};

/**
 * Legacy function - kept for backward compatibility
 * @deprecated Use useUserDetail hook instead
 */
export const getUserDetail = async (userId: number): Promise<UserDetailResponse> => {
  const response = await instance.get<UserDetailResponse>(`/admin/users/${userId}`);
  return response.data;
};

/**
 * Update user status (admin only)
 * Mutation hook with automatic cache invalidation
 */
export const useUpdateUserStatus = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      userId,
      status,
    }: {
      userId: number;
      status: "active" | "inactive";
    }): Promise<{ success: boolean; message: string }> => {
      const response = await instance.patch(`/admin/users/${userId}/status`, { status });
      return response.data;
    },
    onSuccess: (data, variables) => {
      // Invalidate user list cache to refetch with updated data
      queryClient.invalidateQueries({ queryKey: ["admin", "users"] });

      // Invalidate specific user detail cache
      queryClient.invalidateQueries({ queryKey: ["admin", "user-detail", variables.userId] });
    },
  });
};

/**
 * Legacy function - kept for backward compatibility
 * @deprecated Use useUpdateUserStatus hook instead
 */
export const updateUserStatus = async (
  userId: number,
  status: "active" | "inactive"
): Promise<{ success: boolean; message: string }> => {
  const response = await instance.patch(`/admin/users/${userId}/status`, { status });
  return response.data;
};
