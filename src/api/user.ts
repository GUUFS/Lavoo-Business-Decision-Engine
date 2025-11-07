// src/hooks/useCurrentUser.ts
import { useQuery } from "@tanstack/react-query";
import { fetchHelper } from "../lib/fetch-helper";

export interface User {
  id: number;
  email: string;
  name?: string;
}

export const useCurrentUser = () => {
  return useQuery<User, Error>({
    queryKey: ["currentUser"],
    queryFn: () => fetchHelper<User>("/analyzer"),
    retry: false, // don't keep retrying if unauthorized
  });
};
