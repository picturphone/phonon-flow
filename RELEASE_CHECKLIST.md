# Open-Source Release Checklist for PhononFlow

This document outlines the complete process for releasing PhononFlow as an open-source project on GitHub and PyPI.

## Prerequisites

Before going public:

- [ ] **Sanitize credentials**: Remove ALL passwords, API keys, SSH key paths from code and config examples
- [ ] **Check license compatibility**: VASP is proprietary, phonopy is BSD. PhononFlow itself is MIT — this is fine as we don't distribute VASP binaries
- [ ] **Review code for sensitive paths**: No hardcoded IP addresses, usernames, or internal server names in source code (examples can have placeholders)

## Step 1: Create GitHub Repository

```bash
# Initialize git
cd phonon-flow
git init
git add .
git commit -m "Initial commit: PhononFlow v0.1.0"

# Create repo on GitHub (via gh CLI or web UI)
gh repo create phonon-flow/phonon-flow --public --description \
  "Remote-first first-principles phonon calculation workflow engine"

# Push
git remote add origin https://github.com/phonon-flow/phonon-flow.git
git push -u origin main
```

## Step 2: Repository Settings

On GitHub → Settings:

- **Branches**: Protect `main` branch (require PR reviews for merges)
- **Issues**: Enable issues with labels:
  - `bug`, `enhancement`, `documentation`, `good first issue`, `help wanted`
  - `backend/pi`, `backend/hpc`, `phonon/bands`, `phonon/raman`
- **Actions**: Enable GitHub Actions for CI
- **Pages**: Optional — deploy docs via GitHub Pages

## Step 3: CI/CD Setup

Create `.github/workflows/ci.yml`:

```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.10', '3.11', '3.12']
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - name: Install
        run: |
          pip install -e ".[dev]"
          pip install phonopy  # phonopy is needed for some tests
      - name: Lint
        run: |
          ruff check phonon_flow/
      - name: Test
        run: |
          pytest phonon_flow/tests/ -v --cov=phonon_flow --cov-report=term
```

## Step 4: PyPI Release

```bash
# Install build tools
pip install build twine

# Build
python -m build

# Check package
twine check dist/*

# Upload to Test PyPI first
twine upload --repository testpypi dist/*

# Test install from Test PyPI
pip install --index-url https://test.pypi.org/simple/ phonon-flow

# Upload to real PyPI
twine upload dist/*
```

## Step 5: Documentation

Deploy docs to ReadTheDocs or GitHub Pages:

```bash
pip install mkdocs mkdocs-material mkdocstrings[python]
mkdocs new docs
# Configure mkdocs.yml, then:
mkdocs build
mkdocs gh-deploy
```

## Step 6: Community Building

- Add `README.md` badges:
  - PyPI version, Python versions, License, CI status
- Create `CHANGELOG.md` for version tracking
- Set up Discussions tab on GitHub for Q&A
- Announce on relevant communities:
  - VASP mailing list
  - phonopy Google Group
  - Materials Science Stack Exchange
  - Twitter/X with #compchem #DFT #phonon

## Step 7: Long-term Maintenance

- Tag releases with semantic versioning: `git tag v0.1.0 && git push --tags`
- Use GitHub Milestones for release planning
- Set up Dependabot for dependency updates
- Consider CODEOWNERS file for review assignment

## Repository Structure Checklist

```
phonon-flow/
├── README.md              ✅ Project overview
├── LICENSE                ✅ MIT license
├── CONTRIBUTING.md        ✅ Contribution guide
├── CHANGELOG.md           ⬜ Release notes
├── CODE_OF_CONDUCT.md     ⬜ Community standards
├── pyproject.toml         ✅ Package metadata
├── requirements.txt       ✅ Dependencies
├── .gitignore             ✅ Git ignore rules
├── .github/
│   ├── workflows/ci.yml   ⬜ CI pipeline
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.md  ⬜ Bug report template
│   │   └── feature.md     ⬜ Feature request template
│   └── dependabot.yml     ⬜ Dep updates
├── phonon_flow/           ✅ Main package
├── examples/              ✅ Example configs
├── docs/                  ⬜ Documentation
└── tests/                 ✅ Test suite
```

## Before First Release

**Must do:**
- Remove ALL real credentials from examples (they use placeholders or `YOUR_*`)
- Make sure no hardcoded internal IPs in source (only in example configs)
- Add disclaimer about VASP license requirements

**Nice to have:**
- Tested on at least 1 HPC + 1 Raspberry Pi
- At least 80% test coverage
- Documentation for all public APIs
- At least 1 complete example (Si is a good candidate — standard VASP tutorial)

---

## Quick Release Commands

```bash
# One-time setup
cd phonon-flow
git init && git add . && git commit -m "v0.1.0: Initial release"
gh repo create phonon-flow/phonon-flow --public --push --source=.

# Build and publish
python -m build
twine upload dist/*

# Tag release
git tag v0.1.0
git push origin v0.1.0
```
