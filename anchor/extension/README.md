# MasseurBoost Bridge — Browser Extension

## What it does

The extension is the **data bridge** between RentMasseur and the MasseurBoost dashboard. The iframe alone cannot read RM data due to same-origin policy. This extension:

- **Detects login state** on RentMasseur pages
- **Extracts visitor counts** from profile/dashboard pages
- **Extracts profile data** (name, bio, location, rate)
- **Inserts AI-generated bios** into the RM profile editor
- **Forwards all data** to the MasseurBoost dashboard via message passing

## Install (Chrome / Edge / Brave)

1. Open `chrome://extensions/` (or `edge://extensions/`)
2. Enable **Developer mode** (top right toggle)
3. Click **Load unpacked**
4. Select this `extension/` directory
5. The MasseurBoost icon appears in your toolbar

## Install (Firefox)

1. Open `about:debugging#/runtime/this-firefox`
2. Click **Load Temporary Add-on**
3. Select `manifest.json` in this directory

## Usage

1. Open the MasseurBoost dashboard (`masseurboost.html`)
2. Click the extension icon → **Connect to Dashboard**
3. Open RentMasseur in a tab (or use the iframe in the dashboard)
4. Log in to RentMasseur normally
5. The extension auto-detects login and extracts visitor counts
6. Use AI tools in the dashboard — generated bios can be inserted directly into the RM profile editor via the extension

## Architecture

```
MasseurBoost dashboard (masseurboost.html)
        │
        ├── RentMasseur iframe (window only, no data access)
        │
        └── MasseurBoost extension (data bridge)
              ├── content.js — runs on RM pages, reads DOM
              ├── background.js — coordinates messages
              └── popup.js — manual controls
```

## Privacy

- No credentials are stored — login happens directly on RentMasseur
- Visitor counts and profile data are only read when you're on RM pages
- Data is forwarded to the dashboard via Chrome message passing (local only)
- No data is sent to any external server
