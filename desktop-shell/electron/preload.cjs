const { contextBridge } = require("electron");

contextBridge.exposeInMainWorld("javisDesktop", {
  getPlatform: () => process.platform,
  getApiBaseUrl: () => "http://127.0.0.1:8765",
});
