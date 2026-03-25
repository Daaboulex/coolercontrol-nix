{
  rustPlatform,
  lib,
  libdrm,
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

    # Patch the inline pci_ids module to use the Nix store hwdata path.
    # The module has a @hwdata@ placeholder for build-time substitution.
    substituteInPlace daemon/src/repositories/hwmon/pci_ids.rs \
      --replace-fail '@hwdata@' '${hwdata}'
  '';

  # systemd unit is defined in module.nix — not shipped in the package
  # (NixOS auto-discovers units in lib/systemd/system/ and overrides our module)

  postFixup = ''
    addDriverRunpath "$out/bin/coolercontrold"

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
    maintainers = [ "Daaboulex" ];
  };
}
