'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  FaCheckCircle,
  FaExclamationTriangle,
  FaTimesCircle,
  FaDatabase,
  FaServer,
  FaMicrochip,
  FaHdd,
  FaNetworkWired,
  FaSync,
} from 'react-icons/fa';

interface ServiceStatus {
  name: string;
  status: 'healthy' | 'degraded' | 'down';
  latency?: number;
  uptime: string;
  lastCheck: string;
}

interface HealthData {
  services: ServiceStatus[];
  resources: {
    cpu: number;
    memory: number;
    disk: number;
    networkIn: number;
    networkOut: number;
  };
  database: {
    totalChunks: number;
    sectionsIndexed: number;
    embeddingsGenerated: number;
    storageUsed: string;
    connectionPool: {
      active: number;
      idle: number;
      max: number;
    };
  };
  overallStatus: 'healthy' | 'degraded' | 'down';
  lastUpdated: string;
}

const statusConfig = {
  healthy: {
    icon: <FaCheckCircle className="text-green-500" />,
    label: 'Healthy',
    bg: 'bg-green-100',
    text: 'text-green-700',
  },
  degraded: {
    icon: <FaExclamationTriangle className="text-amber-500" />,
    label: 'Degraded',
    bg: 'bg-amber-100',
    text: 'text-amber-700',
  },
  down: {
    icon: <FaTimesCircle className="text-red-500" />,
    label: 'Down',
    bg: 'bg-red-100',
    text: 'text-red-700',
  },
};

