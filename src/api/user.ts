// src/hooks/useCurrentUser.ts
import { useQuery } from "@tanstack/react-query";
import { fetchHelper } from "../lib/fetch-helper";
import axios from "axios";

export interface User {
  id: number;
  email: string;
  name?: string;
}

export const useCurrentUser = () => {
  return useQuery({
    queryKey: ["currentUser"],  // ✅ required as part of options object
    queryFn: async () => {
      const res = await axios.get("http://localhost:8000/me", {
        withCredentials: true,  // send HTTP-only cookie
      });
      return res.data; // should return {id, name, email, role, ...}
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
