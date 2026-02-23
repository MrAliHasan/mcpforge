



class TestConfigCommand:
    def test_claude_config_path_detection(self):
        """Verify config path detection returns a string."""
        from mcp_maker.cli import _get_claude_config_path
        path = _get_claude_config_path()
        # On macOS/Linux/Windows, should return a path
        assert path is not None
        assert "claude_desktop_config.json" in path
