import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'
import { resolve } from 'node:path'
import AutoImport from 'unplugin-auto-import/vite'

const base = process.env.BASE_PATH || '/'
const isPreview = process.env.IS_PREVIEW  ? true : false;
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
  base:'/',
  build: {
    sourcemap: true,
    outDir: 'web',  // Changed from 'out' to 'web' to match backend expectations
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, './src'),
      'react': resolve(__dirname, './node_modules/react'),
      'react-dom': resolve(__dirname, './node_modules/react-dom')
    }
  },
  server: {
    port: 3000,
    host: '0.0.0.0',
    proxy: {
      // Proxy all /api requests to FastAPI backend
      '^/api/.*': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
        // This is the CRITICAL part: forward cookies properly
        configure: (proxy, _options) => {
          proxy.on('proxyReq', (proxyReq, req, _res) => {
            // Forward cookies from browser → FastAPI
            if (req.headers.cookie) {
              proxyReq.setHeader('Cookie', req.headers.cookie);
            }
          });
        },
      },
    },
  },
})
