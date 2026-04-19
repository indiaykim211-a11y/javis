/// <reference types="vite/client" />

declare global {
  interface Window {
    javisDesktop?: {
      getPlatform?: () => string;
      getApiBaseUrl?: () => string;
    };
  }
}

export {};
