"""Tests for the deploy CLI command."""

import os
import tempfile

from typer.testing import CliRunner

from mcp_maker.cli import app
from mcp_maker.cli.deploy import (
    _detect_requirements,
    _generate_dockerfile,
    _generate_dockerignore,
    _generate_railway_config,
    _generate_render_config,
    _generate_fly_config,
    _write_file,
)


runner = CliRunner()


class TestDeployHelpers:
    def test_detect_requirements_basic(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("import sqlite3\nfrom fastmcp import FastMCP\n")
            path = f.name
        try:
            reqs = _detect_requirements(path)
            assert "mcp>=1.0.0" in reqs
            # sqlite3 is built-in, should NOT appear
            assert not any("sqlite" in r for r in reqs)
        finally:
            os.unlink(path)

    def test_detect_requirements_postgres(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("import psycopg2\nimport httpx\n")
            path = f.name
        try:
            reqs = _detect_requirements(path)
            assert any("psycopg2" in r for r in reqs)
            assert any("httpx" in r for r in reqs)
        finally:
            os.unlink(path)

    def test_detect_requirements_mongo(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("import pymongo\n")
            path = f.name
        try:
            reqs = _detect_requirements(path)
            assert any("pymongo" in r for r in reqs)
        finally:
            os.unlink(path)

    def test_detect_requirements_async(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("import aiosqlite\nimport asyncpg\nimport aiomysql\n")
            path = f.name
        try:
            reqs = _detect_requirements(path)
            assert any("aiosqlite" in r for r in reqs)
            assert any("asyncpg" in r for r in reqs)
            assert any("aiomysql" in r for r in reqs)
        finally:
            os.unlink(path)

    def test_detect_requirements_supabase(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("from supabase import create_client\n")
            path = f.name
        try:
            reqs = _detect_requirements(path)
            assert any("supabase" in r for r in reqs)
        finally:
            os.unlink(path)

    def test_detect_requirements_with_autogen(self):
        """When _autogen_mcp_server.py exists beside the server file, its imports should also be detected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            server_path = os.path.join(tmpdir, "mcp_server.py")
            autogen_path = os.path.join(tmpdir, "_autogen_mcp_server.py")
            with open(server_path, "w") as f:
                f.write("import sqlite3\n")
            with open(autogen_path, "w") as f:
                f.write("import pymysql\n")
            reqs = _detect_requirements(server_path)
            assert any("pymysql" in r for r in reqs)

    def test_generate_dockerfile(self):
        dockerfile = _generate_dockerfile("mcp_server.py", 8000)
        assert "FROM python:3.12-slim" in dockerfile
        assert "COPY mcp_server.py" in dockerfile
        assert "EXPOSE 8000" in dockerfile

    def test_generate_dockerignore(self):
        content = _generate_dockerignore()
        assert "__pycache__" in content
        assert ".venv" in content

    def test_generate_railway_config(self):
        config = _generate_railway_config(8000)
        assert config["build"]["builder"] == "DOCKERFILE"
        assert "$schema" in config

    def test_generate_render_config(self):
        content = _generate_render_config("mcp_server.py", 8080)
        assert "mcp-server" in content
        assert "8080" in content

    def test_generate_fly_config(self):
        content = _generate_fly_config("mcp_server.py", 9000)
        assert "internal_port = 9000" in content
        assert "auto_stop_machines" in content

    def test_write_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.txt")
            _write_file(path, "hello")
            assert os.path.isfile(path)
            with open(path) as f:
                assert f.read() == "hello"


class TestDeployCommand:
    def test_deploy_missing_server(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(app, ["deploy", "--file", os.path.join(tmpdir, "missing.py")])
            assert result.exit_code == 1

    def test_deploy_unsupported_platform(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            server = os.path.join(tmpdir, "mcp_server.py")
            with open(server, "w") as f:
                f.write("import sqlite3\n")
            result = runner.invoke(app, ["deploy", "--platform", "heroku", "--file", server])
            assert result.exit_code == 1

    def test_deploy_railway(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            server = os.path.join(tmpdir, "mcp_server.py")
            with open(server, "w") as f:
                f.write("import sqlite3\n")
            old_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["deploy", "--platform", "railway", "--file", server])
                assert result.exit_code == 0
                assert os.path.isfile(os.path.join(tmpdir, "Dockerfile"))
                assert os.path.isfile(os.path.join(tmpdir, "requirements.txt"))
                assert os.path.isfile(os.path.join(tmpdir, "railway.json"))
            finally:
                os.chdir(old_cwd)

    def test_deploy_render(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            server = os.path.join(tmpdir, "mcp_server.py")
            with open(server, "w") as f:
                f.write("import sqlite3\n")
            old_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["deploy", "--platform", "render", "--file", server])
                assert result.exit_code == 0
                assert os.path.isfile(os.path.join(tmpdir, "render.yaml"))
            finally:
                os.chdir(old_cwd)

    def test_deploy_fly(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            server = os.path.join(tmpdir, "mcp_server.py")
            with open(server, "w") as f:
                f.write("import sqlite3\n")
            old_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["deploy", "--platform", "fly", "--file", server])
                assert result.exit_code == 0
                assert os.path.isfile(os.path.join(tmpdir, "fly.toml"))
            finally:
                os.chdir(old_cwd)
