import type { RouteObject } from "react-router-dom";
import NotFound from "../pages/NotFound";
import Home from "../pages/home/page";
import Analyze from "../pages/dashboard/analyze/page";
import Results from "../pages/results/page";
import SignUp from "../pages/signup/page";
import Login from "../pages/login/page";
import Dashboard from "../pages/dashboard/page";
import DashboardAnalyze from "../pages/dashboard/analyze/page";
import { ProtectedRoute } from "../components/protectedRoute";

import DashboardLayout from "../components/dashboard-layouts";
// User Dashboard pages
import OpportunityAlerts from '../pages/dashboard/alerts/page';
import Earnings from '../pages/dashboard/earnings/page';
import Profile from "../pages/dashboard/profile/page";
import AIInsights from "../pages/dashboard/insights/page";
import Reviews from "../pages/dashboard/reviews/page";
import AITrends from "../pages/dashboard/ai_trends/page";
import CustomerService from '../pages/dashboard/customer-service/page';
import Upgrade from '../pages/dashboard/upgrade/page';
import AdminReviews from "../pages/dashboard/admin_reviews/page";
import AnalysisHistoryPage from '../pages/analysis-history/page';
import ReviewChats from '../pages/dashboard/conversations/page';
import ReportChats from '../pages/dashboard/customer-service/conversation/[id]/page';

// Admin pages
import AdminDashboard from "../pages/admin/page";
import AdminProfile from "../pages/admin/profile/page";
import Users from "../pages/admin/users/page";
import Analytics from "../pages/admin/analytics/page";
import ReviewsStore from "../pages/admin/reviews/page";
import Reports from "../pages/admin/reports/page";
import Revenue from "../pages/admin/revenue/page";
import SystemHealth from "../pages/admin/system-health/page";
import Security from "../pages/admin/security/page";
import Database from "../pages/admin/database/page";
import Notifications from "../pages/admin/notifications/page";
import Settings from "../pages/admin/settings/page";
import AnalysisHistory from "../pages/admin/ai-analysis/page";
import CustomerChats from "../pages/admin/report-conversations/page";
import Content from "../pages/admin/content-management/page";
import CustomerReviews from "../pages/admin/conversations/page";


const routes: RouteObject[] = [
  { path: "/", element: <Home /> },

  {
    // Protected area
    element: <ProtectedRoute />,
    children: [
      { path: "/analyze", element: <Analyze /> },
      {
        path: "/results",
        element: <DashboardLayout />,
        children: [
          { index: true, element: <Results /> },
        ]
      },
      {
        path: "/analysis-history",
        element: <DashboardLayout />,
        children: [
          { index: true, element: <AnalysisHistoryPage /> },
        ]
      },

      // Admin layout wrapper
      { path: "/admin", element: <DashboardLayout />, children: [
        { path: "", element: <AdminDashboard /> },
        { path: "profile", element: <AdminProfile /> },
        { path: "users", element: <Users /> },
        { path: "analytics", element: <Analytics /> },
        { path: "reviews", element: <ReviewsStore /> },
        { path: "reports", element: <Reports /> },
        { path: "revenue", element: <Revenue /> },
        { path: "system-health", element: <SystemHealth /> },
        { path: "security", element: <Security /> },
        { path: "database", element: <Database /> },
        { path: "notifications", element: <Notifications /> },
        { path: "settings", element: <Settings /> },
        { path: "ai-analysis", element: <AnalysisHistory /> },
        { path: "report-conversations/:reportId", element: <CustomerChats />},
        { path: "content-management", element: <Content />},
        { path: "conversations/:reviewId", element: < CustomerReviews/>},
        ]
      },

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
          { path: "ai_trends", element: <AITrends /> },
          { path: "analyze", element: <DashboardAnalyze /> },
          { path: "upgrade", element: <Upgrade />},
          { path: '/dashboard/admin-reviews', element: <AdminReviews /> },
          { path: "conversations/:reviewId", element: <ReviewChats/>},
          { path: "customer-service/conversation/:id", element: <ReportChats />},
        ],
      },



    ],
  },

  { path: "/signup", element: <SignUp /> },
  { path: "/login", element: <Login /> },
  { path: "*", element: <NotFound /> },
];

export default routes;
