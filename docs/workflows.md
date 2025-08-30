# 🔄 Workflows (CI/CD)

The repo uses GitHub Actions to ensure quality.

## `.github/workflows/ci.yml`
- Install dependencies
- Run `flake8` linting
- Run `black --check` formatting
- Run `pytest` (if tests exist)

✅ If workflow passes = Repo is **ready for deployment**.
