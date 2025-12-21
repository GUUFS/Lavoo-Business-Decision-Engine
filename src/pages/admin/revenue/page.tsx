import { useState, useEffect } from 'react';
import AdminSidebar from '../../../components/feature/AdminSidebar';
import AdminHeader from '../../../components/feature/AdminHeader';

const API_BASE_URL = 'http://localhost:8000';

type StatusType =
  | 'completed'
  | 'active'
  | 'paid'
  | 'pending'
  | 'approved'
  | 'failed'
  | 'refunded'
  | 'processing';

interface Transaction {
  id: string;
  user: string;
  user_email: string;
  plan: string;
  amount: number;
  status: StatusType;
  date: string;
}

interface Commission {
  user_id: number;
  user: string;
  user_email: string;
  total_commissions: number;
  pending_commissions: number;
  processing_commissions: number;
  paid_commissions: number;
  payout_status: StatusType;
  last_commission_date?: string | null;
  available_payment_methods: string[];
  has_payout_account: boolean;
}

interface Payout {
  id: number;
  user: string;
  user_email: string;
  amount: number;
  currency: string;
  status: StatusType;
  method: string;
  requested_at: string;
  completed_at?: string | null;
  failure_reason?: string | null;
}

interface RevenueStats {
  monthly_revenue: number;
  total_subscription_revenue: number;
  referral_commissions_paid: number;
  refunds: number;
  growth_rate: number;
}

