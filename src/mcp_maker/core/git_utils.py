import subprocess
from rich.console import Console

console = Console()

def is_git_repo(directory: str) -> bool:
    """Check if the given directory is within a Git repository."""
    try:
        subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=directory,
            capture_output=True,
            check=True
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def commit_schema_changes(output_dir: str, files_to_commit: list[str], diff: dict | None = None) -> None:
    """Stage and commit specific files with an auto-generated message."""
    if not is_git_repo(output_dir):
        console.print("  [dim]⚠️  --auto-commit ignored: Not inside a git repository.[/dim]")
        return

    try:
        # Add files
        subprocess.run(
            ["git", "add"] + files_to_commit,
            cwd=output_dir,
            check=True,
            capture_output=True
        )

        # Generate commit message
        msg = "chore: mcp-maker generated schema sync"
        if diff:
            added = len(diff.get("added", []))
            removed = len(diff.get("removed", []))
            changed = len(diff.get("column_changes", {}))
            
            details = []
            if added:
                details.append(f"+{added} tab")
            if removed:
                details.append(f"-{removed} tab")
            if changed:
                details.append(f"~{changed} alt")
            
            if details:
                msg += f"\n\nChanges: {', '.join(details)}."

        # Execute commit
        res = subprocess.run(
            ["git", "commit", "-m", msg],
            cwd=output_dir,
            capture_output=True
        )
        
        output_str = res.stdout.decode().lower()
        if res.returncode == 0:
            console.print("  [green]✅ Auto-committed schema changes to Git.[/green]")
        elif "nothing to commit" in output_str:
            console.print("  [dim]• Git: No file changes to commit.[/dim]")
        else:
            console.print(f"  [dim]⚠️  Auto-commit failed: {res.stdout.decode().strip()}[/dim]")
            
    except Exception as e:
        console.print(f"  [dim]⚠️  Auto-commit process failed: {e}[/dim]")
