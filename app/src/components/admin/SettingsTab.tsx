'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  FaCog,
  FaDatabase,
  FaKey,
  FaPalette,
  FaBell,
  FaShieldAlt,
  FaSave,
  FaToggleOn,
  FaToggleOff,
  FaSync,
} from 'react-icons/fa';

interface SettingToggleProps {
  label: string;
  description: string;
  enabled: boolean;
  onChange: (enabled: boolean) => void;
}

interface SettingsData {
  general: {
    systemName: string;
    defaultLanguage: string;
    autoEmbedding: boolean;
    maintenanceMode: boolean;
  };
  database: {
    host: string;
    port: string;
    name: string;
    status: 'healthy' | 'degraded' | 'down';
  };
  api: {
    openaiKey: string;
    cohereKey: string;
    apiLogging: boolean;
  };
  notifications: {
    emailNotifications: boolean;
  };
  security: {
    twoFactor: boolean;
  };
  appearance: {
    darkMode: boolean;
  };
}

function SettingToggle({ label, description, enabled, onChange }: SettingToggleProps) {
  return (
    <div className="flex items-center justify-between py-4 border-b border-gray-100 last:border-0">
      <div>
        <p className="font-medium text-gray-900">{label}</p>
        <p className="text-sm text-gray-500">{description}</p>
      </div>
      <button
        onClick={() => onChange(!enabled)}
        className="text-2xl transition-colors"
      >
        {enabled ? (
          <FaToggleOn className="text-orange-500" />
        ) : (
          <FaToggleOff className="text-gray-300" />
        )}
      </button>
    </div>
  );
}

