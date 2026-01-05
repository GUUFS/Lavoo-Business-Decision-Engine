import AdminSidebar from '../../../components/feature/AdminSidebar';
import AdminHeader from '../../../components/feature/AdminHeader';
import { toast } from 'react-toastify';


const API_BASE_URL = 'http://localhost:8000';

const getAuthToken = (): string | null => {
  return localStorage.getItem('access_token') || localStorage.getItem('token') || localStorage.getItem('authToken');
};

const getAuthHeaders = (): Record<string, string> => {
  const token = getAuthToken();
  return {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  };
};

interface UserDetails {
  id: number;
  name: string;
  email: string;
  join_date: string;
  subscription: string;
}

interface AnalysisDetail {
  id: number;
  title: string;
  user: string;
  user_email: string;
  type: string;
  status: string;
  confidence: number;
  duration: string;
  date: string;
  insights: number;
  recommendations: number;
  user_details?: UserDetails;
  // Full analysis data structure
  bottlenecks?: any[];
  business_strategies?: any[];
  ai_tools?: any[];
  roadmap?: any[];
  roi_metrics?: any[];
  [key: string]: any;
}

const AnalysisDetailModal = ({ analysis, onClose, onDownload }: { analysis: AnalysisDetail, onClose: () => void, onDownload: () => void }) => {
  if (!analysis) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black bg-opacity-50 backdrop-blur-sm overflow-y-auto">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-y-auto flex flex-col">
        {/* Modal Header */}
        <div className="sticky top-0 bg-white px-6 py-4 border-b border-gray-200 flex justify-between items-center z-10">
          <div>
            <h2 className="text-xl font-bold text-gray-900">{analysis.title}</h2>
            <p className="text-sm text-gray-500">Analysis ID: #{analysis.id} • {analysis.date}</p>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-full transition-colors">
            <i className="ri-close-line text-2xl text-gray-500"></i>
          </button>
        </div>

        {/* Modal Content */}
        <div className="p-6 space-y-8">

          {/* User Details Section */}
          {analysis.user_details && (
            <div className="bg-blue-50 rounded-xl p-5 border border-blue-100">
              <h3 className="text-lg font-semibold text-blue-900 mb-3 flex items-center gap-2">
                <i className="ri-user-star-line"></i> User Profile
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-blue-600 mb-1">Name</p>
                  <p className="font-medium text-gray-900">{analysis.user_details.name}</p>
                </div>
                <div>
                  <p className="text-sm text-blue-600 mb-1">Email</p>
                  <p className="font-medium text-gray-900">{analysis.user_details.email}</p>
                </div>
                <div>
                  <p className="text-sm text-blue-600 mb-1">Subscription</p>
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                    {analysis.user_details.subscription}
                  </span>
                </div>
                <div>
                  <p className="text-sm text-blue-600 mb-1">Member Since</p>
                  <p className="font-medium text-gray-900">{analysis.user_details.join_date}</p>
                </div>
              </div>
            </div>
          )}

          {/* Analysis Summary */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-gray-50 p-4 rounded-lg border border-gray-100">
              <p className="text-sm text-gray-500 mb-1">Type</p>
              <p className="font-medium">{analysis.type}</p>
            </div>
            <div className="bg-gray-50 p-4 rounded-lg border border-gray-100">
              <p className="text-sm text-gray-500 mb-1">Status</p>
              <span className={`px-2 py-1 rounded-full text-xs font-medium ${analysis.status === 'completed' ? 'bg-green-100 text-green-800' :
                analysis.status === 'processing' ? 'bg-blue-100 text-blue-800' : 'bg-red-100 text-red-800'
                }`}>
                {analysis.status.toUpperCase()}
              </span>
            </div>
            <div className="bg-gray-50 p-4 rounded-lg border border-gray-100">
              <p className="text-sm text-gray-500 mb-1">Confidence</p>
              <div className="flex items-center gap-2">
                <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div className="h-full bg-purple-500" style={{ width: `${analysis.confidence}%` }}></div>
                </div>
                <span className="font-bold text-purple-600">{analysis.confidence}%</span>
              </div>
            </div>
          </div>

          {/* Full Details Preview (Bottlenecks, etc.) */}
          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Analysis Highlights</h3>

            {/* Bottlenecks */}
            {analysis.bottlenecks && analysis.bottlenecks.length > 0 && (
              <div className="mb-6">
                <h4 className="font-medium text-gray-700 mb-2">Identified Bottlenecks</h4>
                <div className="space-y-3">
                  {analysis.bottlenecks.slice(0, 3).map((b: any, idx: number) => (
                    <div key={idx} className="bg-white border border-gray-200 rounded-lg p-3 shadow-sm">
                      <div className="flex justify-between items-start">
                        <span className="font-medium text-red-600">{b.title}</span>
                        <span className="text-xs bg-red-50 text-red-600 px-2 py-1 rounded">{b.priority}</span>
                      </div>
                      <p className="text-sm text-gray-600 mt-1 line-clamp-2">{b.description}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Recommendations */}
            {analysis.business_strategies && analysis.business_strategies.length > 0 && (
              <div>
                <h4 className="font-medium text-gray-700 mb-2">Top Recommendations</h4>
                <div className="space-y-3">
                  {analysis.business_strategies.slice(0, 3).map((s: any, idx: number) => (
                    <div key={idx} className="bg-white border border-gray-200 rounded-lg p-3 shadow-sm">
                      <p className="font-medium text-green-700">{s.title}</p>
                      <p className="text-sm text-gray-600 mt-1 line-clamp-2">{s.description}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Modal Footer */}
        <div className="sticky bottom-0 bg-white px-6 py-4 border-t border-gray-200 flex justify-end items-center gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 font-medium transition-colors"
          >
            Close
          </button>
          <button
            onClick={onDownload}
            className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 font-medium flex items-center gap-2 transition-colors shadow-sm"
          >
            <i className="ri-download-line"></i>
            Download Report
          </button>
        </div>
      </div>
    </div>
  );
};

export default function AdminAIAnalysis() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [filterStatus, setFilterStatus] = useState('all');
  const [showAdminDropdown, setShowAdminDropdown] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 8;

  const [analyses, setAnalyses] = useState<AnalysisDetail[]>([]);
  const [loading, setLoading] = useState(true);
  const [totalItems, setTotalItems] = useState(0);
  const [selectedAnalysis, setSelectedAnalysis] = useState<AnalysisDetail | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);

  // Fetch Analyses
  const fetchAnalyses = async () => {
    try {
      setLoading(true);
      const queryParams = new URLSearchParams({
        page: currentPage.toString(),
        limit: itemsPerPage.toString(),
        status: filterStatus === 'all' ? '' : filterStatus
      });

      const response = await fetch(`${API_BASE_URL}/api/business/admin/analyses?${queryParams}`, {
        headers: getAuthHeaders()
      });

      if (response.ok) {
        const data = await response.json();
        setAnalyses(data.data);
        setTotalItems(data.total);
      } else {
        console.error('Failed to fetch analyses');
      }
    } catch (error) {
      console.error('Error fetching analyses:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalyses();
  }, [currentPage, filterStatus]);

  const handleViewAnalysis = async (id: number) => {
    try {
      // Fetch detailed data including user info
      const response = await fetch(`${API_BASE_URL}/api/business/admin/analyses/${id}`, {
        headers: getAuthHeaders()
      });

      if (response.ok) {
        const data = await response.json();
        setSelectedAnalysis(data.data);
        setIsModalOpen(true);
      } else {
        console.error('Failed to fetch detail');
        toast.error('Could not load analysis details');
      }
    } catch (error) {
      console.error("Error loading detail:", error);
    }
  };

  const generatePDF = async (analysisData: any) => {
    try {
      setIsDownloading(true);
      const jsPDF = (await import('jspdf')).default;
      const doc = new jsPDF('p', 'mm', 'a4');
      const pageWidth = doc.internal.pageSize.getWidth();
      const pageHeight = doc.internal.pageSize.getHeight();
      // const companyName = "Guufs Global";

      // Simple PDF generation logic (simplified from Results page for reliability)
      // Header
      doc.setFillColor(249, 115, 22); // Orange
      doc.rect(0, 0, pageWidth, 40, 'F');
      doc.setTextColor(255, 255, 255);
      doc.setFontSize(22);
      doc.setFont('helvetica', 'bold');
      doc.text("Business Intelligence Report", pageWidth / 2, 20, { align: 'center' });
      doc.setFontSize(10);
      doc.text(`Generated for ${analysisData.user_details?.name || 'User'}`, pageWidth / 2, 30, { align: 'center' });

      // Content
      let y = 60;
      doc.setTextColor(51, 51, 51);

      // Goal
      doc.setFontSize(14);
      doc.setFont('helvetica', 'bold');
      doc.text("Business Goal", 20, y);
      y += 10;
      doc.setFontSize(11);
      doc.setFont('helvetica', 'normal');
      const goalLines = doc.splitTextToSize(analysisData.title || analysisData.business_goal || "N/A", pageWidth - 40);
      doc.text(goalLines, 20, y);
      y += goalLines.length * 7 + 10;

      // Bottlenecks
      if (analysisData.bottlenecks) {
        doc.setFontSize(14);
        doc.setFont('helvetica', 'bold');
        doc.text("Key Bottlenecks", 20, y);
        y += 10;
        analysisData.bottlenecks.forEach((b: any, i: number) => {
          doc.setFontSize(12);
          doc.setTextColor(220, 38, 38);
          doc.text(`${i + 1}. ${b.title}`, 20, y);
          y += 7;
          doc.setFontSize(10);
          doc.setTextColor(80, 80, 80);
          const desc = doc.splitTextToSize(b.description, pageWidth - 45);
          doc.text(desc, 25, y);
          y += desc.length * 5 + 5;

          if (y > pageHeight - 20) { doc.addPage(); y = 20; }
        });
      }
      y += 10;

      // Recommendations
      if (analysisData.business_strategies) {
        doc.setFontSize(14);
        doc.setFont('helvetica', 'bold');
        doc.setTextColor(51, 51, 51);
        doc.text("Strategic Recommendations", 20, y);
        y += 10;
        analysisData.business_strategies.forEach((s: any, i: number) => {
          doc.setFontSize(12);
          doc.setTextColor(22, 163, 74); // Green
          doc.text(`${i + 1}. ${s.title}`, 20, y);
          y += 7;
          doc.setFontSize(10);
          doc.setTextColor(80, 80, 80);
          const desc = doc.splitTextToSize(s.description, pageWidth - 45);
          doc.text(desc, 25, y);
          y += desc.length * 5 + 5;

          if (y > pageHeight - 20) { doc.addPage(); y = 20; }
        });
      }

      doc.save(`Analysis_Report_${analysisData.id}.pdf`);

    } catch (e) {
      console.error("PDF Generate Error", e);
      toast.error("Failed to generate PDF");
    } finally {
      setIsDownloading(false);
    }
  };

  const handleDownloadReport = async (analysis: AnalysisDetail) => {
    // If we already have details (e.g. from modal), use them.
    // But 'analysis' from table list might be partial.
    // So fetch full if needed.
    let dataToPrint = analysis;
    if (!analysis.bottlenecks) {
      const response = await fetch(`${API_BASE_URL}/api/business/admin/analyses/${analysis.id}`, { headers: getAuthHeaders() });
      if (response.ok) {
        const json = await response.json();
        dataToPrint = json.data;
      }
    }
    generatePDF(dataToPrint);
  };

  const totalPages = Math.ceil(totalItems / itemsPerPage);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'bg-green-100 text-green-600';
      case 'processing': return 'bg-blue-100 text-blue-600';
      case 'failed': return 'bg-red-100 text-red-600';
      case 'queued': return 'bg-yellow-100 text-yellow-600';
      default: return 'bg-gray-100 text-gray-600';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return 'ri-check-line';
      case 'processing': return 'ri-loader-line';
      case 'failed': return 'ri-close-line';
      case 'queued': return 'ri-time-line';
      default: return 'ri-question-line';
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 90) return 'text-green-600';
    if (confidence >= 80) return 'text-yellow-600';
    if (confidence >= 70) return 'text-orange-600';
    return 'text-red-600';
  };

  return (
    <div className="min-h-screen bg-gray-50 flex">
      <AdminSidebar
        isMobileMenuOpen={isMobileMenuOpen}
        setIsMobileMenuOpen={setIsMobileMenuOpen}
      />

      <div className="flex-1 flex flex-col">
        <AdminHeader setIsMobileMenuOpen={setIsMobileMenuOpen} />

        <div className="flex-1 p-4 md:p-6 lg:p-8">
          <div className="max-w-7xl mx-auto">
            {/* Header */}
            <div className="mb-6 md:mb-8 flex justify-between items-end">
              <div>
                <h1 className="text-2xl md:text-3xl font-bold text-gray-900 mb-2">AI Analysis Monitor</h1>
                <p className="text-gray-600">Monitor AI analysis performance and user activities</p>
              </div>
              <button
                onClick={fetchAnalyses}
                className="p-2 text-gray-600 hover:text-blue-600 transition-colors"
                title="Refresh Data"
              >
                <i className="ri-refresh-line text-xl"></i>
              </button>
            </div>

            {/* Quick Stats (Calculated from current page or fetch separate stats if needed - here we use placeholders or simple logic) */}
            {/* For real implementation we should probably have a stats endpoint, but for now we skip or keep static */}

            {/* Filters */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 mb-6">
              <select
                value={filterStatus}
                onChange={(e) => { setFilterStatus(e.target.value); setCurrentPage(1); }}
                className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">All Status</option>
                <option value="completed">Completed</option>
                <option value="processing">Processing</option>
                <option value="failed">Failed</option>
              </select>
            </div>

            {/* Analyses Table */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50 border-b border-gray-200">
                    <tr>
                      <th className="text-left py-3 px-4 font-medium text-gray-900">Analysis</th>
                      <th className="text-left py-3 px-4 font-medium text-gray-900">User</th>
                      <th className="text-left py-3 px-4 font-medium text-gray-900">Status</th>
                      <th className="text-left py-3 px-4 font-medium text-gray-900">Confidence</th>
                      <th className="text-left py-3 px-4 font-medium text-gray-900">Date</th>
                      <th className="text-left py-3 px-4 font-medium text-gray-900">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {loading ? (
                      <tr>
                        <td colSpan={6} className="py-8 text-center text-gray-500">
                          <i className="ri-loader-4-line text-2xl animate-spin mx-auto block mb-2"></i>
                          Loading analyses...
                        </td>
                      </tr>
                    ) : analyses.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="py-8 text-center text-gray-500">No analyses found.</td>
                      </tr>
                    ) : (
                      analyses.map((analysis) => (
                        <tr key={analysis.id} className="hover:bg-gray-50 transition-colors">
                          <td className="py-4 px-4">
                            <p className="font-medium text-gray-900 line-clamp-1 max-w-xs" title={analysis.title}>{analysis.title}</p>
                            <span className="text-xs text-gray-500">{analysis.type}</span>
                          </td>
                          <td className="py-4 px-4">
                            <div className="flex flex-col">
                              <span className="text-gray-900 font-medium">{analysis.user}</span>
                              <span className="text-xs text-gray-500">{analysis.user_email}</span>
                            </div>
                          </td>
                          <td className="py-4 px-4">
                            <div className="flex items-center gap-2">
                              <i className={`${getStatusIcon(analysis.status)} ${analysis.status === 'processing' ? 'animate-spin' : ''
                                } text-gray-400`}></i>
                              <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(analysis.status)}`}>
                                {analysis.status}
                              </span>
                            </div>
                          </td>
                          <td className="py-4 px-4">
                            {analysis.confidence > 0 ? (
                              <span className={`font-medium ${getConfidenceColor(analysis.confidence)}`}>
                                {analysis.confidence}%
                              </span>
                            ) : '-'}
                          </td>
                          <td className="py-4 px-4 text-sm text-gray-600">
                            {analysis.date}
                          </td>
                          <td className="py-4 px-4">
                            <div className="flex items-center gap-2">
                              <button
                                onClick={() => handleViewAnalysis(analysis.id)}
                                className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                                title="View Details"
                              >
                                <i className="ri-eye-line"></i>
                              </button>
                              <button
                                onClick={() => handleDownloadReport(analysis)}
                                disabled={isDownloading}
                                className="p-2 text-green-600 hover:bg-green-50 rounded-lg transition-colors disabled:opacity-50"
                                title="Download Report"
                              >
                                <i className="ri-download-line"></i>
                              </button>
                            </div>
                          </td>
                        </tr>
                      )))}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="px-4 py-4 border-t border-gray-200 flex justify-between items-center">
                  <span className="text-sm text-gray-600">Page {currentPage} of {totalPages}</span>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                      disabled={currentPage === 1}
                      className="px-3 py-1 border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50"
                    >
                      Previous
                    </button>
                    <button
                      onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                      disabled={currentPage === totalPages}
                      className="px-3 py-1 border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50"
                    >
                      Next
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Detail Modal */}
      {isModalOpen && selectedAnalysis && (
        <AnalysisDetailModal
          analysis={selectedAnalysis}
          onClose={() => setIsModalOpen(false)}
          onDownload={() => selectedAnalysis && handleDownloadReport(selectedAnalysis)}
        />
      )}
    </div>
  );
}