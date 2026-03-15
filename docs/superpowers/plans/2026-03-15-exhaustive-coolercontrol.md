# Exhaustive CoolerControl Home Manager & Export Plan

> **For agentic workers:** REQUIRED: Use superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the Home Manager module and `export-config.sh` script to support 100% of the CoolerControl v4.0 REST API features, including per-device settings, lighting/LCD control, and plugins.

**Architecture:** 
1.  Extend `hm-module.nix` with new submodules for `devices` (per-channel settings) and `plugins`.
2.  Add API application logic for these new sections in `applyScript`.
3.  Update `export-config.sh` to include these sections in its attribute-set output.
4.  Implement display order persistence by respecting the attribute order in the Nix config.

**Tech Stack:** Nix (Home Manager), Bash, `curl`, `jq`.

---

## Chunk 1: Home Manager Module Extensions

### Task 1: Add Device and Channel Submodules
**Files:**
- Modify: `hm-module.nix`

- [ ] **Step 1: Define `channelSettingsSubmodule`**
Include options for `profile_uid`, `speed_fixed`, `lighting`, and `lcd`.

```nix
  channelSettingsSubmodule = lib.types.submodule {
    options = {
      profile_uid = lib.mkOption {
        type = lib.types.nullOr lib.types.str;
        default = null;
      };
      speed_fixed = lib.mkOption {
        type = lib.types.nullOr lib.types.int;
        default = null;
      };
      lighting = lib.mkOption {
        type = lib.types.nullOr lib.types.attrs;
        default = null;
      };
      lcd = lib.mkOption {
        type = lib.types.nullOr lib.types.attrs;
        default = null;
      };
    };
  };
```

- [ ] **Step 2: Define `deviceSettingsSubmodule`**
Include per-device flags and the `channels` mapping.

```nix
  deviceSettingsSubmodule = lib.types.submodule {
    options = {
      uid = lib.mkOption { type = lib.types.str; };
      is_legacy690 = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
      };
      thinkpad_fan_control = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
      };
      channels = lib.mkOption {
        type = lib.types.lazyAttrsOf channelSettingsSubmodule;
        default = { };
      };
    };
  };
```

- [ ] **Step 3: Define `pluginSubmodule`**
```nix
  pluginSubmodule = lib.types.submodule {
    options = {
      id = lib.mkOption { type = lib.types.str; };
      enabled = lib.mkOption { type = lib.types.bool; default = true; };
      config = lib.mkOption { type = lib.types.nullOr lib.types.str; default = null; };
    };
  };
```

- [ ] **Step 4: Add top-level options for `devices` and `plugins`**
Add these to `options.programs.coolercontrol`.

- [ ] **Step 5: Commit changes**

### Task 2: Implement Application Logic in `applyScript`
**Files:**
- Modify: `hm-module.nix`

- [ ] **Step 1: Add logic to apply per-channel settings (Manual/Profile/Lighting/LCD)**
- [ ] **Step 2: Add logic to apply device-level flags (`is_legacy690`)**
- [ ] **Step 3: Add logic to apply plugin configurations**
- [ ] **Step 4: Add logic to apply Order (profiles, functions, modes)**
- [ ] **Step 5: Commit changes**

---

## Chunk 2: Export Script Enhancements

### Task 3: Update `export-config.sh` for Exhaustive Output
**Files:**
- Modify: `export-config.sh`

- [ ] **Step 1: Add fetching for `/plugins`**
- [ ] **Step 2: Add fetching for per-device settings via `/devices/{uid}/settings`**
- [ ] **Step 3: Update the Nix output to include these new sections**
- [ ] **Step 4: Commit changes**

---

## Chunk 3: Verification

### Task 4: Verify 1:1 Round-trip
- [ ] **Step 1: Run the updated export script**
- [ ] **Step 2: Verify the output can be used in a Home Manager config**
- [ ] **Step 3: Verify no breaking changes for existing configs**
