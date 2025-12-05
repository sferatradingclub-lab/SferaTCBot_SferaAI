# Changelog

## [3.1.0] - 2025-12-05

### 🐛 Bug Fixes

#### Critical Bugs Fixed
1. **agent.py:71** - Fixed `UnboundLocalError` where `unified_state` was used before initialization
   - Moved `unified_state = get_unified_instance()` before `get_user_name()` call
   - Also moved `memory_client` initialization to same location for consistency

2. **chatgpt_service.py** - Removed duplicate `get_chatgpt_response` function definition
   - Deleted lines 308-314 (duplicate function)
   - Added docstring to remaining function

3. **session-view.tsx** - Restored `VideoTrack` component for camera display
   - Added `VideoTrack` to imports from `@livekit/components-react`
   - Uncommented VideoTrack component (was commented due to "import error")

### 📚 Documentation

#### Complete Documentation Overhaul
- **README.md** - Completely rewritten based on actual codebase
  - Removed mentions of deleted features (training, psychologist, ChatGPT buttons)
  - Added accurate description of existing functionality
  - Updated technology stack
  - Added proper setup instructions
  - Added systemd service examples
  - Added troubleshooting section for fixed bugs

#### New Documentation Files
- **complete_code_analysis.md** - Detailed code analysis artifact
  - ~30,000+ lines of code analyzed
  - Factual structure breakdown
  - Actual vs documented features comparison
  - Critical bugs identified (now fixed)
  - Prioritized recommendations

### 🔍 Known Issues (Non-Critical)

1. **Empty Tool Categories** - "Скринеры", "Терминалы", "Снизить ping" показывают "скоро наполним"
   - Not a bug, but planned features

2. **search_internet vs search_web** - Some duplication in agent.py vs tools.py
   - Both work correctly, but could be refactored for consistency

### 📊 Statistics

- **Files Modified**: 4
  - `SferaAI_2/agent.py`
  - `services/chatgpt_service.py`
  - `SferaAI_2/frontend/components/app/session-view.tsx`
  - `README.md`

- **Bugs Fixed**: 3 critical

## [3.0.0] - Previous

Initial integration of Sfera AI into Telegram Bot
Multi-persona system  
Hybrid Knowledge Base
Memory system implementation
Frontend (Next.js 15) integration

---

**Legend:**
- 🐛 Bug Fixes
- ✨ New Features
- 📚 Documentation
- 🔧 Configuration
- ⚡ Performance
- 🔒 Security