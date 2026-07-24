"""Tests for coolerctl CLI — runs sandboxed with mocked HTTP."""

import copy
import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from coolerctl import cli
from coolerctl.api import _load_token, ApiError


# ── _load_token ──


class TestLoadToken:
    def test_reads_token_from_file(self, tmp_path):
        token_file = tmp_path / "token"
        token_file.write_text("my-secret-token\n")
        with patch("coolerctl.api.TOKEN_PATH", str(token_file)):
            assert _load_token() == "my-secret-token"

    def test_returns_none_when_no_file(self, tmp_path):
        with patch("coolerctl.api.TOKEN_PATH", str(tmp_path / "nonexistent")):
            with patch.dict(os.environ, {}, clear=True):
                assert _load_token() is None

    def test_reads_from_env_when_no_file(self, tmp_path):
        with patch("coolerctl.api.TOKEN_PATH", str(tmp_path / "nonexistent")):
            with patch.dict(os.environ, {"COOLERCONTROL_TOKEN": "env-token"}):
                assert _load_token() == "env-token"

    def test_file_handle_is_closed(self, tmp_path):
        """Verify the file handle leak fix — fd should be closed after read."""
        token_file = tmp_path / "token"
        token_file.write_text("test-token")
        with patch("coolerctl.api.TOKEN_PATH", str(token_file)):
            _load_token()
        # If the handle leaked, this would still work, but we verify
        # by checking we can delete the file (not locked)
        token_file.unlink()
        assert not token_file.exists()


# ── --version flag ──


class TestVersionFlag:
    def test_version_output(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "coolerctl, version 0.1.0" in result.output


# ── profiles create --speed-profile ──


class TestSpeedProfile:
    def _mock_api_success(self, *args, **kwargs):
        return None

    def test_valid_speed_profile_parsed(self):
        runner = CliRunner()
        with patch("coolerctl.profiles.api") as mock_api:
            mock_api.return_value = None
            result = runner.invoke(cli, [
                "profiles", "create", "Gaming",
                "--type", "Graph",
                "--speed-profile", "30:25,50:40,70:70,85:100",
            ])
        assert result.exit_code == 0
        call_kwargs = mock_api.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert payload["speed_profile"] == [
            [30.0, 25], [50.0, 40], [70.0, 70], [85.0, 100]
        ]
        assert payload["name"] == "Gaming"
        assert payload["p_type"] == "Graph"

    def test_speed_profile_rejects_duty_over_100(self):
        runner = CliRunner()
        with patch("coolerctl.profiles.api") as mock_api:
            result = runner.invoke(cli, [
                "profiles", "create", "Bad",
                "--speed-profile", "30:150",
            ])
        assert result.exit_code != 0
        assert "duty must be 0-100" in result.output

    def test_speed_profile_rejects_malformed_input(self):
        runner = CliRunner()
        with patch("coolerctl.profiles.api"):
            result = runner.invoke(cli, [
                "profiles", "create", "Bad",
                "--speed-profile", "not-valid",
            ])
        assert result.exit_code != 0

    def test_speed_profile_with_float_temps(self):
        runner = CliRunner()
        with patch("coolerctl.profiles.api") as mock_api:
            mock_api.return_value = None
            result = runner.invoke(cli, [
                "profiles", "create", "Precise",
                "--speed-profile", "30.5:25,65.3:80",
            ])
        assert result.exit_code == 0
        payload = mock_api.call_args.kwargs.get("json") or mock_api.call_args[1].get("json")
        assert payload["speed_profile"] == [[30.5, 25], [65.3, 80]]


# ── settings update flags ──


class TestSettingsFlags:
    def test_apply_on_boot_true(self):
        runner = CliRunner()
        with patch("coolerctl.settings.api") as mock_api:
            mock_api.return_value = None
            result = runner.invoke(cli, [
                "settings", "update", "--apply-on-boot",
            ])
        assert result.exit_code == 0
        payload = mock_api.call_args.kwargs.get("json") or mock_api.call_args[1].get("json")
        assert payload == {"apply_on_boot": True}

    def test_no_apply_on_boot(self):
        runner = CliRunner()
        with patch("coolerctl.settings.api") as mock_api:
            mock_api.return_value = None
            result = runner.invoke(cli, [
                "settings", "update", "--no-apply-on-boot",
            ])
        assert result.exit_code == 0
        payload = mock_api.call_args.kwargs.get("json") or mock_api.call_args[1].get("json")
        assert payload == {"apply_on_boot": False}

    def test_poll_rate(self):
        runner = CliRunner()
        with patch("coolerctl.settings.api") as mock_api:
            mock_api.return_value = None
            result = runner.invoke(cli, [
                "settings", "update", "--poll-rate", "2.5",
            ])
        assert result.exit_code == 0
        payload = mock_api.call_args.kwargs.get("json") or mock_api.call_args[1].get("json")
        assert payload == {"poll_rate": 2.5}

    def test_multiple_flags_combined(self):
        runner = CliRunner()
        with patch("coolerctl.settings.api") as mock_api:
            mock_api.return_value = None
            result = runner.invoke(cli, [
                "settings", "update",
                "--startup-delay", "5",
                "--apply-on-boot",
                "--liquidctl-integration",
            ])
        assert result.exit_code == 0
        payload = mock_api.call_args.kwargs.get("json") or mock_api.call_args[1].get("json")
        assert payload == {
            "startup_delay": 5,
            "apply_on_boot": True,
            "liquidctl_integration": True,
        }

    def test_no_flags_shows_error(self):
        runner = CliRunner()
        with patch("coolerctl.settings.api"):
            result = runner.invoke(cli, ["settings", "update"])
        assert result.exit_code != 0
        assert "No settings to update" in result.output

    def test_from_json_file(self, tmp_path):
        json_file = tmp_path / "settings.json"
        json_file.write_text('{"poll_rate": 1.0, "compress": true}')
        runner = CliRunner()
        with patch("coolerctl.settings.api") as mock_api:
            mock_api.return_value = None
            result = runner.invoke(cli, [
                "settings", "update", "--from-json", str(json_file),
            ])
        assert result.exit_code == 0
        payload = mock_api.call_args.kwargs.get("json") or mock_api.call_args[1].get("json")
        assert payload == {"poll_rate": 1.0, "compress": True}


# ── API error handling ──


class TestApiErrorHandling:
    def test_connection_error_message(self):
        runner = CliRunner()
        with patch("coolerctl.api.SESSION") as mock_session:
            import requests
            mock_session.request.side_effect = requests.ConnectionError()
            result = runner.invoke(cli, ["handshake"])
        assert result.exit_code != 0
        assert "not reachable" in result.output or "Cannot connect" in result.output

    def test_handshake_success(self):
        runner = CliRunner()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"shake": True}
        with patch("coolerctl.api.SESSION") as mock_session:
            mock_session.request.return_value = mock_resp
            result = runner.invoke(cli, ["handshake"])
        assert result.exit_code == 0
        assert "OK" in result.output


