# Coverage Improvement Plan
## Goal: Increase from 76% to 90%+

### Current State
- **Total Lines:** 3649
- **Covered:** 2778 (76%)
- **Missing:** 871 lines
- **Target:** 3284 lines (90%)
- **Need to Cover:** 506 more lines

---

## Priority 1: CRS API (269 missing lines) - CRITICAL
**File:** `app/api/crs.py`
**Current:** 38% (167/436 covered)
**Target:** Add 200+ lines of coverage

### Missing Endpoints/Features to Test:
1. ✅ POST / - Create CRS (has basic tests)
2. ✅ GET /latest - Get latest CRS (has test)
3. ✅ GET /session/{id} - Get CRS by session (has test)
4. ❌ POST /{crs_id}/update-from-session - Update from session (MISSING)
5. ✅ GET /sessions/{id}/preview - Preview (has test)
6. ✅ GET /review - Pending reviews (has test)
7. ✅ GET /my-requests - My requests (has test)
8. ❌ GET /versions - Get versions (NEEDS MORE TESTS)
9. ✅ GET /{id} - Get by ID (has test)
10. ❌ PUT /{id}/status - Update status (NEEDS ERROR CASES)
11. ✅ GET /{id}/audit - Audit logs (has test)
12. ✅ PUT /{id}/content - Update content (has test)
13. ✅ POST /{id}/export - Export (has tests)

### Tests to Add:
- [ ] Error handling for all endpoints (401, 403, 404, 400)
- [ ] Edge cases for CRS creation (invalid data, duplicate)
- [ ] Version history edge cases
- [ ] Status transitions edge cases
- [ ] Permission checks for different user roles
- [ ] Session-based updates
- [ ] Conflict resolution scenarios

---

## Priority 2: Notification Service (54 missing lines)
**File:** `app/services/notification_service.py`
**Current:** 27% (20/74 covered)
**Target:** Add 40+ lines of coverage

### Missing Test Scenarios:
- [ ] Test all notification functions with email sending enabled
- [ ] Test error handling when user not found
- [ ] Test notification creation with various metadata
- [ ] Test email sending failures
- [ ] Test batch notifications
- [ ] Test notification filtering

---

## Priority 3: Chat API (46 missing lines)
**File:** `app/api/chats.py`
**Current:** 78% (163/209 covered)
**Target:** Add 30+ lines of coverage

### Missing Features to Test:
- [ ] Error handling for chat operations
- [ ] Message validation edge cases
- [ ] Chat session management edge cases
- [ ] Permission checks
- [ ] Concurrent access scenarios

---

## Priority 4: Teams API (63 missing lines)
**File:** `app/api/teams.py`
**Current:** 74% (177/240 covered)
**Target:** Add 40+ lines of coverage

### Missing Test Scenarios:
- [ ] Team member role transitions
- [ ] Permission edge cases
- [ ] Team deletion with dependencies
- [ ] Bulk operations
- [ ] Error handling

---

## Priority 5: Export Service (34 missing lines)
**File:** `app/services/export_service.py`
**Current:** 73% (92/126 covered)
**Target:** Add 25+ lines of coverage

### Missing Features:
- [ ] PDF export edge cases
- [ ] HTML export with custom templates
- [ ] Markdown export variations
- [ ] CSV export with complex data
- [ ] Error handling for all formats

---

## Priority 6: Projects API (36 missing lines)
**File:** `app/api/projects.py`
**Current:** 79% (132/168 covered)
**Target:** Add 25+ lines of coverage

---

## Priority 7: Invitations API (33 missing lines)
**File:** `app/api/invitations.py`
**Current:** 59% (47/80 covered)
**Target:** Add 25+ lines of coverage

---

## Quick Wins (High Impact, Low Effort)

### 1. Template Filler Node (20 missing lines)
**File:** `app/ai/nodes/template_filler/template_filler_node.py`
**Current:** 20% (5/25 covered)
**Effort:** LOW - Add 1-2 unit tests
**Impact:** +20 lines

### 2. Memory Node (17 missing lines)
**File:** `app/ai/nodes/memory_node.py`
**Current:** 26% (6/23 covered)
**Effort:** LOW - Add 1-2 unit tests
**Impact:** +17 lines

### 3. Email Utils (20 missing lines)
**File:** `app/utils/email.py`
**Current:** 33% (10/30 covered)
**Effort:** LOW - Add email sending tests with mocks
**Impact:** +20 lines

### 4. Echo Node (2 missing lines)
**File:** `app/ai/nodes/echo_node.py`
**Current:** 50% (2/4 covered)
**Effort:** VERY LOW - Add 1 test
**Impact:** +2 lines

---

## Implementation Order

### Phase 1: Quick Wins (59 lines) - Day 1
1. Echo Node (+2 lines)
2. Template Filler Node (+20 lines)
3. Memory Node (+17 lines)
4. Email Utils (+20 lines)
**Total:** +59 lines → **77.6% coverage**

### Phase 2: Medium Priority (150 lines) - Day 2-3
1. Notification Service (+40 lines)
2. Export Service (+25 lines)
3. Chat API (+30 lines)
4. Teams API (+40 lines)
5. Invitations API (+15 lines)
**Total:** +150 lines → **81.7% coverage**

### Phase 3: CRS API Focus (300 lines) - Day 4-5
1. CRS API comprehensive tests (+200 lines)
2. CRS edge cases (+50 lines)
3. CRS error handling (+50 lines)
**Total:** +300 lines → **90.9% coverage** ✅

---

## Expected Final Coverage: 91%+

**Covered lines:** 2778 + 509 = 3287
**Total lines:** 3649
**Coverage:** 3287/3649 = **90.1%** ✅
