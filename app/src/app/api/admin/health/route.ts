import { NextResponse } from 'next/server';

// System health data - will be replaced with actual monitoring
const getSystemHealth = () => {
  // Simulate some variability in metrics
  const baseLatency = 800;
  const variance = Math.floor(Math.random() * 100) - 50;

  return {
    services: [
      {
        name: 'PostgreSQL Database',
        status: 'healthy',
        latency: 12 + Math.floor(Math.random() * 5),
        uptime: '99.99%',
        lastCheck: new Date().toISOString(),
      },
      {
        name: 'Embedding Service',
        status: 'healthy',
        latency: 245 + Math.floor(Math.random() * 30),
        uptime: '99.95%',
        lastCheck: new Date().toISOString(),
      },
      {
        name: 'Retrieval API',
        status: 'healthy',
        latency: baseLatency + variance,
        uptime: '99.98%',
        lastCheck: new Date().toISOString(),
      },
      {
        name: 'LLM Synthesis',
        status: Math.random() > 0.8 ? 'degraded' : 'healthy',
        latency: 1250 + Math.floor(Math.random() * 200),
        uptime: '98.50%',
        lastCheck: new Date().toISOString(),
      },
      {
        name: 'File Storage',
        status: 'healthy',
        uptime: '100%',
        lastCheck: new Date().toISOString(),
      },
    ],
    resources: {
      cpu: 35 + Math.floor(Math.random() * 20),
      memory: 60 + Math.floor(Math.random() * 15),
      disk: 54,
      networkIn: 4 + Math.floor(Math.random() * 3),
      networkOut: 8 + Math.floor(Math.random() * 4),
    },
    database: {
      totalChunks: 1016,
      sectionsIndexed: 43,
      embeddingsGenerated: 892,
      storageUsed: '2.4 GB',
      connectionPool: {
        active: 5,
        idle: 15,
        max: 20,
      },
    },
    lastUpdated: new Date().toISOString(),
  };
};

export async function GET() {
  const health = getSystemHealth();

  // Determine overall status
  const hasDown = health.services.some(s => s.status === 'down');
  const hasDegraded = health.services.some(s => s.status === 'degraded');

  const overallStatus = hasDown ? 'down' : hasDegraded ? 'degraded' : 'healthy';

  return NextResponse.json({
    success: true,
    data: {
      ...health,
      overallStatus,
    },
  });
}
