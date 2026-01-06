// src/api/admin-analysis.ts
// Admin AI Analysis Monitoring API Service

import { useQuery } from "@tanstack/react-query";
import { instance } from "../lib/axios";

// ==================== TYPE DEFINITIONS ====================

export interface UserInfo {
  id: number;
  display_name: string;
  email: string;
}

export interface AnalysisItem {
  id: number;
  title: string;
  user: string;
  userName: string;
  userEmail: string;
  type: string;
  status: string;
  confidence: number;
  duration: string;
  date: string;
  insights: number;
  recommendations: number;
}

export interface AnalysisStats {
  completed: number;
  failed: number;
  avgConfidence: number;
}

export interface GetAnalysesResponse {
  analyses: AnalysisItem[];
  total: number;
  stats: AnalysisStats;
  pagination: {
    currentPage: number;
    totalPages: number;
    hasNext: boolean;
    hasPrev: boolean;
  };
}

export interface AnalysisType {
  analysis_type: string;
  count: number;
}

export interface GetAnalysisTypesResponse {
  types: AnalysisType[];
}

export interface AnalysisDetail {
  id: number;
  business_goal: string;
  status: string;
  confidence_score: number | null;
  duration: string | null;
  analysis_type: string | null;
  insights_count: number;
  recommendations_count: number;
  estimated_cost: number | null;
  timeline_weeks: number | null;
  created_at: string;
  user: UserInfo;
}

// ==================== API HOOKS ====================

/**
 * Hook to fetch paginated analyses with filters (admin only)
 * Cached for 2 minutes
 */
export const useAnalyses = (params: {
  page?: number;
  limit?: number;
  status?: string;
  type?: string;
}) => {
  const { page = 1, limit = 5, status = "all", type = "all" } = params;

  return useQuery({
    queryKey: ["admin", "analyses", page, limit, status, type],
    queryFn: async (): Promise<GetAnalysesResponse> => {
      const response = await instance.get<GetAnalysesResponse>(
        `/admin/analyses?page=${page}&limit=${limit}&status=${status}&type=${type}`
      );
      return response.data;
    },
    staleTime: 2 * 60 * 1000, // 2 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
    refetchOnWindowFocus: true,
  });
};

/**
 * Hook to fetch analysis types with counts (admin only)
 * Cached for 5 minutes (rarely changes)
 */
export const useAnalysisTypes = () => {
  return useQuery({
    queryKey: ["admin", "analysis-types"],
    queryFn: async (): Promise<GetAnalysisTypesResponse> => {
      const response = await instance.get<GetAnalysisTypesResponse>("/admin/analysis-types");
      return response.data;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 15 * 60 * 1000, // 15 minutes
  });
};

/**
 * Hook to fetch detailed analysis by ID (admin only)
 * Cached for 5 minutes
 */
export const useAnalysisDetail = (id: number) => {
  return useQuery({
    queryKey: ["admin", "analysis-detail", id],
    queryFn: async (): Promise<AnalysisDetail> => {
      const response = await instance.get<AnalysisDetail>(`/admin/analyses/${id}`);
      return response.data;
    },
    enabled: !!id,
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 15 * 60 * 1000, // 15 minutes
  });
};

// ==================== LEGACY API FUNCTIONS (for backward compatibility) ====================

/**
 * Get paginated analyses with filters (admin only)
 * @deprecated Use useAnalyses hook instead
 */
export const getAnalyses = async (params: {
  page?: number;
  limit?: number;
  status?: string;
  type?: string;
}): Promise<GetAnalysesResponse> => {
  const { page = 1, limit = 5, status = "all", type = "all" } = params;

  const response = await instance.get<GetAnalysesResponse>(
    `/admin/analyses?page=${page}&limit=${limit}&status=${status}&type=${type}`
  );
  return response.data;
};

/**
 * Get analysis types with counts (admin only)
 * @deprecated Use useAnalysisTypes hook instead
 */
export const getAnalysisTypes = async (): Promise<GetAnalysisTypesResponse> => {
  const response = await instance.get<GetAnalysisTypesResponse>("/admin/analysis-types");
  return response.data;
};

/**
 * Get detailed analysis by ID (admin only)
 * @deprecated Use useAnalysisDetail hook instead
 */
export const getAnalysisDetail = async (id: number): Promise<AnalysisDetail> => {
  const response = await instance.get<AnalysisDetail>(`/admin/analyses/${id}`);
  return response.data;
};
