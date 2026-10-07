{
  rustPlatform,
  lib,
  libdrm,
  libglvnd,
  vulkan-loader,
  runtimeShell,
  addDriverRunpath,
  python3Packages,
  liquidctl,
  protobuf,
  kmod,
  hwdata,
  nodejs,
  coolercontrol-ui-data,
  version,
  src,
  cargoHash,
}:

rustPlatform.buildRustPackage {
  pname = "coolercontrold";
  inherit version src;
  sourceRoot = "${src.name}/coolercontrold";

  inherit cargoHash;

  patches = [
    ./patches/i2c-client-identity.patch
    ./patches/macsmc-hwmon-fan-control.patch
    ./patches/apple-silicon-cpu-device.patch
    ./patches/tas2764-unsampled-temp.patch
  ];

  env.HWDATA_PKGDATADIR = "${hwdata}/share/hwdata";

  buildInputs = [
    libdrm
    nodejs
  ];

  nativeBuildInputs = [
    protobuf
    addDriverRunpath
    python3Packages.wrapPython
  ];

  pythonPath = [ liquidctl ];

  postPatch = ''
    mkdir -p ui-build
    cp -R ${coolercontrol-ui-data}/* resources/app/

    substituteInPlace daemon/src/repositories/utils.rs \
      --replace-fail 'Command::new("sh")' 'Command::new("${runtimeShell}")'
  '';

  postInstall = ''
    install -Dm444 "${src}/packaging/systemd/coolercontrold.service" -t "$out/lib/systemd/system"
    substituteInPlace "$out/lib/systemd/system/coolercontrold.service" \
      --replace-fail '/usr/bin' "$out/bin"

    # NixOS: redirect config/plugins/state to StateDirectory (/var/lib/coolercontrol)
    # so the daemon works with ProtectSystem=strict (can't write to /etc)
    sed -i '/\[Service\]/a Environment="CC_CONFIG_DIR=/var/lib/coolercontrol"' \
      "$out/lib/systemd/system/coolercontrold.service"
    grep -qF 'Environment="CC_CONFIG_DIR=/var/lib/coolercontrol"' \
      "$out/lib/systemd/system/coolercontrold.service" || {
      echo "[FAIL] coolercontrold.service: no [Service] section to append CC_CONFIG_DIR after."
      echo "Without it the daemon cannot write its config under ProtectSystem=strict."
      exit 1
    }
  '';

  postFixup = ''
    addDriverRunpath "$out/bin/coolercontrold"

    # libdrm_amdgpu_sys dlopens libdrm_amdgpu.so.1, and the GPU stress test's
    # wgpu dlopens libvulkan.so.1 and libEGL.so.1, so nothing links them and
    # buildInputs alone leaves the daemon unable to find them: AMD detection
    # degrades, an RDNA3/4 card is never identified, and the stress test finds
    # no GPU. The RUNPATH resolves them from the binary itself, which also puts
    # them in the runtime closure.
    patchelf --add-rpath "${
      lib.makeLibraryPath [
        libdrm
        vulkan-loader
        libglvnd
      ]
    }" "$out/bin/coolercontrold"

    buildPythonPath "''${pythonPath[*]}"
    wrapProgram "$out/bin/coolercontrold" \
      --prefix PATH : ${
        lib.makeBinPath [
          kmod
          nodejs
        ]
      }:$program_PATH \
      --prefix PYTHONPATH : $program_PYTHONPATH
  '';

  meta = {
    description = "CoolerControl daemon — monitor and control your cooling devices";
    homepage = "https://gitlab.com/coolercontrol/coolercontrol";
    license = lib.licenses.gpl3Plus;
    platforms = [
      "x86_64-linux"
      "aarch64-linux"
    ];
    mainProgram = "coolercontrold";
    maintainers = [
      {
        name = "Daaboulex";
        github = "Daaboulex";
        githubId = 39669593;
      }
    ];
  };
}
