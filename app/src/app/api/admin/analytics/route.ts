import { NextResponse } from 'next/server';

// Analytics data - will be replaced with actual metrics collection
const getAnalyticsData = (period: string) => {
  const multiplier = period === '7d' ? 0.5 : period === '30d' ? 1 : period === '90d' ? 3 : 1;

  return {
    summary: {
      totalCost: 0.16 * multiplier,
      totalTokens: Math.floor(25352 * multiplier),
      latencyP50: 822,
      latencyP95: 1450,
      latencyP99: 2100,
      errorRate: 2.36,
      totalRequests: Math.floor(56 * multiplier),
    },
    changes: {
      cost: 1.72,
      tokens: 1.44,
      latency: 0.33,
      errorRate: -2.58,
    },
    models: [
      { 
        name: 'embed-english-light', 
        provider: 'cohere',
        avgCostPerReq: 0.003, 
        totalTokens: 8712, 
        inputPerReq: 5133, 
        outputPerReq: 3579, 
        tokensPerSec: 25352,
        requests: 45,
      },
      { 
        name: 'gemini-2.5-flash', 
        provider: 'google',
        avgCostPerReq: 0.003, 
        totalTokens: 8712, 
        inputPerReq: 5133, 
        outputPerReq: 3579, 
        tokensPerSec: 25352,
        requests: 32,
      },
      { 
        name: 'gpt-4o', 
        provider: 'openai',
        avgCostPerReq: 0.015, 
        totalTokens: 12450, 
        inputPerReq: 8200, 
        outputPerReq: 4250, 
        tokensPerSec: 18500,
        requests: 28,
      },
      { 
        name: 'gpt-4o-mini', 
        provider: 'openai',
        avgCostPerReq: 0.003, 
        totalTokens: 8712, 
        inputPerReq: 5133, 
        outputPerReq: 3579, 
        tokensPerSec: 25352,
        requests: 56,
      },
      { 
        name: 'sonar-pro', 
        provider: 'perplexity',
        avgCostPerReq: 0.005, 
        totalTokens: 9800, 
        inputPerReq: 6200, 
        outputPerReq: 3600, 
        tokensPerSec: 22000,
        requests: 15,
      },
    ],
    hourlyDistribution: generateHourlyData(),
    topQueries: [
      { query: 'What are the requirements for board meetings?', count: 45 },
      { query: 'Director disqualification grounds', count: 38 },
      { query: 'Annual return filing deadline', count: 32 },
      { query: 'CSR spending requirements', count: 28 },
      { query: 'Related party transaction approval', count: 24 },
    ],
  };
};

function generateHourlyData() {
  const data = [];
  for (let hour = 0; hour < 24; hour++) {
    // Simulate higher traffic during business hours (9 AM - 6 PM IST)
    const isBusinessHour = hour >= 9 && hour <= 18;
    const baseValue = isBusinessHour ? 40 : 10;
    const variance = Math.floor(Math.random() * 30);

    data.push({
      hour: `${hour.toString().padStart(2, '0')}:00`,
      requests: baseValue + variance,
    });
  }
  return data;
}

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const period = searchParams.get('period') || '15d';

  const analytics = getAnalyticsData(period);

  return NextResponse.json({
    success: true,
    data: analytics,
    period,
    generatedAt: new Date().toISOString(),
  });
}
