import { useMutation } from "@tanstack/react-query";
import { instance } from "../lib/axios";
import { toast } from "react-toastify";
import Cookies from "js-cookie";

interface AuthResponse {
  access_token: string;
  refresh_token?: string;
  data: string
}

interface LoginData {
  email: string;
  password: string;
}

interface SignupData {
  email: string;
  password: string;
  confirm_password:string;
  name?: string;
}

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

      return response.json();
    },

    onSuccess: (data) => {
      // Save token to cookies (15-minute expiry)
      Cookies.set("access_token", data.access_token, {
        expires: 1 / 96, // 15 minutes = 1/96 of a day
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

export const useSignup = () => {
  return useMutation<AuthResponse, Error, FormData>({
    mutationFn: async (data) => {
      const res = await instance.post<AuthResponse>("/api/signup", data);
      return res.data;    },
  });
};