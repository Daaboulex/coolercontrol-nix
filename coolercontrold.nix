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
      --set HWDATA_PATH "${hwdata}/share/hwdata" \
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
