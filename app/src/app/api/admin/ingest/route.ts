import { NextResponse } from 'next/server';

// Ingestion API - handles document upload and metadata storage
// Will be connected to the actual ingestion pipeline later
// Note: writeFile, mkdir, and path are commented out until file storage is implemented
// import { writeFile, mkdir } from 'fs/promises';
// import path from 'path';

interface IngestionRequest {
  documentType: string;
  isBinding: boolean;
  section?: string;
  inputType: 'text' | 'pdf';
  textContent?: string;
  title?: string;
  dateIssued: string;
  effectiveDateFrom?: string;
  effectiveDateTo?: string;
  complianceArea: string;
  documentLanguage: string;
  notificationNumber?: string;
  issuedBy?: string;
}

// In-memory queue for ingestion jobs (will be replaced with proper queue)
const ingestionQueue: Array<{
  id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  data: IngestionRequest;
  createdAt: string;
  completedAt?: string;
  error?: string;
}> = [];

export async function POST(request: Request) {
  try {
    const contentType = request.headers.get('content-type');

    let ingestionData: IngestionRequest;
    let fileBuffer: Buffer | null = null;
    let fileName: string | null = null;

    if (contentType?.includes('multipart/form-data')) {
      // Handle file upload
      const formData = await request.formData();
      
      const file = formData.get('file') as File | null;
      const metadata = formData.get('metadata') as string;
      
      if (!metadata) {
        return NextResponse.json(
          { success: false, error: 'Metadata is required' },
          { status: 400 }
        );
      }

      ingestionData = JSON.parse(metadata);

      if (file) {
        fileBuffer = Buffer.from(await file.arrayBuffer());
        fileName = file.name;
      }
    } else {
      // Handle JSON request (text content)
      ingestionData = await request.json();
    }

    // Validate required fields
    const requiredFields = ['documentType', 'dateIssued', 'complianceArea', 'documentLanguage'];
    for (const field of requiredFields) {
      if (!ingestionData[field as keyof IngestionRequest]) {
        return NextResponse.json(
          { success: false, error: `${field} is required` },
          { status: 400 }
        );
      }
    }

    // Validate binding documents have section
    if (ingestionData.isBinding && !ingestionData.section) {
      const bindingTypes = ['act', 'rule', 'notification', 'circular', 'order', 'form', 'schedule', 'register', 'return'];
      if (bindingTypes.includes(ingestionData.documentType)) {
        return NextResponse.json(
          { success: false, error: 'Section is required for binding documents' },
          { status: 400 }
        );
      }
    }

    // Generate ingestion job ID
    const jobId = `ING-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

    // Determine storage path
    let storagePath: string;
    if (ingestionData.isBinding && ingestionData.section) {
      const sectionPadded = ingestionData.section.padStart(3, '0');
      storagePath = `raw/companies_act/section_${sectionPadded}/${ingestionData.documentType}s`;
    } else {
      // Non-binding documents
      const typeFolder = ingestionData.documentType === 'qa' || ingestionData.documentType === 'qa_book' 
        ? 'qa' 
        : ingestionData.documentType === 'textbook' || ingestionData.documentType === 'commentary'
          ? 'textbooks'
          : 'other';
      storagePath = `raw/non-binding/${typeFolder}`;
    }

    // Create ingestion job
    const job = {
      id: jobId,
      status: 'pending' as const,
      data: ingestionData,
      createdAt: new Date().toISOString(),
      storagePath,
      fileName,
      hasFile: !!fileBuffer,
    };

    ingestionQueue.push(job);

    // In a real implementation, we would:
    // 1. Save the file to the storage path
    // 2. Trigger the chunking engine
    // 3. Generate embeddings
    // 4. Store in PostgreSQL database

    // For now, simulate async processing
    setTimeout(() => {
      const jobIndex = ingestionQueue.findIndex(j => j.id === jobId);
      if (jobIndex !== -1) {
        ingestionQueue[jobIndex].status = 'completed';
        ingestionQueue[jobIndex].completedAt = new Date().toISOString();
      }
    }, 3000);

    return NextResponse.json({
      success: true,
      data: {
        jobId,
        status: 'pending',
        message: 'Document queued for ingestion',
        storagePath,
        estimatedTime: '30 seconds',
      },
    });

  } catch (error) {
    console.error('Ingestion error:', error);
    return NextResponse.json(
      { success: false, error: 'Failed to process ingestion request' },
      { status: 500 }
    );
  }
}

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const jobId = searchParams.get('jobId');

  if (jobId) {
    const job = ingestionQueue.find(j => j.id === jobId);
    if (!job) {
      return NextResponse.json(
        { success: false, error: 'Job not found' },
        { status: 404 }
      );
    }
    return NextResponse.json({ success: true, data: job });
  }

  // Return all jobs
  return NextResponse.json({
    success: true,
    data: ingestionQueue,
    total: ingestionQueue.length,
  });
}
