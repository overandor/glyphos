// MasseurBoost Bridge — Popup Script

document.addEventListener('DOMContentLoaded', () => {
  const statusBox = document.getElementById('status-box');
  const statusText = document.getElementById('status-text');
  const dataSection = document.getElementById('data-section');
  const btnConnect = document.getElementById('btn-connect');
  const btnExtract = document.getElementById('btn-extract');

  // Load current state
  chrome.storage.local.get('bridgeState', (result) => {
    const state = result.bridgeState;
    if (state && state.connected) {
      statusBox.className = 'status connected';
      statusText.textContent = 'Connected to dashboard';
      dataSection.style.display = 'block';
      document.getElementById('rm-login').textContent = state.rmLoggedIn ? '✓ Logged in' : 'Not logged in';
      document.getElementById('rm-visitors').textContent = state.lastVisitorCount ?? '—';
      document.getElementById('rm-profile').textContent = state.lastProfileData?.name || '—';
    }
  });

  // Connect to dashboard
  btnConnect.addEventListener('click', () => {
    chrome.runtime.sendMessage({ type: 'DASHBOARD_CONNECT' }, (response) => {
      if (response?.ok) {
        statusBox.className = 'status connected';
        statusText.textContent = 'Connected to dashboard';
        dataSection.style.display = 'block';
      }
    });
  });

  // Extract data from active RM tab
  btnExtract.addEventListener('click', () => {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0] && tabs[0].url && tabs[0].url.includes('rentmasseur.com')) {
        chrome.tabs.sendMessage(tabs[0].id, { type: 'EXTRACT_DATA' }, (response) => {
          if (response?.ok) {
            document.getElementById('rm-visitors').textContent = response.visitors ?? '—';
            document.getElementById('rm-profile').textContent = response.profile?.name || '—';
            chrome.storage.local.get('bridgeState', (result) => {
              const state = result.bridgeState || {};
              document.getElementById('rm-login').textContent = state.rmLoggedIn ? '✓ Logged in' : 'Not logged in';
            });
          } else {
            statusText.textContent = 'No RM data found on this page';
          }
        });
      } else {
        statusText.textContent = 'Open a RentMasseur page first';
      }
    });
  });
});
