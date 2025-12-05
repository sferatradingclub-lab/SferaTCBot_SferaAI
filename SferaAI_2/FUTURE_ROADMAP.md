# Future Development Roadmap

This document outlines the next phases of development for Sfera AI, following the completion of the Core Agent and Knowledge Base.

## 📋 Pending Features

- [ ] **Subscription System** <!-- id: 22 -->
    - [ ] **Backend**: Add usage tracking to `LTMClient` (`interaction_count`, `subscription_tier`). <!-- id: 23 -->
    - [ ] **Backend**: Implement usage limit check in `agent.py`. <!-- id: 24 -->
    - [ ] **Backend**: Add logic to prompt for upgrade when limit reached. <!-- id: 25 -->

- [ ] **Telegram Mini App Integration** <!-- id: 26 -->
    - [ ] **Frontend**: Install `@twa-dev/sdk`. <!-- id: 27 -->
    - [ ] **Frontend**: Initialize WebApp & call `expand()` on mount. <!-- id: 28 -->
    - [ ] **Frontend**: Adapt UI for mobile/desktop TMA (responsive check). <!-- id: 29 -->

- [ ] **Payment & Subscription Service** <!-- id: 30 -->
    - [ ] **Service**: Create `subscription_service.py` (FastAPI) for webhooks & cron. <!-- id: 31 -->
    - [ ] **Payments**: Integrate Cryptomus API (Invoices, Webhooks). <!-- id: 32 -->
    - [ ] **Promo Codes**: Implement `promo_manager.py` (Generate, Redeem, Track). <!-- id: 33 -->
    - [ ] **Notifications**: Implement Telegram Bot notifier for expirations/marketing. <!-- id: 34 -->
    - [ ] **Database**: Migrate `ltm.json` to `sfera.db` (SQLite) for reliability. <!-- id: 35 -->

- [ ] **Support & Feedback** <!-- id: 36 -->
    - [ ] **Frontend**: Implement `SupportModal` (in-app form). <!-- id: 37 -->
    - [ ] **Backend**: Add `/api/support` endpoint to forward messages to Admin Telegram. <!-- id: 38 -->

- [ ] **Production Preparation** <!-- id: 11 -->
    - [ ] **Security & Config**: Audit `.env`, separate Dev/Prod keys, set up CORS. <!-- id: 12 -->
    - [ ] **Backend Deployment**: Dockerize `agent.py`, configure for LiveKit Cloud/VPS. <!-- id: 13 -->
    - [ ] **Frontend Deployment**: Optimize build (`npm run build`), configure Nginx/PM2 or Vercel. <!-- id: 14 -->
    - [ ] **Database Migration**: Plan migration from local TinyDB to persistent storage (if needed). <!-- id: 15 -->
    - [ ] **Monitoring**: Set up logging (Sentry/LogRocket) and health checks. <!-- id: 16 -->

## ✅ Completed Core Features

- [x] **Deep Code Analysis**
- [x] **Documentation Update**
- [x] **Backend Implementation** (Auth, LTM, Tools, Prompts)
- [x] **Frontend Implementation** (Connection details)
- [x] **Knowledge Base Ingestion** (Local files, Gemini 2.5 Flash, Retry logic)