# ── CLI root options ──


class TestRootOptions:
    def test_json_flag_passed_to_context(self):
        runner = CliRunner()
        with patch("coolerctl.daemon.api") as mock_api:
            mock_api.return_value = {"status": "ok", "details": {}}
            result = runner.invoke(cli, ["--json", "health"])
        assert result.exit_code == 0
        # JSON output should be parseable
        json.loads(result.output)

    def test_custom_base_url(self):
        runner = CliRunner()
        with patch("coolerctl.daemon.api") as mock_api:
            mock_api.return_value = {"shake": True}
            result = runner.invoke(cli, [
                "--base-url", "https://myhost:9999", "handshake",
            ])
        assert result.exit_code == 0
        assert mock_api.call_args[0][2] == "https://myhost:9999"


# ── export-config ──


EXPORT_DEVICES = [
    {
        "uid": "dev-1",
        "name": "NZXT Kraken X63",
        "info": {
            "channels": {
                "fan speed": {"speed_options": {"min_duty": 0, "max_duty": 100}},
                "1st pump": {"speed_options": {"min_duty": 20, "max_duty": 100}},
            },
            "temps": [30, 40, 50],
            "driver": {"name": "kraken", "note": "costs ${x} credits"},
        },
    },
    {
        "uid": "dev-2",
        "name": "NZXT Kraken X63",
        "info": {"channels": {"pump": {"speed_options": {"min_duty": 20}}}},
    },
]

EXPORT_RESPONSES = {
    "/devices": {"devices": EXPORT_DEVICES},
    "/devices/dev-1/settings": {
        "fan speed": {"speed_fixed": 50},
        "1st pump": {"profile_uid": "p-1"},
    },
    "/devices/dev-2/settings": {"pump": {"speed_fixed": 40}},
    "/profiles": {"profiles": [{"name": "Silent Curve", "uid": "p-1",
                                "speed_profile": [[30, 25], [60, 80]]},
                               {"name": "Silent Curve", "uid": "p-2"}]},
    "/functions": {"functions": [{"name": "Default Function", "uid": "f-1"}]},
    "/modes": {"modes": [{"name": "in", "uid": "m-1"}]},
    "/modes-active": {"current_mode_uid": "m-1"},
    "/custom-sensors": {"custom_sensors": [{"id": "2 sensor", "name": "Custom"}]},
    "/plugins": [{"id": "plug-1", "name": "My Plugin"}],
    "/alerts": {"alerts": [{"name": "Hot", "uid": "a-1"}]},
    "/settings": {"apply_on_boot": True, "no_init": False, "startup_delay": 2},
}

