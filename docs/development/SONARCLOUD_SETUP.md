# SonarCloud Setup Guide

## Quick Setup

Run the automated setup script:

```bash
./scripts/setup-sonarcloud.sh
```

This will:
1. ✅ Update your `sonar-project.properties` with correct project information
2. ✅ Display step-by-step setup instructions
3. ✅ Validate your configuration

## Manual Setup Steps

### 1. SonarCloud Account Setup

1. Go to [SonarCloud.io](https://sonarcloud.io)
2. Sign in with your GitHub account
3. Import your repository:
   - Click "Analyze new project"
   - Select your GitHub organization
   - Choose your repository

### 2. Get SonarCloud Token

1. Go to **My Account** → **Security**
2. Generate a new token with a descriptive name
3. Copy the token (you won't see it again)

### 3. Configure GitHub Secrets

1. Go to your GitHub repository
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **"New repository secret"**
4. Add:
   - **Name**: `SONAR_TOKEN`
   - **Value**: Your SonarCloud token

### 4. Verify Configuration

Your `sonar-project.properties` should look like:

```properties
sonar.projectKey=your_github_username_repository_name
sonar.organization=your_github_username
sonar.projectName=Japanese Stock Analysis Platform (Kessan)
```

## Testing the Setup

### Validate Configuration
```bash
./scripts/setup-sonarcloud.sh validate
```

### Test Connection (with token)
```bash
SONAR_TOKEN=your_token ./scripts/setup-sonarcloud.sh test
```

### Run Local Analysis
```bash
# Install SonarScanner
npm install -g sonarqube-scanner

# Run analysis
sonar-scanner \
  -Dsonar.projectKey=your_project_key \
  -Dsonar.organization=your_org \
  -Dsonar.sources=. \
  -Dsonar.host.url=https://sonarcloud.io \
  -Dsonar.login=your_token
```

## Troubleshooting

### Common Issues

#### 1. "SONAR_TOKEN not found"
- Ensure you've added the `SONAR_TOKEN` secret to GitHub
- Check the token is valid and not expired

#### 2. "Project not found"
- Verify the project key matches your SonarCloud project
- Ensure the organization name is correct

#### 3. "Permission denied"
- Check your SonarCloud token has the right permissions
- Ensure you're a member of the organization

#### 4. CI/CD Pipeline Fails
- The workflow will skip SonarCloud if `SONAR_TOKEN` is not available
- A fallback code quality check will run instead

### Getting Help

1. Check the [SonarCloud Documentation](https://docs.sonarcloud.io/)
2. Review the CI/CD logs for specific error messages
3. Validate your configuration with the setup script
4. Ensure all required files are present and properly configured

## Quality Standards

Once set up, SonarCloud will enforce:

- **Coverage**: ≥80% for new code
- **Duplicated Lines**: ≤3%
- **Maintainability Rating**: A
- **Reliability Rating**: A  
- **Security Rating**: A

## Next Steps

After setup:

1. ✅ Push code to trigger the first analysis
2. ✅ Review the SonarCloud dashboard
3. ✅ Address any quality issues found
4. ✅ Set up quality gates for your team
5. ✅ Monitor quality trends over time