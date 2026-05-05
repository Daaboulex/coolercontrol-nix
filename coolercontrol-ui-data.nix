{
  buildNpmPackage,
  lib,
  version,
  src,
  npmDepsHash,
}:

buildNpmPackage {
  pname = "coolercontrol-ui";
  inherit version src;
  sourceRoot = "${src.name}/coolercontrol-ui";

  npmDepsFetcherVersion = 2;
  inherit npmDepsHash;

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
