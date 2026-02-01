import { NextResponse } from 'next/server';

// Settings storage - will be replaced with database/config file
let settings = {
  general: {
    systemName: 'Pragya - Company Law CompanyGPT',
    defaultLanguage: 'English',
    autoEmbedding: true,
    maintenanceMode: false,
  },
  database: {
    host: 'localhost',
    port: 5432,
    name: 'pragya_governance',
    status: 'connected',
  },
  api: {
    openaiKey: 'sk-••••••••••••••••••••••••••••••••',
    cohereKey: '••••••••••••••••••••••••••••••••',
    apiLogging: true,
  },
  notifications: {
    emailEnabled: true,
    emailRecipients: ['admin@pragya.in'],
    slackEnabled: false,
    slackWebhook: '',
  },
  security: {
    twoFactorEnabled: false,
    sessionTimeout: 3600,
    maxLoginAttempts: 5,
  },
  appearance: {
    darkMode: false,
    compactMode: false,
  },
};

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const section = searchParams.get('section');

  if (section && settings[section as keyof typeof settings]) {
    return NextResponse.json({
      success: true,
      data: settings[section as keyof typeof settings],
    });
  }

  // Return all settings (mask sensitive data)
  const maskedSettings = {
    ...settings,
    api: {
      ...settings.api,
      openaiKey: settings.api.openaiKey ? '••••••••••••••••' : '',
      cohereKey: settings.api.cohereKey ? '••••••••••••••••' : '',
    },
  };

  return NextResponse.json({
    success: true,
    data: maskedSettings,
  });
}

export async function PATCH(request: Request) {
  try {
    const body = await request.json();
    const { section, updates } = body;

    if (!section || !updates) {
      return NextResponse.json(
        { success: false, error: 'Section and updates are required' },
        { status: 400 }
      );
    }

    if (!settings[section as keyof typeof settings]) {
      return NextResponse.json(
        { success: false, error: 'Invalid section' },
        { status: 400 }
      );
    }

    // Update settings
    settings = {
      ...settings,
      [section]: {
        ...settings[section as keyof typeof settings],
        ...updates,
      },
    };

    return NextResponse.json({
      success: true,
      message: 'Settings updated successfully',
      data: settings[section as keyof typeof settings],
    });
  } catch {
    return NextResponse.json(
      { success: false, error: 'Failed to update settings' },
      { status: 500 }
    );
  }
}
