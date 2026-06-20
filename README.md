---
title: Email Crawler Dashboard
emoji: 📧
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# Email Crawler Dashboard

Dual-job email collection pipeline with real-time dashboard. Crawls public law firm websites, hedge fund directories, VC/PE firms, tech transfer offices, IP brokers, and investment banks for business email addresses.

## Features
- **2 simultaneous crawl jobs** running in parallel threads
- **Real-time WebSocket dashboard** with live stats and logs
- **Micro-dossier per email**: name, title, organization, location, phone, category
- **Response likelihood scoring** (0-100) based on heuristics
- **Clustering** by organization domain
- **SQLite storage** with JSON/CSV export

## Categories
- IP Lawyers (patent, trademark, copyright)
- M&A Lawyers (corporate, transactional)
- Hedge Funds
- Private Equity Firms
- Venture Capital Firms
- Tech Transfer Offices (universities)
- IP Brokers & Marketplaces
- IP Valuation Firms
- Investment Banks
