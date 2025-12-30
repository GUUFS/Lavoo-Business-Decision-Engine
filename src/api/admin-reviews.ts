// src/api/admin-reviews.ts
// Admin Reviews API Service with TanStack Query Caching

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { instance } from "../lib/axios";

// ==================== TYPE DEFINITIONS ====================

export interface Message {
  id: number;
  review_id: number;
  sender_type: 'user' | 'admin';
  message: string;
  timestamp: string;
  is_read: boolean;
}

export interface Review {
  id: number;
  user_name: string;
  user_email: string;
  business_name: string;
  review_title: string;
  rating: number;
  review_text: string;
  date_submitted: string;
  status: string;
  category: string;
  admin_response: boolean;
  conversation_count: number;
  unread_messages: number;
  is_attended: boolean;
}

export interface ReviewStats {
  total_reviews: number;
  pending_reviews: number;
  responded_reviews: number;
  average_rating: number;
}

export interface GetReviewsResponse {
  reviews: Review[];
  total: number;
  stats: ReviewStats;
  pagination: {
    currentPage: number;
    totalPages: number;
    hasNext: boolean;
    hasPrev: boolean;
  };
}

// ==================== API HOOKS ====================

/**
 * Hook to fetch admin reviews with pagination and filters
 * Cached for 2 minutes
 */
export const useAdminReviews = (params: {
  page?: number;
  limit?: number;
  status?: string;
  rating?: string;
}) => {
  const { page = 1, limit = 10, status = "all", rating = "all" } = params;

  return useQuery({
    queryKey: ["admin", "reviews", page, limit, status, rating],
    queryFn: async (): Promise<GetReviewsResponse> => {
      const response = await instance.get<GetReviewsResponse>(
        `/api/admin/reviews?page=${page}&limit=${limit}&status=${status}&rating=${rating}`
      );
      return response.data;
    },
    staleTime: 2 * 60 * 1000, // 2 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
    refetchOnWindowFocus: true,
  });
};

/**
 * Hook to fetch review conversations/messages
 * Cached for 30 seconds for near real-time updates
 */
export const useReviewConversations = (reviewId: number) => {
  return useQuery({
    queryKey: ["admin", "review-conversations", reviewId],
    queryFn: async (): Promise<Message[]> => {
      const response = await instance.get<Message[]>(
        `/api/admin/reviews/${reviewId}/conversations`
      );
      return response.data;
    },
    enabled: !!reviewId,
    staleTime: 30 * 1000, // 30 seconds
    gcTime: 5 * 60 * 1000, // 5 minutes
    refetchOnWindowFocus: true,
  });
};

/**
 * Mutation to reply to a review
 */
export const useReplyToReview = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ reviewId, message }: { reviewId: number; message: string }) => {
      const response = await instance.post(`/api/admin/reviews/${reviewId}/reply`, { message });
      return response.data;
    },
    onSuccess: (_, variables) => {
      // Invalidate the conversations for this review
      queryClient.invalidateQueries({ queryKey: ["admin", "review-conversations", variables.reviewId] });
      // Invalidate the reviews list to update unread counts
      queryClient.invalidateQueries({ queryKey: ["admin", "reviews"] });
    },
  });
};

/**
 * Mutation to update review status
 */
export const useUpdateReviewStatus = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ reviewId, status }: { reviewId: number; status: string }) => {
      const response = await instance.patch(`/api/admin/reviews/${reviewId}/status`, { status });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "reviews"] });
    },
  });
};
