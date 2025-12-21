import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'
import { resolve } from 'node:path'
import AutoImport from 'unplugin-auto-import/vite'
import path from 'path'

const base = process.env.BASE_PATH || '/'
const isPreview = process.env.IS_PREVIEW ? true : false;
// https://vite.dev/config/
export default defineConfig({
  define: {
    __BASE_PATH__: JSON.stringify(base),
    __IS_PREVIEW__: JSON.stringify(isPreview)
  },
  plugins: [react(),
  AutoImport({
    imports: [
      {
        'react': [
          'React',
          'useState',
          'useEffect',
          'useContext',
          'useReducer',
          'useCallback',
          'useMemo',
          'useRef',
          'useImperativeHandle',
          'useLayoutEffect',
          'useDebugValue',
          'useDeferredValue',
          'useId',
          'useInsertionEffect',
          'useSyncExternalStore',
          'useTransition',
          'startTransition',
          'lazy',
          'memo',
          'forwardRef',
          'createContext',
          'createElement',
          'cloneElement',
          'isValidElement'
        ]
      },
      {
        'react-router-dom': [
          'useNavigate',
          'useLocation',
          'useParams',
          'useSearchParams',
          'Link',
          'NavLink',
          'Navigate',
          'Outlet'
        ]
      },
      // React i18n
      {
        'react-i18next': [
          'useTranslation',
          'Trans'
        ]
      }
    ],
    dts: true,
  }),
  ],
  base: '/',
  build: {
    sourcemap: true,
    outDir: 'web',  // Changed from 'out' to 'web' to match backend expectations
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      'react': resolve(__dirname, './node_modules/react'),
      'react-dom': resolve(__dirname, './node_modules/react-dom')
    }
  },
  server: {
    port: 3000,
    host: '0.0.0.0',
    // Header for Stripe connect webhooks to work locally
    headers: {
      'Content-Security-Policy': [
        // Base security
        "default-src 'self'",

        // Scripts - Payment providers
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://js.stripe.com https://checkout.flutterwave.com https://*.flutterwave.com https://*.sentry.io",

        // Frames - Payment modals
        "frame-src 'self' https://js.stripe.com https://checkout.flutterwave.com https://*.f4b-flutterwave.com",

        // API connections - CRITICAL FIX: Use * wildcard for all paths
        "connect-src 'self' http://localhost:8000 https://localhost:8000 http://127.0.0.1:8000 https://127.0.0.1:8000 ws://localhost:8000 wss://localhost:8000 ws://127.0.0.1:8000 wss://127.0.0.1:8000 http://localhost:8000/* https://localhost:8000/* https://api.stripe.com https://api.flutterwave.com https://*.flutterwave.com https://api.ravepay.co https://metrics.flutterwave.com https://*.sentry.io https://*.ingest.sentry.io",

        // Styles - All CSS sources
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com https://cdn.jsdelivr.net",

        // Fonts
        "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com data:",

        // Images
        "img-src 'self' data: https: blob:"
      ].join('; ')
    },
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
        // Remove any fancy configure — this simple version works 100%
      }
    }
  }
})
