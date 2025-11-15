import { useState } from 'react';
import { Link } from 'react-router-dom';
import AdminSidebar from '../../../components/feature/AdminSidebar';

export default function AdminSecurity() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [showAdminDropdown, setShowAdminDropdown] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 5;

  const securityMetrics = {
    threatLevel: 'Low',
    blockedAttacks: 247,
    failedLogins: 18,
    suspiciousActivity: 5,
    activeFirewallRules: 156,
    lastSecurityScan: '2 hours ago'
  };

  const securityEvents = [
    {
      id: 1,
      type: 'failed_login',
      severity: 'medium',
      user: 'unknown@suspicious.com',
      ip: '192.168.1.100',
      location: 'Unknown',
      description: 'Multiple failed login attempts detected',
      time: '5 minutes ago',
      status: 'blocked'
    },
    {
      id: 2,
      type: 'suspicious_activity',
      severity: 'high',
      user: 'john.doe@company.com',
      ip: '10.0.0.45',
      location: 'New York, US',
      description: 'Unusual API access pattern detected',
      time: '15 minutes ago',
      status: 'investigating'
    },
    {
      id: 3,
      type: 'blocked_attack',
      severity: 'high',
      user: 'N/A',
      ip: '203.0.113.0',
      location: 'Unknown',
      description: 'SQL injection attempt blocked',
      time: '1 hour ago',
      status: 'blocked'
    },
    {
      id: 4,
      type: 'password_change',
      severity: 'low',
      user: 'sarah.johnson@email.com',
      ip: '172.16.0.10',
      location: 'California, US',
      description: 'Password changed successfully',
      time: '2 hours ago',
      status: 'completed'
    },
    {
      id: 5,
      type: 'admin_access',
      severity: 'medium',
      user: 'admin@company.com',
      ip: '192.168.1.50',
      location: 'Office Network',
      description: 'Admin panel accessed',
      time: '3 hours ago',
      status: 'completed'
    },
    {
      id: 6,
      type: 'failed_login',
      severity: 'high',
      user: 'attacker@malicious.com',
      ip: '198.51.100.42',
      location: 'Unknown',
      description: 'Brute force attack detected',
      time: '4 hours ago',
      status: 'blocked'
    },
    {
      id: 7,
      type: 'suspicious_activity',
      severity: 'medium',
      user: 'user@example.com',
      ip: '192.0.2.15',
      location: 'London, UK',
      description: 'Unusual download pattern detected',
      time: '5 hours ago',
      status: 'investigating'
    },
    {
      id: 8,
      type: 'blocked_attack',
      severity: 'high',
      user: 'N/A',
      ip: '203.0.113.99',
      location: 'Unknown',
      description: 'XSS attack attempt blocked',
      time: '6 hours ago',
      status: 'blocked'
    }
  ];

  // Pagination calculations
  const totalPages = Math.ceil(securityEvents.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const endIndex = startIndex + itemsPerPage;
  const currentEvents = securityEvents.slice(startIndex, endIndex);

  const firewallRules = [
    {
      id: 1,
      name: 'Block Suspicious IPs',
      type: 'IP Block',
      status: 'active',
      priority: 'high',
      description: 'Block known malicious IP addresses',
      created: '2024-01-15',
      hits: 1247
    },
    {
      id: 2,
      name: 'Rate Limiting',
      type: 'Rate Limit',
      status: 'active',
      priority: 'medium',
      description: 'Limit API requests per minute',
      created: '2024-01-20',
      hits: 89
    },
    {
      id: 3,
      name: 'SQL Injection Protection',
      type: 'WAF Rule',
      status: 'active',
      priority: 'high',
      description: 'Detect and block SQL injection attempts',
      created: '2024-01-10',
      hits: 23
    },
    {
      id: 4,
      name: 'Geographic Restrictions',
      type: 'Geo Block',
      status: 'inactive',
      priority: 'low',
      description: 'Block access from specific countries',
      created: '2024-02-01',
      hits: 0
    }
  ];

  const vulnerabilityScans = [
    {
      id: 1,
      type: 'Full System Scan',
      status: 'completed',
      severity: 'low',
      findings: 2,
      date: '2024-02-26 08:00',
      duration: '45 minutes'
    },
    {
      id: 2,
      type: 'Database Security Scan',
      status: 'completed',
      severity: 'medium',
      findings: 1,
      date: '2024-02-25 20:00',
      duration: '23 minutes'
    },
    {
      id: 3,
      type: 'Web Application Scan',
      status: 'in_progress',
      severity: 'unknown',
      findings: 0,
      date: '2024-02-26 14:30',
      duration: 'Running...'
    }
  ];

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'high': return 'bg-red-100 text-red-600';
      case 'medium': return 'bg-yellow-100 text-yellow-600';
      case 'low': return 'bg-green-100 text-green-600';
      default: return 'bg-gray-100 text-gray-600';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'bg-green-100 text-green-600';
      case 'blocked': return 'bg-red-100 text-red-600';
      case 'investigating': return 'bg-yellow-100 text-yellow-600';
      case 'completed': return 'bg-blue-100 text-blue-600';
      case 'inactive': return 'bg-gray-100 text-gray-600';
      case 'in_progress': return 'bg-blue-100 text-blue-600';
      default: return 'bg-gray-100 text-gray-600';
    }
  };

  const getEventIcon = (type: string) => {
    switch (type) {
      case 'failed_login': return 'ri-lock-line';
      case 'suspicious_activity': return 'ri-eye-line';
      case 'blocked_attack': return 'ri-shield-line';
      case 'password_change': return 'ri-key-line';
      case 'admin_access': return 'ri-admin-line';
      default: return 'ri-alert-line';
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
              <h1 className="text-2xl md:text-3xl font-bold text-gray-900 mb-2">Security Center</h1>
              <p className="text-gray-600">Monitor security threats, manage firewall rules, and track system vulnerabilities</p>
            </div>

            {/* Security Overview */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6 mb-8">
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 md:p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                    <i className="ri-shield-check-line text-xl text-green-600"></i>
                  </div>
                  <span className="text-sm font-medium px-2 py-1 rounded-full bg-green-100 text-green-600">{securityMetrics.threatLevel}</span>
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
              <div className="p-4 md:p-6 border-b border-gray-200">
                <h3 className="text-lg font-semibold text-gray-900">Recent Security Events</h3>
              </div>
              <div className="divide-y divide-gray-200">
                {currentEvents.map((event) => (
                  <div key={event.id} className="p-4 md:p-6 hover:bg-gray-50">
                    <div className="flex items-start gap-4">
                      <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                        event.severity === 'high' ? 'bg-red-100' :
                        event.severity === 'medium' ? 'bg-yellow-100' : 'bg-green-100'
                      }`}>
                        <i className={`${getEventIcon(event.type)} ${
                          event.severity === 'high' ? 'text-red-600' :
                          event.severity === 'medium' ? 'text-yellow-600' : 'text-green-600'
                        }`}></i>
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${getSeverityColor(event.severity)}`}>
                            {event.severity.charAt(0).toUpperCase() + event.severity.slice(1)}
                          </span>
                          <span className="text-sm font-medium text-gray-900">{event.user}</span>
                          <span className="text-sm text-gray-500">{event.time}</span>
                        </div>
                        <p className="text-gray-700 mb-2">{event.description}</p>
                        <div className="flex items-center gap-4 text-sm text-gray-600">
                          <span>IP: {event.ip}</span>
                          <span>Location: {event.location}</span>
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(event.status)}`}>
                            {event.status.charAt(0).toUpperCase() + event.status.slice(1)}
                          </span>
                        </div>
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
                      Showing {startIndex + 1} to {Math.min(endIndex, securityEvents.length)} of {securityEvents.length} events
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

            {/* Firewall Rules and Vulnerability Scans */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
              {/* Firewall Rules */}
              <div className="bg-white rounded-xl shadow-sm border border-gray-200">
                <div className="p-4 md:p-6 border-b border-gray-200">
                  <h3 className="text-lg font-semibold text-gray-900">Firewall Rules</h3>
                </div>
                <div className="p-4 md:p-6">
                  <div className="space-y-4">
                    {firewallRules.map((rule) => (
                      <div key={rule.id} className="border border-gray-200 rounded-lg p-4">
                        <div className="flex items-center justify-between mb-2">
                          <h4 className="font-medium text-gray-900">{rule.name}</h4>
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(rule.status)}`}>
                            {rule.status.charAt(0).toUpperCase() + rule.status.slice(1)}
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
                </div>
              </div>

              {/* Vulnerability Scans */}
              <div className="bg-white rounded-xl shadow-sm border border-gray-200">
                <div className="p-4 md:p-6 border-b border-gray-200">
                  <h3 className="text-lg font-semibold text-gray-900">Vulnerability Scans</h3>
                </div>
                <div className="p-4 md:p-6">
                  <div className="space-y-4">
                    {vulnerabilityScans.map((scan) => (
                      <div key={scan.id} className="border border-gray-200 rounded-lg p-4">
                        <div className="flex items-center justify-between mb-2">
                          <h4 className="font-medium text-gray-900">{scan.type}</h4>
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(scan.status)}`}>
                            {scan.status.replace('_', ' ').charAt(0).toUpperCase() + scan.status.replace('_', ' ').slice(1)}
                          </span>
                        </div>
                        <div className="flex items-center justify-between text-sm">
                          <span className="text-gray-600">Findings: {scan.findings}</span>
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${getSeverityColor(scan.severity)}`}>
                            {scan.severity.charAt(0).toUpperCase() + scan.severity.slice(1)}
                          </span>
                        </div>
                        <div className="flex items-center justify-between text-xs text-gray-500 mt-2">
                          <span>{scan.date}</span>
                          <span>{scan.duration}</span>
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
    </div>
  );
}