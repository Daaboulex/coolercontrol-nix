# CI + Auto-update Automation Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add CI build verification, automated upstream updates with hash recalculation, stale cleanup, and flake.lock auto-updates.

**Architecture:** Four independent GitHub Actions workflows. CI validates PRs. Auto-update creates PRs with correct hashes. Stale bot cleans up. Lock updater keeps nixpkgs current.

**Tech Stack:** GitHub Actions, Nix, DeterminateSystems actions

**Spec:** `docs/superpowers/specs/2026-03-16-ci-auto-update-design.md`

---

### Task 1: CI workflow

**Files:** Create `.github/workflows/ci.yml`

- [ ] **Step 1:** Write ci.yml
- [ ] **Step 2:** Commit

### Task 2: Enhanced auto-update workflow

**Files:** Replace `.github/workflows/check-upstream.yml`

- [ ] **Step 1:** Rewrite check-upstream.yml with hash extraction and PR creation
- [ ] **Step 2:** Commit

### Task 3: Stale cleanup workflow

**Files:** Create `.github/workflows/stale.yml`

- [ ] **Step 1:** Write stale.yml
- [ ] **Step 2:** Commit

### Task 4: Flake lock update workflow

**Files:** Create `.github/workflows/update-lock.yml`

- [ ] **Step 1:** Write update-lock.yml
- [ ] **Step 2:** Commit

### Task 5: Push and verify

- [ ] **Step 1:** Push all changes
- [ ] **Step 2:** Verify workflows appear in GitHub Actions tab
