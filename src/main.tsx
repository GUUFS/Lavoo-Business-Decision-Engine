import { StrictMode } from 'react'
import './i18n'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { ToastContainer } from 'react-toastify'
import "react-toastify/dist/ReactToastify.css";

import { initFrontendSentry } from './monitoring/SentryFrontend';

// Initialize Sentry for error tracking
initFrontendSentry();

// Configure TanStack Query with smart caching strategies
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Prevent refetch on window focus for better UX
      refetchOnWindowFocus: false,

      // Retry failed requests once (balance reliability & performance)
      retry: 1,

      // Default stale time: 5 minutes (data considered fresh for 5min)
      staleTime: 5 * 60 * 1000, // 5 minutes

      // Default garbage collection: 10 minutes (unused cache cleared after 10min)
      gcTime: 10 * 60 * 1000, // 10 minutes (formerly cacheTime)
    },
    mutations: {
      // Retry failed mutations once
      retry: 1,
    },
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
      <ToastContainer position="top-right" autoClose={3000} />
      {/* React Query DevTools - only shows in development */}
      <ReactQueryDevtools initialIsOpen={false} position="bottom-right" />
    </QueryClientProvider>
  </StrictMode>
)
