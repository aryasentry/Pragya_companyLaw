import { NextRequest, NextResponse } from 'next/server';

const FLASK_API_URL = process.env.FLASK_API_URL || 'http://localhost:5000';

export async function GET(request: NextRequest) {
  try {
    const response = await fetch(`${FLASK_API_URL}/api/health`, {
      method: 'GET',
    });

    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json(
        { error: 'Flask backend is not healthy', details: data },
        { status: response.status }
      );
    }

    return NextResponse.json({
      status: 'ok',
      backend: data,
      message: 'Both frontend and backend are running'
    });
  } catch (error) {
    console.error('Health check error:', error);
    return NextResponse.json(
      { 
        status: 'error',
        error: 'Failed to connect to Flask backend',
        message: 'Make sure the Flask server is running on port 5000'
      },
      { status: 503 }
    );
  }
}
