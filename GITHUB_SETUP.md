# Complete Guide: GitHub Repository to PyPI Publishing

This guide walks you through creating a GitHub repository, setting up GitHub Actions, and publishing your package to PyPI.

## Step 1: Create GitHub Repository

1. **Go to GitHub**: https://github.com
2. **Click the "+" icon** (top right) → **New repository**
3. **Repository settings**:
   - **Repository name**: `python-raft-kv` (or your preferred name)
   - **Description**: "A distributed key-value store in Python using Raft consensus"
   - **Visibility**: Public (required for PyPI if you want it discoverable)
   - **DO NOT** initialize with README, .gitignore, or license (we already have these)
4. **Click "Create repository"**

## Step 2: Prepare Your Local Repository

1. **Initialize git** (if not already done):
   ```bash
   cd python-raft-kv
   git init
   ```

2. **Create/Update .gitignore** (if needed):
   ```bash
   # Make sure .gitignore exists and includes:
   # - __pycache__/
   # - *.pyc
   # - dist/
   # - build/
   # - *.egg-info/
   # - raft-bridge/raft-bridge.exe
   # - raft-bridge/raft-bridge
   ```

3. **Add all files**:
   ```bash
   git add .
   ```

4. **Make initial commit**:
   ```bash
   git commit -m "Initial commit: Python Raft KV Store"
   ```

## Step 3: Connect to GitHub and Push

1. **Add remote** (replace `yourusername` with your GitHub username):
   ```bash
   git remote add origin https://github.com/yourusername/python-raft-kv.git
   ```

2. **Rename branch to main** (if needed):
   ```bash
   git branch -M main
   ```

3. **Push to GitHub**:
   ```bash
   git push -u origin main
   ```

4. **Verify**: Go to your GitHub repository page and confirm all files are there.

## Step 4: Create PyPI Account

1. **Go to PyPI**: https://pypi.org/account/register/
2. **Create account**:
   - Username (will be part of package URL)
   - Email address
   - Password
   - Confirm email
3. **Verify email** (check your inbox)

## Step 5: Generate PyPI API Token

1. **Login to PyPI**: https://pypi.org/account/login/
2. **Go to Account Settings**: Click your username → **Account settings**
3. **API tokens**: Click **API tokens** in the left sidebar
4. **Create token**:
   - Click **Add API token**
   - **Token name**: `github-actions` (or any name)
   - **Scope**: Select **Entire account** (or just the project if you created one)
   - Click **Add token**
5. **Copy the token**: It starts with `pypi-` - **SAVE THIS NOW!** You won't see it again.
   - Example: `pypi-AgEIcHJ5cGkub3Jn...` (long string)

## Step 6: Add Secret to GitHub

1. **Go to your repository** on GitHub
2. **Settings**: Click **Settings** tab (top menu)
3. **Secrets**: Click **Secrets and variables** → **Actions** (left sidebar)
4. **New repository secret**:
   - Click **New repository secret**
   - **Name**: `PYPI_API_TOKEN` (exactly this name)
   - **Secret**: Paste your PyPI token (the `pypi-...` string)
   - Click **Add secret**
5. **Verify**: You should see `PYPI_API_TOKEN` in the secrets list

## Step 7: Update Package Metadata

1. **Update `setup.py`**:
   ```python
   # Change these fields:
   author="Your Name",
   author_email="your.email@example.com",
   url="https://github.com/yourusername/python-raft-kv",
   ```

2. **Update `pyproject.toml`**:
   ```toml
   authors = [
       {name = "Your Name", email = "your.email@example.com"}
   ]
   ```

3. **Update README.md**:
   - Replace `yourusername` with your actual GitHub username
   - Update any placeholder URLs

4. **Commit changes**:
   ```bash
   git add setup.py pyproject.toml README.md
   git commit -m "Update package metadata"
   git push
   ```

## Step 8: Test the Workflow (Optional)

1. **Go to Actions tab** in your GitHub repository
2. **Select "Publish to PyPI"** workflow
3. **Run workflow**:
   - Click **Run workflow** dropdown
   - Enter version: `0.1.0`
   - Click **Run workflow**
