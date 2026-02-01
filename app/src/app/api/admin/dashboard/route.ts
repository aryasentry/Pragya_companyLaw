import { NextResponse } from 'next/server';

// Dashboard statistics - will be replaced with database aggregations
const getDashboardStats = () => {
  const now = new Date();
  const dayOfMonth = now.getDate();

  // Simulate growing numbers based on day
  return {
    overview: {
      totalQueries: 1200 + dayOfMonth * 47,
      queryChange: 15.58,
      totalDocuments: 1016,
      documentChange: 1.44,
      activeUsers: 340 + Math.floor(Math.random() * 10),
      userChange: 0.33,
      avgLatency: `${800 + Math.floor(Math.random() * 50)}ms`,
      latencyChange: -2.58,
    },
    documentsByType: [
      { type: 'Act', count: 42, color: 'bg-blue-500' },
      { type: 'Rules', count: 156, color: 'bg-green-500' },
      { type: 'Notifications', count: 234, color: 'bg-amber-500' },
      { type: 'Circulars', count: 189, color: 'bg-purple-500' },
      { type: 'Forms', count: 78, color: 'bg-pink-500' },
      { type: 'Orders', count: 45, color: 'bg-indigo-500' },
      { type: 'Schedules', count: 32, color: 'bg-cyan-500' },
      { type: 'Q&A', count: 240, color: 'bg-orange-500' },
    ],
    recentActivity: [
      { title: 'New notification ingested', time: '30m ago', type: 'ingest' },
      { title: 'Circular updated for Section 134', time: '1h ago', type: 'update' },
      { title: 'Batch embedding completed', time: '2h ago', type: 'system' },
      { title: 'New user registered', time: '3h ago', type: 'user' },
      { title: 'Q&A document added', time: '4h ago', type: 'ingest' },
    ],
    chartData: generateChartData(15),
  };
};

function generateChartData(days: number): number[] {
  const data: number[] = [];

  for (let i = 0; i < days; i++) {
    data.push(30 + Math.floor(Math.random() * 70));
  }

  return data;
}

export async function GET() {
  const stats = getDashboardStats();

  return NextResponse.json({
    success: true,
    data: stats,
    generatedAt: new Date().toISOString(),
  });
}
