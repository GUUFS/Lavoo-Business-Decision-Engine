import { useState } from 'react';
import { Link } from 'react-router-dom';
import AdminSidebar from '../../../components/feature/AdminSidebar';

export default function AdminSystemHealth() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [showAdminDropdown, setShowAdminDropdown] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 5;

  const systemMetrics = {
    uptime: 99.97,
    responseTime: 245,
    cpuUsage: 34.2,
    memoryUsage: 67.8,
    diskUsage: 45.3,
    activeConnections: 1247,
    analysesProcessed: 3429,
    errorRate: 0.03
  };

  const services = [
    {
      name: 'AI Analysis Engine',
      status: 'healthy',
      uptime: 99.98,
      responseTime: 180,
      lastCheck: '2 minutes ago'
    },
    {
      name: 'Database Cluster',
      status: 'healthy',
      uptime: 99.95,
      responseTime: 45,
      lastCheck: '1 minute ago'
    },
    {
      name: 'Authentication Service',
      status: 'healthy',
      uptime: 99.99,
      responseTime: 120,
      lastCheck: '30 seconds ago'
    },
    {
      name: 'File Storage',
      status: 'warning',
      uptime: 99.85,
      responseTime: 320,
      lastCheck: '3 minutes ago'
    },
    {
      name: 'Email Service',
      status: 'healthy',
      uptime: 99.92,
      responseTime: 890,
      lastCheck: '1 minute ago'
    },
    {
      name: 'Payment Gateway',
      status: 'healthy',
      uptime: 99.96,
      responseTime: 450,
      lastCheck: '2 minutes ago'
    }
  ];

  const recentAlerts = [
    {
      id: 1,
      type: 'warning',
      service: 'File Storage',
      message: 'High response time detected (>300ms)',
      time: '5 minutes ago',
      status: 'investigating'
    },
    {
      id: 2,
      type: 'info',
      service: 'AI Analysis Engine',
      message: 'Scheduled maintenance completed successfully',
      time: '2 hours ago',
      status: 'resolved'
    },
    {
      id: 3,
      type: 'error',
      service: 'Database Cluster',
      message: 'Connection timeout resolved',
      time: '6 hours ago',
      status: 'resolved'
    },
    {
      id: 4,
      type: 'warning',
      service: 'Email Service',
      message: 'Queue processing delay',
      time: '1 day ago',
      status: 'resolved'
    },
    {
      id: 5,
      type: 'error',
      service: 'Payment Gateway',
      message: 'Transaction processing error',
      time: '1 day ago',
      status: 'resolved'
    },
    {
      id: 6,
      type: 'warning',
      service: 'Authentication Service',
      message: 'Increased login latency detected',
      time: '2 days ago',
      status: 'resolved'
    },
    {
      id: 7,
      type: 'info',
      service: 'Database Cluster',
      message: 'Backup completed successfully',
      time: '2 days ago',
      status: 'resolved'
    },
    {
      id: 8,
      type: 'error',
      service: 'File Storage',
      message: 'Disk space warning threshold reached',
      time: '3 days ago',
      status: 'resolved'
    }
  ];

  // Pagination calculations
  const totalPages = Math.ceil(recentAlerts.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const endIndex = startIndex + itemsPerPage;
  const currentAlerts = recentAlerts.slice(startIndex, endIndex);

  const performanceData = [
    { time: '00:00', cpu: 25, memory: 60, analyses: 45 },
    { time: '04:00', cpu: 18, memory: 58, analyses: 23 },
    { time: '08:00', cpu: 42, memory: 72, analyses: 89 },
    { time: '12:00', cpu: 38, memory: 68, analyses: 156 },
    { time: '16:00', cpu: 45, memory: 75, analyses: 134 },
    { time: '20:00', cpu: 34, memory: 65, analyses: 98 }
  ];

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy': return 'bg-green-100 text-green-600';
      case 'warning': return 'bg-yellow-100 text-yellow-600';
      case 'error': return 'bg-red-100 text-red-600';
      case 'maintenance': return 'bg-blue-100 text-blue-600';
      default: return 'bg-gray-100 text-gray-600';
    }
  };

  const getAlertColor = (type: string) => {
    switch (type) {
      case 'error': return 'bg-red-100 text-red-600';
      case 'warning': return 'bg-yellow-100 text-yellow-600';
      case 'info': return 'bg-blue-100 text-blue-600';
      default: return 'bg-gray-100 text-gray-600';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy': return 'ri-check-line';
      case 'warning': return 'ri-alert-line';
      case 'error': return 'ri-close-line';
      case 'maintenance': return 'ri-tools-line';
      default: return 'ri-question-line';
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex">
      <AdminSidebar 
        isMobileMenuOpen={isMobileMenuOpen} 
        setIsMobileMenuOpen={setIsMobileMenuOpen} 
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
            
            </div>
            <div className="relative">
              <button
                onClick={() => setShowAdminDropdown(!showAdminDropdown)}
                className="flex items-center gap-2 px-3 py-2 text-gray-700 hover:text-gray-900 transition-colors"
              >
                <div className="w-8 h-8 bg-orange-100 rounded-full flex items-center justify-center">
                  <i className="ri-user-line text-orange-600"></i>
                </div>
                <span className="font-medium">John Admin</span>
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
                    <button className="w-full flex items-center px-4 py-2 text-gray-700 hover:bg-gray-50 transition-colors">
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
            <div className="mb-6 md:mb-8">
              <h1 className="text-2xl md:text-3xl font-bold text-gray-900 mb-2">System Health Monitor</h1>
              <p className="text-gray-600">Real-time monitoring of AI analysis platform performance and services</p>
            </div>

            {/* System Overview */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6 mb-8">
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 md:p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                    <i className="ri-time-line text-xl text-green-600"></i>
                  </div>
                  <span className="text-sm font-medium px-2 py-1 rounded-full bg-green-100 text-green-600">Excellent</span>
                </div>
                <h3 className="text-sm font-medium text-gray-600 mb-1">System Uptime</h3>
                <p className="text-2xl font-bold text-gray-900">{systemMetrics.uptime}%</p>
              </div>

              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 md:p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                    <i className="ri-speed-line text-xl text-blue-600"></i>
                  </div>
                  <span className="text-sm font-medium px-2 py-1 rounded-full bg-green-100 text-green-600">Good</span>
                </div>
                <h3 className="text-sm font-medium text-gray-600 mb-1">Avg Response Time</h3>
                <p className="text-2xl font-bold text-gray-900">{systemMetrics.responseTime}ms</p>
              </div>

              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 md:p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
                    <i className="ri-cpu-line text-xl text-purple-600"></i>
                  </div>
                  <span className="text-sm font-medium px-2 py-1 rounded-full bg-green-100 text-green-600">Normal</span>
                </div>
                <h3 className="text-sm font-medium text-gray-600 mb-1">CPU Usage</h3>
                <p className="text-2xl font-bold text-gray-900">{systemMetrics.cpuUsage}%</p>
              </div>

              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 md:p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="w-12 h-12 bg-orange-100 rounded-lg flex items-center justify-center">
                    <i className="ri-database-line text-xl text-orange-600"></i>
                  </div>
                  <span className="text-sm font-medium px-2 py-1 rounded-full bg-yellow-100 text-yellow-600">Monitor</span>
                </div>
                <h3 className="text-sm font-medium text-gray-600 mb-1">Memory Usage</h3>
                <p className="text-2xl font-bold text-gray-900">{systemMetrics.memoryUsage}%</p>
              </div>
            </div>

            {/* Services Status */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 md:p-6 mb-8">
              <h3 className="text-lg font-semibold text-gray-900 mb-6">Service Status</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {services.map((service) => (
                  <div key={service.name} className="border border-gray-200 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-3">
                      <h4 className="font-medium text-gray-900">{service.name}</h4>
                      <div className="flex items-center gap-2">
                        <i className={`${getStatusIcon(service.status)} text-lg ${
                          service.status === 'healthy' ? 'text-green-600' :
                          service.status === 'warning' ? 'text-yellow-600' : 'text-red-600'
                        }`}></i>
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(service.status)}`}>
                          {service.status.charAt(0).toUpperCase() + service.status.slice(1)}
                        </span>
                      </div>
                    </div>
                    <div className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600">Uptime</span>
                        <span className="font-medium">{service.uptime}%</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600">Response Time</span>
                        <span className="font-medium">{service.responseTime}ms</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600">Last Check</span>
                        <span className="text-gray-500">{service.lastCheck}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Performance Chart */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 md:p-6 mb-8">
              <h3 className="text-lg font-semibold text-gray-900 mb-6">24-Hour Performance</h3>
              <div className="h-64 flex items-end justify-between gap-4">
                {performanceData.map((data, index) => (
                  <div key={index} className="flex-1 flex flex-col items-center">
                    <div className="w-full flex flex-col gap-1 mb-2">
                      <div 
                        className="w-full bg-blue-500 rounded-t-sm"
                        style={{ height: `${(data.cpu / 100) * 80}px` }}
                        title={`CPU: ${data.cpu}%`}
                      ></div>
                      <div 
                        className="w-full bg-green-500"
                        style={{ height: `${(data.memory / 100) * 80}px` }}
                        title={`Memory: ${data.memory}%`}
                      ></div>
                      <div 
                        className="w-full bg-purple-500 rounded-b-sm"
                        style={{ height: `${(data.analyses / 200) * 80}px` }}
                        title={`Analyses: ${data.analyses}`}
                      ></div>
                    </div>
                    <span className="text-sm text-gray-600">{data.time}</span>
                  </div>
                ))}
              </div>
              <div className="flex justify-center gap-6 mt-4">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 bg-blue-500 rounded"></div>
                  <span className="text-sm text-gray-600">CPU Usage</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 bg-green-500 rounded"></div>
                  <span className="text-sm text-gray-600">Memory Usage</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 bg-purple-500 rounded"></div>
                  <span className="text-sm text-gray-600">Analyses Processed</span>
                </div>
              </div>
            </div>

            {/* Recent Alerts */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
              <div className="p-4 md:p-6 border-b border-gray-200">
                <h3 className="text-lg font-semibold text-gray-900">Recent Alerts</h3>
              </div>
              <div className="divide-y divide-gray-200">
                {currentAlerts.map((alert) => (
                  <div key={alert.id} className="p-4 md:p-6 hover:bg-gray-50">
                    <div className="flex items-start gap-4">
                      <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                        alert.type === 'error' ? 'bg-red-100' :
                        alert.type === 'warning' ? 'bg-yellow-100' : 'bg-blue-100'
                      }`}>
                        <i className={`${
                          alert.type === 'error' ? 'ri-close-circle-line text-red-600' :
                          alert.type === 'warning' ? 'ri-alert-line text-yellow-600' : 'ri-information-line text-blue-600'
                        }`}></i>
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${getAlertColor(alert.type)}`}>
                            {alert.type.charAt(0).toUpperCase() + alert.type.slice(1)}
                          </span>
                          <span className="text-sm font-medium text-gray-900">{alert.service}</span>
                          <span className="text-sm text-gray-500">{alert.time}</span>
                        </div>
                        <p className="text-gray-700 mb-2">{alert.message}</p>
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                          alert.status === 'resolved' ? 'bg-green-100 text-green-600' : 'bg-yellow-100 text-yellow-600'
                        }`}>
                          {alert.status.charAt(0).toUpperCase() + alert.status.slice(1)}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="px-4 py-4 border-t border-gray-200">
                  <div className="flex items-center justify-between">
                    <div className="text-sm text-gray-600">
                      Showing {startIndex + 1} to {Math.min(endIndex, recentAlerts.length)} of {recentAlerts.length} alerts
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                        disabled={currentPage === 1}
                        className="px-3 py-1 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
                      >
                        Previous
                      </button>
                      {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
                        <button
                          key={page}
                          onClick={() => setCurrentPage(page)}
                          className={`px-3 py-1 rounded-lg text-sm font-medium whitespace-nowrap ${
                            currentPage === page
                              ? 'bg-red-600 text-white'
                              : 'border border-gray-300 text-gray-700 hover:bg-gray-50'
                          }`}
                        >
                          {page}
                        </button>
                      ))}
                      <button
                        onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                        disabled={currentPage === totalPages}
                        className="px-3 py-1 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
                      >
                        Next
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}