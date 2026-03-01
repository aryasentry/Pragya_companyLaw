import { NextRequest, NextResponse } from 'next/server';

const FLASK_API_URL = process.env.FLASK_API_URL || 'http://localhost:5000';

/** POST batch upload to Flask (saves to data/uploads, creates PENDING audit entries). Forward raw body so multiple files are preserved. */
export async function POST(req: NextRequest) {
  try {
    const contentType = req.headers.get('Content-Type') || '';
    const body = await req.arrayBuffer();
    const response = await fetch(`${FLASK_API_URL}/api/admin/batch-upload`, {
      method: 'POST',
      headers: contentType ? { 'Content-Type': contentType } : undefined,
      body: body.byteLength ? body : undefined,
    });
    const result = await response.json();
    return NextResponse.json(result, { status: response.status });
  } catch (error) {
    console.error('[BATCH-UPLOAD] Proxy error:', error);
    return NextResponse.json(
      { success: false, error: error instanceof Error ? error.message : 'Batch upload failed' },
      { status: 500 }
    );
  }
}