export default function AdminRevenue() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<'transactions' | 'commissions' | 'payouts'>('transactions');
  const [revenueStats, setRevenueStats] = useState<RevenueStats | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [commissions, setCommissions] = useState<Commission[]>([]);
  const [payouts, setPayouts] = useState<Payout[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [totalItems, setTotalItems] = useState<number>(0);
  const itemsPerPage = 10;

  const [dialog, setDialog] = useState<{
    open: boolean;
    userId?: number;
    name?: string;
    loading?: boolean;
    availableMethods?: string[];
    selectedMethod?: string;
    pendingAmount?: number;
    customAmount?: number;
  }>({
    open: false,
    userId: undefined,
    name: undefined,
    loading: false,
    availableMethods: [],
    selectedMethod: undefined,
    pendingAmount: 0,
    customAmount: 0,
  });

  const [toast, setToast] = useState<{
    show: boolean;
    type: 'success' | 'error' | 'warning';
    message: string;
  }>({ show: false, type: 'success', message: '' });

  const showToast = (type: 'success' | 'error' | 'warning', message: string) => {
    setToast({ show: true, type, message });
    setTimeout(() => setToast({ ...toast, show: false }), 5000);
  };

  const openDialog = (userId: number, name: string, availableMethods: string[], pendingAmount: number) => {
    setDialog({
      open: true,
      userId,
      name,
      loading: false,
      availableMethods,
      selectedMethod: availableMethods[0] || 'stripe',
      pendingAmount,
      customAmount: pendingAmount
    });
  };

  const closeDialog = () => {
    setDialog({
      open: false,
      userId: undefined,
      name: undefined,
      loading: false,
      availableMethods: [],
      selectedMethod: undefined
    });
  };

  const [historyModal, setHistoryModal] = useState<{
    open: boolean;
    loading: boolean;
    user: { name: string; email: string } | null;
    commissions: any[];
  }>({
    open: false,
    loading: false,
    user: null,
    commissions: []
  });

  // Helper function for status colors


  // Helper function for status colors
  const getStatusColor = (status: string) => {
    const s = status?.toLowerCase();
    if (['completed', 'active', 'paid'].includes(s)) return 'bg-green-100 text-green-600';
    if (['pending', 'approved'].includes(s)) return 'bg-yellow-100 text-yellow-600';
    if (['processing'].includes(s)) return 'bg-blue-100 text-blue-600';
    if (['failed', 'cancelled'].includes(s)) return 'bg-red-100 text-red-600';
    return 'bg-gray-100 text-gray-600';
  };

  // Fetch initial data
  useEffect(() => {
    fetchRevenueStats();
    fetchTransactions();
    fetchCommissions();
    fetchPayouts();
  }, [currentPage, activeTab]);

  const handleViewHistory = async (userId: number) => {
    setHistoryModal(prev => ({ ...prev, open: true, loading: true }));
    try {
      const token = document.cookie
        .split('; ')
        .find((row) => row.startsWith('access_token='))
        ?.split('=')[1];

      const response = await fetch(`${API_BASE_URL}/api/control/revenue/commissions/user/${userId}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setHistoryModal(prev => ({
          ...prev,
          user: data.user,
          commissions: data.commissions,
          loading: false
        }));
      } else {
        showToast('error', 'Failed to fetch history');
        setHistoryModal(prev => ({ ...prev, loading: false, open: false }));
      }
    } catch (error) {
      console.error('Error fetching history:', error);
      setHistoryModal(prev => ({ ...prev, loading: false }));
    }
  };

  // ... (keeping existing render logic)

  // In the Commissions Table loop:
  // After the "Approve & Pay" button logic (or alongside it)
  // ...


  // ...

  // Render History Modal at the end (before or after other modals)
  {
    historyModal.open && (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
        <div className="bg-white rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] flex flex-col animate-scale-in">
          <div className="p-6 border-b border-gray-100 flex items-center justify-between">
            <div>
              <h3 className="text-xl font-bold text-gray-900">Commission History</h3>
              {historyModal.user && (
                <p className="text-sm text-gray-600">
                  {historyModal.user.name} ({historyModal.user.email})
                </p>
              )}
            </div>
            <button
              onClick={() => setHistoryModal(prev => ({ ...prev, open: false }))}
              className="p-2 hover:bg-gray-100 rounded-full transition"
            >
              <i className="ri-close-line text-xl text-gray-500"></i>
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-6">
            {historyModal.loading ? (
              <div className="py-12 text-center">
                <div className="animate-spin w-8 h-8 border-4 border-red-500 border-t-transparent rounded-full mx-auto"></div>
                <p className="mt-2 text-sm text-gray-500">Loading history...</p>
              </div>
            ) : historyModal.commissions.length === 0 ? (
              <div className="text-center py-12 text-gray-500">No commission history found.</div>
            ) : (
              <div className="space-y-6">
                {/* Provide a summary or timeline view */}
                {/* Grouping by Month/Year or just a list */}
                <table className="w-full text-sm text-left">
                  <thead className="text-xs text-gray-500 uppercase bg-gray-50">
                    <tr>
                      <th className="px-4 py-3">Date</th>
                      <th className="px-4 py-3">Referred User</th>
                      <th className="px-4 py-3">Plan</th>
                      <th className="px-4 py-3">Amount</th>
                      <th className="px-4 py-3">Status</th>
                      <th className="px-4 py-3">Payout Info</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {historyModal.commissions.map((item: any) => (
                      <tr key={item.commission_id} className="hover:bg-gray-50">
                        <td className="px-4 py-3 whitespace-nowrap">
                          <div className="font-medium text-gray-900">{item.created_at.split(' ')[0]}</div>
                          <div className="text-xs text-gray-500">{item.created_at.split(' ')[1]}</div>
                        </td>
                        <td className="px-4 py-3">
                          <div className="font-medium text-gray-900">{item.referred_user}</div>
                          <div className="text-xs text-gray-500">{item.referred_user_email}</div>
                        </td>
                        <td className="px-4 py-3">{item.subscription_plan}</td>
                        <td className="px-4 py-3 font-medium text-gray-900">${item.amount.toFixed(2)}</td>
                        <td className="px-4 py-3">
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(item.status)}`}>
                            {item.status}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          {item.paid_at ? (
                            <div>
                              <div className="text-xs text-green-600 font-medium">Paid: {item.paid_at}</div>
                              <div className="text-xs text-gray-500 capitalize">{item.payout_method || 'Manual'}</div>
                            </div>
                          ) : item.status === 'processing' ? (
                            <span className="text-xs text-blue-600">Processing Payout</span>
                          ) : (
                            <span className="text-xs text-gray-400">-</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <div className="p-4 border-t border-gray-100 bg-gray-50 flex justify-end">
            <button
              onClick={() => setHistoryModal(prev => ({ ...prev, open: false }))}
              className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-white transition"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    )
  }

  useEffect(() => {
    if (activeTab === 'transactions') {
      fetchTransactions();
    } else if (activeTab === 'commissions') {
      fetchCommissions();
    } else {
      fetchPayouts();
    }
  }, [activeTab, currentPage]);

  const fetchRevenueStats = async () => {
    try {
      const token = document.cookie
        .split('; ')
        .find((row) => row.startsWith('access_token='))
        ?.split('=')[1];

      const response = await fetch(`${API_BASE_URL}/api/control/revenue/stats`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setRevenueStats(data);
      }
    } catch (error) {
      console.error('Error fetching revenue stats:', error);
    }
  };

  const fetchTransactions = async () => {
    try {
      setLoading(true);
      const token = document.cookie
        .split('; ')
        .find((row) => row.startsWith('access_token='))
        ?.split('=')[1];

      const offset = (currentPage - 1) * itemsPerPage;
      const response = await fetch(`${API_BASE_URL}/api/control/revenue/transactions?limit=${itemsPerPage}&offset=${offset}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setTransactions(data.transactions);
        setTotalItems(data.total);
      }
    } catch (error) {
      console.error('Error fetching transactions:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchCommissions = async () => {
    try {
      setLoading(true);
      const token = document.cookie
        .split('; ')
        .find((row) => row.startsWith('access_token='))
        ?.split('=')[1];

      const offset = (currentPage - 1) * itemsPerPage;
      const response = await fetch(`${API_BASE_URL}/api/control/revenue/commissions?limit=${itemsPerPage}&offset=${offset}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setCommissions(data.commissions);
        setTotalItems(data.total);
      }
    } catch (error) {
      console.error('Error fetching commissions:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchPayouts = async () => {
    try {
      setLoading(true);
      const token = document.cookie
        .split('; ')
        .find((row) => row.startsWith('access_token='))
        ?.split('=')[1];

      const offset = (currentPage - 1) * itemsPerPage;
      const response = await fetch(`${API_BASE_URL}/api/control/revenue/payouts?limit=${itemsPerPage}&offset=${offset}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setPayouts(data.payouts);
        setTotalItems(data.total);
      }
    } catch (error) {
      console.error('Error fetching payouts:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleApproveCommissions = async () => {
    if (!dialog.userId) return;

    setDialog(prev => ({ ...prev, loading: true }));

    try {
      const token = document.cookie
        .split('; ')
        .find((row) => row.startsWith('access_token='))
        ?.split('=')[1];

      const response = await fetch(`${API_BASE_URL}/api/control/revenue/commissions/approve/${dialog.userId}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          payment_method: dialog.selectedMethod,
          amount: dialog.customAmount
        }),
      });

      const result = await response.json();

      if (response.ok) {
        // Handle different response statuses
        switch (result.status) {
          case 'success':
            let successMsg = result.message;
            if (result.transfer_id) {
              successMsg += ` (Transfer ID: ${result.transfer_id})`;
            } else if (result.provider_response && result.provider_response.id) {
              successMsg += ` (ID: ${result.provider_response.id})`;
            }
            console.log('Provider Response:', result.provider_response);
            showToast('success', successMsg);
            break;
          case 'processing':
            showToast('warning', result.message);
            break;
          case 'failed':
            showToast('error', result.message);
            break;
          case 'info':
            showToast('warning', result.message);
            break;
          default:
            showToast('success', result.message || 'Operation completed');
        }
      } else {
        // HTTP error response
        const errorMessage = result.detail || result.message || 'Failed to process payout';
        showToast('error', errorMessage);
      }

      // Always refresh data to show actual database state
      fetchCommissions();
      fetchRevenueStats();
      fetchPayouts();
      closeDialog();

    } catch (error) {
      console.error('Error approving commissions:', error);
      showToast('error', 'Network error: Failed to connect to server');

    } finally {
      setDialog(prev => ({ ...prev, loading: false }));
    }
  };

  const totalPages = Math.ceil(totalItems / itemsPerPage);

  if (!revenueStats) {
    return (
      <div className="min-h-screen bg-gray-50 flex">
        <AdminSidebar
          isMobileMenuOpen={isMobileMenuOpen}
          setIsMobileMenuOpen={setIsMobileMenuOpen}
        />
        <div className="flex-1 flex items-center justify-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-red-500"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 flex">
      <AdminSidebar
        isMobileMenuOpen={isMobileMenuOpen}
        setIsMobileMenuOpen={setIsMobileMenuOpen}
      />

      {/* Toast Notification */}
      {toast.show && (
        <div className="fixed top-6 right-6 z-50 animate-slide-in">
          <div className={`flex items-center gap-4 px-8 py-4 rounded-xl shadow-2xl text-white font-bold text-lg min-w-[300px] border-l-8 ${toast.type === 'success' ? 'bg-green-600 border-green-800' :
              toast.type === 'warning' ? 'bg-yellow-500 border-yellow-700 text-gray-900' :
                'bg-red-600 border-red-800'
            }`}>
            <i className={`ri-${toast.type === 'success' ? 'check' : toast.type === 'warning' ? 'alert' : 'close'}-fill text-3xl`}></i>
            <div className="flex-1">
              <div className="text-xl capitalize mb-0.5">{toast.type}</div>
              <p className="text-sm font-medium opacity-90">{toast.message}</p>
            </div>
          </div>
        </div>
      )}

      {/* Approval Dialog */}
      {dialog.open && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full p-6 animate-scale-in">
            <div className="flex items-center gap-4 mb-6">
              <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center flex-shrink-0">
                <i className="ri-money-dollar-circle-line text-2xl text-green-600"></i>
              </div>
              <div>
                <h3 className="text-xl font-bold text-gray-900">Approve & Pay Commissions</h3>
                <p className="text-sm text-gray-600">For: <span className="font-medium">{dialog.name}</span></p>
              </div>
            </div>

            <div className="space-y-5">

              {/* Amount Input */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Payout Amount (USD) <span className="text-red-500">*</span>
                </label>
                <input
                  type="number"
                  step="0.01"
                  min="5.00"
                  max={dialog.pendingAmount}
                  placeholder={`Max: $${dialog.pendingAmount?.toFixed(2) || '0.00'} `}
                  className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-green-500 focus:border-green-500 text-lg font-medium"
                  value={dialog.customAmount || ''}
                  onChange={(e) => {
                    const val = parseFloat(e.target.value) || 0;
                    setDialog(prev => ({ ...prev, customAmount: val }));
                  }}
                />
                <p className="text-xs text-gray-500 mt-2">
                  Available: <strong>${dialog.pendingAmount?.toFixed(2) || '0.00'}</strong> | Minimum payout: $5.00
                </p>
              </div>

              {/* Payment Method Selection */}
              {dialog.availableMethods && dialog.availableMethods.length > 0 ? (
                <>
                  <div>
                    <p className="text-sm font-medium text-gray-700 mb-3">Payment Method</p>
                    <div className="space-y-2">
                      {dialog.availableMethods.includes('stripe') && (
                        <label className="flex items-center gap-3 p-3 rounded-lg border-2 transition-all cursor-pointer hover:border-purple-500">
                          <input
                            type="radio"
                            name="method"
                            value="stripe"
                            checked={dialog.selectedMethod === 'stripe'}
                            onChange={() => setDialog(prev => ({ ...prev, selectedMethod: 'stripe' }))}
                            className="w-5 h-5 text-purple-600"
                          />
                          <div className="flex-1">
                            <div className="font-medium text-gray-900">Stripe Connect</div>
                            <div className="text-xs text-gray-600">Instant payout • Recommended</div>
                          </div>
                          <i className="ri-bank-card-line text-purple-600 text-xl"></i>
                        </label>
                      )}
                      {dialog.availableMethods.includes('flutterwave') && (
                        <label className="flex items-center gap-3 p-3 rounded-lg border-2 transition-all cursor-pointer hover:border-orange-500">
                          <input
                            type="radio"
                            name="method"
                            value="flutterwave"
                            checked={dialog.selectedMethod === 'flutterwave'}
                            onChange={() => setDialog(prev => ({ ...prev, selectedMethod: 'flutterwave' }))}
                            className="w-5 h-5 text-orange-600"
                          />
                          <div className="flex-1">
                            <div className="font-medium text-gray-900">Bank Transfer</div>
                            <div className="text-xs text-gray-600">1–3 business days</div>
                          </div>
                          <i className="ri-bank-line text-orange-600 text-xl"></i>
                        </label>
                      )}
                    </div>
                  </div>
                </>
              ) : (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-center">
                  <p className="text-sm text-red-600 font-medium">
                    Warning: User has no payout account configured
                  </p>
                  <p className="text-xs text-red-500 mt-1">
                    Commissions will be approved but payout cannot be sent until they set up Stripe or bank details.
                  </p>
                </div>
              )}

              {/* Info Box */}
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <p className="text-sm text-blue-800 leading-relaxed">
                  <strong>Payout Flow:</strong><br />
                  • Commissions marked as <strong>processing</strong> while payout is initiated<br />
                  • ${dialog.customAmount || '0.00'} sent via <strong>{dialog.selectedMethod === 'stripe' ? 'Stripe' : 'Bank Transfer'}</strong><br />
                  • On success: status changes to <strong>paid</strong><br />
                  • On failure: status reverts to <strong>pending</strong> (can retry)
                </p>
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={closeDialog}
                disabled={dialog.loading}
                className="flex-1 px-5 py-3 border border-gray-300 text-gray-700 rounded-xl font-medium hover:bg-gray-50 transition"
              >
                Cancel
              </button>
              <button
                onClick={handleApproveCommissions}
                disabled={
                  dialog.loading ||
                  !dialog.customAmount ||
                  dialog.customAmount < 5 ||
                  dialog.customAmount > (dialog.pendingAmount || 0)
                }
                className="flex-1 px-5 py-3 bg-green-600 text-white rounded-xl font-medium hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 transition"
              >
                {dialog.loading ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                    Processing...
                  </>
                ) : (
                  <>
                    <i className="ri-check-double-line"></i>
                    Approve & Pay Now
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="flex-1 flex flex-col">
        {/* Admin Header */}
        <AdminHeader setIsMobileMenuOpen={setIsMobileMenuOpen} />

        <div className="flex-1 p-4 md:p-6 lg:p-8">
          <div className="max-w-7xl mx-auto">
            {/* Header */}
            <div className="mb-6 md:mb-8">
              <h1 className="text-2xl md:text-3xl font-bold text-gray-900 mb-2">Revenue Analytics</h1>
              <p className="text-gray-600">Monitor subscription revenue, transactions, and financial performance</p>
            </div>

            {/* Revenue Stats */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6 mb-8">
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 md:p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                    <i className="ri-money-dollar-circle-line text-xl text-green-600"></i>
                  </div>
                  <span className="text-sm font-medium px-2 py-1 rounded-full bg-green-100 text-green-600">
                    +{revenueStats.growth_rate}%
                  </span>
                </div>
                <h3 className="text-sm font-medium text-gray-600 mb-1">Monthly Revenue</h3>
                <p className="text-2xl font-bold text-gray-900">${revenueStats.monthly_revenue.toLocaleString()}</p>
              </div>

              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 md:p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                    <i className="ri-refresh-line text-xl text-blue-600"></i>
                  </div>
                </div>
                <h3 className="text-sm font-medium text-gray-600 mb-1">Subscription Revenue</h3>
                <p className="text-2xl font-bold text-gray-900">${revenueStats.total_subscription_revenue.toLocaleString()}</p>
              </div>

              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 md:p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
                    <i className="ri-share-line text-xl text-purple-600"></i>
                  </div>
                </div>
                <h3 className="text-sm font-medium text-gray-600 mb-1">Commissions Paid</h3>
                <p className="text-2xl font-bold text-gray-900">${revenueStats.referral_commissions_paid.toLocaleString()}</p>
              </div>

              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 md:p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="w-12 h-12 bg-red-100 rounded-lg flex items-center justify-center">
                    <i className="ri-refund-line text-xl text-red-600"></i>
                  </div>
                </div>
                <h3 className="text-sm font-medium text-gray-600 mb-1">Refunds</h3>
                <p className="text-2xl font-bold text-gray-900">${revenueStats.refunds.toLocaleString()}</p>
              </div>
            </div>

            {/* Tabs and Table */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
              <div className="p-4 md:p-6 border-b border-gray-200 flex items-center justify-between flex-wrap gap-4">
                <div className="flex gap-6">
                  <button
                    onClick={() => {
                      setActiveTab('transactions');
                      setCurrentPage(1);
                    }}
                    className={`pb-4 px-4 font-bold border-b-2 transition-all flex items-center gap-3 ${activeTab === 'transactions'
                      ? 'border-red-600 text-red-600'
                      : 'border-transparent text-gray-500 hover:text-gray-900 hover:bg-gray-50 rounded-t-lg'
                      }`}
                  >
                    <i className="ri-exchange-dollar-line text-2xl"></i>
                    <span>Transactions</span>
                  </button>
                  <button
                    onClick={() => {
                      setActiveTab('commissions');
                      setCurrentPage(1);
                    }}
                    className={`pb-4 px-4 font-bold border-b-2 transition-all flex items-center gap-3 ${activeTab === 'commissions'
                      ? 'border-red-600 text-red-600'
                      : 'border-transparent text-gray-500 hover:text-gray-900 hover:bg-gray-50 rounded-t-lg'
                      }`}
                  >
                    <i className="ri-coin-line text-2xl"></i>
                    <span>Commissions</span>
                  </button>
                  <button
                    onClick={() => {
                      setActiveTab('payouts');
                      setCurrentPage(1);
                    }}
                    className={`pb-4 px-4 font-bold border-b-2 transition-all flex items-center gap-3 ${activeTab === 'payouts'
                      ? 'border-red-600 text-red-600'
                      : 'border-transparent text-gray-500 hover:text-gray-900 hover:bg-gray-50 rounded-t-lg'
                      }`}
                  >
                    <i className="ri-bank-card-line text-2xl"></i>
                    <span>Payouts</span>
                  </button>
                </div>
              </div>

              <div className="overflow-x-auto">
                {loading ? (
                  <div className="py-12 text-center">
                    <div className="animate-spin w-8 h-8 border-4 border-red-500 border-t-transparent rounded-full mx-auto"></div>
                  </div>
                ) : (
                  <>
                    {activeTab === 'transactions' && (
                      <table className="w-full">
                        <thead className="bg-gray-50 border-b border-gray-200">
                          <tr>
                            <th className="text-left py-3 px-4 font-medium text-gray-900">Transaction ID</th>
                            <th className="text-left py-3 px-4 font-medium text-gray-900">User</th>
                            <th className="text-left py-3 px-4 font-medium text-gray-900">Email</th>
                            <th className="text-left py-3 px-4 font-medium text-gray-900">Plan</th>
                            <th className="text-left py-3 px-4 font-medium text-gray-900">Amount</th>
                            <th className="text-left py-3 px-4 font-medium text-gray-900">Status</th>
                            <th className="text-left py-3 px-4 font-medium text-gray-900">Date</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-200">
                          {transactions.map((txn) => (
                            <tr key={txn.id} className="hover:bg-gray-50">
                              <td className="py-4 px-4">
                                <span className="font-mono text-sm text-gray-900">{txn.id}</span>
                              </td>
                              <td className="py-4 px-4">
                                <span className="font-medium text-gray-900">{txn.user}</span>
                              </td>
                              <td className="py-4 px-4">
                                <span className="text-sm text-gray-600">{txn.user_email}</span>
                              </td>
                              <td className="py-4 px-4">
                                <span className="text-gray-900">{txn.plan}</span>
                              </td>
                              <td className="py-4 px-4">
                                <span className="font-medium text-gray-900">${txn.amount}</span>
                              </td>
                              <td className="py-4 px-4">
                                <span className={`px - 2 py - 1 rounded - full text - xs font - medium ${getStatusColor(txn.status)} `}>
                                  {txn.status}
                                </span>
                              </td>
                              <td className="py-4 px-4">
                                <span className="text-sm text-gray-600">{txn.date}</span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}

                    {activeTab === 'commissions' && (
                      <table className="w-full">
                        <thead className="bg-gray-50 border-b border-gray-200">
                          <tr>
                            <th className="text-left py-3 px-4 font-medium text-gray-900">User</th>
                            <th className="text-left py-3 px-4 font-medium text-gray-900">Total</th>
                            <th className="text-left py-3 px-4 font-medium text-gray-900">Pending</th>
                            <th className="text-left py-3 px-4 font-medium text-gray-900">Processing</th>
                            <th className="text-left py-3 px-4 font-medium text-gray-900">Paid</th>
                            <th className="text-left py-3 px-4 font-medium text-gray-900">Status</th>
                            <th className="text-left py-3 px-4 font-medium text-gray-900">Last Commission</th>
                            <th className="text-left py-3 px-4 font-medium text-gray-900">Actions</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-200">
                          {commissions.map((comm) => (
                            <tr key={comm.user_id} className="hover:bg-gray-50">
                              <td className="py-4 px-4">
                                <div>
                                  <div className="font-medium text-gray-900">{comm.user}</div>
                                  <div className="text-sm text-gray-600">{comm.user_email}</div>
                                </div>
                              </td>
                              <td className="py-4 px-4">
                                <span className="font-medium text-gray-900">${comm.total_commissions.toFixed(2)}</span>
                              </td>
                              <td className="py-4 px-4">
                                <span className="text-yellow-600 font-medium">${comm.pending_commissions.toFixed(2)}</span>
                              </td>
                              <td className="py-4 px-4">
                                <span className="text-blue-600 font-medium">${(comm.processing_commissions || 0).toFixed(2)}</span>
                              </td>
                              <td className="py-4 px-4">
                                <span className="text-green-600 font-medium">${comm.paid_commissions.toFixed(2)}</span>
                              </td>
                              <td className="py-4 px-4">
                                <span className={`px - 2 py - 1 rounded - full text - xs font - medium ${getStatusColor(comm.payout_status)} `}>
                                  {comm.payout_status}
                                </span>
                              </td>
                              <td className="py-4 px-4">
                                <span className="text-sm text-gray-600">{comm.last_commission_date || 'N/A'}</span>
                              </td>
                              <td className="py-4 px-4">
                                <div className="flex items-center gap-2">
                                  {comm.pending_commissions > 0 && (
                                    <>
                                      {comm.has_payout_account ? (
                                        <button
                                          onClick={() => openDialog(comm.user_id, comm.user, comm.available_payment_methods, comm.pending_commissions)}
                                          className="px-4 py-2 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700 transition font-medium"
                                        >
                                          Approve & Pay
                                        </button>
                                      ) : (
                                        <div className="text-sm">
                                          <span className="text-amber-600 font-medium">⚠️ No payout account</span>
                                        </div>
                                      )}
                                    </>
                                  )}
                                  <button
                                    onClick={() => handleViewHistory(comm.user_id)}
                                    className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                                    title="View Commission History"
                                  >
                                    <i className="ri-eye-line text-lg"></i>
                                  </button>
                                </div>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}

                    {activeTab === 'payouts' && (
                      <table className="w-full">
                        <thead className="bg-gray-50 border-b border-gray-200">
                          <tr>
                            <th className="text-left py-3 px-4 font-medium text-gray-900">ID</th>
                            <th className="text-left py-3 px-4 font-medium text-gray-900">User</th>
                            <th className="text-left py-3 px-4 font-medium text-gray-900">Amount</th>
                            <th className="text-left py-3 px-4 font-medium text-gray-900">Method</th>
                            <th className="text-left py-3 px-4 font-medium text-gray-900">Status</th>
                            <th className="text-left py-3 px-4 font-medium text-gray-900">Requested</th>
                            <th className="text-left py-3 px-4 font-medium text-gray-900">Completed</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-200">
                          {payouts.map((payout) => (
                            <tr key={payout.id} className="hover:bg-gray-50">
                              <td className="py-4 px-4">
                                <span className="font-mono text-sm text-gray-900">#{payout.id}</span>
                              </td>
                              <td className="py-4 px-4">
                                <div>
                                  <div className="font-medium text-gray-900">{payout.user}</div>
                                  <div className="text-sm text-gray-600">{payout.user_email}</div>
                                </div>
                              </td>
                              <td className="py-4 px-4">
                                <span className="font-medium text-gray-900">${payout.amount.toFixed(2)}</span>
                              </td>
                              <td className="py-4 px-4">
                                <span className="capitalize text-gray-900">{payout.method}</span>
                              </td>
                              <td className="py-4 px-4">
                                <span className={`px - 2 py - 1 rounded - full text - xs font - medium ${getStatusColor(payout.status)} `}>
                                  {payout.status}
                                </span>
                              </td>
                              <td className="py-4 px-4">
                                <span className="text-sm text-gray-600">{payout.requested_at}</span>
                              </td>
                              <td className="py-4 px-4">
                                <span className="text-sm text-gray-600">{payout.completed_at || '-'}</span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                  </>
                )}
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="px-4 py-4 border-t border-gray-200">
                  <div className="flex items-center justify-between flex-wrap gap-4">
                    <div className="text-sm text-gray-600">
                      Showing {(currentPage - 1) * itemsPerPage + 1} to {Math.min(currentPage * itemsPerPage, totalItems)} of {totalItems}
                    </div>
                    <div className="flex items-center gap-3 flex-wrap">
                      <button
                        onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                        disabled={currentPage === 1}
                        className="px-5 py-2.5 border-2 border-gray-300 rounded-xl text-base font-bold text-gray-700 hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed whitespace-nowrap transition-colors flex items-center gap-2"
                      >
                        <i className="ri-arrow-left-s-line"></i>
                        Previous
                      </button>

                      {/* Progressive Pagination: 3 distinct page numbers */}
                      {Array.from({ length: totalPages }, (_, i) => i + 1)
                        .filter(pageNum => {
                          if (totalPages <= 3) return true;
                          if (currentPage === 1) return pageNum <= 3;
                          if (currentPage === totalPages) return pageNum >= totalPages - 2;
                          return pageNum >= currentPage - 1 && pageNum <= currentPage + 1;
                        })
                        .map((pageNum, index, filteredArray) => (
                          <div key={pageNum} className="flex items-center gap-2">
                            {/* Dot indicator if there's a gap at the start */}
                            {index === 0 && pageNum > 1 && <span className="text-gray-400 font-bold px-1">...</span>}

                            <button
                              onClick={() => setCurrentPage(pageNum)}
                              className={`w-12 h-12 rounded-xl text-lg font-bold transition-all ${currentPage === pageNum
                                  ? 'bg-red-600 text-white shadow-lg shadow-red-200 ring-2 ring-red-600 ring-offset-2'
                                  : 'border-2 border-gray-200 text-gray-600 hover:border-red-600 hover:text-red-600 hover:bg-red-50'
                                }`}
                            >
                              {pageNum}
                            </button>

                            {/* Dot indicator if there's a gap at the end */}
                            {index === filteredArray.length - 1 && pageNum < totalPages && <span className="text-gray-400 font-bold px-1">...</span>}
                          </div>
                        ))}

                      <button
                        onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                        disabled={currentPage === totalPages}
                        className="px-5 py-2.5 border-2 border-gray-300 rounded-xl text-base font-bold text-gray-700 hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed whitespace-nowrap transition-colors flex items-center gap-2"
                      >
                        Next
                        <i className="ri-arrow-right-s-line"></i>
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
      {/* History Modal */}
      {historyModal.open && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] flex flex-col animate-scale-in">
            <div className="p-6 border-b border-gray-100 flex items-center justify-between">
              <div>
                <h3 className="text-xl font-bold text-gray-900">Commission History</h3>
                {historyModal.user && (
                  <p className="text-sm text-gray-600">
                    {historyModal.user.name} ({historyModal.user.email})
                  </p>
                )}
              </div>
              <button
                onClick={() => setHistoryModal(prev => ({ ...prev, open: false }))}
                className="p-2 hover:bg-gray-100 rounded-full transition"
              >
                <i className="ri-close-line text-xl text-gray-500"></i>
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-6">
              {historyModal.loading ? (
                <div className="py-12 text-center">
                  <div className="animate-spin w-8 h-8 border-4 border-red-500 border-t-transparent rounded-full mx-auto"></div>
                  <p className="mt-2 text-sm text-gray-500">Loading history...</p>
                </div>
              ) : historyModal.commissions.length === 0 ? (
                <div className="text-center py-12 text-gray-500">No commission history found.</div>
              ) : (
                <div className="space-y-6">
                  <table className="w-full text-sm text-left">
                    <thead className="text-xs text-gray-500 uppercase bg-gray-50">
                      <tr>
                        <th className="px-4 py-3">Date</th>
                        <th className="px-4 py-3">Referred User</th>
                        <th className="px-4 py-3">Plan</th>
                        <th className="px-4 py-3">Amount</th>
                        <th className="px-4 py-3">Status</th>
                        <th className="px-4 py-3">Payout Info</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {historyModal.commissions.map((item: any) => (
                        <tr key={item.commission_id} className="hover:bg-gray-50">
                          <td className="px-4 py-3 whitespace-nowrap">
                            <div className="font-medium text-gray-900">{item.created_at.split(' ')[0]}</div>
                            <div className="text-xs text-gray-500">{item.created_at.split(' ')[1]}</div>
                          </td>
                          <td className="px-4 py-3">
                            <div className="font-medium text-gray-900">{item.referred_user}</div>
                            <div className="text-xs text-gray-500">{item.referred_user_email}</div>
                          </td>
                          <td className="px-4 py-3">{item.subscription_plan}</td>
                          <td className="px-4 py-3 font-medium text-gray-900">${item.amount.toFixed(2)}</td>
                          <td className="px-4 py-3">
                            <span className={`px - 2 py - 1 rounded - full text - xs font - medium ${getStatusColor(item.status)} `}>
                              {item.status}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            {item.paid_at ? (
                              <div>
                                <div className="text-xs text-green-600 font-medium">Paid: {item.paid_at}</div>
                                <div className="text-xs text-gray-500 capitalize">{item.payout_method || 'Manual'}</div>
                              </div>
                            ) : item.status === 'processing' ? (
                              <span className="text-xs text-blue-600">Processing Payout</span>
                            ) : (
                              <span className="text-xs text-gray-400">-</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            <div className="p-4 border-t border-gray-100 bg-gray-50 flex justify-end">
              <button
                onClick={() => setHistoryModal(prev => ({ ...prev, open: false }))}
                className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-white transition"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}