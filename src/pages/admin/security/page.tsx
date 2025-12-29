import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import AdminSidebar from '../../../components/feature/AdminSidebar';
import { getAuthToken } from '../../../utils/auth';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:3000/api';

// Create axios instance with auth
const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Authorization': `Bearer ${getAuthToken()}`
  }
});

// Add auth token to all requests
api.interceptors.request.use((config) => {
  const token = getAuthToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default function AdminSecurity() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [showAdminDropdown, setShowAdminDropdown] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');
  const itemsPerPage = 10;

  // State for REAL data
  const [securityMetrics, setSecurityMetrics] = useState({
    threatLevel: 'Loading...',
    blockedAttacks: 0,
    failedLogins: 0,
    suspiciousActivity: 0,
    activeFirewallRules: 0,
    lastSecurityScan: 'Loading...'
  });

  const [securityEvents, setSecurityEvents] = useState<any[]>([]);
  const [firewallRules, setFirewallRules] = useState<any[]>([]);
  const [vulnerabilityScans, setVulnerabilityScans] = useState<any[]>([]);

  const handleLogout = () => {
    // Clear all auth tokens
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    document.cookie = 'access_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
    document.cookie = 'refresh_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';

    // Redirect to login
    window.location.href = '/login';
  };

  const fetchSecurityData = async (isInitial = false) => {
    try {
      if (isInitial) setLoading(true);
      else setRefreshing(true);

      // Fetch metrics
      const metricsRes = await api.get('/security/metrics');
      setSecurityMetrics(metricsRes.data);

      // Fetch security events
      const eventsRes = await api.get('/security/events?limit=50');
      setSecurityEvents(eventsRes.data.events || []);

      // Fetch firewall rules
      const rulesRes = await api.get('/security/firewall-rules');
      setFirewallRules(rulesRes.data.rules || []);

      // Fetch vulnerability scans
      const scansRes = await api.get('/security/vulnerability-scans');
      setVulnerabilityScans(scansRes.data.scans || []);

      setLoading(false);
      setRefreshing(false);
    } catch (err: any) {
      console.error('Failed to fetch security data:', err);
      setError(err.response?.data?.error || 'Failed to load security data');
      setLoading(false);
      setRefreshing(false);
    }
  };

  // Fetch all security data
  useEffect(() => {
    fetchSecurityData(true);

    // Auto-refresh every 30 seconds
    const interval = setInterval(() => fetchSecurityData(false), 30000);
    return () => clearInterval(interval);
  }, []);

  // Pagination calculations
  const totalPages = Math.ceil(securityEvents.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const endIndex = startIndex + itemsPerPage;
  const currentEvents = securityEvents.slice(startIndex, endIndex);

  const getSeverityColor = (severity: string) => {
    switch (severity?.toLowerCase()) {
      case 'high': return 'bg-red-100 text-red-600';
      case 'medium': return 'bg-yellow-100 text-yellow-600';
      case 'low': return 'bg-green-100 text-green-600';
      default: return 'bg-gray-100 text-gray-600';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'active': return 'bg-green-100 text-green-600';
      case 'blocked': return 'bg-red-100 text-red-600';
      case 'investigating': return 'bg-yellow-100 text-yellow-600';
      case 'completed': return 'bg-blue-100 text-blue-600';
      case 'logged': return 'bg-gray-100 text-gray-600';
      case 'inactive': return 'bg-gray-100 text-gray-600';
      case 'in_progress': return 'bg-blue-100 text-blue-600';
      default: return 'bg-gray-100 text-gray-600';
    }
  };

  const getEventIcon = (type: string) => {
    switch (type?.toLowerCase()) {
      case 'failed_login': return 'ri-lock-line';
      case 'login': return 'ri-login-box-line';
      case 'suspicious_activity': return 'ri-eye-line';
      case 'blocked_attack': return 'ri-shield-line';
      case 'sql_injection': return 'ri-shield-cross-line';
      case 'xss_attempt': return 'ri-shield-cross-line';
      case 'brute_force': return 'ri-skull-line';
      case 'password_change': return 'ri-key-line';
      case 'admin_access': return 'ri-admin-line';
      case 'blocked_ip': return 'ri-forbid-line';
      default: return 'ri-alert-line';
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return 'just now';
    if (minutes < 60) return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
    if (hours < 24) return `${hours} hour${hours > 1 ? 's' : ''} ago`;
    if (days < 7) return `${days} day${days > 1 ? 's' : ''} ago`;

    return date.toLocaleDateString();
  };

  const getThreatLevelColor = (level: string) => {
    switch (level?.toLowerCase()) {
      case 'high': return 'bg-red-100 text-red-600';
      case 'medium': return 'bg-yellow-100 text-yellow-600';
      case 'low': return 'bg-green-100 text-green-600';
      default: return 'bg-gray-100 text-gray-600';
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-orange-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">Loading security dashboard...</p>
        </div>
      </div>
    );
  }

  if (error && securityEvents.length === 0) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <i className="ri-error-warning-line text-6xl text-red-600 mb-4"></i>
          <p className="text-xl text-gray-900 mb-2">Failed to load security data</p>
          <p className="text-gray-600 mb-4">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 flex">
      <AdminSidebar
        isMobileMenuOpen={isMobileMenuOpen}
        setIsMobileMenuOpen={setIsMobileMenuOpen}
        isCollapsed={false}
        setIsCollapsed={() => { }}
      />

      <div className="flex-1 ml-0 flex flex-col">
        {/* Admin Header */}
        <div className="bg-white border-b border-gray-200 px-4 md:px-6 lg:px-8 py-4">
          <div className="flex justify-between items-center">
            <div className="flex items-center">
              <button
                className="md:hidden p-2 text-gray-600 hover:text-gray-900 mr-3"
                onClick={() => setIsMobileMenuOpen(true)}
              >
                <i className="ri-menu-line text-xl"></i>
              </button>
              <h2 className="text-lg font-semibold text-gray-900">Admin User</h2>
            </div>
            <div className="relative">
              <button
                onClick={() => setShowAdminDropdown(!showAdminDropdown)}
                className="flex items-center gap-2 px-3 py-2 text-gray-700 hover:text-gray-900 transition-colors"
              >
                <div className="w-8 h-8 bg-orange-100 rounded-full flex items-center justify-center">
                  <i className="ri-user-line text-orange-600"></i>
                </div>
                <span className="font-medium">Admin</span>
                <i className="ri-arrow-down-s-line"></i>
              </button>

              {showAdminDropdown && (
                <>
                  <div
                    className="fixed inset-0 z-40"
                    onClick={() => setShowAdminDropdown(false)}
                  ></div>
                  <div className="absolute top-full right-0 mt-2 w-48 bg-white rounded-lg shadow-xl border border-gray-200 py-2 z-50">
                    <Link
                      to="/admin/profile"
                      className="w-full flex items-center px-4 py-2 text-gray-700 hover:bg-gray-50 transition-colors"
                      onClick={() => setShowAdminDropdown(false)}
                    >
                      <i className="ri-user-line mr-3"></i>
                      Profile
                    </Link>
                    <button
                      onClick={handleLogout}
                      className="w-full flex items-center px-4 py-2 text-gray-700 hover:bg-gray-50 transition-colors"
                    >
                      <i className="ri-logout-box-line mr-3"></i>
                      Logout
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>

        <div className="flex-1 p-4 md:p-6 lg:p-8">
          <div className="max-w-7xl mx-auto">
            {/* Header */}
            <div className="mb-6 md:mb-8 flex items-center justify-between">
              <div>
                <h1 className="text-2xl md:text-3xl font-bold text-gray-900 mb-2">Security Center</h1>
                <p className="text-gray-600">Real-time security monitoring and threat detection</p>
              </div>
              <button
                onClick={() => fetchSecurityData(false)}
                disabled={refreshing}
                className={`px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 flex items-center gap-2 transition-all ${refreshing ? 'opacity-75 cursor-wait' : ''}`}
              >
                <i className={`ri-refresh-line ${refreshing ? 'animate-spin' : ''}`}></i>
                {refreshing ? 'Refreshing...' : 'Refresh'}
              </button>
            </div>

            {/* Security Overview */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6 mb-8">
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 md:p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                    <i className="ri-shield-check-line text-xl text-green-600"></i>
                  </div>
                  <span className={`text-sm font-medium px-2 py-1 rounded-full ${getThreatLevelColor(securityMetrics.threatLevel)}`}>
                    {securityMetrics.threatLevel}
                  </span>
                </div>
                <h3 className="text-sm font-medium text-gray-600 mb-1">Threat Level</h3>
                <p className="text-2xl font-bold text-gray-900">{securityMetrics.threatLevel}</p>
              </div>

              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 md:p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="w-12 h-12 bg-red-100 rounded-lg flex items-center justify-center">
                    <i className="ri-shield-line text-xl text-red-600"></i>
                  </div>
                  <span className="text-sm font-medium px-2 py-1 rounded-full bg-green-100 text-green-600">24h</span>
                </div>
                <h3 className="text-sm font-medium text-gray-600 mb-1">Blocked Attacks</h3>
                <p className="text-2xl font-bold text-gray-900">{securityMetrics.blockedAttacks}</p>
              </div>

              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 md:p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="w-12 h-12 bg-yellow-100 rounded-lg flex items-center justify-center">
                    <i className="ri-lock-line text-xl text-yellow-600"></i>
                  </div>
                  <span className="text-sm font-medium px-2 py-1 rounded-full bg-yellow-100 text-yellow-600">Monitor</span>
                </div>
                <h3 className="text-sm font-medium text-gray-600 mb-1">Failed Logins</h3>
                <p className="text-2xl font-bold text-gray-900">{securityMetrics.failedLogins}</p>
              </div>

              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 md:p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
                    <i className="ri-eye-line text-xl text-purple-600"></i>
                  </div>
                  <span className="text-sm font-medium px-2 py-1 rounded-full bg-purple-100 text-purple-600">Active</span>
                </div>
                <h3 className="text-sm font-medium text-gray-600 mb-1">Suspicious Activity</h3>
                <p className="text-2xl font-bold text-gray-900">{securityMetrics.suspiciousActivity}</p>
              </div>
            </div>

            {/* Security Events */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 mb-8">
              <div className="p-4 md:p-6 border-b border-gray-200 flex items-center justify-between">
                <h3 className="text-lg font-semibold text-gray-900">Recent Security Events</h3>
                <span className="text-sm text-gray-500">{securityEvents.length} total events</span>
              </div>
              <div className="divide-y divide-gray-200">
                {currentEvents.length === 0 ? (
                  <div className="p-8 text-center text-gray-500">
                    <i className="ri-shield-check-line text-4xl mb-2"></i>
                    <p>No security events recorded yet</p>
                  </div>
                ) : (
                  currentEvents.map((event) => (
                    <div key={event.id} className="p-4 md:p-6 hover:bg-gray-50">
                      <div className="flex items-start gap-4">
                        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${event.severity === 'high' ? 'bg-red-100' :
                          event.severity === 'medium' ? 'bg-yellow-100' : 'bg-green-100'
                          }`}>
                          <i className={`${getEventIcon(event.type)} ${event.severity === 'high' ? 'text-red-600' :
                            event.severity === 'medium' ? 'text-yellow-600' : 'text-green-600'
                            }`}></i>
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1 flex-wrap">
                            <span className={`px-2 py-1 rounded-full text-xs font-medium ${getSeverityColor(event.severity)}`}>
                              {event.severity?.charAt(0).toUpperCase() + event.severity?.slice(1)}
                            </span>
                            <span className="text-sm font-medium text-gray-900">{event.type?.replace(/_/g, ' ').toUpperCase()}</span>
                            <span className="text-sm text-gray-500">{formatDate(event.created_at)}</span>
                          </div>
                          <p className="text-gray-700 mb-2">{event.description}</p>
                          <div className="flex items-center gap-4 text-sm text-gray-600 flex-wrap">
                            {event.ip_address && <span>IP: {event.ip_address}</span>}
                            {event.location && <span>Location: {event.location}</span>}
                            <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(event.status)}`}>
                              {event.status?.charAt(0).toUpperCase() + event.status?.slice(1)}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="px-4 py-4 border-t border-gray-200">
                  <div className="flex items-center justify-between flex-wrap gap-4">
                    <div className="text-sm text-gray-600">
                      Showing {startIndex + 1} to {Math.min(endIndex, securityEvents.length)} of {securityEvents.length} events
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                        disabled={currentPage === 1}
                        className="px-3 py-1 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        Previous
                      </button>
                      {Array.from({ length: Math.min(5, totalPages) }, (_, i) => i + 1).map((page) => (
                        <button
                          key={page}
                          onClick={() => setCurrentPage(page)}
                          className={`px-3 py-1 rounded-lg text-sm font-medium ${currentPage === page
                            ? 'bg-orange-600 text-white'
                            : 'border border-gray-300 text-gray-700 hover:bg-gray-50'
                            }`}
                        >
                          {page}
                        </button>
                      ))}
                      <button
                        onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                        disabled={currentPage === totalPages}
                        className="px-3 py-1 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        Next
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Firewall Rules and Vulnerability Scans */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
              {/* Firewall Rules */}
              <div className="bg-white rounded-xl shadow-sm border border-gray-200">
                <div className="p-4 md:p-6 border-b border-gray-200">
                  <h3 className="text-lg font-semibold text-gray-900">Firewall Rules</h3>
                </div>
                <div className="p-4 md:p-6">
                  {firewallRules.length === 0 ? (
                    <p className="text-center text-gray-500 py-8">No firewall rules configured</p>
                  ) : (
                    <div className="space-y-4">
                      {firewallRules.slice(0, 4).map((rule) => (
                        <div key={rule.id} className="border border-gray-200 rounded-lg p-4">
                          <div className="flex items-center justify-between mb-2">
                            <h4 className="font-medium text-gray-900">{rule.name}</h4>
                            <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(rule.status)}`}>
                              {rule.status?.charAt(0).toUpperCase() + rule.status?.slice(1)}
                            </span>
                          </div>
                          <p className="text-sm text-gray-600 mb-2">{rule.description}</p>
                          <div className="flex items-center justify-between text-xs text-gray-500">
                            <span>{rule.type}</span>
                            <span>{rule.hits} hits</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Vulnerability Scans */}
              <div className="bg-white rounded-xl shadow-sm border border-gray-200">
                <div className="p-4 md:p-6 border-b border-gray-200">
                  <h3 className="text-lg font-semibold text-gray-900">Vulnerability Scans</h3>
                </div>
                <div className="p-4 md:p-6">
                  {vulnerabilityScans.length === 0 ? (
                    <p className="text-center text-gray-500 py-8">No scans performed yet</p>
                  ) : (
                    <div className="space-y-4">
                      {vulnerabilityScans.slice(0, 3).map((scan) => (
                        <div key={scan.id} className="border border-gray-200 rounded-lg p-4">
                          <div className="flex items-center justify-between mb-2">
                            <h4 className="font-medium text-gray-900">{scan.scan_type}</h4>
                            <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(scan.status)}`}>
                              {scan.status?.replace('_', ' ').charAt(0).toUpperCase() + scan.status?.replace('_', ' ').slice(1)}
                            </span>
                          </div>
                          <div className="flex items-center justify-between text-sm">
                            <span className="text-gray-600">Findings: {scan.findings}</span>
                            {scan.severity && (
                              <span className={`px-2 py-1 rounded-full text-xs font-medium ${getSeverityColor(scan.severity)}`}>
                                {scan.severity.charAt(0).toUpperCase() + scan.severity.slice(1)}
                              </span>
                            )}
                          </div>
                          <div className="flex items-center justify-between text-xs text-gray-500 mt-2">
                            <span>{formatDate(scan.started_at)}</span>
                            <span>{scan.duration_seconds ? `${scan.duration_seconds}s` : 'Running...'}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}