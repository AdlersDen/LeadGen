import { Toaster } from "@/components/ui/toaster"
import { QueryClientProvider } from '@tanstack/react-query'
import { queryClientInstance } from '@/lib/query-client'
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import PageNotFound from './lib/PageNotFound';
import { AuthProvider } from '@/lib/AuthContext';
import AppLayout from '@/components/layout/AppLayout';
import ErrorBoundary from '@/components/ErrorBoundary';
import Dashboard from '@/pages/Dashboard';
import Discover from '@/pages/Discover';
import Companies from '@/pages/Companies';
import Contacts from '@/pages/Contacts';
import Outreach from '@/pages/Outreach';
import Runs from '@/pages/Runs';
import Unsubscribe from '@/pages/Unsubscribe';

function App() {
  return (
    <AuthProvider>
      <QueryClientProvider client={queryClientInstance}>
        <Router>
          <Routes>
            <Route element={<AppLayout />}>
              <Route path="/" element={<ErrorBoundary><Dashboard /></ErrorBoundary>} />
              <Route path="/discover" element={<ErrorBoundary><Discover /></ErrorBoundary>} />
              <Route path="/companies" element={<ErrorBoundary><Companies /></ErrorBoundary>} />
              <Route path="/contacts" element={<ErrorBoundary><Contacts /></ErrorBoundary>} />
              <Route path="/outreach" element={<ErrorBoundary><Outreach /></ErrorBoundary>} />
              <Route path="/runs" element={<ErrorBoundary><Runs /></ErrorBoundary>} />
            </Route>
            {/* Standalone page — no AppLayout nav */}
            <Route path="/unsubscribe" element={<ErrorBoundary><Unsubscribe /></ErrorBoundary>} />
            <Route path="*" element={<PageNotFound />} />
          </Routes>
        </Router>
        <Toaster />
      </QueryClientProvider>
    </AuthProvider>
  )
}

export default App