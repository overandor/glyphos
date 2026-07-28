// MasseurBoost Bridge — Content Script
// Runs on rentmasseur.com pages
// Detects login state, reads visitor counts, inserts bios

(function () {
  'use strict';

  const RM_ORIGIN = 'https://rentmasseur.com';
  const RM_WWW_ORIGIN = 'https://www.rentmasseur.com';

  // === LOGIN DETECTION ===
  // Check for login indicators on the page
  function detectLoginState() {
    const url = window.location.href;
    const body = document.body?.innerHTML?.toLowerCase() || '';

    // Logged in indicators
    const loggedInIndicators = [
      'logout',
      'my account',
      'my profile',
      'dashboard',
      'edit profile',
      'my listings'
    ];

    // Logged out indicators
    const loggedOutIndicators = [
      'login',
      'sign in',
      'create account',
      'register'
    ];

    const hasLoggedIn = loggedInIndicators.some(ind => body.includes(ind));
    const hasLoggedOut = loggedOutIndicators.some(ind => body.includes(ind));

    // Check for login form specifically
    const loginForm = document.querySelector('form[action*="login"], form[id*="login"], form[class*="login"]');
    const hasLoginForm = !!loginForm;

    if (hasLoggedIn && !hasLoginForm) {
      chrome.runtime.sendMessage({ type: 'RM_LOGIN_DETECTED' });
    } else if (hasLoggedOut && hasLoginForm) {
      chrome.runtime.sendMessage({ type: 'RM_LOGOUT_DETECTED' });
    }
  }

  // === VISITOR COUNT EXTRACTION ===
  // Look for visitor stats on profile/dashboard pages
  function extractVisitorCount() {
    // Try common patterns for visitor count display
    const patterns = [
      // Text-based: "Visitors: 1234" or "Views: 1234"
      /(?:visitors?|views?|profile\s+views?)[:\s]+(\d+)/i,
      // Element with class/id containing "visitor" or "view"
    ];

    // Check elements with visitor/view-related classes
    const visitorElements = document.querySelectorAll(
      '[class*="visitor"], [class*="view"], [id*="visitor"], [id*="view"], [class*="stat"], [class*="counter"]'
    );

    for (const el of visitorElements) {
      const text = el.textContent?.trim() || '';
      for (const pattern of patterns) {
        const match = text.match(pattern);
        if (match) {
          const count = parseInt(match[1]);
          if (count >= 0) {
            chrome.runtime.sendMessage({ type: 'RM_VISITOR_COUNT', count });
            return count;
          }
        }
      }
      // Also check if the element itself is just a number
      const numMatch = text.match(/^(\d+)$/);
      if (numMatch) {
        const count = parseInt(numMatch[1]);
        // Heuristic: only send if the class/id suggests it's a visitor count
        const cls = (el.className + ' ' + el.id).toLowerCase();
        if (cls.includes('visitor') || cls.includes('view')) {
          chrome.runtime.sendMessage({ type: 'RM_VISITOR_COUNT', count });
          return count;
        }
      }
    }

    // Try data attributes
    const dataEl = document.querySelector('[data-visitors], [data-views], [data-profile-views]');
    if (dataEl) {
      const count = parseInt(dataEl.dataset.visitors || dataEl.dataset.views || dataEl.dataset.profileViews || '0');
      if (count >= 0) {
        chrome.runtime.sendMessage({ type: 'RM_VISITOR_COUNT', count });
        return count;
      }
    }

    return null;
  }

  // === PROFILE DATA EXTRACTION ===
  function extractProfileData() {
    const data = {};

    // Try to get profile name
    const nameEl = document.querySelector('h1, h2, [class*="profile-name"], [class*="provider-name"], [id*="profile-name"]');
    if (nameEl) data.name = nameEl.textContent?.trim();

    // Try to get bio text
    const bioEl = document.querySelector('[class*="bio"], [class*="about"], [class*="description"], [id*="bio"], [id*="about"]');
    if (bioEl) data.bio = bioEl.textContent?.trim();

    // Try to get location
    const locationEl = document.querySelector('[class*="location"], [class*="city"], [id*="location"]');
    if (locationEl) data.location = locationEl.textContent?.trim();

    // Try to get rate
    const rateEl = document.querySelector('[class*="rate"], [class*="price"], [class*="fee"]');
    if (rateEl) data.rate = rateEl.textContent?.trim();

    if (Object.keys(data).length > 0) {
      chrome.runtime.sendMessage({ type: 'RM_PROFILE_DATA', data });
    }

    return data;
  }

  // === BIO INSERTION ===
  // Insert AI-generated bio into the RM profile editor
  function insertBio(bioText) {
    // Look for bio/about textarea on profile edit page
    const bioFields = document.querySelectorAll(
      'textarea[name*="bio"], textarea[name*="about"], textarea[name*="description"], ' +
      'textarea[id*="bio"], textarea[id*="about"], textarea[id*="description"], ' +
      'textarea[class*="bio"], textarea[class*="about"], textarea[class*="description"]'
    );

    if (bioFields.length > 0) {
      // Use the first matching textarea
      const field = bioFields[0];

      // Use native setter to trigger React/Vue change events
      const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
        window.HTMLTextAreaElement.prototype, 'value'
      ).set;
      nativeInputValueSetter.call(field, bioText);

      field.dispatchEvent(new Event('input', { bubbles: true }));
      field.dispatchEvent(new Event('change', { bubbles: true }));

      // Visual feedback
      field.style.transition = 'background-color 0.3s';
      field.style.backgroundColor = 'rgba(16, 185, 129, 0.2)';
      setTimeout(() => { field.style.backgroundColor = ''; }, 2000);

      return { ok: true, message: 'Bio inserted into profile editor' };
    }

    return { ok: false, error: 'No bio textarea found on this page. Navigate to your profile editor first.' };
  }

  // === MESSAGE LISTENER ===
  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    switch (message.type) {
      case 'INSERT_BIO':
        const result = insertBio(message.bioText);
        sendResponse(result);
        break;

      case 'EXTRACT_DATA':
        const visitors = extractVisitorCount();
        const profile = extractProfileData();
        detectLoginState();
        sendResponse({ ok: true, visitors, profile });
        break;

      default:
        sendResponse({ ok: false, error: 'Unknown message' });
    }
  });

  // === AUTO-RUN ON PAGE LOAD ===
  // Wait for page to fully render
  setTimeout(() => {
    detectLoginState();
    extractVisitorCount();
    extractProfileData();
  }, 2000);

  // Re-check on navigation (RM may be SPA)
  let lastUrl = window.location.href;
  const observer = new MutationObserver(() => {
    if (!document.body) return;
    if (window.location.href !== lastUrl) {
      lastUrl = window.location.href;
      setTimeout(() => {
        detectLoginState();
        extractVisitorCount();
        extractProfileData();
      }, 1500);
    }
  });
  if (document.body) {
    observer.observe(document.body, { childList: true, subtree: true });
  } else {
    document.addEventListener('DOMContentLoaded', () => {
      observer.observe(document.body, { childList: true, subtree: true });
    });
  }

})();
