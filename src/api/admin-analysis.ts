// src/api/admin-analysis.ts
// Admin AI Analysis Monitoring API Service

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

// ==================== API FUNCTIONS ====================

/**
 * Get paginated analyses with filters (admin only)
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
 */
export const getAnalysisTypes = async (): Promise<GetAnalysisTypesResponse> => {
  const response = await instance.get<GetAnalysisTypesResponse>("/admin/analysis-types");
  return response.data;
};

/**
 * Get detailed analysis by ID (admin only)
 */
export const getAnalysisDetail = async (id: number): Promise<AnalysisDetail> => {
  const response = await instance.get<AnalysisDetail>(`/admin/analyses/${id}`);
  return response.data;
};
