
import { useState } from 'react';

export default function EarningsPage() {
  const [selectedPeriod, setSelectedPeriod] = useState('month');

  // User level data
  const userLevel = {
    name: 'Builder',
    badge: '🏗️',
    currentPoints: 279,
    nextLevelPoints: 500,
    progress: 56 // percentage
  };

  const pointsToNext = userLevel.nextLevelPoints - userLevel.currentPoints;

  const earningsData = {
    totalRevenue: 45280,
    transactions: 1247,
    avgOrderValue: 36.32,
    growthRate: 12.5,
    referrals: 24,
    referralConversions: 18,
    conversionRate: 75
  };

  const revenueStreams = [
    {
      name: 'AI Analysis Reports',
      amount: 18500,
      growth: 15.2,
      icon: 'ri-file-chart-line'
    },
    {
      name: 'Consultation Services',
      amount: 12800,
      growth: 8.7,
      icon: 'ri-user-voice-line'
    },
    {
      name: 'Premium Subscriptions',
      amount: 8900,
      growth: 22.1,
      icon: 'ri-vip-crown-line'
    },
    {
      name: 'Referral Earnings',
      amount: 1200,
      growth: 45.3,
      icon: 'ri-share-forward-line'
    }
  ];

  const monthlyData = [
    { month: 'Jan', revenue: 32000, transactions: 890 },
    { month: 'Feb', revenue: 35000, transactions: 950 },
    { month: 'Mar', revenue: 38000, transactions: 1020 },
    { month: 'Apr', revenue: 42000, transactions: 1150 },
    { month: 'May', revenue: 45280, transactions: 1247 }
  ];

  return (
    <div className="min-h-screen bg-gray-50 p-4 sm:p-6 lg:p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6 sm:mb-8">
          <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-gray-900 mb-2">Earnings Dashboard</h1>
          <p className="text-sm sm:text-base text-gray-600">Track your revenue and performance metrics</p>
        </div>

        {/* Key Metrics */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 sm:gap-6 mb-6 sm:mb-8">
          <div className="bg-white rounded-lg sm:rounded-xl p-4 sm:p-6 border border-gray-200 shadow-sm">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs sm:text-sm font-medium text-gray-600">Total Revenue</p>
                <p className="text-xl sm:text-2xl font-bold text-gray-900">${earningsData.totalRevenue.toLocaleString()}</p>
              </div>
              <div className="w-8 h-8 sm:w-10 sm:h-10 bg-green-100 rounded-lg flex items-center justify-center">
                <i className="ri-money-dollar-circle-line text-green-600 text-lg sm:text-xl"></i>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg sm:rounded-xl p-4 sm:p-6 border border-gray-200 shadow-sm">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs sm:text-sm font-medium text-gray-600">Transactions</p>
                <p className="text-xl sm:text-2xl font-bold text-gray-900">{earningsData.transactions.toLocaleString()}</p>
              </div>
              <div className="w-8 h-8 sm:w-10 sm:h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                <i className="ri-shopping-cart-line text-blue-600 text-lg sm:text-xl"></i>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg sm:rounded-xl p-4 sm:p-6 border border-gray-200 shadow-sm">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs sm:text-sm font-medium text-gray-600">Avg Order Value</p>
                <p className="text-xl sm:text-2xl font-bold text-gray-900">${earningsData.avgOrderValue}</p>
              </div>
              <div className="w-8 h-8 sm:w-10 sm:h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                <i className="ri-calculator-line text-purple-600 text-lg sm:text-xl"></i>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg sm:rounded-xl p-4 sm:p-6 border border-gray-200 shadow-sm">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs sm:text-sm font-medium text-gray-600">Growth Rate</p>
                <p className="text-xl sm:text-2xl font-bold text-green-600">+{earningsData.growthRate}%</p>
              </div>
              <div className="w-8 h-8 sm:w-10 sm:h-10 bg-orange-100 rounded-lg flex items-center justify-center">
                <i className="ri-trending-up-line text-orange-600 text-lg sm:text-xl"></i>
              </div>
            </div>
          </div>
        </div>

        {/* User Level Progress */}
        <div className="bg-white rounded-lg sm:rounded-xl p-4 sm:p-6 border border-gray-200 shadow-sm mb-6 sm:mb-8">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-4">
            <div className="flex items-center gap-3">
              <div className="text-2xl sm:text-3xl">{userLevel.badge}</div>
              <div>
                <h3 className="text-lg sm:text-xl font-bold text-gray-900">{userLevel.name} Level</h3>
                <p className="text-sm text-gray-600">{userLevel.currentPoints} points earned</p>
              </div>
            </div>
            <div className="text-right">
              <p className="text-sm text-gray-600">Next level in</p>
              <p className="text-lg font-bold text-orange-600">{pointsToNext} points</p>
            </div>
          </div>
          
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-gray-600">Progress to next level</span>
              <span className="font-medium text-gray-900">{userLevel.progress}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-3">
              <div 
                className="bg-gradient-to-r from-orange-500 to-orange-600 h-3 rounded-full transition-all duration-300"
                style={{ width: `${userLevel.progress}%` }}
              ></div>
            </div>
            <div className="flex justify-between text-xs text-gray-500">
              <span>{userLevel.currentPoints} points</span>
              <span>{userLevel.nextLevelPoints} points</span>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 sm:gap-8">
          {/* Revenue Streams */}
          <div className="lg:col-span-2">
            <div className="bg-white rounded-lg sm:rounded-xl p-4 sm:p-6 border border-gray-200 shadow-sm">
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
                <h2 className="text-lg sm:text-xl font-bold text-gray-900">Revenue Streams</h2>
                <select
                  value={selectedPeriod}
                  onChange={(e) => setSelectedPeriod(e.target.value)}
                  className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500 text-sm"
                >
                  <option value="week">This Week</option>
                  <option value="month">This Month</option>
                  <option value="quarter">This Quarter</option>
                  <option value="year">This Year</option>
                </select>
              </div>

              <div className="space-y-4">
                {revenueStreams.map((stream, index) => (
                  <div key={index} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-white rounded-lg flex items-center justify-center border border-gray-200">
                        <i className={`${stream.icon} text-gray-600 text-lg`}></i>
                      </div>
                      <div>
                        <h3 className="font-semibold text-gray-900 text-sm sm:text-base">{stream.name}</h3>
                        <p className="text-xs sm:text-sm text-gray-600">
                          <span className={`${stream.growth >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                            {stream.growth >= 0 ? '+' : ''}{stream.growth}%
                          </span>
                          {' '}vs last period
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="font-bold text-gray-900 text-sm sm:text-base">${stream.amount.toLocaleString()}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Referrals Section */}
          <div className="space-y-6 sm:space-y-8">
            {/* Referral Stats */}
            <div className="bg-white rounded-lg sm:rounded-xl p-4 sm:p-6 border border-gray-200 shadow-sm">
              <h2 className="text-lg sm:text-xl font-bold text-gray-900 mb-4">Referrals</h2>
              
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
                  <p className="text-xl font-bold text-gray-900">{earningsData.referrals}</p>
                </div>

                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
                      <i className="ri-check-line text-green-600 text-lg"></i>
                    </div>
                    <div>
                      <p className="font-semibold text-gray-900">Conversions</p>
                      <p className="text-sm text-gray-600">{earningsData.conversionRate}% rate</p>
                    </div>
                  </div>
                  <p className="text-xl font-bold text-green-600">{earningsData.referralConversions}</p>
                </div>

                <div className="pt-4 border-t border-gray-200">
                  <button className="w-full bg-orange-500 text-white px-4 py-2 rounded-lg hover:bg-orange-600 transition-colors font-medium text-sm whitespace-nowrap">
                    Share Referral Link
                  </button>
                </div>
              </div>
            </div>

            {/* Monthly Performance */}
            <div className="bg-white rounded-lg sm:rounded-xl p-4 sm:p-6 border border-gray-200 shadow-sm">
              <h2 className="text-lg sm:text-xl font-bold text-gray-900 mb-4">Monthly Performance</h2>
              
              <div className="space-y-3">
                {monthlyData.slice(-3).map((month, index) => (
                  <div key={index} className="flex items-center justify-between">
                    <div>
                      <p className="font-medium text-gray-900">{month.month}</p>
                      <p className="text-sm text-gray-600">{month.transactions} transactions</p>
                    </div>
                    <p className="font-bold text-gray-900">${month.revenue.toLocaleString()}</p>
                  </div>
                ))}
              </div>

              <div className="mt-4 pt-4 border-t border-gray-200">
                <button className="w-full border border-gray-300 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-50 transition-colors font-medium text-sm whitespace-nowrap">
                  View Full Report
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
