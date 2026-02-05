'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  FaArrowUp,
  FaArrowDown,
  FaSync,
} from 'react-icons/fa';

interface MetricData {
  label: string;
  value: string;
  change: number;
  chartData: number[];
}

interface ModelData {
  name: string;
  cost: number;
  tokens: number;
  input: number;
  output: number;
  speed: number;
}

interface AnalyticsData {
  metrics: MetricData[];
  models: ModelData[];
  queriesByHour: number[];
  topQueries: Array<{ query: string; count: number }>;
}

export default function AnalyticsTab() {
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState('15d');

  const fetchAnalytics = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch(`/api/admin/analytics?period=${period}`);
      const data = await response.json();

      if (data.success) {
        setAnalytics(data.data);
      }
    } catch (error) {
      console.error('Failed to fetch analytics:', error);
    } finally {
      setLoading(false);
    }
  }, [period]);

  useEffect(() => {
    fetchAnalytics();
  }, [fetchAnalytics]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center">
          <FaSync className="animate-spin text-3xl text-orange-500 mx-auto mb-3" />
          <p className="text-gray-500">Loading analytics...</p>
        </div>
      </div>
    );
  }

  if (!analytics) {
    return (
      <div className="text-center py-20">
        <p className="text-gray-500">Failed to load analytics</p>
        <button
          onClick={fetchAnalytics}
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
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Analytics</h2>
          <p className="text-gray-600">Query performance and usage statistics</p>
        </div>
        <div className="flex gap-2">
          {['7d', '15d', '30d', '90d'].map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                period === p
                  ? 'bg-orange-500 text-white' 
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      {/* Metrics Cards */}
      <div className="grid md:grid-cols-4 gap-4">
        {(analytics.metrics ?? []).map((metric) => (
          <div key={metric.label} className="bg-white rounded-xl border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-500">{metric.label}</span>
              <span className={`flex items-center gap-1 text-sm font-medium ${
                metric.change >= 0 ? 'text-green-600' : 'text-red-600'
              }`}>
                {metric.change >= 0 ? <FaArrowUp className="text-xs" /> : <FaArrowDown className="text-xs" />}
                {Math.abs(metric.change).toFixed(2)}%
              </span>
            </div>
            <div className="text-2xl font-bold text-gray-900">{metric.value}</div>
            <div className="mt-4 h-12 flex items-end gap-1">
              {metric.chartData.map((h, i) => (
                <div 
                  key={i}
                  className="flex-1 bg-orange-200 rounded-t-sm transition-all hover:bg-orange-400"
                  style={{ height: `${h}%` }}
                />
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Models Table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <div className="flex gap-4">
            <button className="px-4 py-2 bg-gray-100 rounded-lg text-sm font-medium text-gray-900">
              Models
            </button>
            <button className="px-4 py-2 text-sm font-medium text-gray-500 hover:text-gray-900">
              Deployments
            </button>
          </div>
          <div className="flex gap-2">
            <button className="px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded-lg">
              Filter
            </button>
            <button className="px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded-lg">
              Columns
            </button>
          </div>
        </div>
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Name</th>
              <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Avg Cost/Req ($)</th>
              <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Total Tokens</th>
              <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Input/Req</th>
              <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Output/Req</th>
              <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Tokens/Sec</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {(analytics.models ?? []).map((model) => (
              <tr key={model.name} className="hover:bg-gray-50">
                <td className="px-6 py-4">
                  <div className="flex items-center gap-2">
                    <div className="w-6 h-6 bg-linear-to-br from-orange-400 to-orange-600 rounded-md" />
                    <span className="font-medium text-gray-900">{model.name}</span>
                  </div>
                </td>
                <td className="px-6 py-4 text-sm text-gray-600">{(model.cost ?? 0).toFixed(3)}</td>
                <td className="px-6 py-4 text-sm text-gray-600">{(model.tokens ?? 0).toLocaleString()}</td>
                <td className="px-6 py-4 text-sm text-gray-600">{(model.input ?? 0).toLocaleString()}</td>
                <td className="px-6 py-4 text-sm text-gray-600">{(model.output ?? 0).toLocaleString()}</td>
                <td className="px-6 py-4 text-sm text-gray-600">{(model.speed ?? 0).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