export default function SystemHealthTab() {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [loading, setLoading] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const fetchHealth = useCallback(async () => {
    try {
      const response = await fetch('/api/admin/health');
      const data = await response.json();

      if (data.success) {
        setHealth(data.data);
      }
    } catch (error) {
      console.error('Failed to fetch health data:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchHealth();

    // Auto-refresh every 30 seconds if enabled
    let interval: NodeJS.Timeout;
    if (autoRefresh) {
      interval = setInterval(fetchHealth, 30000);
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [fetchHealth, autoRefresh]);

  const formatLastCheck = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);

    if (diffSeconds < 60) return `${diffSeconds} sec ago`;
    if (diffSeconds < 3600) return `${Math.floor(diffSeconds / 60)} min ago`;
    return new Intl.DateTimeFormat('en-IN', {
      hour: '2-digit',
      minute: '2-digit',
    }).format(date);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center">
          <FaSync className="animate-spin text-3xl text-orange-500 mx-auto mb-3" />
          <p className="text-gray-500">Loading system health...</p>
        </div>
      </div>
    );
  }

  if (!health) {
    return (
      <div className="text-center py-20">
        <FaTimesCircle className="text-4xl text-red-400 mx-auto mb-3" />
        <p className="text-gray-500">Failed to load health data</p>
        <button
          onClick={fetchHealth}
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
          <h2 className="text-2xl font-bold text-gray-900">System Health</h2>
          <p className="text-gray-600">Monitor system status and performance metrics</p>
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-gray-600">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="rounded border-gray-300 text-orange-500 focus:ring-orange-500"
            />
            Auto-refresh
          </label>
          <button 
            onClick={fetchHealth}
            className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-700 font-medium hover:bg-gray-50 transition-colors"
          >
            <FaSync className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>
      </div>

      {/* Overall Status */}
      <div className={`rounded-xl p-6 ${
        health.overallStatus === 'healthy' ? 'bg-green-50 border border-green-200' :
        health.overallStatus === 'degraded' ? 'bg-amber-50 border border-amber-200' :
        'bg-red-50 border border-red-200'
      }`}>
        <div className="flex items-center gap-4">
          <div className={`w-16 h-16 rounded-xl flex items-center justify-center text-2xl ${
            health.overallStatus === 'healthy' ? 'bg-green-100' :
            health.overallStatus === 'degraded' ? 'bg-amber-100' :
            'bg-red-100'
          }`}>
            {statusConfig[health.overallStatus].icon}
          </div>
          <div>
            <h3 className="text-xl font-bold text-gray-900">
              System Status: {statusConfig[health.overallStatus].label}
            </h3>
            <p className="text-gray-600">
              {health.overallStatus === 'healthy' 
                ? 'All systems are operational'
                : health.overallStatus === 'degraded'
                  ? 'Some services are experiencing issues'
                  : 'Critical services are down'
              }
            </p>
            <p className="text-sm text-gray-500 mt-1">
              Last updated: {formatLastCheck(health.lastUpdated)}
            </p>
          </div>
        </div>
      </div>

      {/* Resource Metrics */}
      <div className="grid md:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
              <FaMicrochip className="text-blue-500" />
            </div>
            <span className="font-medium text-gray-900">CPU Usage</span>
          </div>
          <div className="text-3xl font-bold text-gray-900 mb-2">{health.resources.cpu}%</div>
          <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${
                health.resources.cpu > 80 ? 'bg-red-500' :
                health.resources.cpu > 60 ? 'bg-amber-500' : 'bg-blue-500'
              }`}
              style={{ width: `${health.resources.cpu}%` }}
            />
          </div>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
              <FaServer className="text-green-500" />
            </div>
            <span className="font-medium text-gray-900">Memory</span>
          </div>
          <div className="text-3xl font-bold text-gray-900 mb-2">{health.resources.memory}%</div>
          <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${
                health.resources.memory > 80 ? 'bg-red-500' :
                health.resources.memory > 60 ? 'bg-amber-500' : 'bg-green-500'
              }`}
              style={{ width: `${health.resources.memory}%` }}
            />
          </div>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
              <FaHdd className="text-purple-500" />
            </div>
            <span className="font-medium text-gray-900">Disk Usage</span>
          </div>
          <div className="text-3xl font-bold text-gray-900 mb-2">{health.resources.disk}%</div>
          <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
            <div className="h-full bg-purple-500 rounded-full" style={{ width: `${health.resources.disk}%` }} />
          </div>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 bg-amber-100 rounded-lg flex items-center justify-center">
              <FaNetworkWired className="text-amber-500" />
            </div>
            <span className="font-medium text-gray-900">Network I/O</span>
          </div>
          <div className="text-3xl font-bold text-gray-900 mb-2">
            {health.resources.networkIn + health.resources.networkOut} MB/s
          </div>
          <div className="text-sm text-gray-500">
            ↑ {health.resources.networkOut} MB/s  ↓ {health.resources.networkIn} MB/s
          </div>
        </div>
      </div>

      {/* Service Status Table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="font-semibold text-gray-900">Service Status</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Service</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Status</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Latency</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Uptime</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Last Check</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {health.services.map((service) => (
                <tr key={service.name} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <FaDatabase className="text-gray-400" />
                      <span className="font-medium text-gray-900">{service.name}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${statusConfig[service.status].bg} ${statusConfig[service.status].text}`}>
                      {statusConfig[service.status].icon}
                      {statusConfig[service.status].label}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-600">
                    {service.latency ? `${service.latency}ms` : '-'}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-600">{service.uptime}</td>
                  <td className="px-6 py-4 text-sm text-gray-500">{formatLastCheck(service.lastCheck)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Database Stats */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="font-semibold text-gray-900 mb-4">Database Statistics</h3>
        <div className="grid md:grid-cols-4 gap-6">
          <div className="text-center">
            <div className="text-3xl font-bold text-gray-900">{health.database.totalChunks.toLocaleString()}</div>
            <div className="text-sm text-gray-500">Total Chunks</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-gray-900">{health.database.sectionsIndexed}</div>
            <div className="text-sm text-gray-500">Sections Indexed</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-gray-900">{health.database.embeddingsGenerated.toLocaleString()}</div>
            <div className="text-sm text-gray-500">Embeddings Generated</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-gray-900">{health.database.storageUsed}</div>
            <div className="text-sm text-gray-500">Storage Used</div>
          </div>
        </div>
        <div className="mt-6 pt-4 border-t border-gray-200">
          <div className="flex items-center justify-center gap-8 text-sm">
            <div>
              <span className="text-gray-500">Active Connections:</span>
              <span className="ml-2 font-semibold text-gray-900">{health.database.connectionPool.active}</span>
            </div>
            <div>
              <span className="text-gray-500">Idle:</span>
              <span className="ml-2 font-semibold text-gray-900">{health.database.connectionPool.idle}</span>
            </div>
            <div>
              <span className="text-gray-500">Max:</span>
              <span className="ml-2 font-semibold text-gray-900">{health.database.connectionPool.max}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
