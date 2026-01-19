// Earnings API with TanStack Query caching
import { useQuery } from "@tanstack/react-query";
import api from "../pages/dashboard/earnings/service"; // Use existing axios client

// --- INTERFACES ---
export interface EarningsSummary {
  totalCommissions: number;
  totalPaidReferrals: number;
  referralChops: number;
  growthRate: number;
  totalRevenue: number;
  transactions: number;
  avgOrderValue: number;
  commissionRate: number;
  paidCommissions: number;
  pendingCommissions: number;
}

export interface ReferralData {
  total_referrals: number;
  total_chops_earned: number;
  referrals_this_month: number;
  recent_referrals: Array<{
    id: number;
    referred_user_email: string;
    referred_user_name: string;
    chops_awarded: number;
    created_at: string;
  }>;
}

export interface UserData {
  id: number;
  name: string;
  email: string;
  total_chops: number;
  referral_chops: number;
  referral_count: number;
  referral_code: string;
}

export interface MonthlyMetrics {
  month: string;
  month_number?: number;
  year: number;
  referral_count: number;
  paid_referral_count: number;
  referral_chops: number;
  commission: number;
  revenue: number;
}

// --- HOOKS WITH CACHING ---

/**
 * Hook to fetch current user data for earnings page
 * Cached for 5 minutes to prevent reloads when switching tabs
 */
export const useEarningsUser = () => {
  return useQuery({
    queryKey: ["earnings", "user"],
    queryFn: async (): Promise<UserData> => {
      const response = await api.get("/user/me");
      return response.data;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
    refetchOnWindowFocus: false,
    refetchInterval: false,
  });
};

/**
 * Hook to fetch referral statistics
 * Cached for 3 minutes (can change more frequently than user data)
 */
export const useReferralStats = () => {
  return useQuery({
    queryKey: ["earnings", "referrals"],
    queryFn: async (): Promise<ReferralData> => {
      const response = await api.get("/api/referrals/stats");
      return response.data;
    },
    staleTime: 3 * 60 * 1000, // 3 minutes
    gcTime: 10 * 60 * 1000,
    refetchOnWindowFocus: false,
    refetchInterval: false,
  });
};

/**
 * Hook to fetch earnings summary
 * Cached for 3 minutes
 */
export const useEarningsSummary = () => {
  return useQuery({
    queryKey: ["earnings", "summary"],
    queryFn: async (): Promise<EarningsSummary> => {
      const response = await api.get("/earnings/summary");
      return response.data;
    },
    staleTime: 3 * 60 * 1000, // 3 minutes
    gcTime: 10 * 60 * 1000,
    refetchOnWindowFocus: false,
    refetchInterval: false,
  });
};

/**
 * Hook to fetch available years for earnings data
 * Cached for 10 minutes (changes rarely)
 */
export const useAvailableYears = () => {
  return useQuery({
    queryKey: ["earnings", "years"],
    queryFn: async (): Promise<number[]> => {
      const response = await api.get("/earnings/available-years");
      return response.data.years || [];
    },
    staleTime: 10 * 60 * 1000, // 10 minutes
    gcTime: 30 * 60 * 1000,
    refetchOnWindowFocus: false,
    refetchInterval: false,
  });
};

/**
 * Hook to fetch monthly performance data
 * Cached for 5 minutes
 */
export const useMonthlyPerformance = (year: number, month: number) => {
  return useQuery({
    queryKey: ["earnings", "monthly", year, month],
    queryFn: async (): Promise<MonthlyMetrics> => {
      const response = await api.get(`/earnings/monthly/${year}/${month}`);
      return response.data;
    },
    enabled: !!year && !!month,
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000,
    refetchOnWindowFocus: false,
    refetchInterval: false,
  });
};
