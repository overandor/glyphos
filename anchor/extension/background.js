// MasseurBoost Bridge — Background Service Worker
// Coordinates between content script (on RM pages) and dashboard

const DASHBOARD_ORIGINS = [
  'http://localhost:*',
  'https://overandor.github.io',
  'https://anchor-blond-sigma.vercel.app',
  'https://josephrw-ollama.hf.space'
];

// State stored in extension storage
let bridgeState = {
  connected: false,
  rmLoggedIn: false,
  lastVisitorCount: null,
  lastProfileData: null,
  dashboardTabId: null
};

// Listen for messages from content script and dashboard
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  switch (message.type) {
    case 'RM_LOGIN_DETECTED':
      bridgeState.rmLoggedIn = true;
      chrome.storage.local.set({ bridgeState });
      notifyDashboard({ type: 'RM_LOGIN_DETECTED' });
      sendResponse({ ok: true });
      break;

    case 'RM_LOGOUT_DETECTED':
      bridgeState.rmLoggedIn = false;
      chrome.storage.local.set({ bridgeState });
      notifyDashboard({ type: 'RM_LOGOUT_DETECTED' });
      sendResponse({ ok: true });
      break;

    case 'RM_VISITOR_COUNT':
      bridgeState.lastVisitorCount = message.count;
      chrome.storage.local.set({ bridgeState });
      notifyDashboard({ type: 'RM_VISITOR_COUNT', count: message.count });
      sendResponse({ ok: true });
      break;

    case 'RM_PROFILE_DATA':
      bridgeState.lastProfileData = message.data;
      chrome.storage.local.set({ bridgeState });
      notifyDashboard({ type: 'RM_PROFILE_DATA', data: message.data });
      sendResponse({ ok: true });
      break;

    case 'DASHBOARD_CONNECT':
      bridgeState.connected = true;
      bridgeState.dashboardTabId = sender.tab?.id || null;
      chrome.storage.local.set({ bridgeState });
      sendResponse({ ok: true, state: bridgeState });
      break;

    case 'DASHBOARD_INSERT_BIO':
      // Forward bio text to content script on active RM tab
      chrome.tabs.query({ url: ['https://rentmasseur.com/*', 'https://www.rentmasseur.com/*'] }, (tabs) => {
        if (tabs.length > 0) {
          chrome.tabs.sendMessage(tabs[0].id, {
            type: 'INSERT_BIO',
            bioText: message.bioText
          }, (response) => {
            sendResponse(response || { ok: false, error: 'No response from RM page' });
          });
        } else {
          sendResponse({ ok: false, error: 'No RentMasseur tab open' });
        }
      });
      return true; // async response

    case 'DASHBOARD_GET_STATE':
      sendResponse({ ok: true, state: bridgeState });
      break;

    default:
      sendResponse({ ok: false, error: 'Unknown message type' });
  }
});

// Notify dashboard — try tabs.sendMessage first, then externally_connectable
function notifyDashboard(message) {
  if (bridgeState.dashboardTabId) {
    chrome.tabs.sendMessage(bridgeState.dashboardTabId, message).catch(() => { });
  }
  // Also broadcast via runtime to any listening dashboard tabs
  chrome.tabs.query({}, (tabs) => {
    for (const tab of tabs) {
      if (tab.id === bridgeState.dashboardTabId) continue;
      const url = tab.url || '';
      const isDashboard = DASHBOARD_ORIGINS.some(o => url.startsWith(o.replace('*', '')));
      if (isDashboard) {
        chrome.tabs.sendMessage(tab.id, message).catch(() => { });
      }
    }
  });
}

// Initialize from storage
chrome.storage.local.get('bridgeState', (result) => {
  if (result.bridgeState) {
    bridgeState = { ...bridgeState, ...result.bridgeState };
  }
});
