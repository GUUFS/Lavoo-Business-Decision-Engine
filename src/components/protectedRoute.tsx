// components/ProtectedRoute.tsx
import { Navigate, Outlet } from "react-router-dom";
import Cookies from "js-cookie";
import {jwtDecode} from "jwt-decode";

type JwtPayload = {
  exp: number;
  sub: string;
};

const isTokenValid = (token: string) => {
  try {
    const decoded: JwtPayload = jwtDecode(token);
    const now = Date.now() / 1000;
    return decoded.exp > now;
  } catch {
    return false;
  }
};

export const ProtectedRoute = () => {
  const token = Cookies.get("access_token");

  if (!token || !isTokenValid(token)) {
    Cookies.remove("access_token");
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
};
