
import { useState } from 'react';
import AdminSidebar from '../../../components/feature/AdminSidebar';

export default function AdminDatabase() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isProfileDropdownOpen, setIsProfileDropdownOpen] = useState(false);

  const databaseMetrics = {
    totalSize: '2.4 TB',
    activeConnections: 47,
    queriesPerSecond: 1247,
    avgResponseTime: 45,
    uptime: 99.97,
    backupStatus: 'completed'
  };

  const databases = [
    {
      name: 'ai_analysis_prod',
      type: 'PostgreSQL',
      size: '1.2 TB',
      status: 'healthy',
      connections: 23,
      lastBackup: '2 hours ago',
      tables: 47
    },
    {
      name: 'user_data_prod',
      type: 'PostgreSQL',
      size: '890 GB',
      status: 'healthy',
      connections: 15,
      lastBackup: '2 hours ago',
      tables: 28
    },
    {
      name: 'analytics_warehouse',
      type: 'PostgreSQL',
      size: '340 GB',
      status: 'warning',
      connections: 9,
      lastBackup: '4 hours ago',
      tables: 15
    },
    {
      name: 'session_cache',
      type: 'Redis',
      size: '12 GB',
      status: 'healthy',
      connections: 156,
      lastBackup: 'N/A',
      tables: 0
    }
  ];

  const backupHistory = [
    {
      id: 1,
      database: 'ai_analysis_prod',
      type: 'Full Backup',
      size: '1.2 TB',
      status: 'completed',
      duration: '45 minutes',
      time: '2024-02-26 02:00'
    },
    {
      id: 2,
      database: 'user_data_prod',
      type: 'Full Backup',
      size: '890 GB',
      status: 'completed',
      duration: '32 minutes',
      time: '2024-02-26 02:00'
    },
    {
      id: 3,
      database: 'analytics_warehouse',
      type: 'Incremental',
      size: '45 GB',
      status: 'failed',
      duration: '12 minutes',
      time: '2024-02-26 02:00'
    },
    {
      id: 4,
      database: 'ai_analysis_prod',
      type: 'Incremental',
      size: '23 GB',
      status: 'completed',
      duration: '8 minutes',
      time: '2024-02-25 14:00'
    }
  ];

  const performanceData = [
    { time: '00:00', queries: 890, connections: 34, responseTime: 42 },
    { time: '04:00', queries: 456, connections: 18, responseTime: 38 },
    { time: '08:00', queries: 1234, connections: 52, responseTime: 48 },
    { time: '12:00', queries: 1567, connections: 67, responseTime: 52 },
    { time: '16:00', queries: 1890, connections: 78, responseTime: 58 },
    { time: '20:00', queries: 1247, connections: 47, responseTime: 45 }
  ];

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy': return 'bg-green-100 text-green-600';
      case 'warning': return 'bg-yellow-100 text-yellow-600';
      case 'error': return 'bg-red-100 text-red-600';
      case 'completed': return 'bg-green-100 text-green-600';
      case 'failed': return 'bg-red-100 text-red-600';
      case 'slow': return 'bg-yellow-100 text-yellow-600';
      default: return 'bg-gray-100 text-gray-600';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy': return 'ri-check-line';
      case 'warning': return 'ri-alert-line';
      case 'error': return 'ri-close-line';
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
          <div className="flex items-center justify-between">
            <button
              onClick={() => setIsMobileMenuOpen(true)}
              className="md:hidden p-2 rounded-lg text-gray-600 hover:bg-gray-100"
            >
              <i className="ri-menu-line text-xl"></i>
            </button>
            <div className="flex-1"></div>
            <div className="relative">
              <button 
                onClick={() => setIsProfileDropdownOpen(!isProfileDropdownOpen)}
                className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50 transition-colors"
              >
                <div className="w-8 h-8 bg-red-100 rounded-full flex items-center justify-center">
                  <i className="ri-user-line text-red-600"></i>
                </div>
                <span className="font-medium text-gray-900">Admin User</span>
                <i className="ri-arrow-down-s-line text-gray-400"></i>
              </button>
              
              {/* Profile Dropdown */}
              {isProfileDropdownOpen && (
                <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border border-gray-200 py-2 z-50">
                  <button className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 flex items-center gap-3">
                    <i className="ri-user-line text-gray-500"></i>
                    Profile
                  </button>
                  <button className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 flex items-center gap-3">
                    <i className="ri-logout-box-line text-gray-500"></i>
                    Logout
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="flex-1 p-4 md:p-6 lg:p-8">
          <div className="max-w-7xl mx-auto">
            {/* Header */}
            <div className="mb-6 md:mb-8">
              <h1 className="text-2xl md:text-3xl font-bold text-gray-900 mb-2">Database Management</h1>
              <p className="text-gray-600">Monitor database performance, manage backups, and track query analytics</p>
            </div>

            {/* Database Overview */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6 mb-8">
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 md:p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                    <i className="ri-database-line text-xl text-blue-600"></i>
                  </div>
                  <span className="text-sm font-medium px-2 py-1 rounded-full bg-green-100 text-green-600">Healthy</span>
                </div>
                <h3 className="text-sm font-medium text-gray-600 mb-1">Total Size</h3>
                <p className="text-2xl font-bold text-gray-900">{databaseMetrics.totalSize}</p>
              </div>

              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 md:p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                    <i className="ri-links-line text-xl text-green-600"></i>
                  </div>
                  <span className="text-sm font-medium px-2 py-1 rounded-full bg-green-100 text-green-600">Normal</span>
                </div>
                <h3 className="text-sm font-medium text-gray-600 mb-1">Active Connections</h3>
                <p className="text-2xl font-bold text-gray-900">{databaseMetrics.activeConnections}</p>
              </div>

              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 md:p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
                    <i className="ri-speed-line text-xl text-purple-600"></i>
                  </div>
                  <span className="text-sm font-medium px-2 py-1 rounded-full bg-green-100 text-green-600">Optimal</span>
                </div>
                <h3 className="text-sm font-medium text-gray-600 mb-1">Queries/Second</h3>
                <p className="text-2xl font-bold text-gray-900">{databaseMetrics.queriesPerSecond}</p>
              </div>

              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 md:p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="w-12 h-12 bg-orange-100 rounded-lg flex items-center justify-center">
                    <i className="ri-time-line text-xl text-orange-600"></i>
                  </div>
                  <span className="text-sm font-medium px-2 py-1 rounded-full bg-green-100 text-green-600">Good</span>
                </div>
                <h3 className="text-sm font-medium text-gray-600 mb-1">Avg Response Time</h3>
                <p className="text-2xl font-bold text-gray-900">{databaseMetrics.avgResponseTime}ms</p>
              </div>
            </div>

            {/* Database Instances */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 md:p-6 mb-8">
              <h3 className="text-lg font-semibold text-gray-900 mb-6">Database Instances</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {databases.map((db) => (
                  <div key={db.name} className="border border-gray-200 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-3">
                      <h4 className="font-medium text-gray-900">{db.name}</h4>
                      <div className="flex items-center gap-2">
                        <i className={`${getStatusIcon(db.status)} text-lg ${
                          db.status === 'healthy' ? 'text-green-600' :
                          db.status === 'warning' ? 'text-yellow-600' : 'text-red-600'
                        }`}></i>
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(db.status)}`}>
                          {db.status.charAt(0).toUpperCase() + db.status.slice(1)}
                        </span>
                      </div>
                    </div>
                    <div className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600">Type</span>
                        <span className="font-medium">{db.type}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600">Size</span>
                        <span className="font-medium">{db.size}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600">Connections</span>
                        <span className="font-medium">{db.connections}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600">Tables</span>
                        <span className="font-medium">{db.tables}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600">Last Backup</span>
                        <span className="text-gray-500">{db.lastBackup}</span>
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
                        style={{ height: `${(data.queries / 2000) * 80}px` }}
                        title={`Queries: ${data.queries}`}
                      ></div>
                      <div 
                        className="w-full bg-green-500"
                        style={{ height: `${(data.connections / 100) * 80}px` }}
                        title={`Connections: ${data.connections}`}
                      ></div>
                      <div 
                        className="w-full bg-orange-500 rounded-b-sm"
                        style={{ height: `${(data.responseTime / 100) * 80}px` }}
                        title={`Response Time: ${data.responseTime}ms`}
                      ></div>
                    </div>
                    <span className="text-sm text-gray-600">{data.time}</span>
                  </div>
                ))}
              </div>
              <div className="flex justify-center gap-6 mt-4">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 bg-blue-500 rounded"></div>
                  <span className="text-sm text-gray-600">Queries/Hour</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 bg-green-500 rounded"></div>
                  <span className="text-sm text-gray-600">Connections</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 bg-orange-500 rounded"></div>
                  <span className="text-sm text-gray-600">Response Time</span>
                </div>
              </div>
            </div>

            {/* Backup History */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200">
              <div className="p-4 md:p-6 border-b border-gray-200">
                <h3 className="text-lg font-semibold text-gray-900">Backup History</h3>
              </div>
              <div className="p-4 md:p-6">
                <div className="space-y-4">
                  {backupHistory.map((backup) => (
                    <div key={backup.id} className="border border-gray-200 rounded-lg p-4">
                      <div className="flex items-center justify-between mb-2">
                        <h4 className="font-medium text-gray-900">{backup.database}</h4>
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(backup.status)}`}>
                          {backup.status.charAt(0).toUpperCase() + backup.status.slice(1)}
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-gray-600">{backup.type}</span>
                        <span className="font-medium">{backup.size}</span>
                      </div>
                      <div className="flex items-center justify-between text-xs text-gray-500 mt-2">
                        <span>{backup.time}</span>
                        <span>{backup.duration}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
 
      </div>
    </div>
  );
}