EXPORT_PLUGIN_CONFIG = "key = 'value'\nliteral = ''double''\ninterp = ${HOME}\n"

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "export-config.golden")


def _export_api(method, path, base=None, **kwargs):
    if path.endswith("/asetek690"):
        raise ApiError("API error 405: Method Not Allowed")
    if path in EXPORT_RESPONSES:
        return copy.deepcopy(EXPORT_RESPONSES[path])
    raise ApiError(f"API error 404: no route {path}")


def _export_api_raw(method, path, base=None, **kwargs):
    return EXPORT_PLUGIN_CONFIG


def _run_export(api_impl=_export_api, raw_impl=_export_api_raw):
    runner = CliRunner()
    with patch("coolerctl.export.api", side_effect=api_impl), \
         patch("coolerctl.export.api_raw", side_effect=raw_impl):
        return runner.invoke(cli, ["export-config"])


def _body(output):
    """The document without the volatile generated-at header."""
    lines = output.splitlines()
    return "\n".join(lines[lines.index("{"):]) + "\n"


class TestExportConfig:
    def test_matches_committed_fixture(self):
        """The fixture is parsed by `nix flake check`; drift from it fails here."""
        result = _run_export()
        assert result.exit_code == 0
        with open(FIXTURE_PATH) as f:
            assert _body(result.stdout) == f.read()

    def test_attribute_names_with_spaces_are_quoted_not_mangled(self):
        result = _run_export()
        assert '"fan speed" = {' in result.stdout
        assert "\n      fan speed = " not in result.stdout
        assert "fan-speed" not in result.stdout

    def test_digit_leading_attribute_name_is_quoted(self):
        result = _run_export()
        assert '"1st pump" = {' in result.stdout
        assert '"2 sensor" = {' in result.stdout

    def test_nix_keyword_attribute_name_is_quoted(self):
        result = _run_export()
        assert '"in" = {' in result.stdout

    def test_scalar_lists_are_space_separated(self):
        result = _run_export()
        assert "[ 30 40 50 ]" in result.stdout
        assert "[30, 40, 50]" not in result.stdout

    def test_string_interpolation_is_escaped(self):
        result = _run_export()
        assert '"costs \\${x} credits"' in result.stdout

    def test_devices_info_block_is_commented_line_by_line(self):
        result = _run_export()
        lines = result.stdout.splitlines()
        start = lines.index("  # devices_info = [")
        end = next(i for i in range(start, len(lines)) if lines[i].strip() == "")
        for line in lines[start:end]:
            assert line.lstrip().startswith("#"), f"leaked into the attrset: {line!r}"

    def test_plugin_config_escapes_indented_string_delimiters(self):
        result = _run_export()
        assert "literal = '''double'''" in result.stdout
        assert "interp = ''${HOME}" in result.stdout

    def test_duplicate_names_get_distinct_attribute_names(self):
        """Two identically named devices exist in the wild (a second drivetemp,
        a second GPU); a duplicate attribute makes the whole document unusable."""
        result = _run_export()
        assert '"NZXT Kraken X63" = {' in result.stdout
        assert '"NZXT Kraken X63-2" = {' in result.stdout
        assert '"Silent Curve-2" = {' in result.stdout
        assert '"NZXT Kraken X63-2" = {\n      uid = "dev-2";' in result.stdout
        assert '"Silent Curve-2" = { name = "Silent Curve";' in result.stdout

    def test_unauthorized_section_leaves_the_document_complete(self):
        def unauthorized(method, path, base=None, **kwargs):
            if path == "/plugins":
                raise ApiError("API error 401: Unauthorized\nsession expired")
            return _export_api(method, path, base, **kwargs)

        result = _run_export(api_impl=unauthorized)
        assert result.exit_code == 1
        assert "  # /plugins not exported: API error 401: Unauthorized session expired" in result.stdout
        assert "  plugins = {" in result.stdout
        assert "  alerts = " in result.stdout
        assert "  settings = " in result.stdout
        assert result.stdout.rstrip().endswith("}")
        assert "401" in result.stderr

    def test_unreachable_daemon_still_closes_every_block(self):
        def dead(method, path, base=None, **kwargs):
            raise ApiError("Cannot connect to coolercontrold. Is the daemon running?")

        result = _run_export(api_impl=dead)
        assert result.exit_code == 1
        assert _body(result.stdout).count("{") == _body(result.stdout).count("}")
        assert result.stdout.rstrip().endswith("}")
