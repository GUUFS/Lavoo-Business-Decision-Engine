import { useState, useMemo } from 'react';
import { calculateUserLevel } from './levelcalculator';
import type { UserLevelInfo } from './levelcalculator';
import ReferralLinkModal from './referralLink';
import {
  useEarningsUser,
  useReferralStats,
  useEarningsSummary,
  useAvailableYears,
  useMonthlyPerformance,
} from '@/api/earnings';

export default function EarningsPage() {
  const [selectedYear, setSelectedYear] = useState<number>(new Date().getFullYear());
  const [selectedMonth, setSelectedMonth] = useState<number>(new Date().getMonth() + 1);
  const [showReferralModal, setShowReferralModal] = useState(false);

  // Use TanStack Query hooks for all data fetching with automatic caching
  const { data: userData, isLoading: isLoadingUser, error: userError } = useEarningsUser();
  const { data: referralData, isLoading: isLoadingReferrals } = useReferralStats();
  const { data: earningsData, isLoading: isLoadingEarnings } = useEarningsSummary();
  const { data: availableYears = [], isLoading: isLoadingYears } = useAvailableYears();
  const { data: specificMonthData, isLoading: isLoadingMonth } = useMonthlyPerformance(selectedYear, selectedMonth);

  // Calculate user level from chops (memoized)
  const userLevelInfo: UserLevelInfo | null = useMemo(() => {
    if (!userData) return null;
    const totalChops = userData.total_chops || 0;
    return calculateUserLevel(totalChops);
  }, [userData]);

  // Generate referral link (memoized)
  const referralLink = useMemo(() => {
    if (!userData?.referral_code) return '';
    const baseUrl = window.location.origin;
    return `${baseUrl}/signup?ref=${userData.referral_code}`;
  }, [userData?.referral_code]);

  // Combined loading state
  const loading = isLoadingUser || isLoadingReferrals || isLoadingEarnings;
  const error = userError ? 'Your session has expired. Please log in again.' : null;

  const months = [
    { value: 1, label: 'January' },
    { value: 2, label: 'February' },
    { value: 3, label: 'March' },
    { value: 4, label: 'April' },
    { value: 5, label: 'May' },
    { value: 6, label: 'June' },
    { value: 7, label: 'July' },
    { value: 8, label: 'August' },
    { value: 9, label: 'September' },
    { value: 10, label: 'October' },
    { value: 11, label: 'November' },
    { value: 12, label: 'December' },
  ];

  const handleShareReferralLink = () => {
    setShowReferralModal(true);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-orange-50 to-white flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-500 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading earnings dashboard...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-orange-50 to-white px-4 py-6 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
            <div className="text-red-500 text-4xl mb-4">⚠️</div>
            <h3 className="text-lg font-bold text-red-800 mb-2">Unable to Load Earnings Data</h3>
            <p className="text-red-700 mb-4">{error}</p>
            <div className="flex gap-3 justify-center">
              <button onClick={() => window.location.reload()} className="bg-orange-500 text-white px-4 py-2 rounded-lg hover:bg-orange-600 transition-colors">
                Reload Page
              </button>
              <button onClick={() => window.location.href = '/dashboard'} className="border border-gray-300 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-50 transition-colors">
                Back to Dashboard
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const safeNumber = (value: number | null | undefined): number => value || 0;

  const LoadingSkeleton = ({ className = "" }: { className?: string }) => (
    <div className={`animate-pulse bg-gray-200 rounded ${className}`}></div>
  );

  const totalCommissions = safeNumber(earningsData?.totalCommissions);
  const totalPaidReferrals = safeNumber(earningsData?.totalPaidReferrals);
  const referralChops = safeNumber(earningsData?.referralChops);
  const commissionRate = safeNumber(earningsData?.commissionRate);

  const totalReferrals = safeNumber(referralData?.total_referrals);
  const totalChopsEarned = safeNumber(referralData?.total_chops_earned);

  return (
    <div className="min-h-screen bg-gradient-to-br from-orange-50 to-white px-4 py-6 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6 sm:mb-8">
          <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-gray-900 mb-2">
            Earnings Dashboard
          </h1>
          <p className="text-sm sm:text-base text-gray-600">
            Track your commissions and referral performance ({commissionRate}% commission rate)
          </p>
        </div>

        {/* Key Metrics */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4 sm:gap-6 mb-6 sm:mb-8">
          <div className="bg-white rounded-lg sm:rounded-xl p-4 sm:p-6 border border-gray-200 shadow-sm">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <p className="text-xs sm:text-sm font-medium text-gray-600 mb-1">Total Commissions</p>
                {isLoadingEarnings ? (
                  <LoadingSkeleton className="h-8 w-20 mt-1" />
                ) : (
                  <p className="text-xl sm:text-2xl font-bold text-gray-900">
                    ${totalCommissions.toLocaleString()}
                  </p>
                )}
              </div>
              <div className="w-8 h-8 sm:w-10 sm:h-10 bg-green-100 rounded-lg flex items-center justify-center">
                <i className="ri-money-dollar-circle-line text-green-600 text-lg sm:text-xl"></i>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg sm:rounded-xl p-4 sm:p-6 border border-gray-200 shadow-sm">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <p className="text-xs sm:text-sm font-medium text-gray-600 mb-1">Paid Commissions</p>
                {isLoadingEarnings ? (
                  <LoadingSkeleton className="h-8 w-20 mt-1" />
                ) : (
                  <p className="text-xl sm:text-2xl font-bold text-gray-900">
                    ${(earningsData?.paidCommissions || 0).toLocaleString()}
                  </p>
                )}
              </div>
              <div className="w-8 h-8 sm:w-10 sm:h-10 bg-emerald-100 rounded-lg flex items-center justify-center">
                <i className="ri-check-double-line text-emerald-600 text-lg sm:text-xl"></i>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg sm:rounded-xl p-4 sm:p-6 border border-gray-200 shadow-sm">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <p className="text-xs sm:text-sm font-medium text-gray-600 mb-1">Pending Commissions</p>
                {isLoadingEarnings ? (
                  <LoadingSkeleton className="h-8 w-20 mt-1" />
                ) : (
                  <p className="text-xl sm:text-2xl font-bold text-gray-900">
                    ${(earningsData?.pendingCommissions || 0).toLocaleString()}
                  </p>
                )}
              </div>
              <div className="w-8 h-8 sm:w-10 sm:h-10 bg-yellow-100 rounded-lg flex items-center justify-center">
                <i className="ri-time-line text-yellow-600 text-lg sm:text-xl"></i>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg sm:rounded-xl p-4 sm:p-6 border border-gray-200 shadow-sm">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <p className="text-xs sm:text-sm font-medium text-gray-600 mb-1">Paid Referrals</p>
                {isLoadingReferrals ? (
                  <LoadingSkeleton className="h-8 w-16 mt-1" />
                ) : (
                  <p className="text-xl sm:text-2xl font-bold text-gray-900">
                    {totalPaidReferrals.toLocaleString()}
                  </p>
                )}
              </div>
              <div className="w-8 h-8 sm:w-10 sm:h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                <i className="ri-user-star-line text-blue-600 text-lg sm:text-xl"></i>
              </div>
            </div>
          </div>

          {/* <div className="bg-white rounded-lg sm:rounded-xl p-4 sm:p-6 border border-gray-200 shadow-sm">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <p className="text-xs sm:text-sm font-medium text-gray-600">
                  Referral Chops
                </p>
                {isLoadingReferrals ? (
                  <LoadingSkeleton className="h-8 w-16 mt-1" />
                ) : (
                  <p className="text-xl sm:text-2xl font-bold text-gray-900">
                    {referralChops.toLocaleString()}
                  </p>
                )}
              </div>
              <div className="w-8 h-8 sm:w-10 sm:h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                <i className="ri-gift-line text-purple-600 text-lg sm:text-xl"></i>
              </div>
            </div>
          </div> */}
        </div>

        {/* User Level Progress */}
        {/* {userLevelInfo && (
          <div className="bg-white rounded-lg sm:rounded-xl p-4 sm:p-6 border border-gray-200 shadow-sm mb-6 sm:mb-8">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-4">
              <div className="flex items-center gap-3">
                <div className="text-2xl sm:text-3xl">{userLevelInfo.currentLevel.badge}</div>
                <div>
                  <h3 className="text-lg sm:text-xl font-bold text-gray-900">
                    Level {userLevelInfo.currentLevel.level}: {userLevelInfo.currentLevel.rank}
                  </h3>
                  <p className="text-sm text-gray-600">
                    {userLevelInfo.totalChops.toLocaleString()} total chops earned
                  </p>
                </div>
              </div>
              <div className="text-right">
                <p className="text-sm text-gray-600">Next level in</p>
                <p className="text-lg font-bold text-orange-600">
                  {userLevelInfo.pointsToNextLevel > 0
                    ? userLevelInfo.pointsToNextLevel.toLocaleString() + ' chops'
                    : 'MAX LEVEL!'}
                </p>
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Progress to next level</span>
                <span className="font-medium text-gray-900">
                  {userLevelInfo.progressPercentage}%
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-3">
                <div
                  className="bg-gradient-to-r from-orange-500 to-orange-600 h-3 rounded-full transition-all duration-300"
                  style={{ width: `${userLevelInfo.progressPercentage}%` }}
                ></div>
              </div>
            </div>
          </div>
        )} */}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 sm:gap-8">
          {/* Monthly Metrics */}
          <div className="lg:col-span-2">
            <div className="bg-white rounded-lg sm:rounded-xl p-4 sm:p-6 border border-gray-200 shadow-sm">
              <div className="mb-6">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-4">
                  <div>
                    <h2 className="text-lg sm:text-xl font-bold text-gray-900">Monthly Metrics</h2>
                    <p className="text-sm text-gray-600 mt-1">Track your referral performance by month</p>
                  </div>

                  <div className="flex gap-2">
                    <select
                      value={selectedYear}
                      onChange={(e) => setSelectedYear(Number(e.target.value))}
                      disabled={isLoadingYears}
                      className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-orange-500 bg-white"
                    >
                      {isLoadingYears ? (
                        <option>Loading...</option>
                      ) : availableYears.length > 0 ? (
                        availableYears.map(year => (
                          <option key={year} value={year}>{year}</option>
                        ))
                      ) : (
                        <option value={new Date().getFullYear()}>{new Date().getFullYear()}</option>
                      )}
                    </select>

                    <select
                      value={selectedMonth}
                      onChange={(e) => setSelectedMonth(Number(e.target.value))}
                      className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-orange-500 bg-white"
                    >
                      {months.map(month => (
                        <option key={month.value} value={month.value}>{month.label}</option>
                      ))}
                    </select>
                  </div>
                </div>

                {/* Selected Month Data */}
                {isLoadingMonth ? (
                  <div className="p-4 bg-gradient-to-r from-gray-50 to-white rounded-lg border border-gray-200">
                    <LoadingSkeleton className="h-32 w-full" />
                  </div>
                ) : specificMonthData ? (
                  <div className="p-4 bg-gradient-to-r from-orange-50 to-white rounded-lg border border-orange-200">
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="text-lg font-bold text-gray-900">
                        {specificMonthData.month} {specificMonthData.year}
                      </h3>
                      <div className="text-right">
                        <p className="text-sm text-gray-600">Commission Earned</p>
                        <p className="text-2xl font-bold text-green-600">
                          ${(specificMonthData.commission || 0).toLocaleString()}
                        </p>
                      </div>
                    </div>

                    <div className="grid grid-cols-3 gap-4">
                      {/* <div className="bg-white p-3 rounded-lg border border-gray-100">
                        <p className="text-xs text-gray-600 mb-1">Referral Chops</p>
                        <p className="text-lg font-bold text-purple-600">
                          {(specificMonthData.referral_chops || 0).toLocaleString()}
                        </p>
                      </div> */}

                      <div className="bg-white p-3 rounded-lg border border-gray-100">
                        <p className="text-xs text-gray-600 mb-1">Total Referrals</p>
                        <p className="text-lg font-bold text-blue-600">
                          {specificMonthData.referral_count || 0}
                        </p>
                      </div>

                      <div className="bg-white p-3 rounded-lg border border-gray-100">
                        <p className="text-xs text-gray-600 mb-1">Paid Referrals</p>
                        <p className="text-lg font-bold text-orange-600">
                          {specificMonthData.paid_referral_count || 0}
                        </p>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-12 text-gray-500">
                    <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                      <i className="ri-calendar-line text-2xl text-gray-400"></i>
                    </div>
                    <p>No data available for selected month</p>
                    <p className="text-sm mt-2">Start referring users to see your monthly metrics!</p>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Sidebar Stats */}
          <div className="space-y-6 sm:space-y-8">
            {/* Referral Stats */}
            <div className="bg-white rounded-lg sm:rounded-xl p-4 sm:p-6 border border-gray-200 shadow-sm">
              <h2 className="text-lg sm:text-xl font-bold text-gray-900 mb-4">Referral Stats</h2>

              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                      <i className="ri-user-add-line text-blue-600 text-lg"></i>
                    </div>
                    <div>
                      <p className="font-semibold text-gray-900">Total Referrals</p>
                      <p className="text-sm text-gray-600">All time</p>
                    </div>
                  </div>
                  {isLoadingReferrals ? (
                    <LoadingSkeleton className="h-7 w-12" />
                  ) : (
                    <p className="text-xl font-bold text-gray-900">{totalReferrals}</p>
                  )}
                </div>

                <div className="flex items-center justify-between">
                  {/* <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
                      <i className="ri-money-dollar-circle-line text-green-600 text-lg"></i>
                    </div>
                    <div>
                      <p className="font-semibold text-gray-900">Total Chops</p>
                      <p className="text-sm text-gray-600">From referrals</p>
                    </div>
                  </div>
                  {isLoadingReferrals ? (
                    <LoadingSkeleton className="h-7 w-12" />
                  ) : (
                    <p className="text-xl font-bold text-green-600">{totalChopsEarned}</p>
                  )} */}
                </div>

                <div className="pt-4 border-t border-gray-200">
                  <button
                    onClick={handleShareReferralLink}
                    disabled={!referralLink}
                    className="w-full bg-orange-500 text-white px-4 py-2 rounded-lg hover:bg-orange-600 transition-colors font-medium text-sm disabled:bg-gray-300 disabled:cursor-not-allowed"
                  >
                    Share Referral Link
                  </button>
                </div>
              </div>
            </div>

            {/* Commission Info */}
            <div className="bg-gradient-to-br from-orange-50 to-orange-100 rounded-lg sm:rounded-xl p-4 sm:p-6 border border-orange-200">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 bg-orange-500 rounded-lg flex items-center justify-center">
                  <i className="ri-percent-line text-white text-lg"></i>
                </div>
                <div>
                  <h3 className="font-bold text-gray-900">Commission Rate</h3>
                  <p className="text-sm text-gray-600">Per referral subscription</p>
                </div>
              </div>
              <p className="text-3xl font-bold text-orange-600">{commissionRate}%</p>
              <p className="text-sm text-gray-600 mt-2">
                Earn {commissionRate}% commission on every subscription payment made by your referrals!
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Referral Link Modal */}
      {showReferralModal && referralLink && (
        <ReferralLinkModal
          referralLink={referralLink}
          onClose={() => setShowReferralModal(false)}
        />
      )}
    </div>
  );
}
