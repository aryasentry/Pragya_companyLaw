import { NextRequest, NextResponse } from 'next/server';

/**
 * Ingest API - Proxies to Flask backend
 * All file handling and pipeline execution happens in Flask
 */
export async function POST(req: NextRequest) {
  try {
    const formData = await req.formData();
    
    // Forward to Flask backend
    const response = await fetch('http://localhost:5000/api/admin/ingest', {
      method: 'POST',
      body: formData,
    });
    
    const result = await response.json();
    
    return NextResponse.json(result, { status: response.status });
    
  } catch (error) {
    console.error('[INGEST] Proxy error:', error);
    return NextResponse.json(
      { success: false, error: error instanceof Error ? error.message : 'Ingest failed' },
      { status: 500 }
    );
  }
}
