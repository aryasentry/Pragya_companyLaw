import { NextRequest, NextResponse } from 'next/server';

const FLASK_API_URL = process.env.FLASK_API_URL || 'http://localhost:5000';

/** GET audit log from Flask (reads admin_audit_log table) */
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const url = `${FLASK_API_URL}/api/admin/audit?${searchParams.toString()}`;
    const response = await fetch(url);
    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('[AUDIT] Proxy error:', error);
    return NextResponse.json(
      { success: false, error: error instanceof Error ? error.message : 'Audit fetch failed' },
      { status: 500 }
    );
  }
}
