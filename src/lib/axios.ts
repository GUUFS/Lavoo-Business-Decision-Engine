import axios, {
  AxiosError,
  type AxiosInstance,
  type AxiosRequestConfig,
  type AxiosResponse,
} from "axios";
import Cookies from "js-cookie";

// Extend AxiosRequestConfig to include custom property
interface CustomAxiosRequestConfig extends AxiosRequestConfig {
  skipAuth?: boolean;
  _retry?: boolean;
}

// Utility: Check if the request requires authentication
const isAuthRequired = (config?: CustomAxiosRequestConfig): boolean => {
  // Only skip auth if explicitly told to
  return !config?.skipAuth;
};

// Exported helper for manual usage (optional)
export const configOptions = (): AxiosRequestConfig => {
  if (typeof window === "undefined") return {};

  const accessToken = Cookies.get("access_token");
  if (!accessToken) return {};

  return {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  };
};

// Create Axios instance
export const instance: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_APP_API_BASE_URL,
});

// Request interceptor
instance.interceptors.request.use(
  async (config) => {
    const token = Cookies.get("access_token");

    // Normalize headers for Axios v1.x
    const headers =
      typeof config.headers?.toJSON === "function"
        ? config.headers.toJSON()
        : { ...config.headers };

    if (isAuthRequired(config)) {
     ( config.headers as any) = {
        ...headers,
        Authorization: token ? `Bearer ${token}` : "",
        // "Content-Type": "application/json",
      };
    } else {
      (config.headers as any) = {
        ...headers,
        // "Content-Type": "application/json",
      };
    }

    return config;
  },
  (error: AxiosError) => Promise.reject(error)
);

// Response interceptor
instance.interceptors.response.use(
  (response: AxiosResponse) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as CustomAxiosRequestConfig;

    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      isAuthRequired(originalRequest)
    ) {
      originalRequest._retry = true;

      try {
        // 🔹 TODO: Implement real token refresh logic here
        // const newAccessToken = await refreshToken();
        // if (newAccessToken) {
        //   Cookies.set("access_token", newAccessToken);
        //   if (originalRequest.headers) {
        //     const headers =
        //       typeof originalRequest.headers.toJSON === "function"
        //         ? originalRequest.headers.toJSON()
        //         : originalRequest.headers;
        //     originalRequest.headers = {
        //       ...headers,
        //       Authorization: `Bearer ${newAccessToken}`,
        //     };
        //   }
        //   return instance(originalRequest);
        // }
        return { message: "Not added" };
      } catch (refreshError) {
        Cookies.remove("access_token");
        Cookies.remove("refresh_token");
        window.location.href = "/auth-login";
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);
