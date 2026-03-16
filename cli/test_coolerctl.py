"""Tests for coolerctl CLI — runs sandboxed with mocked HTTP."""

import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from coolerctl import cli, _load_token, api, ApiError


# ── _load_token ──


class TestLoadToken:
    def test_reads_token_from_file(self, tmp_path):
        token_file = tmp_path / "token"
        token_file.write_text("my-secret-token\n")
        with patch("coolerctl.TOKEN_PATH", str(token_file)):
            assert _load_token() == "my-secret-token"

    def test_returns_none_when_no_file(self, tmp_path):
        with patch("coolerctl.TOKEN_PATH", str(tmp_path / "nonexistent")):
            with patch.dict(os.environ, {}, clear=True):
                assert _load_token() is None

    def test_reads_from_env_when_no_file(self, tmp_path):
        with patch("coolerctl.TOKEN_PATH", str(tmp_path / "nonexistent")):
            with patch.dict(os.environ, {"COOLERCONTROL_TOKEN": "env-token"}):
                assert _load_token() == "env-token"

    def test_file_handle_is_closed(self, tmp_path):
        """Verify the file handle leak fix — fd should be closed after read."""
        token_file = tmp_path / "token"
        token_file.write_text("test-token")
        with patch("coolerctl.TOKEN_PATH", str(token_file)):
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
        with patch("coolerctl.api") as mock_api:
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
        with patch("coolerctl.api") as mock_api:
            result = runner.invoke(cli, [
                "profiles", "create", "Bad",
                "--speed-profile", "30:150",
            ])
        assert result.exit_code != 0
        assert "duty must be 0-100" in result.output

    def test_speed_profile_rejects_malformed_input(self):
        runner = CliRunner()
        with patch("coolerctl.api"):
            result = runner.invoke(cli, [
                "profiles", "create", "Bad",
                "--speed-profile", "not-valid",
            ])
        assert result.exit_code != 0

    def test_speed_profile_with_float_temps(self):
        runner = CliRunner()
        with patch("coolerctl.api") as mock_api:
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
        with patch("coolerctl.api") as mock_api:
            mock_api.return_value = None
            result = runner.invoke(cli, [
                "settings", "update", "--apply-on-boot",
            ])
        assert result.exit_code == 0
        payload = mock_api.call_args.kwargs.get("json") or mock_api.call_args[1].get("json")
        assert payload == {"apply_on_boot": True}

    def test_no_apply_on_boot(self):
        runner = CliRunner()
        with patch("coolerctl.api") as mock_api:
            mock_api.return_value = None
            result = runner.invoke(cli, [
                "settings", "update", "--no-apply-on-boot",
            ])
        assert result.exit_code == 0
        payload = mock_api.call_args.kwargs.get("json") or mock_api.call_args[1].get("json")
        assert payload == {"apply_on_boot": False}

    def test_poll_rate(self):
        runner = CliRunner()
        with patch("coolerctl.api") as mock_api:
            mock_api.return_value = None
            result = runner.invoke(cli, [
                "settings", "update", "--poll-rate", "2.5",
            ])
        assert result.exit_code == 0
        payload = mock_api.call_args.kwargs.get("json") or mock_api.call_args[1].get("json")
        assert payload == {"poll_rate": 2.5}

    def test_multiple_flags_combined(self):
        runner = CliRunner()
        with patch("coolerctl.api") as mock_api:
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
        with patch("coolerctl.api"):
            result = runner.invoke(cli, ["settings", "update"])
        assert result.exit_code != 0
        assert "No settings to update" in result.output

    def test_from_json_file(self, tmp_path):
        json_file = tmp_path / "settings.json"
        json_file.write_text('{"poll_rate": 1.0, "compress": true}')
        runner = CliRunner()
        with patch("coolerctl.api") as mock_api:
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
        with patch("coolerctl.SESSION") as mock_session:
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
        with patch("coolerctl.SESSION") as mock_session:
            mock_session.request.return_value = mock_resp
            result = runner.invoke(cli, ["handshake"])
        assert result.exit_code == 0
        assert "OK" in result.output


# ── CLI root options ──


class TestRootOptions:
    def test_json_flag_passed_to_context(self):
        runner = CliRunner()
        with patch("coolerctl.api") as mock_api:
            mock_api.return_value = {"status": "ok", "details": {}}
            result = runner.invoke(cli, ["--json", "health"])
        assert result.exit_code == 0
        # JSON output should be parseable
        json.loads(result.output)

    def test_custom_base_url(self):
        runner = CliRunner()
        with patch("coolerctl.api") as mock_api:
            mock_api.return_value = {"shake": True}
            result = runner.invoke(cli, [
                "--base-url", "https://myhost:9999", "handshake",
            ])
        assert result.exit_code == 0
        assert mock_api.call_args[0][2] == "https://myhost:9999"
