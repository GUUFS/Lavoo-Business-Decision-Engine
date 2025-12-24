// src/api/admin-content.ts
// Admin Content Management API Service

import { instance } from "../lib/axios";

// ==================== TYPE DEFINITIONS ====================

export interface InsightCreate {
  title: string;
  category: string;
  read_time: string;
  what_changed: string;
  why_it_matters: string;
  action_to_take: string;
  source?: string;
  date?: string;
}

export interface InsightResponse {
  id: number;
  title: string;
  category: string;
  read_time: string;
  what_changed: string;
  why_it_matters: string;
  action_to_take: string;
  source: string | null;
  url: string | null;
  date: string;
  is_active: boolean;
  total_views: number;
  total_shares: number;
  created_at: string;
}

export interface AlertCreate {
  title: string;
  category: string;
  priority: string;
  score: number;
  time_remaining: string;
  why_act_now: string;
  potential_reward: string;
  action_required: string;
  source?: string;
  date?: string;
}

export interface AlertResponse {
  id: number;
  title: string;
  category: string;
  priority: string;
  score: number;
  time_remaining: string;
  why_act_now: string;
  potential_reward: string;
  action_required: string;
  source: string | null;
  url: string | null;
  date: string;
  is_active: boolean;
  total_views: number;
  total_shares: number;
  created_at: string;
}

export interface TrendCreate {
  title: string;
  industry: string;
  description: string;
  viral_score: number;
  nature: string;
  action_items: string;
  engagement?: string;
  growth?: string;
  search_volume?: string;
  peak_time?: string;
  competition?: "low" | "medium" | "high";
  opportunity?: "high" | "medium" | "low";
  hashtags?: string[];
  platforms?: string[];
}

export interface TrendResponse {
  id: number;
  title: string;
  industry: string;
  description: string;
  engagement: string | null;
  growth: string | null;
  viral_score: number;
  search_volume: string | null;
  peak_time: string | null;
  competition: string;
  opportunity: string | null;
  nature: string;
  hashtags: string[] | null;
  platforms: string[] | null;
  action_items: string;
  is_active: boolean;
  created_at: string;
}

// ==================== API FUNCTIONS ====================

/**
 * Create a new insight (admin only)
 */
export const createInsight = async (data: InsightCreate): Promise<InsightResponse> => {
  const response = await instance.post<InsightResponse>("/admin/content/insights", data);
  return response.data;
};

/**
 * Create a new alert (admin only)
 */
export const createAlert = async (data: AlertCreate): Promise<AlertResponse> => {
  const response = await instance.post<AlertResponse>("/admin/content/alerts", data);
  return response.data;
};

/**
 * Create a new trend (admin only)
 */
export const createTrend = async (data: TrendCreate): Promise<TrendResponse> => {
  const response = await instance.post<TrendResponse>("/admin/content/trends", data);
  return response.data;
};

/**
 * Get recent insights (admin only)
 */
export const getInsights = async (limit = 20): Promise<{ insights: InsightResponse[] }> => {
  const response = await instance.get<{ insights: InsightResponse[] }>(
    `/admin/content/insights?limit=${limit}`
  );
  return response.data;
};

/**
 * Get recent alerts (admin only)
 */
export const getAlerts = async (limit = 20): Promise<{ alerts: AlertResponse[] }> => {
  const response = await instance.get<{ alerts: AlertResponse[] }>(
    `/admin/content/alerts?limit=${limit}`
  );
  return response.data;
};

/**
 * Get recent trends (admin only)
 */
export const getTrends = async (limit = 20): Promise<{ trends: TrendResponse[] }> => {
  const response = await instance.get<{ trends: TrendResponse[] }>(
    `/admin/content/trends?limit=${limit}`
  );
  return response.data;
};
