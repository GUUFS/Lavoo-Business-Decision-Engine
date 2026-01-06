// src/api/admin-revenue.ts
// Admin Revenue API Service with TanStack Query Caching

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { instance } from "../lib/axios";

// ==================== TYPE DEFINITIONS ====================

export type StatusType =
  | 'completed'
  | 'active'
  | 'paid'
  | 'pending'
  | 'approved'
  | 'failed'
  | 'refunded'
  | 'processing';

export interface Transaction {
  id: string;
  user: string;
  user_email: string;
  plan: string;
  amount: number;
  status: StatusType;
  date: string;
}

export interface Commission {
  user_id: number;
  user: string;
  user_email: string;
  total_commissions: number;
  pending_commissions: number;
  processing_commissions: number;
  paid_commissions: number;
  payout_status: StatusType;
  last_commission_date?: string | null;
  available_payment_methods: string[];
  has_payout_account: boolean;
}

export interface Payout {
  id: number;
  user: string;
  user_email: string;
  amount: number;
  currency: string;
  status: StatusType;
  method: string;
  requested_at: string;
  completed_at?: string | null;
  failure_reason?: string | null;
}

export interface RevenueStats {
  monthly_revenue: number;
  total_subscription_revenue: number;
  referral_commissions_paid: number;
  refunds: number;
  growth_rate: number;
}

export interface GetTransactionsResponse {
  transactions: Transaction[];
  total: number;
  pagination: {
    currentPage: number;
    totalPages: number;
    hasNext: boolean;
    hasPrev: boolean;
  };
}

export interface GetCommissionsResponse {
  commissions: Commission[];
  total: number;
  pagination: {
    currentPage: number;
    totalPages: number;
    hasNext: boolean;
    hasPrev: boolean;
  };
}

export interface GetPayoutsResponse {
  payouts: Payout[];
  total: number;
  pagination: {
    currentPage: number;
    totalPages: number;
    hasNext: boolean;
    hasPrev: boolean;
  };
}

// ==================== API HOOKS ====================

/**
 * Hook to fetch revenue stats
 * Cached for 2 minutes
 */
export const useRevenueStats = () => {
  return useQuery({
    queryKey: ["admin", "revenue", "stats"],
    queryFn: async (): Promise<RevenueStats> => {
      const response = await instance.get<RevenueStats>("/api/control/revenue/stats");
      return response.data;
    },
    staleTime: 2 * 60 * 1000, // 2 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
    refetchOnWindowFocus: true,
  });
};

/**
 * Hook to fetch transactions with pagination
 * Cached for 2 minutes
 */
export const useTransactions = (params: {
  page?: number;
  limit?: number;
  status?: string;
}) => {
  const { page = 1, limit = 10, status = "all" } = params;

  return useQuery({
    queryKey: ["admin", "revenue", "transactions", page, limit, status],
    queryFn: async (): Promise<GetTransactionsResponse> => {
      const response = await instance.get<GetTransactionsResponse>(
        `/api/control/revenue/transactions?page=${page}&limit=${limit}${status !== 'all' ? `&status=${status}` : ''}`
      );
      return response.data;
    },
    staleTime: 2 * 60 * 1000, // 2 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
    refetchOnWindowFocus: true,
  });
};

/**
 * Hook to fetch commissions with pagination
 * Cached for 2 minutes
 */
export const useCommissions = (params: {
  page?: number;
  limit?: number;
}) => {
  const { page = 1, limit = 10 } = params;

  return useQuery({
    queryKey: ["admin", "revenue", "commissions", page, limit],
    queryFn: async (): Promise<GetCommissionsResponse> => {
      const response = await instance.get<GetCommissionsResponse>(
        `/api/control/revenue/commissions?page=${page}&limit=${limit}`
      );
      return response.data;
    },
    staleTime: 2 * 60 * 1000, // 2 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
    refetchOnWindowFocus: true,
  });
};

/**
 * Hook to fetch payouts with pagination
 * Cached for 2 minutes
 */
export const usePayouts = (params: {
  page?: number;
  limit?: number;
  status?: string;
}) => {
  const { page = 1, limit = 10, status = "all" } = params;

  return useQuery({
    queryKey: ["admin", "revenue", "payouts", page, limit, status],
    queryFn: async (): Promise<GetPayoutsResponse> => {
      const response = await instance.get<GetPayoutsResponse>(
        `/api/control/revenue/payouts?page=${page}&limit=${limit}${status !== 'all' ? `&status=${status}` : ''}`
      );
      return response.data;
    },
    staleTime: 2 * 60 * 1000, // 2 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
    refetchOnWindowFocus: true,
  });
};

/**
 * Mutation to process a payout
 */
export const useProcessPayout = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ userId, method }: { userId: number; method: string }) => {
      const response = await instance.post(`/api/control/revenue/payouts/process`, {
        user_id: userId,
        method
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "revenue", "payouts"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "revenue", "commissions"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "revenue", "stats"] });
    },
  });
};

/**
 * Mutation to approve/reject a payout
 */
export const useUpdatePayoutStatus = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ payoutId, action }: { payoutId: number; action: 'approve' | 'reject' }) => {
      const response = await instance.patch(`/api/control/revenue/payouts/${payoutId}/${action}`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "revenue", "payouts"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "revenue", "stats"] });
    },
  });
};
