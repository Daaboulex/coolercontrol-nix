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
  npmDepsHash = "sha256-NmTNaHm7NGkNWnNbTfLC9/3cSJRR+ir1YS+ot4MJNog=";

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
