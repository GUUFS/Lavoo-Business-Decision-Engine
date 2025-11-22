import { useQuery } from "@tanstack/react-query";
import { fetchHelper } from "../lib/fetch-helper";
import axios from "axios";

export interface User {
  id: number;
  email: string;
  name?: string;
  subscription_status?: string;
  subscription_plan?: string;
}

export const useCurrentUser = () => {
  return useQuery({
    queryKey: ["currentUser"],  // ✅ required as part of options object
    queryFn: async () => {
      try {
        const res = await axios.get("http://localhost:8000/me", {
          withCredentials: true,  // send HTTP-only cookie
        });
        return res.data; // should return {id, name, email, role, ...}
      } catch (err: any) {
        if (err.response?.status === 401) {
          try {
            await axios.post(
              "http://localhost:8000/refresh",
              {},
              { withCredentials: true } // send refresh_token cookie
            );

            const retryRes = await axios.get("http://localhost:8000/me", {
              withCredentials: true,
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
// export const useCurrentUser = () => {
  //  / useQuery(["currentUser"], async () => {
    // const res = await axios.get("http://localhost:8000/me", { withCredentials: true });
    // return res.data;
  // return useQuery<User, Error>({
    // queryKey: ["currentUser"],
    // queryFn: () => fetchHelper<User>("/analyzer"),
    // retry: false, // don't keep retrying if unauthorized
  // });
// };