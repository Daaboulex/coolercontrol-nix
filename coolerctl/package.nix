# coolerctl — CLI for CoolerControl daemon REST API.
# Wraps coolercontrold's HTTP API for scripting, automation,
# StreamController integration, and LLM-driven fan curve tuning.
{
  lib,
  python3Packages,
}:
python3Packages.buildPythonApplication {
  pname = "coolerctl";
  version = "0.1.0";
  format = "setuptools";

  src = ./.;

  propagatedBuildInputs = with python3Packages; [
    click
    requests
  ];

  nativeCheckInputs = with python3Packages; [
    pytest
  ];

  checkPhase = ''
    runHook preCheck
    pytest test_coolerctl.py -v
    runHook postCheck
  '';

  meta = {
    homepage = "https://gitlab.com/coolercontrol/coolercontrol";
    description = "CoolerControl daemon CLI — fan curves, profiles, modes, alerts, and device control";
    license = lib.licenses.gpl3Plus;
    platforms = lib.platforms.linux;
    mainProgram = "coolerctl";
  };
}
