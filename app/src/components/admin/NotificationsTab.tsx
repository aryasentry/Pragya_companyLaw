'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  FaBell,
  FaCheckCircle,
  FaExclamationTriangle,
  FaInfoCircle,
  FaTimesCircle,
  FaCheck,
  FaTrash,
  FaCog,
  FaSync,
} from 'react-icons/fa';
import { SystemNotification } from '@/types/admin';

const typeStyles: Record<string, { bg: string; border: string; icon: React.ReactNode; iconBg: string }> = {
  SUCCESS: {
    bg: 'bg-green-50',
    border: 'border-green-200',
    iconBg: 'bg-green-100',
    icon: <FaCheckCircle className="text-green-500" />,
  },
  WARNING: {
    bg: 'bg-amber-50',
    border: 'border-amber-200',
    iconBg: 'bg-amber-100',
    icon: <FaExclamationTriangle className="text-amber-500" />,
  },
  ERROR: {
    bg: 'bg-red-50',
    border: 'border-red-200',
    iconBg: 'bg-red-100',
    icon: <FaTimesCircle className="text-red-500" />,
  },
  INFO: {
    bg: 'bg-blue-50',
    border: 'border-blue-200',
    iconBg: 'bg-blue-100',
    icon: <FaInfoCircle className="text-blue-500" />,
  },
};

export default function NotificationsTab() {
  const [notifications, setNotifications] = useState<SystemNotification[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'unread'>('all');
  const [unreadCount, setUnreadCount] = useState(0);

  const fetchNotifications = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch(`/api/admin/notifications?filter=${filter}`);
      const data = await response.json();

      if (data.success) {
        setNotifications(data.data);
        setUnreadCount(data.unreadCount);
      }
    } catch (error) {
      console.error('Failed to fetch notifications:', error);
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    fetchNotifications();
  }, [fetchNotifications]);

  const markAsRead = async (id: string) => {
    try {
      const response = await fetch('/api/admin/notifications', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id, action: 'markAsRead' }),
      });

      if (response.ok) {
        setNotifications(prev =>
          prev.map(n => n.id === id ? { ...n, read: true } : n)
        );
        setUnreadCount(prev => Math.max(0, prev - 1));
      }
    } catch (error) {
      console.error('Failed to mark as read:', error);
    }
  };

  const markAllAsRead = async () => {
    try {
      const response = await fetch('/api/admin/notifications', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'markAllAsRead' }),
      });

      if (response.ok) {
        setNotifications(prev => prev.map(n => ({ ...n, read: true })));
        setUnreadCount(0);
      }
    } catch (error) {
      console.error('Failed to mark all as read:', error);
    }
  };

  const deleteNotification = async (id: string) => {
    try {
      const response = await fetch(`/api/admin/notifications?id=${id}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        const wasUnread = notifications.find(n => n.id === id)?.read === false;
        setNotifications(prev => prev.filter(n => n.id !== id));
        if (wasUnread) {
          setUnreadCount(prev => Math.max(0, prev - 1));
        }
      }
    } catch (error) {
      console.error('Failed to delete notification:', error);
    }
  };

  const filteredNotifications = filter === 'unread'
    ? notifications.filter(n => !n.read)
    : notifications;

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffHours < 1) {
      return 'Just now';
    } else if (diffHours < 24) {
      return `${diffHours}h ago`;
    } else if (diffDays < 7) {
      return `${diffDays}d ago`;
    } else {
      return new Intl.DateTimeFormat('en-IN', {
        day: '2-digit',
        month: 'short',
      }).format(date);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
            Notifications
            {unreadCount > 0 && (
              <span className="px-2.5 py-1 bg-orange-500 text-white text-sm font-semibold rounded-full">
                {unreadCount} new
              </span>
            )}
          </h2>
          <p className="text-gray-600">System alerts and important updates</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={fetchNotifications}
            className="flex items-center gap-2 px-4 py-2 text-gray-700 font-medium hover:bg-gray-100 rounded-lg transition-colors"
          >
            <FaSync className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
          <button
            onClick={markAllAsRead}
            disabled={unreadCount === 0}
            className="flex items-center gap-2 px-4 py-2 text-gray-700 font-medium hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <FaCheck />
            Mark all as read
          </button>
          <button className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-700 font-medium hover:bg-gray-50 transition-colors">
            <FaCog />
            Settings
          </button>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex gap-1 bg-gray-100 p-1 rounded-lg w-fit">
        <button
          onClick={() => setFilter('all')}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            filter === 'all'
              ? 'bg-white text-gray-900 shadow-sm'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          All ({notifications.length})
        </button>
        <button
          onClick={() => setFilter('unread')}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            filter === 'unread'
              ? 'bg-white text-gray-900 shadow-sm'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          Unread ({unreadCount})
        </button>
      </div>

      {/* Notifications List */}
      <div className="space-y-3">
        {loading ? (
          <div className="text-center py-12 bg-white rounded-xl border border-gray-200">
            <FaSync className="animate-spin text-2xl text-orange-500 mx-auto mb-3" />
            <p className="text-gray-500">Loading notifications...</p>
          </div>
        ) : filteredNotifications.length === 0 ? (
          <div className="text-center py-12 bg-white rounded-xl border border-gray-200">
            <FaBell className="text-4xl text-gray-300 mx-auto mb-3" />
            <p className="text-gray-500">No notifications to display</p>
          </div>
        ) : (
          filteredNotifications.map((notification) => {
            const style = typeStyles[notification.type];
            return (
              <div
                key={notification.id}
                className={`relative p-4 rounded-xl border transition-all ${style.bg} ${style.border} ${
                  !notification.read ? 'ring-2 ring-orange-500 ring-opacity-50' : ''
                }`}
              >
                {!notification.read && (
                  <div className="absolute top-4 right-4 w-2.5 h-2.5 bg-orange-500 rounded-full" />
                )}
                
                <div className="flex gap-4">
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${style.iconBg}`}>
                    {style.icon}
                  </div>
                  
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <h4 className="font-semibold text-gray-900">{notification.title}</h4>
                        <p className="text-sm text-gray-600 mt-1">{notification.message}</p>
                        <p className="text-xs text-gray-400 mt-2">{formatDate(notification.timestamp)}</p>
                      </div>
                      
                      <div className="flex items-center gap-2">
                        {!notification.read && (
                          <button
                            onClick={() => markAsRead(notification.id)}
                            className="p-2 text-gray-400 hover:text-green-500 hover:bg-white rounded-lg transition-colors"
                            title="Mark as read"
                          >
                            <FaCheck />
                          </button>
                        )}
                        <button
                          onClick={() => deleteNotification(notification.id)}
                          className="p-2 text-gray-400 hover:text-red-500 hover:bg-white rounded-lg transition-colors"
                          title="Delete"
                        >
                          <FaTrash />
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
