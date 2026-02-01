import { NextResponse } from 'next/server';

// Document listing - will be replaced with filesystem/database queries
const documents = [
  { 
    id: 'doc-001',
    name: 'Notification_GSR_123E.pdf', 
    section: '134', 
    type: 'notification', 
    size: '245 KB',
    createdAt: '2026-02-01T10:30:00Z',
    status: 'active',
  },
  { 
    id: 'doc-002',
    name: 'Circular_CSR_Amendment.pdf', 
    section: '135', 
    type: 'circular', 
    size: '189 KB',
    createdAt: '2026-01-31T16:45:00Z',
    status: 'active',
  },
  { 
    id: 'doc-003',
    name: 'Rule_14A_Board_Meetings.pdf', 
    section: '173', 
    type: 'rule', 
    size: '567 KB',
    createdAt: '2026-01-30T14:20:00Z',
    status: 'active',
  },
  { 
    id: 'doc-004',
    name: 'Form_MGT-7_Annual_Return.pdf', 
    section: '92', 
    type: 'form', 
    size: '890 KB',
    createdAt: '2026-01-29T11:00:00Z',
    status: 'active',
  },
  {
    id: 'doc-005',
    name: 'Section_2_Definitions.pdf',
    section: '002',
    type: 'act',
    size: '2.4 MB',
    createdAt: '2026-01-15T09:00:00Z',
    status: 'active',
  },
  {
    id: 'doc-006',
    name: 'Directors_FAQ.pdf',
    section: null,
    type: 'qa',
    size: '890 KB',
    createdAt: '2026-01-20T14:30:00Z',
    status: 'active',
    binding: false,
  },
];

const folderStructure = {
  name: 'raw',
  type: 'folder',
  children: [
    {
      name: 'companies_act',
      type: 'folder',
      children: [
        {
          name: 'section_001',
          type: 'folder',
          children: [
            { name: 'act', type: 'folder', children: [
              { name: 'section_1_short_title.pdf', type: 'file', size: '124 KB', id: 'file-001' }
            ]},
            { name: 'rules', type: 'folder', children: [] },
            { name: 'notifications', type: 'folder', children: [] },
            { name: 'circulars', type: 'folder', children: [] },
          ],
        },
        {
          name: 'section_002',
          type: 'folder',
          children: [
            { name: 'act', type: 'folder', children: [
              { name: 'section_2_definitions.pdf', type: 'file', size: '2.4 MB', id: 'file-002' }
            ]},
            { name: 'rules', type: 'folder', children: [] },
          ],
        },
        {
          name: 'section_134',
          type: 'folder',
          children: [
            { name: 'act', type: 'folder', children: [
              { name: 'section_134_financial_statement.pdf', type: 'file', size: '456 KB', id: 'file-003' }
            ]},
            { name: 'notifications', type: 'folder', children: [
              { name: 'Notification_GSR_123E.pdf', type: 'file', size: '245 KB', id: 'doc-001' }
            ]},
          ],
        },
      ],
    },
    {
      name: 'non-binding',
      type: 'folder',
      children: [
        {
          name: 'qa',
          type: 'folder',
          children: [
            { name: 'directors_faq.pdf', type: 'file', size: '890 KB', id: 'doc-006' },
            { name: 'agm_common_questions.pdf', type: 'file', size: '567 KB', id: 'file-004' },
          ],
        },
        {
          name: 'textbooks',
          type: 'folder',
          children: [
            { name: 'company_law_guide_2024.pdf', type: 'file', size: '15.2 MB', id: 'file-005' },
          ],
        },
      ],
    },
  ],
};

const stats = {
  totalDocuments: 1016,
  sectionsCount: 43,
  totalSize: '156 MB',
  byType: {
    act: 42,
    rule: 156,
    notification: 234,
    circular: 189,
    form: 78,
    order: 45,
    schedule: 32,
    qa: 240,
  },
};

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const view = searchParams.get('view') || 'list';
  const type = searchParams.get('type');
  const section = searchParams.get('section');
  const search = searchParams.get('search');

  if (view === 'tree') {
    return NextResponse.json({
      success: true,
      data: folderStructure,
    });
  }

  if (view === 'stats') {
    return NextResponse.json({
      success: true,
      data: stats,
    });
  }

  // List view with filters
  let filteredDocs = [...documents];

  if (type) {
    filteredDocs = filteredDocs.filter(d => d.type === type);
  }

  if (section) {
    filteredDocs = filteredDocs.filter(d => d.section === section);
  }

  if (search) {
    const searchLower = search.toLowerCase();
    filteredDocs = filteredDocs.filter(d => 
      d.name.toLowerCase().includes(searchLower)
    );
  }

  return NextResponse.json({
    success: true,
    data: filteredDocs,
    total: filteredDocs.length,
  });
}
