# CI/CD Troubleshooting Guide

## Overview

This guide helps you troubleshoot common issues in the GitHub Actions CI/CD pipeline for the Japanese Stock Analysis Platform.

## Common Issues and Solutions

### 1. Backend Test Failures

#### Issue: "requirements.txt not found"
**Solution**: Ensure the requirements.txt file exists in the backend directory:
```bash
# Check if file exists
ls -la backend/requirements.txt

# If missing, create it with basic dependencies
cd backend
pip freeze > requirements.txt
```

#### Issue: "app/ directory not found"
**Solution**: Verify the backend directory structure:
```bash
backend/
├── app/
│   ├── __init__.py
│   ├── main.py
│   └── ...
├── tests/
├── requirements.txt
└── ...
```

#### Issue: Database connection failures
**Solution**: The CI uses PostgreSQL service. Check:
- Service configuration in workflow
- Connection string format
- Wait for service readiness

```yaml
# In CI workflow
- name: Wait for services
  run: |
    timeout 30 bash -c 'until pg_isready -h localhost -p 5432; do sleep 1; done'
```

### 2. Frontend Test Failures

#### Issue: "package.json not found"
**Solution**: Ensure package.json exists in frontend directory:
```bash
# Check if file exists
ls -la frontend/package.json

# If missing, initialize npm project
cd frontend
npm init -y
```

#### Issue: "npm ci failed"
**Solution**: Try these steps:
1. Delete package-lock.json and node_modules
2. Run `npm install` to regenerate lock file
3. Commit the new package-lock.json

```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
git add package-lock.json
git commit -m "fix: regenerate package-lock.json"
```

#### Issue: TypeScript compilation errors
**Solution**: Check TypeScript configuration:
```bash
# Run type check locally
cd frontend
npm run type-check

# Fix common issues
npm install --save-dev typescript @types/node @types/react
```

### 3. Docker Build Failures

#### Issue: "Dockerfile not found"
**Solution**: Create Dockerfiles for backend and frontend:

**Backend Dockerfile** (`backend/Dockerfile`):
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Frontend Dockerfile** (`frontend/Dockerfile`):
```dockerfile
FROM node:18-alpine

WORKDIR /app
COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=0 /app/dist /usr/share/nginx/html
```

### 4. SonarCloud Issues

#### Issue: "SONAR_TOKEN not found"
**Solution**: The workflow is designed to handle this gracefully:
- If SONAR_TOKEN is not set, it runs fallback quality checks
- To enable SonarCloud, add the token to GitHub secrets

#### Issue: "Project not found in SonarCloud"
**Solution**: Update sonar-project.properties:
```properties
sonar.projectKey=your_github_username_repository_name
sonar.organization=your_github_username
```

### 5. Performance Test Issues

#### Issue: "Lighthouse CI failed"
**Solution**: The workflow includes fallback performance tests:
- Lighthouse CI runs if build succeeds
- Falls back to bundle size analysis if Lighthouse fails
- Check build output exists in `dist/` directory

### 6. Security Scan Issues

#### Issue: Trivy or Snyk failures
**Solution**: These are set to `continue-on-error: true`:
- Security scans won't fail the entire pipeline
- Review security reports in the Actions tab
- Address high-severity vulnerabilities

## Debugging Strategies

### 1. Check Workflow Logs

1. Go to your repository on GitHub
2. Click "Actions" tab
3. Click on the failed workflow run
4. Expand the failed job to see detailed logs

### 2. Run Tests Locally

Before pushing, run tests locally:

```bash
# Backend tests
cd backend
pip install -r requirements.txt
pytest tests/

# Frontend tests
cd frontend
npm install
npm test
npm run build
```

### 3. Use Basic Validation Workflow

The repository includes a basic validation workflow that:
- Checks repository structure
- Validates JSON files
- Tests basic Python/Node.js setup
- Provides quick feedback

### 4. Enable Debug Logging

Add debug steps to your workflow:

```yaml
- name: Debug Environment
  run: |
    echo "Current directory: $(pwd)"
    echo "Directory contents:"
    ls -la
    echo "Environment variables:"
    env | grep -E "(NODE_|PYTHON_|DATABASE_)" || true
```

## Workflow Configuration

### Environment Variables

The CI workflow uses these environment variables:
- `PYTHON_VERSION`: Python version (default: 3.11)
- `NODE_VERSION`: Node.js version (default: 18)
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string

### Secrets Required

Optional secrets (workflow continues without them):
- `SONAR_TOKEN`: SonarCloud authentication
- `CODECOV_TOKEN`: Code coverage reporting
- `SNYK_TOKEN`: Security vulnerability scanning
- `LHCI_GITHUB_APP_TOKEN`: Lighthouse CI integration

### Service Dependencies

The workflow uses these services:
- PostgreSQL 15 (for backend tests)
- Redis 7 (for caching tests)

## Best Practices

### 1. Incremental Fixes

- Fix one issue at a time
- Test locally before pushing
- Use draft PRs for experimental changes

### 2. Monitoring

- Check CI status regularly
- Set up notifications for failures
- Review security scan results

### 3. Maintenance

- Keep dependencies updated
- Review and update workflow configurations
- Monitor performance trends

## Getting Help

### 1. Check Documentation

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Docker Documentation](https://docs.docker.com/)
- [SonarCloud Documentation](https://docs.sonarcloud.io/)

### 2. Common Commands

```bash
# Check workflow syntax
act --list  # If you have 'act' installed

# Validate Docker builds locally
docker build -t test-backend ./backend
docker build -t test-frontend ./frontend

# Run security scans locally
trivy fs .
```

### 3. Workflow Status

You can check the current status of all workflows:
- Green checkmark: All tests passing
- Red X: Some tests failing
- Yellow dot: Tests in progress
- Gray circle: Tests skipped/cancelled

## Emergency Fixes

If the CI is completely broken:

1. **Disable failing workflows temporarily**:
   - Go to Actions tab → Select workflow → Disable workflow

2. **Use basic validation only**:
   - The basic-validation.yml workflow should always work
   - Provides minimal checks while you fix main CI

3. **Rollback recent changes**:
   ```bash
   git revert HEAD~1  # Revert last commit
   git push origin main
   ```

4. **Create hotfix branch**:
   ```bash
   git checkout -b hotfix/ci-fix
   # Make minimal fixes
   git push origin hotfix/ci-fix
   # Create PR for review
   ```

Remember: The CI is designed to be resilient with `continue-on-error: true` for non-critical jobs, so most issues won't completely break the pipeline.