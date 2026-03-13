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
  coolercontrol-ui-data,
  version,
  src,
}:

rustPlatform.buildRustPackage {
  pname = "coolercontrold";
  inherit version src;
  sourceRoot = "${src.name}/coolercontrold";

  cargoHash = "sha256-i6QYJ2kVXpYVbGyY/5EeGbCVCkxLeqf1mgvrXKRdup0=";

  buildInputs = [ libdrm ];

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

    # Patch the vendored pciid-parser crate to use the Nix store hwdata path.
    # The crate has a @hwdata@ placeholder designed for build-time substitution
    # but nobody substitutes it — so pci.ids lookup fails on NixOS.
    # $cargoDepsCopy is set by cargoSetupPostUnpackHook during the unpack phase.
    substituteInPlace "$cargoDepsCopy/pciid-parser-0.8.0/src/lib.rs" \
      --replace-fail '@hwdata@' '${hwdata}'
  '';

  postInstall = ''
    install -Dm444 "${src}/packaging/systemd/coolercontrold.service" -t "$out/lib/systemd/system"
    substituteInPlace "$out/lib/systemd/system/coolercontrold.service" \
      --replace-fail '/usr/bin' "$out/bin"
  '';

  postFixup = ''
    addDriverRunpath "$out/bin/coolercontrold"

    buildPythonPath "''${pythonPath[*]}"
    wrapProgram "$out/bin/coolercontrold" \
      --prefix PATH : ${lib.makeBinPath [ kmod ]}:$program_PATH \
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
