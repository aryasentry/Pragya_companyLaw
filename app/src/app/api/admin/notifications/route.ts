import { NextResponse } from 'next/server';

// In-memory storage for notifications (will be replaced with database)
let notifications = [
  {
    id: 'notif-001',
    type: 'SUCCESS',
    title: 'Ingestion Complete',
    message: 'Successfully ingested 15 documents from batch upload. All embeddings generated.',
    timestamp: '2026-02-01T10:30:00Z',
    read: false,
  },
  {
    id: 'notif-002',
    type: 'WARNING',
    title: 'Embedding Queue Backlog',
    message: 'There are 42 documents pending embedding generation. Consider scaling up workers.',
    timestamp: '2026-02-01T09:15:00Z',
    read: false,
  },
  {
    id: 'notif-003',
    type: 'ERROR',
    title: 'Database Connection Issue',
    message: 'Intermittent connection failures detected with PostgreSQL. Last failure: 2 hours ago.',
    timestamp: '2026-02-01T08:00:00Z',
    read: false,
  },
  {
    id: 'notif-004',
    type: 'INFO',
    title: 'System Maintenance Scheduled',
    message: 'Scheduled maintenance window: Feb 5, 2026, 02:00-04:00 IST. Services may be unavailable.',
    timestamp: '2026-01-31T16:45:00Z',
    read: true,
  },
  {
    id: 'notif-005',
    type: 'SUCCESS',
    title: 'New Section Added',
    message: 'Section 43 folder structure created successfully with all subfolders.',
    timestamp: '2026-01-31T14:20:00Z',
    read: true,
  },
  {
    id: 'notif-006',
    type: 'INFO',
    title: 'API Usage Report',
    message: 'Weekly API usage report is ready. Total queries: 1,247. Average latency: 822ms.',
    timestamp: '2026-01-30T11:00:00Z',
    read: true,
  },
];

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const filter = searchParams.get('filter') || 'all';

  let filteredNotifications = [...notifications];

  if (filter === 'unread') {
    filteredNotifications = filteredNotifications.filter(n => !n.read);
  }

  const unreadCount = notifications.filter(n => !n.read).length;

  return NextResponse.json({
    success: true,
    data: filteredNotifications,
    unreadCount,
    total: notifications.length,
  });
}

export async function PATCH(request: Request) {
  const body = await request.json();
  const { id, action } = body;

  if (action === 'markAsRead' && id) {
    notifications = notifications.map(n =>
      n.id === id ? { ...n, read: true } : n
    );
    return NextResponse.json({ success: true, message: 'Notification marked as read' });
  }

  if (action === 'markAllAsRead') {
    notifications = notifications.map(n => ({ ...n, read: true }));
    return NextResponse.json({ success: true, message: 'All notifications marked as read' });
  }

  return NextResponse.json({ success: false, error: 'Invalid action' }, { status: 400 });
}

export async function DELETE(request: Request) {
  const { searchParams } = new URL(request.url);
  const id = searchParams.get('id');

  if (!id) {
    return NextResponse.json({ success: false, error: 'ID required' }, { status: 400 });
  }

  notifications = notifications.filter(n => n.id !== id);
  return NextResponse.json({ success: true, message: 'Notification deleted' });
}
