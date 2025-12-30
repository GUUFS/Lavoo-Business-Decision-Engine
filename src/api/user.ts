import { useQuery, useQueryClient } from "@tanstack/react-query";
// import { fetchHelper } from "../lib/fetch-helper";
import axios from "axios";
import { useEffect } from "react";

export interface User {
  id: number;
  email: string;
  name?: string;
  subscription_status?: string;
  subscription_plan?: string;
  referral_code?: string;
  total_chops?: number;
  created_at?: string;
  department?: string;
  location?: string;
  bio?: string;
}

export const useCurrentUser = () => {
  return useQuery({
    queryKey: ["currentUser"],  // ✅ required as part of options object
    queryFn: async () => {
      const token = localStorage.getItem("auth_token") || localStorage.getItem("user_token") || localStorage.getItem("access_token");
      if (!token) return null; // Prevent 401 if not logged in

      try {
        const res = await axios.get("http://localhost:8000/api/me", {
          withCredentials: true,
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
        return res.data; // should return {id, name, email, role, ...}
      } catch (err: any) {
        if (err.response?.status === 401) {
          try {
            await axios.post(
              "http://localhost:8000/api/refresh",
              {},
              { withCredentials: true } // send refresh_token cookie
            );

            const retryRes = await axios.get("http://localhost:8000/api/me", {
              withCredentials: true,
              headers: token ? { Authorization: `Bearer ${token}` } : {},
            });
            return retryRes.data
          } catch (refreshErr) {
            // Refresh failed, user must login
            throw new Error("Session expired. Please login again.");
          }
        } else {
          throw err
        }
      }
    },
  });
};

export const updateProfile = async (data: any) => {
  const token = localStorage.getItem("access_token");
  const res = await axios.patch("http://localhost:8000/me", data, {
    withCredentials: true,
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  return res.data;
};

// --- CHOPS MANAGEMENT ---

export interface UserChops {
  total_chops: number;
  alert_reading_chops: number;
  alert_sharing_chops: number;
  insight_reading_chops: number;
  insight_sharing_chops: number;
  referral_chops: number;
  referral_count: number;
}

/**
 * Hook to fetch and manage user chops with fast updates and cross-tab sync
 * Cached for 30 seconds, refetches in background every 30 seconds
 * Invalidates immediately when chops are earned anywhere
 */
export const useUserChops = () => {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ["userChops"],
    queryFn: async (): Promise<UserChops> => {
      const token = localStorage.getItem("auth_token") || localStorage.getItem("user_token") || localStorage.getItem("access_token");
      if (!token) throw new Error("No auth token");

      try {
        const res = await axios.get("http://localhost:8000/users/me", {
          withCredentials: true,
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });

        const userData = res.data;
        return {
          total_chops: userData.total_chops || 0,
          alert_reading_chops: userData.alert_reading_chops || 0,
          alert_sharing_chops: userData.alert_sharing_chops || 0,
          insight_reading_chops: userData.insight_reading_chops || 0,
          insight_sharing_chops: userData.insight_sharing_chops || 0,
          referral_chops: userData.referral_chops || 0,
          referral_count: userData.referral_count || 0,
        };
      } catch (err: any) {
        if (err.response?.status === 401) {
          try {
            await axios.post(
              "http://localhost:8000/api/refresh",
              {},
              { withCredentials: true }
            );

            const retryRes = await axios.get("http://localhost:8000/users/me", {
              withCredentials: true,
              headers: token ? { Authorization: `Bearer ${token}` } : {},
            });

            const userData = retryRes.data;
            return {
              total_chops: userData.total_chops || 0,
              alert_reading_chops: userData.alert_reading_chops || 0,
              alert_sharing_chops: userData.alert_sharing_chops || 0,
              insight_reading_chops: userData.insight_reading_chops || 0,
              insight_sharing_chops: userData.insight_sharing_chops || 0,
              referral_chops: userData.referral_chops || 0,
              referral_count: userData.referral_count || 0,
            };
          } catch (refreshErr) {
            throw new Error("Session expired. Please login again.");
          }
        } else {
          throw err;
        }
      }
    },
    enabled: !!localStorage.getItem("auth_token") || !!localStorage.getItem("user_token") || !!localStorage.getItem("access_token"),
    staleTime: 30 * 1000, // 30 seconds
    gcTime: 5 * 60 * 1000, // 5 minutes
    refetchOnWindowFocus: true,
    refetchInterval: 30 * 1000, // Auto-refresh every 30 seconds
  });

  // Cross-tab synchronization using BroadcastChannel
  useEffect(() => {
    const channel = new BroadcastChannel('chops-updates');

    const handleChopsUpdate = () => {
      // Invalidate and refetch chops immediately
      queryClient.invalidateQueries({ queryKey: ["userChops"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard", "stats"] });
      queryClient.invalidateQueries({ queryKey: ["currentUser"] });
    };

    channel.addEventListener('message', handleChopsUpdate);

    return () => {
      channel.removeEventListener('message', handleChopsUpdate);
      channel.close();
    };
  }, [queryClient]);

  return {
    ...query,
    // Method to invalidate chops across all tabs
    invalidateChops: () => {
      queryClient.invalidateQueries({ queryKey: ["userChops"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard", "stats"] });
      queryClient.invalidateQueries({ queryKey: ["currentUser"] });

      // Broadcast to other tabs
      const channel = new BroadcastChannel('chops-updates');
      channel.postMessage({ type: 'chops-updated' });
      channel.close();
    }
  };
};

/**
 * Utility function to update chops after earning them
 * This should be called whenever chops are earned (sharing, viewing, etc.)
 */
export const updateChopsAfterAction = async (queryClient: any) => {
  // Invalidate all chops-related queries immediately
  queryClient.invalidateQueries({ queryKey: ["userChops"] });
  queryClient.invalidateQueries({ queryKey: ["dashboard", "stats"] });
  queryClient.invalidateQueries({ queryKey: ["currentUser"] });

  // Broadcast to other tabs
  const channel = new BroadcastChannel('chops-updates');
  channel.postMessage({ type: 'chops-updated' });
  channel.close();
};
