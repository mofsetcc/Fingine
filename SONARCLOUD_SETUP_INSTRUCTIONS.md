# SonarCloud Setup Instructions

## 🚨 IMPORTANT SECURITY NOTICE
**Never share your SonarCloud token publicly!** The token you provided should be kept secure and only added to GitHub Secrets.

## 📋 Quick Setup Steps

### Step 1: Add SONAR_TOKEN to GitHub Secrets

1. **Go to your GitHub repository**: https://github.com/mofsetcc/Fingine
2. **Click Settings tab** (in the repository, not your profile)
3. **Navigate to Secrets**: In left sidebar → **Secrets and variables** → **Actions**
4. **Add new secret**:
   - Click **"New repository secret"**
   - **Name**: `SONAR_TOKEN`
   - **Value**: `9189c2cc013cce5c1b0c83906d3aca10659ebab7`
   - Click **"Add secret"**

### Step 2: Verify SonarCloud Project Setup

1. **Go to SonarCloud**: https://sonarcloud.io
2. **Sign in** with your GitHub account
3. **Check your project**:
   - Organization: `mofsetcc`
   - Project Key: `mofsetcc_Fingine`
   - Project Name: `Japanese Stock Analysis Platform (Kessan)`

### Step 3: Test the Setup

After adding the secret, the next push to your repository should trigger SonarCloud analysis successfully.

## 🔧 Configuration Details

Your repository is already configured with:

- **Project Key**: `mofsetcc_Fingine`
- **Organization**: `mofsetcc`
- **Source Paths**: `backend/app`, `frontend/src`
- **Test Paths**: `backend/tests`, `frontend/src/__tests__`

## 🚀 What Happens Next

Once you add the SONAR_TOKEN secret:

1. ✅ **SonarCloud scan will run** on every push to main/develop
2. ✅ **Code quality metrics** will be available in SonarCloud dashboard
3. ✅ **Quality gates** will be enforced
4. ✅ **Coverage reports** will be uploaded automatically

## 🛠️ Troubleshooting

### If SonarCloud still fails:

1. **Check the secret name**: Must be exactly `SONAR_TOKEN`
2. **Verify token validity**: Token should be active in SonarCloud
3. **Check project permissions**: Ensure you have admin access to the SonarCloud project

### Common Issues:

- **"Project not found"**: Verify project key matches `mofsetcc_Fingine`
- **"Token invalid"**: Generate a new token from SonarCloud → My Account → Security
- **"Permission denied"**: Ensure you're a member of the `mofsetcc` organization

## 📊 Expected Results

After successful setup, you'll see:

- ✅ Code Quality job passes in GitHub Actions
- ✅ SonarCloud analysis results in the dashboard
- ✅ Quality metrics for both backend (Python) and frontend (TypeScript)
- ✅ Coverage reports integrated

## 🔗 Useful Links

- **SonarCloud Dashboard**: https://sonarcloud.io/organizations/mofsetcc
- **Your Project**: https://sonarcloud.io/project/overview?id=mofsetcc_Fingine
- **GitHub Actions**: https://github.com/mofsetcc/Fingine/actions

---

**Remember**: Keep your SonarCloud token secure and never commit it to your repository!