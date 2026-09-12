import os
from pathlib import Path

WORKSPACE = Path("d:/Smart ETA")

try:
    from dulwich.repo import Repo
    from dulwich import porcelain
    
    print("Using Dulwich (Git pure-python engine)...")
    
    # Check if repo already exists
    git_dir = WORKSPACE / ".git"
    if not git_dir.exists():
        repo = Repo.init(str(WORKSPACE))
        print(f"Initialized empty Git repository in {WORKSPACE}/.git/")
    else:
        repo = Repo(str(WORKSPACE))
        print(f"Using existing Git repository in {WORKSPACE}/.git/")
        
    # Configure user name/email if not present
    config = repo.get_config()
    try:
        config.get((b"user",), b"name")
    except KeyError:
        config.set((b"user",), b"name", b"SREE")
        config.set((b"user",), b"email", b"sree@example.com")
        config.write_to_path()
        print("Configured default git user (SREE <sree@example.com>).")
        
    # Stage all files respecting .gitignore
    # porcelain.add will respect .gitignore in Dulwich
    print("Staging files...")
    rel_paths = []
    for root, dirs, files in os.walk(WORKSPACE):
        # Skip .git directory
        if ".git" in dirs:
            dirs.remove(".git")
        for file in files:
            full_path = Path(root) / file
            rel_path = full_path.relative_to(WORKSPACE).as_posix()
            rel_paths.append(rel_path)
            
    # Add files
    porcelain.add(repo, rel_paths)
    
    # Commit
    commit_msg = b"Initial Smart ETA prototype"
    commit_id = porcelain.commit(repo, message=commit_msg)
    print(f"\n[master (root-commit) {commit_id.decode()[:7]}] Initial Smart ETA prototype")
    
    # Status
    status = porcelain.status(repo)
    print("\nGit Status after commit:")
    print("  Staged:", status.staged)
    print("  Untracked:", status.untracked)
    
    # Log
    print("\nGit Log:")
    for entry in porcelain.log(repo, max_entries=1):
        print(f"  Commit: {entry.commit.id.decode()}")
        print(f"  Author: {entry.commit.author.decode()}")
        print(f"  Message: {entry.commit.message.decode().strip()}")
        
except ImportError:
    print("Dulwich is not yet installed.")
