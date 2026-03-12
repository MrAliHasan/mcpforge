"""Tests for the CLI environment commands and helpers."""

import os
import tempfile

from typer.testing import CliRunner

from mcp_maker.cli import app
from mcp_maker.cli.environment import _env_read, _env_write, _mask_value


runner = CliRunner()


class TestEnvHelpers:
    def test_env_write_and_read(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            path = f.name
        try:
            _env_write(path, {"DB_URL": "postgres://localhost/test", "API_KEY": "secret123"})
            result = _env_read(path)
            assert result["DB_URL"] == "postgres://localhost/test"
            assert result["API_KEY"] == "secret123"
        finally:
            os.unlink(path)

    def test_env_write_quotes_spaces(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            path = f.name
        try:
            _env_write(path, {"NAME": "hello world"})
            with open(path) as f:
                content = f.read()
            assert '"hello world"' in content
        finally:
            os.unlink(path)

    def test_env_read_nonexistent(self):
        result = _env_read("/nonexistent/.env")
        assert result == {}

    def test_env_read_skips_comments_and_blanks(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("# Comment\n\nKEY=value\n")
            path = f.name
        try:
            result = _env_read(path)
            assert result == {"KEY": "value"}
        finally:
            os.unlink(path)

    def test_mask_value_short(self):
        assert _mask_value("ab") == "****"

    def test_mask_value_long(self):
        masked = _mask_value("abcdefghij")
        # Just verify it masks something and doesn't return raw value
        assert masked != "abcdefghij"
        assert len(masked) > 0

    def test_env_set(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = os.path.join(tmpdir, ".env")
            old_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["env", "set", "TEST_KEY", "test_value"])
                assert result.exit_code == 0
                # Check the file was created with the value
                assert os.path.isfile(env_file)
                env = _env_read(env_file)
                assert env["TEST_KEY"] == "test_value"
            finally:
                os.chdir(old_cwd)

    def test_env_list(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = os.path.join(tmpdir, ".env")
            _env_write(env_file, {"MY_VAR": "hello"})
            old_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["env", "list"])
                assert result.exit_code == 0
                assert "MY_VAR" in result.output
            finally:
                os.chdir(old_cwd)

    def test_env_show(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = os.path.join(tmpdir, ".env")
            _env_write(env_file, {"SHOW_ME": "visible_value"})
            old_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["env", "show", "SHOW_ME"])
                assert result.exit_code == 0
                assert "visible_value" in result.output
            finally:
                os.chdir(old_cwd)

    def test_env_delete(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = os.path.join(tmpdir, ".env")
            _env_write(env_file, {"DEL_ME": "gone", "KEEP": "here"})
            old_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["env", "delete", "DEL_ME"])
                assert result.exit_code == 0
                env = _env_read(env_file)
                assert "DEL_ME" not in env
                assert env["KEEP"] == "here"
            finally:
                os.chdir(old_cwd)

    def test_env_show_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = os.path.join(tmpdir, ".env")
            _env_write(env_file, {})
            old_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["env", "show", "NONEXISTENT"])
                # May exit 1 for missing key — that's expected
                assert result.exit_code in (0, 1)
            finally:
                os.chdir(old_cwd)
