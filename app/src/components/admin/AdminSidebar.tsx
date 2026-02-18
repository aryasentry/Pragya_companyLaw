'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  FaHome,
  FaUpload,
  FaClipboardList,
  FaBell,
  FaChartBar,
  FaHeartbeat,
  FaComments,
  FaFolder,
  FaCog,
  FaSignOutAlt,
  FaSearch,
  FaChevronDown,
  FaBalanceScale,
} from 'react-icons/fa';

interface SidebarItem {
  id: string;
  label: string;
  icon: React.ReactNode;
  badge?: number;
}

interface AdminSidebarProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
}

const mainNavItems: SidebarItem[] = [
  { id: 'dashboard', label: 'Home', icon: <FaHome /> },
  { id: 'ingestion', label: 'Ingestion', icon: <FaUpload /> },
  { id: 'audit', label: 'Audit Log', icon: <FaClipboardList /> },
  { id: 'notifications', label: 'Notifications', icon: <FaBell />, badge: 3 },
];

const systemNavItems: SidebarItem[] = [
  { id: 'chat', label: 'Chat', icon: <FaComments /> },
  { id: 'documents', label: 'Documents', icon: <FaFolder /> },
  { id: 'settings', label: 'Settings', icon: <FaCog /> },
];

export default function AdminSidebar({ activeTab, onTabChange }: AdminSidebarProps) {
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState('');
  const [projectsExpanded, setProjectsExpanded] = useState(true);

  const NavItem = ({ item, isActive }: { item: SidebarItem; isActive: boolean }) => (
    <button
      onClick={() => onTabChange(item.id)}
      className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${
        isActive
          ? 'bg-orange-50 text-orange-600 border-l-3 border-orange-500'
          : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
      }`}
    >
      <span className={`text-lg ${isActive ? 'text-orange-500' : 'text-gray-400'}`}>
        {item.icon}
      </span>
      <span className="flex-1 text-left">{item.label}</span>
      {item.badge && (
        <span className="bg-orange-500 text-white text-xs px-2 py-0.5 rounded-full">
          {item.badge}
        </span>
      )}
    </button>
  );

  return (
    <div className="w-64 bg-white border-r border-gray-200 flex flex-col h-screen">
      {/* Logo Section */}
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-linear-to-br from-orange-400 to-orange-600 rounded-lg flex items-center justify-center">
            <FaBalanceScale className="text-white text-sm" />
          </div>
          <span className="text-lg font-bold text-gray-900">Pragya</span>
          <FaChevronDown className="text-gray-400 text-xs ml-auto" />
        </div>
      </div>

      {/* Search */}
      <div className="p-3">
        <div className="relative">
          <FaSearch className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 text-sm" />
          <input
            type="text"
            placeholder="Search"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-12 py-2 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent"
          />
          <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-gray-400 bg-gray-200 px-1.5 py-0.5 rounded">
            ⌘K
          </span>
        </div>
      </div>

      {/* Main Navigation */}
      <nav className="flex-1 overflow-y-auto px-3 py-2">
        <div className="space-y-1">
          {mainNavItems.map((item) => (
            <NavItem key={item.id} item={item} isActive={activeTab === item.id} />
          ))}
        </div>

        {/* Projects Section */}
        <div className="mt-6">
          <button
            onClick={() => setProjectsExpanded(!projectsExpanded)}
            className="w-full flex items-center gap-2 px-3 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wider hover:text-gray-700"
          >
            <FaChevronDown
              className={`transition-transform ${projectsExpanded ? '' : '-rotate-90'}`}
            />
            System
          </button>
          {projectsExpanded && (
            <div className="mt-1 space-y-1">
              {systemNavItems.map((item) => (
                <NavItem key={item.id} item={item} isActive={activeTab === item.id} />
              ))}
            </div>
          )}
        </div>
      </nav>

      {/* Footer */}
      <div className="p-3 border-t border-gray-200">
        <div className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-gray-100 cursor-pointer">
          <div className="w-8 h-8 bg-linear-to-br from-blue-500 to-blue-700 rounded-full flex items-center justify-center text-white text-sm font-semibold">
            A
          </div>
          <div className="flex-1">
            <div className="text-sm font-medium text-gray-900">Admin User</div>
            <div className="text-xs text-gray-500">Pro plan</div>
          </div>
          <button
            onClick={() => router.push('/')}
            className="text-gray-400 hover:text-gray-600"
            title="Exit Admin"
          >
            <FaSignOutAlt />
          </button>
        </div>
      </div>
    </div>
  );
}