export default function SettingsTab() {
  const [settings, setSettings] = useState<SettingsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [activeSection, setActiveSection] = useState('general');

  const fetchSettings = useCallback(async () => {
    try {
      const response = await fetch('/api/admin/settings');
      const data = await response.json();

      if (data.success) {
        setSettings(data.data);
      }
    } catch (error) {
      console.error('Failed to fetch settings:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSettings();
  }, [fetchSettings]);

  const updateSetting = async (section: string, key: string, value: boolean | string) => {
    if (!settings) return;

    // Update local state immediately
    setSettings(prev => {
      if (!prev) return prev;
      return {
        ...prev,
        [section]: {
          ...(prev[section as keyof SettingsData] as object),
          [key]: value,
        },
      };
    });
  };

  const saveSettings = async () => {
    setSaving(true);
    try {
      const response = await fetch('/api/admin/settings', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings),
      });

      const data = await response.json();
      if (data.success) {
        console.log('Settings saved successfully');
      }
    } catch (error) {
      console.error('Failed to save settings:', error);
    } finally {
      setSaving(false);
    }
  };

  const sections = [
    { id: 'general', label: 'General', icon: <FaCog /> },
    { id: 'database', label: 'Database', icon: <FaDatabase /> },
    { id: 'api', label: 'API Keys', icon: <FaKey /> },
    { id: 'appearance', label: 'Appearance', icon: <FaPalette /> },
    { id: 'notifications', label: 'Notifications', icon: <FaBell /> },
    { id: 'security', label: 'Security', icon: <FaShieldAlt /> },
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center">
          <FaSync className="animate-spin text-3xl text-orange-500 mx-auto mb-3" />
          <p className="text-gray-500">Loading settings...</p>
        </div>
      </div>
    );
  }

  if (!settings) {
    return (
      <div className="text-center py-20">
        <p className="text-gray-500">Failed to load settings</p>
        <button
          onClick={fetchSettings}
          className="mt-4 px-4 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Settings</h2>
        <p className="text-gray-600">Configure system preferences and integrations</p>
      </div>

      <div className="grid lg:grid-cols-4 gap-6">
        {/* Sidebar */}
        <div className="lg:col-span-1">
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <nav className="p-2">
              {sections.map((section) => (
                <button
                  key={section.id}
                  onClick={() => setActiveSection(section.id)}
                  className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-left transition-colors ${
                    activeSection === section.id
                      ? 'bg-orange-50 text-orange-600'
                      : 'text-gray-600 hover:bg-gray-50'
                  }`}
                >
                  <span className={activeSection === section.id ? 'text-orange-500' : 'text-gray-400'}>
                    {section.icon}
                  </span>
                  <span className="font-medium">{section.label}</span>
                </button>
              ))}
            </nav>
          </div>
        </div>

        {/* Content */}
        <div className="lg:col-span-3 space-y-6">
          {activeSection === 'general' && (
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">General Settings</h3>
              
              <div className="space-y-4 mb-6">
                <div>
                  <label className="text-sm font-medium text-gray-700 mb-2">
                    System Name
                  </label>
                  <input
                    type="text"
                    value={settings.general.systemName}
                    onChange={(e) => updateSetting('general', 'systemName', e.target.value)}
                    className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                  />
                </div>
                
                <div>
                  <label className="text-sm font-medium text-gray-700 mb-2">
                    Default Language
                  </label>
                  <select 
                    value={settings.general.defaultLanguage}
                    onChange={(e) => updateSetting('general', 'defaultLanguage', e.target.value)}
                    className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                  >
                    <option value="en">English</option>
                    <option value="hi">Hindi</option>
                  </select>
                </div>
              </div>

              <SettingToggle
                label="Auto-generate Embeddings"
                description="Automatically generate embeddings when new documents are ingested"
                enabled={settings.general.autoEmbedding}
                onChange={(v) => updateSetting('general', 'autoEmbedding', v)}
              />

              <SettingToggle
                label="Maintenance Mode"
                description="Put the system in maintenance mode (users cannot query)"
                enabled={settings.general.maintenanceMode}
                onChange={(v) => updateSetting('general', 'maintenanceMode', v)}
              />
            </div>
          )}

          {activeSection === 'database' && (
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Database Configuration</h3>
              
              <div className="space-y-4">
                <div>
                  <label className="text-sm font-medium text-gray-700 mb-2">
                    PostgreSQL Host
                  </label>
                  <input
                    type="text"
                    value={settings.database.host}
                    onChange={(e) => updateSetting('database', 'host', e.target.value)}
                    className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                  />
                </div>
                
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm font-medium text-gray-700 mb-2">
                      Port
                    </label>
                    <input
                      type="text"
                      value={settings.database.port}
                      onChange={(e) => updateSetting('database', 'port', e.target.value)}
                      className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                    />
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-700 mb-2">
                      Database Name
                    </label>
                    <input
                      type="text"
                      value={settings.database.name}
                      onChange={(e) => updateSetting('database', 'name', e.target.value)}
                      className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                    />
                  </div>
                </div>

                <div className={`border rounded-lg p-4 flex items-center gap-3 ${
                  settings.database.status === 'healthy' 
                    ? 'bg-green-50 border-green-200' 
                    : settings.database.status === 'degraded'
                      ? 'bg-amber-50 border-amber-200'
                      : 'bg-red-50 border-red-200'
                }`}>
                  <div className={`w-3 h-3 rounded-full ${
                    settings.database.status === 'healthy' 
                      ? 'bg-green-500' 
                      : settings.database.status === 'degraded'
                        ? 'bg-amber-500'
                        : 'bg-red-500'
                  }`} />
                  <span className={`font-medium ${
                    settings.database.status === 'healthy' 
                      ? 'text-green-700' 
                      : settings.database.status === 'degraded'
                        ? 'text-amber-700'
                        : 'text-red-700'
                  }`}>
                    Database connection {settings.database.status}
                  </span>
                </div>
              </div>
            </div>
          )}

          {activeSection === 'api' && (
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">API Configuration</h3>
              
              <div className="space-y-4">
                <div>
                  <label className="text-sm font-medium text-gray-700 mb-2">
                    OpenAI API Key
                  </label>
                  <input
                    type="password"
                    value={settings.api.openaiKey}
                    onChange={(e) => updateSetting('api', 'openaiKey', e.target.value)}
                    className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent font-mono"
                  />
                </div>
                
                <div>
                  <label className="text-sm font-medium text-gray-700 mb-2">
                    Cohere API Key
                  </label>
                  <input
                    type="password"
                    value={settings.api.cohereKey}
                    onChange={(e) => updateSetting('api', 'cohereKey', e.target.value)}
                    className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent font-mono"
                  />
                </div>

                <SettingToggle
                  label="API Request Logging"
                  description="Log all API requests for debugging and analytics"
                  enabled={settings.api.apiLogging}
                  onChange={(v) => updateSetting('api', 'apiLogging', v)}
                />
              </div>
            </div>
          )}

          {activeSection === 'notifications' && (
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Notification Preferences</h3>
              
              <SettingToggle
                label="Email Notifications"
                description="Receive email alerts for important system events"
                enabled={settings.notifications.emailNotifications}
                onChange={(v) => updateSetting('notifications', 'emailNotifications', v)}
              />
            </div>
          )}

          {activeSection === 'security' && (
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Security Settings</h3>
              
              <SettingToggle
                label="Two-Factor Authentication"
                description="Require 2FA for admin access"
                enabled={settings.security.twoFactor}
                onChange={(v) => updateSetting('security', 'twoFactor', v)}
              />
            </div>
          )}

          {activeSection === 'appearance' && (
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Appearance</h3>
              
              <SettingToggle
                label="Dark Mode"
                description="Enable dark mode for the admin interface"
                enabled={settings.appearance.darkMode}
                onChange={(v) => updateSetting('appearance', 'darkMode', v)}
              />
            </div>
          )}

          {/* Save Button */}
          <div className="flex justify-end">
            <button 
              onClick={saveSettings}
              disabled={saving}
              className="flex items-center gap-2 px-6 py-3 bg-orange-500 text-white font-semibold rounded-lg hover:bg-orange-600 transition-colors disabled:opacity-50"
            >
              {saving ? <FaSync className="animate-spin" /> : <FaSave />}
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
