{
  buildNpmPackage,
  lib,
  version,
  src,
}:

buildNpmPackage {
  pname = "coolercontrol-ui";
  inherit version src;
  sourceRoot = "${src.name}/coolercontrol-ui";

  npmDepsFetcherVersion = 2;
  npmDepsHash = "sha256-AzRw6DuloOFC7VN7yM9czqxosfVIoXAltv2xHUxac7k=";

  postBuild = ''
    cp -r dist $out
  '';

  dontInstall = true;

  meta = {
    description = "CoolerControl web UI data";
    homepage = "https://gitlab.com/coolercontrol/coolercontrol";
    license = lib.licenses.gpl3Plus;
    platforms = [
      "x86_64-linux"
      "aarch64-linux"
    ];
    maintainers = [ "Daaboulex" ];
  };
}
