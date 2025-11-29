import { useMutation } from "@tanstack/react-query";
import { instance } from "../lib/axios";
import { toast } from "react-toastify";
import Cookies from "js-cookie";

interface AuthResponse {
  id: number;
  access_token: string;
  token_type?: string;
  refresh_token?: string;
  role: "admin" | "user";
}

interface LoginData {
  email: string;
  password: string;
}

interface SignupData {
  email: string;
  password: string;
  confirm_password: string;
  name?: string;
}

export const useAdmin = () => {
  return useMutation<AuthResponse, Error, LoginData>({
    mutationFn: async (data) => {
      const response = await fetch("http://localhost:8000/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        const errorBody = await response.json().catch(() => ({}));
        const message =
          errorBody.detail || `Login failed with status ${response.status}`;
        throw new Error(message);
      }
      return response.json();
    },
    onSuccess: (data) => {
      Cookies.set("access_token", data.access_token, {
        expires: 1 / 96,
        secure: true,
        sameSite: "strict",
      });
      toast.success("Admin Login successful!");
    },
    onError: (error) => {
      toast.error(error.message || "Login failed");
    },
  });
};

export const useLogin = () => {
  return useMutation<AuthResponse, Error, LoginData>({
    mutationFn: async (data) => {
      const response = await fetch("http://localhost:8000/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        const errorBody = await response.json().catch(() => ({}));
        const message =
          errorBody.detail || `Login failed with status ${response.status}`;
        throw new Error(message);
      }
      return (await response.json()) as AuthResponse;
    },

    onSuccess: (data) => {
      Cookies.set("access_token", data.access_token, {
        expires: 1 / 96,
        secure: true,
        sameSite: "strict",
      });

      toast.success("Login successful!");
    },

    onError: (error) => {
      toast.error(error.message || "Login failed");
    },
  });
};

// ✅ FIXED: Use fetch instead of axios instance and correct endpoint
export const useSignup = () => {
  return useMutation<any, Error, FormData>({
    mutationFn: async (data) => {
      const response = await fetch("http://localhost:8000/signup", {
        method: "POST",
        body: data, // Don't set Content-Type for FormData
      });

      if (!response.ok) {
        const errorBody = await response.json().catch(() => ({}));
        const message =
          errorBody.detail || `Signup failed with status ${response.status}`;
        throw new Error(message);
      }

      return response.json();
    },
  });
};