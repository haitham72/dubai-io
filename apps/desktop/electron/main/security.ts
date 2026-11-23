/** Electron webPreferences that the preload bridge depends on. Pure so tests can lock them. */
export const webPreferencesBase = {
  contextIsolation: true,
  nodeIntegration: false,
  sandbox: true,
  webSecurity: true,
} as const;
