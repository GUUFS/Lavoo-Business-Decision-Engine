import type { RouteObject } from "react-router-dom";
import NotFound from "../pages/NotFound";
import Home from "../pages/home/page";
import Results from "../pages/results/page";
import SignUp from "../pages/signup/page";
import Login from "../pages/login/page";
import Dashboard from "../pages/dashboard/page";
import DashboardAnalyze from "../pages/dashboard/analyze/page";
import { ProtectedRoute } from "../components/protectedRoute";

const routes: RouteObject[] = [
  {
    path: "/",
    element: <Home />,
  },
  {
    // Wrap protected routes under ProtectedRoute
    element: <ProtectedRoute />,
    children: [
      {
        path: "/dashboard",
        element: <Dashboard />,
      },
      {
        path: "/dashboard/analyze",
        element: <DashboardAnalyze />,
      },
      {
        path: "/results",
        element: <Results />,
      },
    ],
  },
  {
    path: "/signup",
    element: <SignUp />,
  },
  {
    path: "/login",
    element: <Login />,
  },
  {
    path: "*",
    element: <NotFound />,
  },
];

export default routes;