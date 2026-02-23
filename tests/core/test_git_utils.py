import subprocess
from unittest.mock import patch, MagicMock
from mcp_maker.core.git_utils import is_git_repo, commit_schema_changes

def test_is_git_repo_true():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        assert is_git_repo(".")

def test_is_git_repo_false():
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(128, "git")
        assert not is_git_repo(".")

def test_commit_schema_changes_not_git():
    with patch("mcp_maker.core.git_utils.is_git_repo", return_value=False):
        with patch("subprocess.run") as mock_run:
            commit_schema_changes(".", ["file.txt"])
            mock_run.assert_not_called()

def test_commit_schema_changes_success():
    with patch("mcp_maker.core.git_utils.is_git_repo", return_value=True):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=b"success")
            
            diff = {
                "added": ["table1"],
                "removed": ["table2"],
                "column_changes": {"table3": ["col1"]}
            }
            commit_schema_changes(".", ["file.txt"], diff=diff)
            
            assert mock_run.call_count == 2
            # First call is git add
            assert mock_run.call_args_list[0][0][0] == ["git", "add", "file.txt"]
            # Second call is git commit
            commit_args = mock_run.call_args_list[1][0][0]
            assert commit_args[0] == "git"
            assert commit_args[1] == "commit"
            assert "-m" in commit_args
            
            msg = commit_args[commit_args.index("-m") + 1]
            assert "chore: mcp-maker generated schema sync" in msg
            assert "+1 tab" in msg
            assert "-1 tab" in msg
            assert "~1 alt" in msg

def test_commit_schema_changes_nothing_to_commit():
    with patch("mcp_maker.core.git_utils.is_git_repo", return_value=True):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout=b"nothing to commit")
            commit_schema_changes(".", ["file.txt"])
            assert mock_run.call_count == 2
