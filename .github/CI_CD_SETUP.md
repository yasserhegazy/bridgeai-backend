# GitHub Actions CI/CD Setup Guide

## 🚀 Overview

This repository includes comprehensive CI/CD pipelines using GitHub Actions for automated testing, code quality checks, security scanning, and coverage tracking.

## 📋 Workflows

### 1. **CI Pipeline** (`.github/workflows/ci.yml`)
Runs on every push and pull request to `main`, `develop`, and `crs-generation` branches.

**Jobs:**
- **Lint**: Code quality checks (Black, isort, Flake8, MyPy)
- **Test**: Unit and integration tests with MySQL service
- **Migration Check**: Validates Alembic database migrations
- **Build Validation**: Ensures application starts correctly

### 2. **Coverage Tracking** (`.github/workflows/coverage.yml`)
Generates detailed code coverage reports.

**Features:**
- Coverage reports uploaded to Codecov & Coveralls
- PR comments with coverage changes
- Coverage badges generation
- Minimum threshold enforcement (70%)

### 3. **Security Scanning** (`.github/workflows/security.yml`)
Comprehensive security analysis (runs on push, PR, and weekly schedule).

**Scans:**
- **Dependency Security**: Safety, pip-audit
- **Code Security**: Bandit static analysis
- **CodeQL**: Advanced security analysis
- **Secret Scanning**: TruffleHog, detect-secrets
- **Dependency Review**: License and vulnerability checks
- **Snyk**: Third-party vulnerability scanning

## 🔧 Required GitHub Secrets

Add these secrets in your repository settings (`Settings → Secrets and variables → Actions`):

### Essential Secrets:
```
GROQ_API_KEY          # Your Groq API key
OPENAI_API_KEY        # Your OpenAI API key (if using OpenAI)
```

### Optional Secrets (for enhanced features):
```
CODECOV_TOKEN         # Codecov integration
SNYK_TOKEN           # Snyk security scanning
```

## 📦 Setup Steps

### 1. Install Development Dependencies
```bash
pip install black isort flake8 mypy safety bandit
pip install -r requirements-test.txt
```

### 2. Configure Code Formatters (Optional - for local development)
```bash
# Format code with Black
black app/ tests/

# Sort imports with isort
isort app/ tests/

# Run linting
flake8 app/ tests/
```

### 3. Enable GitHub Actions
- GitHub Actions are automatically enabled when you push workflows
- Check the "Actions" tab in your repository

### 4. Configure Branch Protection (Recommended)
1. Go to `Settings → Branches → Branch protection rules`
2. Add rule for `main` branch:
   - ✅ Require status checks before merging
   - ✅ Require branches to be up to date
   - Select required checks:
     - `Code Quality & Linting`
     - `Unit & Integration Tests`
     - `CodeQL Security Analysis`

## 📊 Badges

Add these badges to your main README.md:

```markdown
![CI Pipeline](https://github.com/KhaledJamalKwaik/bridgeai-backend/workflows/CI%20Pipeline/badge.svg)
![Security](https://github.com/KhaledJamalKwaik/bridgeai-backend/workflows/Security%20Scanning/badge.svg)
[![codecov](https://codecov.io/gh/KhaledJamalKwaik/bridgeai-backend/branch/main/graph/badge.svg)](https://codecov.io/gh/KhaledJamalKwaik/bridgeai-backend)
```

## 🧪 Running Tests Locally

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html --cov-report=term-missing

# Run specific test file
pytest tests/test_auth.py -v

# Run security scans
bandit -r app/ -ll
safety check
```

## 🔍 Understanding Workflow Results

### CI Pipeline Results:
- ✅ **Green**: All checks passed
- ❌ **Red**: Tests failed or linting issues
- 🟡 **Yellow**: Warnings (won't block merge)

### Coverage Reports:
- View HTML reports in workflow artifacts
- Check PR comments for coverage changes
- Target: >70% coverage (enforced), >80% ideal

### Security Scans:
- Review security reports in workflow artifacts
- CodeQL results appear in Security tab
- Critical/High vulnerabilities should be fixed immediately

## 📁 Configuration Files

- **setup.cfg**: Flake8, isort, mypy, coverage configuration
- **.bandit**: Bandit security scanner settings
- **.secrets.baseline**: Baseline for secret detection
- **.github/dependabot.yml**: Automated dependency updates

## 🚨 Troubleshooting

### Tests Failing in CI but Pass Locally:
- Check environment variables in workflow
- Verify MySQL connection settings
- Check Python version (3.13 in CI)

### Coverage Too Low:
- Add more tests for uncovered code
- Check `htmlcov/index.html` for coverage gaps

### Security Scan Failures:
- Review security reports in artifacts
- Update vulnerable dependencies
- Fix Bandit warnings in code

## 🎯 Best Practices

1. **Always run tests locally before pushing**
   ```bash
   pytest tests/ -v
   ```

2. **Format code before committing**
   ```bash
   black app/ tests/
   isort app/ tests/
   ```

3. **Check for security issues**
   ```bash
   bandit -r app/ -ll
   ```

4. **Keep dependencies updated**
   - Review Dependabot PRs weekly
   - Test updates thoroughly

5. **Monitor coverage trends**
   - Don't decrease coverage
   - Add tests for new features

## 📚 Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Codecov Documentation](https://docs.codecov.io/)
- [Bandit Documentation](https://bandit.readthedocs.io/)
- [pytest Documentation](https://docs.pytest.org/)

## 🤝 Contributing

All pull requests must pass:
1. ✅ Linting checks
2. ✅ Unit tests
3. ✅ Security scans
4. ✅ Coverage threshold (70%+)

See [PULL_REQUEST_TEMPLATE.md](.github/PULL_REQUEST_TEMPLATE.md) for PR guidelines.
