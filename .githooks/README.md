# Git Hooks for Chrome Tab Reader

> **Note:** This document is AI-authored with very limited human oversight.

This directory contains custom Git hooks to maintain code quality and consistency.

## Available Hooks

### pre-commit

Ensures PowerShell files (`.ps1`, `.psm1`, `.psd1`) have Windows (CRLF) line endings before committing.

**Why this is important:**
- PowerShell on Windows requires CRLF line endings to parse scripts correctly
- Unix (LF) line endings cause cryptic parser errors in PowerShell
- This hook prevents accidentally committing .ps1 files with incorrect line endings

**What it checks:**
- All staged `.ps1` files for CRLF line endings
- Aborts commit if any PowerShell file has Unix (LF) line endings
- Provides fix instructions if issues are found

## Installation

To enable these hooks for your local repository, run:

```bash
git config core.hooksPath .githooks
```

This tells Git to use hooks from the `.githooks` directory instead of the default `.git/hooks`.

**Verify installation:**
```bash
git config --get core.hooksPath
# Should output: .githooks
```

## Uninstallation

To disable custom hooks and revert to default behavior:

```bash
git config --unset core.hooksPath
```

## Line Ending Configuration

The repository uses `.gitattributes` to automatically enforce line endings:

- **PowerShell files** (`.ps1`, `.psm1`, `.psd1`): Always use **CRLF** (Windows)
- **Shell scripts** (`.sh`, `.bash`): Always use **LF** (Unix)
- **Most other text files**: Use **LF** (Unix)
- **Python, JavaScript, JSON, YAML, etc.**: Use **LF** (Unix)

Git will automatically convert line endings when checking out files based on these rules.

## Fixing Line Endings

If the pre-commit hook reports incorrect line endings, fix them with:

### Option 1: Using sed (Linux/macOS/Git Bash)
```bash
sed -i 's/$/\r/' file.ps1
```

### Option 2: Using dos2unix tools
```bash
# Install dos2unix if needed
# Ubuntu/Debian: sudo apt-get install dos2unix
# macOS: brew install dos2unix

unix2dos file.ps1
```

### Option 3: Let Git fix it automatically
```bash
# Remove file from index
git rm --cached file.ps1

# Re-add file (Git will apply .gitattributes rules)
git add file.ps1
```

After fixing, stage the files again:
```bash
git add file.ps1
git commit
```

## Testing the Hook

To test the pre-commit hook without making a commit:

```bash
# Stage a PowerShell file
git add run_tests.ps1

# Run the hook manually
.githooks/pre-commit

# Should output:
# ✓ run_tests.ps1 has correct line endings (CRLF)
# ✓ All PowerShell files have correct line endings
```

## Bypassing Hooks (Not Recommended)

If you absolutely need to bypass the pre-commit hook (not recommended):

```bash
git commit --no-verify
```

**Warning:** Bypassing hooks may introduce line ending issues that break PowerShell scripts on Windows.

## Troubleshooting

### Hook not running

1. Check if hooks path is configured:
   ```bash
   git config --get core.hooksPath
   ```

2. Ensure hook is executable:
   ```bash
   chmod +x .githooks/pre-commit
   ```

3. Test hook manually:
   ```bash
   .githooks/pre-commit
   ```

### File command not found

The pre-commit hook uses the `file` command to detect line endings. If not available:

- **Ubuntu/Debian**: `sudo apt-get install file`
- **macOS**: Already installed
- **Windows Git Bash**: Already installed

### Hook fails on Windows

If running the hook fails on Windows, ensure you're using Git Bash or WSL, not PowerShell or CMD.

---

**Last Updated:** 2025-11-18
**Maintainer:** Russell Pierce (with AI assistance)
