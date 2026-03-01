import { NextRequest, NextResponse } from 'next/server';

const FLASK_API_URL = process.env.FLASK_API_URL || 'http://localhost:5000';

/** POST approve vision-extracted document (move to data/, run pipeline) */
export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const response = await fetch(`${FLASK_API_URL}/api/admin/approve-vision`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const result = await response.json();
    return NextResponse.json(result, { status: response.status });
  } catch (error) {
    console.error('[APPROVE-VISION] Proxy error:', error);
    return NextResponse.json(
      { success: false, error: error instanceof Error ? error.message : 'Approve failed' },
      { status: 500 }
    );
  }
}
