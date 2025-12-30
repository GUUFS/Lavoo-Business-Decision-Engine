// src/api/admin-reports.ts
// Admin Reports/Customer Service API Service with TanStack Query Caching

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { instance } from "../lib/axios";

// ==================== TYPE DEFINITIONS ====================

export interface Conversation {
  user_id: number;
  user_name: string;
  user_email: string;
  unread_count: number;
  last_message: string;
  last_message_at: string;
  status: string;
}

export interface Message {
  id: number;
  sender_role: 'admin' | 'user' | 'system';
  message: string;
  created_at: string;
  ticket_id: number;
  sender_name?: string;
}

export interface GetConversationsResponse {
  conversations: Conversation[];
  total: number;
  unread_total: number;
}

// ==================== API HOOKS ====================

/**
 * Hook to fetch customer service conversations
 * Cached for 1 minute for near real-time updates
 */
export const useAdminConversations = () => {
  return useQuery({
    queryKey: ["admin", "reports", "conversations"],
    queryFn: async (): Promise<GetConversationsResponse> => {
      const response = await instance.get<GetConversationsResponse>("/api/customer-service/admin/conversations");
      return response.data;
    },
    staleTime: 1 * 60 * 1000, // 1 minute
    gcTime: 5 * 60 * 1000, // 5 minutes
    refetchOnWindowFocus: true,
    refetchInterval: 60 * 1000, // Auto-refresh every minute
  });
};

/**
 * Hook to fetch messages for a specific conversation
 * Cached for 30 seconds for real-time chat experience
 */
export const useConversationMessages = (userId: number) => {
  return useQuery({
    queryKey: ["admin", "reports", "messages", userId],
    queryFn: async (): Promise<{ messages: Message[] }> => {
      const response = await instance.get<{ messages: Message[] }>(
        `/api/customer-service/admin/users/${userId}/messages`
      );
      return response.data;
    },
    enabled: !!userId,
    staleTime: 30 * 1000, // 30 seconds
    gcTime: 5 * 60 * 1000, // 5 minutes
    refetchOnWindowFocus: true,
  });
};

/**
 * Mutation to send a reply to a ticket
 */
export const useSendReply = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ ticketId, message }: { ticketId: number; message: string }) => {
      const response = await instance.post(`/api/customer-service/admin/tickets/${ticketId}/reply`, {
        message,
        ticket_id: ticketId
      });
      return response.data;
    },
    onSuccess: () => {
      // Invalidate conversations list
      queryClient.invalidateQueries({ queryKey: ["admin", "reports", "conversations"] });
    },
  });
};

/**
 * Mutation to resolve all tickets for a user
 */
export const useResolveUserTickets = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (userId: number) => {
      const response = await instance.post(`/api/customer-service/admin/users/${userId}/resolve_all`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "reports", "conversations"] });
    },
  });
};

/**
 * Mutation to close/resolve a conversation
 */
export const useCloseConversation = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (userId: number) => {
      const response = await instance.post(`/api/admin/customer-service/conversations/${userId}/close`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "reports", "conversations"] });
    },
  });
};
