import { useQuery } from "@tanstack/react-query";
// import { fetchHelper } from "../lib/fetch-helper";
import axios from "axios";

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
