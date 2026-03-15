# Fix CoolerControl Plugin Support on NixOS Plan

> **For agentic workers:** REQUIRED: Use superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable plugin support in CoolerControl by patching the daemon to use a configurable plugin path and updating the NixOS module to provide a mutable plugin directory.

**Architecture:** 
1.  Patch `coolercontrold` to check the `COOLERCONTROL_PLUGINS_PATH` environment variable for plugin discovery.
2.  Update the NixOS module to create `/var/lib/coolercontrol/plugins` and set the environment variable.
3.  Ensure the daemon has access to common plugin runtimes (Python, Node.js) in its `PATH`.

**Tech Stack:** Nix (NixOS), Rust (Patching), Bash.

---

## Chunk 1: Patching the Daemon

### Task 1: Add environment variable override for plugin path
**Files:**
- Modify: `coolercontrold.nix`

- [ ] **Step 1: Add a `postPatch` instruction to replace the hardcoded path logic.**
We need to change how `find_service_manifests` determines the `plugins_dir`.

```nix
    substituteInPlace daemon/src/repositories/service_plugin/service_plugin_repo.rs \
      --replace-fail 'let plugins_dir = Path::new(DEFAULT_PLUGINS_PATH);' \
      'let env_path = std::env::var("COOLERCONTROL_PLUGINS_PATH").unwrap_or_else(|_| DEFAULT_PLUGINS_PATH.to_string()); let plugins_dir = Path::new(&env_path);'
```

- [ ] **Step 2: Commit changes**

---

## Chunk 2: Updating the NixOS Module

### Task 2: Configure plugin directory and environment
**Files:**
- Modify: `module.nix`

- [ ] **Step 1: Add `StateDirectory` and `Environment` to the systemd service.**
Create `/var/lib/coolercontrol` and set the plugin path.

```nix
    systemd.services.coolercontrold = {
      serviceConfig = {
        StateDirectory = "coolercontrol";
        Environment = [
          "COOLERCONTROL_PLUGINS_PATH=/var/lib/coolercontrol/plugins"
        ];
      };
    };
```

- [ ] **Step 2: Ensure the plugin directory exists.**
Use `preStart` or `RuntimeDirectory` logic if needed, but `StateDirectory` handles the base. We should add a `preStart` to create the `plugins` subfolder.

```nix
    systemd.services.coolercontrold.preStart = ''
      mkdir -p /var/lib/coolercontrol/plugins
    '';
```

- [ ] **Step 3: Commit changes**

---

## Chunk 3: Runtime Dependencies

### Task 3: Add Node.js and improve Python wrapping
**Files:**
- Modify: `coolercontrold.nix`

- [ ] **Step 1: Add `nodejs` to `buildInputs` and wrap the path.**
Many plugins use Node.js or Python.

```nix
  postFixup = ''
    ...
    wrapProgram "$out/bin/coolercontrold" \
      --prefix PATH : ${lib.makeBinPath [ kmod pkgs.nodejs ]}:$program_PATH \
      ...
  '';
```

- [ ] **Step 2: Commit changes**

---

## Chunk 4: Verification

### Task 4: Verify Plugin Tab
- [ ] **Step 1: Rebuild and switch to the new configuration.**
- [ ] **Step 2: Verify that `/var/lib/coolercontrol/plugins` exists.**
- [ ] **Step 3: Check if the Plugins tab in the GUI is still empty (it should be, but it shouldn't error out).**
- [ ] **Step 4: (Optional) Drop a dummy manifest in the plugin dir to verify discovery.**
