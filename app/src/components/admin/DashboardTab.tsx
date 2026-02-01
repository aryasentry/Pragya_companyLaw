'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  FaChartLine,
  FaDatabase,
  FaFileAlt,
  FaSearch,
  FaUsers,
  FaArrowUp,
  FaArrowDown,
  FaSync,
} from 'react-icons/fa';

interface StatCardProps {
  title: string;
  value: string | number;
  change?: number;
  icon: React.ReactNode;
  color: string;
}

interface DashboardData {
  overview: {
    totalQueries: number;
    queryChange: number;
    totalDocuments: number;
    documentChange: number;
    activeUsers: number;
    userChange: number;
    avgLatency: string;
    latencyChange: number;
  };
  documentsByType: Array<{
    type: string;
    count: number;
    color: string;
  }>;
  recentActivity: Array<{
    title: string;
    time: string;
    type: string;
  }>;
  chartData: number[];
}

const StatCard = ({ title, value, change, icon, color }: StatCardProps) => (
  <div className="bg-white rounded-xl border border-gray-200 p-6">
    <div className="flex items-start justify-between">
      <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${color}`}>
        {icon}
      </div>
      {change !== undefined && (
        <span className={`flex items-center gap-1 text-sm font-medium ${
          change >= 0 ? 'text-green-600' : 'text-red-600'
        }`}>
          {change >= 0 ? <FaArrowUp className="text-xs" /> : <FaArrowDown className="text-xs" />}
          {Math.abs(change).toFixed(2)}%
        </span>
      )}
    </div>
    <div className="mt-4">
      <h3 className="text-3xl font-bold text-gray-900">{value}</h3>
      <p className="text-sm text-gray-500 mt-1">{title}</p>
    </div>
  </div>
);

export default function DashboardTab() {
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchDashboard = useCallback(async () => {
    try {
      const response = await fetch('/api/admin/dashboard');
      const data = await response.json();

      if (data.success) {
        setDashboard(data.data);
      }
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDashboard();
  }, [fetchDashboard]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center">
          <FaSync className="animate-spin text-3xl text-orange-500 mx-auto mb-3" />
          <p className="text-gray-500">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  if (!dashboard) {
    return (
      <div className="text-center py-20">
        <p className="text-gray-500">Failed to load dashboard</p>
        <button
          onClick={fetchDashboard}
          className="mt-4 px-4 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600"
        >
          Retry
        </button>
      </div>
    );
  }
  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Dashboard Overview</h2>
        <p className="text-gray-600">Welcome back! Here&apos;s what&apos;s happening with Pragya.</p>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <button className="flex flex-col items-center gap-3 p-6 bg-linear-to-br from-orange-50 to-orange-100 border border-orange-200 rounded-xl hover:shadow-md transition-all group">
          <div className="w-12 h-12 bg-white rounded-xl flex items-center justify-center shadow-sm group-hover:scale-110 transition-transform">
            <FaFileAlt className="text-orange-500 text-xl" />
          </div>
          <span className="font-medium text-gray-700">Ingest Document</span>
        </button>
        <button className="flex flex-col items-center gap-3 p-6 bg-linear-to-br from-blue-50 to-blue-100 border border-blue-200 rounded-xl hover:shadow-md transition-all group">
          <div className="w-12 h-12 bg-white rounded-xl flex items-center justify-center shadow-sm group-hover:scale-110 transition-transform">
            <FaSearch className="text-blue-500 text-xl" />
          </div>
          <span className="font-medium text-gray-700">Search Documents</span>
        </button>
        <button className="flex flex-col items-center gap-3 p-6 bg-linear-to-br from-green-50 to-green-100 border border-green-200 rounded-xl hover:shadow-md transition-all group">
          <div className="w-12 h-12 bg-white rounded-xl flex items-center justify-center shadow-sm group-hover:scale-110 transition-transform">
            <FaChartLine className="text-green-500 text-xl" />
          </div>
          <span className="font-medium text-gray-700">View Analytics</span>
        </button>
        <button className="flex flex-col items-center gap-3 p-6 bg-linear-to-br from-purple-50 to-purple-100 border border-purple-200 rounded-xl hover:shadow-md transition-all group">
          <div className="w-12 h-12 bg-white rounded-xl flex items-center justify-center shadow-sm group-hover:scale-110 transition-transform">
            <FaDatabase className="text-purple-500 text-xl" />
          </div>
          <span className="font-medium text-gray-700">Database Status</span>
        </button>
      </div>

      {/* Stats Grid */}
      <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Queries"
          value={dashboard.overview.totalQueries.toLocaleString()}
          change={dashboard.overview.queryChange}
          icon={<FaSearch className="text-blue-500 text-xl" />}
          color="bg-blue-100"
        />
        <StatCard
          title="Documents"
          value={dashboard.overview.totalDocuments.toLocaleString()}
          change={dashboard.overview.documentChange}
          icon={<FaFileAlt className="text-green-500 text-xl" />}
          color="bg-green-100"
        />
        <StatCard
          title="Active Users"
          value={dashboard.overview.activeUsers}
          change={dashboard.overview.userChange}
          icon={<FaUsers className="text-amber-500 text-xl" />}
          color="bg-amber-100"
        />
        <StatCard
          title="Avg. Latency"
          value={dashboard.overview.avgLatency}
          change={dashboard.overview.latencyChange}
          icon={<FaChartLine className="text-purple-500 text-xl" />}
          color="bg-purple-100"
        />
      </div>

      {/* Charts Section */}
      <div className="grid lg:grid-cols-2 gap-6">
        {/* Requests Chart Placeholder */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-6">
            <h3 className="font-semibold text-gray-900">Total Requests</h3>
            <select className="text-sm border border-gray-300 rounded-lg px-3 py-1.5">
              <option>Last 15 days</option>
              <option>Last 30 days</option>
              <option>Last 90 days</option>
            </select>
          </div>
          <div className="h-48 flex items-end justify-between gap-2 px-4">
            {(dashboard.chartData || []).map((h, i) => (
              <div key={i} className="flex-1 flex flex-col items-center gap-1">
                <div 
                  className="w-full bg-linear-to-t from-orange-500 to-orange-300 rounded-t-sm transition-all hover:from-orange-600 hover:to-orange-400"
                  style={{ height: `${h}%` }}
                />
              </div>
            ))}
          </div>
          <div className="flex justify-between mt-4 text-xs text-gray-500">
            <span>Jan 18</span>
            <span>Jan 25</span>
            <span>Feb 1</span>
          </div>
        </div>

        {/* Recent Activity */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="font-semibold text-gray-900 mb-4">Recent Activity</h3>
          <div className="space-y-4">
            {(dashboard.recentActivity || []).map((activity, i) => (
              <div key={i} className="flex items-center gap-4 py-2 border-b border-gray-100 last:border-0">
                <div className={`w-2 h-2 rounded-full ${
                  activity.type === 'ingest' ? 'bg-green-500' :
                  activity.type === 'update' ? 'bg-blue-500' :
                  activity.type === 'system' ? 'bg-purple-500' : 'bg-amber-500'
                }`} />
                <div className="flex-1">
                  <p className="text-sm font-medium text-gray-900">{activity.title}</p>
                </div>
                <span className="text-xs text-gray-500">{activity.time}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Document Types Distribution */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="font-semibold text-gray-900 mb-4">Documents by Type</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-4">
          {(dashboard.documentsByType || []).map((item) => (
            <div key={item.type} className="text-center">
              <div className={`w-full h-2 ${item.color} rounded-full mb-2`} />
              <p className="text-lg font-bold text-gray-900">{item.count}</p>
              <p className="text-xs text-gray-500">{item.type}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
