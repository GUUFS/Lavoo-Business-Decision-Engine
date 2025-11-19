import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { AppRoutes } from './router'
import ScrollToTop from './ScrollToTop';
import UpgradePage from './pages/dashboard/upgrade/page';


function App() {
  return (
    <BrowserRouter basename={__BASE_PATH__}>
      <ScrollToTop/>
      <Routes>
        <Route path="/dashboard/upgrade" element={<UpgradePage />} />
        {/* ... other routes */}
      </Routes>
      <AppRoutes />
    </BrowserRouter>
  )
}

export default App