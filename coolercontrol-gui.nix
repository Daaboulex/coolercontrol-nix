{
  cmake,
  stdenv,
  lib,
  qt6,
  version,
  src,
}:

stdenv.mkDerivation {
  pname = "coolercontrol";
  inherit version src;
  sourceRoot = "${src.name}/coolercontrol";

  nativeBuildInputs = [
    cmake
    qt6.wrapQtAppsHook
  ];

  buildInputs = [
    qt6.qtbase
    qt6.qtwebengine
  ];

  postInstall = ''
    install -Dm644 "${src}/packaging/metadata/org.coolercontrol.CoolerControl.desktop" -t "$out/share/applications/"
    install -Dm644 "${src}/packaging/metadata/org.coolercontrol.CoolerControl.metainfo.xml" -t "$out/share/metainfo/"
    install -Dm644 "${src}/packaging/metadata/org.coolercontrol.CoolerControl.png" -t "$out/share/icons/hicolor/256x256/apps/"
    install -Dm644 "${src}/packaging/metadata/org.coolercontrol.CoolerControl-alert.png" -t "$out/share/icons/hicolor/256x256/apps/"
    install -Dm644 "${src}/packaging/metadata/org.coolercontrol.CoolerControl.svg" -t "$out/share/icons/hicolor/scalable/apps/"
    install -Dm644 "${src}/packaging/metadata/org.coolercontrol.CoolerControl-alert.svg" -t "$out/share/icons/hicolor/scalable/apps/"
    install -Dm644 "${src}/packaging/metadata/org.coolercontrol.CoolerControl-symbolic.svg" -t "$out/share/icons/hicolor/symbolic/apps/"
    install -Dm644 "${src}/packaging/metadata/org.coolercontrol.CoolerControl-symbolic-alert.svg" -t "$out/share/icons/hicolor/symbolic/apps/"
  '';

  meta = {
    description = "CoolerControl GUI — monitor and control your cooling devices";
    homepage = "https://gitlab.com/coolercontrol/coolercontrol";
    license = lib.licenses.gpl3Plus;
    platforms = [
      "x86_64-linux"
      "aarch64-linux"
    ];
    mainProgram = "coolercontrol";
    maintainers = [ "Daaboulex" ];
  };
}
