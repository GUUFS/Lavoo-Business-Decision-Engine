import type { RouteObject } from "react-router-dom";
import NotFound from "../pages/NotFound";
import Home from "../pages/home/page";
import Analyze from "../pages/dashboard/analyze/page";
import Results from "../pages/results/page";
import SignUp from "../pages/signup/page";
import Login from "../pages/login/page";
import { ProtectedRoute } from "../components/protectedRoute";

// Dashboard pages
import Dashboard from '../pages/dashboard/page';
import OpportunityAlerts from '../pages/dashboard/alerts/page';
import Earnings from '../pages/dashboard/earnings/page';
import DashboardLayout from "../components/dashboard-layouts";
import Profile from "../pages/dashboard/profile/page";
import AIInsights from "../pages/dashboard/insights/page";
import Reviews from "../pages/dashboard/reviews/page";
import Hub from "../pages/dashboard/hub/page";
import CustomerService from '../pages/dashboard/customer-service/page';
import Upgrade from '../pages/dashboard/upgrade/page';
import AdminReviews from "../pages/dashboard/admin_reviews/page";
import AnalysisHistoryPage from '../pages/analysis-history/page';

const routes: RouteObject[] = [
  { path: "/", element: <Home /> },

  {
    // Protected area
    element: <ProtectedRoute />,
    children: [
      { path: "/analyze", element: <Analyze /> },
 
      { path: "/results", element: <DashboardLayout />, children: [
         { path: '', element: <Results /> },
      ]},
      { path: "/analysis-history", element: <DashboardLayout/>, children: [
        { path: '', element: <AnalysisHistoryPage />},
      ]},

      // Dashboard layout wrapper
      {
        path: "/dashboard",
        element: <DashboardLayout />,
        children: [

          { path: "", element: <Dashboard /> },
          { path: "profile", element: <Profile /> },
          { path: "alerts", element: <OpportunityAlerts /> },
          { path: "insights", element: <AIInsights /> },
          { path: "earnings", element: <Earnings /> },
          { path: "customer-service", element: <CustomerService /> },
          { path: "reviews", element: <Reviews /> },
          { path: "hub", element: <Hub /> },
          { path: "analyze", element: <Analyze /> },
          { path: "upgrade", element: <Upgrade />},
          { path: '/dashboard/admin-reviews', element: <AdminReviews /> },
        ],
      },
      
      
    ],
  },

  { path: "/signup", element: <SignUp /> },
  { path: "/login", element: <Login /> },
  { path: "*", element: <NotFound /> },
];

export default routes;