4. **Watch it run**: Click on the workflow run to see progress
5. **Check for errors**: If it fails, check the logs

## Step 9: Create Your First Release

1. **Update version** in both files:
   - `setup.py`: `version="0.1.0"`
   - `pyproject.toml`: `version = "0.1.0"`

2. **Commit version bump**:
   ```bash
   git add setup.py pyproject.toml
   git commit -m "Bump version to 0.1.0"
   git push
   ```

3. **Create GitHub Release**:
   - Go to your repository on GitHub
   - Click **Releases** (right sidebar) → **Create a new release**
   - **Tag version**: `v0.1.0` (must start with `v`)
   - **Release title**: `v0.1.0` or `Initial Release`
   - **Description**: 
     ```
     Initial release of python-raft-kv
     
     Features:
     - Distributed key-value store with Raft consensus
     - Python API and HTTP API
     - ~1000 ops/sec throughput
     ```
   - **Publish release**: Click **Publish release**

4. **Watch the magic**: 
   - GitHub Actions will automatically trigger
   - Go to **Actions** tab to watch it build and publish
   - Wait 2-5 minutes for completion

## Step 10: Verify Publication

1. **Check PyPI**: 
   - Go to: https://pypi.org/project/python-raft-kv/
   - Your package should appear!

2. **Test installation**:
   ```bash
   # Create a new virtual environment (recommended)
   python -m venv test_env
   source test_env/bin/activate  # On Windows: test_env\Scripts\activate
   
   # Install from PyPI
   pip install python-raft-kv
   
   # Test import
   python -c "from python_kv import KVStore; print('Success!')"
   ```

3. **Verify command**:
   ```bash
   raft-kv-start --help
   ```

## Step 11: Future Releases

For future versions (e.g., 0.2.0):

1. **Update version** in `setup.py` and `pyproject.toml`
2. **Commit and push**:
   ```bash
   git add setup.py pyproject.toml
   git commit -m "Bump version to 0.2.0"
   git push
   ```
3. **Create new release** with tag `v0.2.0`
4. **Workflow automatically publishes** to PyPI

## Troubleshooting

### "Workflow not found"
- Make sure `.github/workflows/publish.yml` exists in your repository
- Check that you pushed it: `git add .github && git commit -m "Add workflows" && git push`

### "Secret not found"
- Verify secret name is exactly `PYPI_API_TOKEN` (case-sensitive)
- Check it's in Settings → Secrets and variables → Actions

### "Authentication failed"
- Verify your PyPI token is correct
- Check token hasn't expired (they don't expire, but verify it's active)
- Make sure token has correct scope

### "Package already exists"
- PyPI doesn't allow overwriting versions
- Use a new version number (e.g., 0.1.1 instead of 0.1.0)

### "Invalid package name"
- Package name must be lowercase
- Can contain hyphens but not underscores
- Check `setup.py` and `pyproject.toml` have same name

## Checklist

Before publishing, make sure:

- [ ] GitHub repository created and code pushed
- [ ] PyPI account created and verified
- [ ] PyPI API token generated and saved
- [ ] `PYPI_API_TOKEN` secret added to GitHub
- [ ] Package metadata updated (author, email, URL)
- [ ] Version set in both `setup.py` and `pyproject.toml`
- [ ] README.md updated with correct GitHub username
- [ ] `.github/workflows/publish.yml` exists
- [ ] All changes committed and pushed
- [ ] GitHub release created with correct tag

## Next Steps

After successful publication:

1. **Add badges** to README (optional):
   ```markdown
   ![PyPI version](https://img.shields.io/pypi/v/python-raft-kv)
   ![PyPI downloads](https://img.shields.io/pypi/dm/python-raft-kv)
   ```

2. **Share your package**: 
   - Update README with PyPI installation instructions
   - Share on social media, Reddit, etc.

3. **Monitor**: 
   - Check PyPI stats: https://pypi.org/project/python-raft-kv/#statistics
   - Monitor GitHub Issues for user feedback

