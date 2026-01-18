# Publishing to PyPI

This guide explains how to publish the `python-raft-kv` package to PyPI using GitHub Actions.

## Prerequisites

1. **PyPI Account**: Create an account at https://pypi.org/account/register/
2. **API Token**: Generate an API token at https://pypi.org/manage/account/token/
   - Go to Account Settings → API tokens
   - Create a new token with "Entire account" scope
   - Copy the token (starts with `pypi-`)

## Setup

### 1. Add PyPI API Token to GitHub Secrets

1. Go to your GitHub repository
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Name: `PYPI_API_TOKEN`
5. Value: Paste your PyPI API token
6. Click **Add secret**

### 2. Update Version in setup.py

Before publishing, update the version in `setup.py`:

```python
version="0.1.0",  # Update this
```

Also update in `pyproject.toml`:

```toml
version = "0.1.0"  # Update this
```

### 3. Publish Methods

#### Method 1: Create a GitHub Release (Recommended)

1. Update version in `setup.py` and `pyproject.toml`
2. Commit and push changes:
   ```bash
   git add setup.py pyproject.toml
   git commit -m "Bump version to 0.1.0"
   git push
   ```
3. Create a new release on GitHub:
   - Go to **Releases** → **Create a new release**
   - Tag: `v0.1.0` (must match version)
   - Title: `v0.1.0`
   - Publish release
4. GitHub Actions will automatically build and publish to PyPI

#### Method 2: Manual Workflow Dispatch

1. Go to **Actions** tab in GitHub
2. Select **Publish to PyPI** workflow
3. Click **Run workflow**
4. Enter version number (e.g., `0.1.0`)
5. Click **Run workflow**

## Verification

After publishing, verify on PyPI:
- Check: https://pypi.org/project/python-raft-kv/
- Test installation: `pip install python-raft-kv`

## Notes

- The workflow builds the package using `python -m build`
- It checks the package with `twine check`
- Only publishes when a release is created or workflow is manually triggered
- The Go source files are included in the package via `MANIFEST.in`

