# Code Quality Guide

## Overview

This guide covers the code quality tools and standards for the Japanese Stock Analysis Platform, including SonarCloud integration, linting, and automated quality checks.

## Code Quality Tools

### 1. SonarCloud Integration

SonarCloud provides comprehensive code quality analysis for both Python and TypeScript/JavaScript code.

#### Configuration

The SonarCloud configuration is located in `sonar-project.properties`:

```properties
sonar.projectKey=mofsetcc_Fingine
sonar.organization=mofsetcc
sonar.sources=backend/app,frontend/src
sonar.tests=backend/tests,frontend/src/__tests__
```

#### Setting Up SonarCloud

1. **Create SonarCloud Account**:
   - Go to [SonarCloud.io](https://sonarcloud.io)
   - Sign in with your GitHub account
   - Import your repository

2. **Configure GitHub Secrets**:
   ```bash
   # Add to GitHub repository secrets
   SONAR_TOKEN=your_sonar_token_here
   ```

3. **Project Configuration**:
   - Update `sonar.projectKey` and `sonar.organization` in `sonar-project.properties`
   - Ensure the project key matches your SonarCloud project

#### Quality Gates

We maintain the following quality standards:

- **Coverage**: ≥80% for new code
- **Duplicated Lines**: ≤3% for new code
- **Maintainability Rating**: A
- **Reliability Rating**: A
- **Security Rating**: A

### 2. Python Code Quality (Backend)

#### Tools Used

- **Flake8**: Style guide enforcement
- **Black**: Code formatting
- **isort**: Import sorting
- **mypy**: Type checking
- **Bandit**: Security analysis

#### Configuration Files

- `.flake8`: Flake8 configuration
- `pyproject.toml`: Black, isort, and other tool configurations
- `mypy.ini`: Type checking configuration

#### Running Locally

```bash
cd backend

# Install quality tools
pip install flake8 black isort mypy bandit

# Run all checks
flake8 app/
black --check app/
isort --check-only app/
mypy app/
bandit -r app/
```

#### Pre-commit Hooks

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

### 3. JavaScript/TypeScript Code Quality (Frontend)

#### Tools Used

- **ESLint**: Linting and style enforcement
- **Prettier**: Code formatting
- **TypeScript**: Type checking
- **Jest**: Testing with coverage

#### Configuration Files

- `.eslintrc.js`: ESLint configuration
- `.prettierrc`: Prettier configuration
- `tsconfig.json`: TypeScript configuration

#### Running Locally

```bash
cd frontend

# Install dependencies
npm install

# Run all checks
npm run lint
npm run type-check
npm run format
npm run test:coverage
```

## CI/CD Integration

### GitHub Actions Workflow

The code quality checks are integrated into our CI/CD pipeline:

```yaml
code-quality:
  name: Code Quality
  runs-on: ubuntu-latest
  if: ${{ secrets.SONAR_TOKEN != '' }}
  
  steps:
    - name: Generate coverage reports
      run: |
        # Backend coverage
        pytest --cov=app --cov-report=xml
        # Frontend coverage
        npm run test:coverage
        
    - name: SonarQube Scan
      uses: SonarSource/sonarqube-scan-action@v5.0.0
      env:
        SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
```

### Fallback Quality Checks

When SonarCloud is not available, we run alternative quality checks:

```yaml
code-quality-fallback:
  name: Code Quality (Fallback)
  if: ${{ secrets.SONAR_TOKEN == '' }}
  
  steps:
    - name: Python quality checks
      run: |
        flake8 app/
        black --check app/
        bandit -r app/
        
    - name: JavaScript quality checks
      run: |
        npm run lint
        npm run type-check
```

## Quality Standards

### Python Code Standards

1. **PEP 8 Compliance**: Follow Python style guidelines
2. **Type Hints**: Use type hints for all functions
3. **Docstrings**: Document all public functions and classes
4. **Error Handling**: Proper exception handling
5. **Security**: No hardcoded secrets or SQL injection vulnerabilities

#### Example:

```python
from typing import Optional, List
from pydantic import BaseModel

class UserService:
    """Service for user management operations."""
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """
        Retrieve a user by their ID.
        
        Args:
            user_id: The unique identifier for the user
            
        Returns:
            User object if found, None otherwise
            
        Raises:
            DatabaseError: If database connection fails
        """
        try:
            return self.db.query(User).filter(User.id == user_id).first()
        except Exception as e:
            logger.error(f"Failed to get user {user_id}: {e}")
            raise DatabaseError("User retrieval failed")
```

### TypeScript/React Standards

1. **TypeScript Strict Mode**: Enable strict type checking
2. **Component Types**: Proper typing for React components
3. **Hook Usage**: Follow React hooks best practices
4. **Error Boundaries**: Implement error handling
5. **Accessibility**: ARIA labels and semantic HTML

#### Example:

```typescript
interface StockSearchProps {
  onStockSelect: (stock: Stock) => void;
  placeholder?: string;
}

const StockSearch: React.FC<StockSearchProps> = ({ 
  onStockSelect, 
  placeholder = "Search stocks..." 
}) => {
  const [query, setQuery] = useState<string>('');
  const [results, setResults] = useState<Stock[]>([]);
  
  const handleSearch = useCallback(async (searchQuery: string) => {
    try {
      const response = await stockApi.search(searchQuery);
      setResults(response.data);
    } catch (error) {
      console.error('Search failed:', error);
      setResults([]);
    }
  }, []);
  
  return (
    <div role="search" aria-label="Stock search">
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder={placeholder}
        aria-label="Stock search input"
      />
      {/* Search results */}
    </div>
  );
};
```

## Troubleshooting

### Common SonarCloud Issues

#### 1. "SONAR_TOKEN not found"

**Solution**: Add the SONAR_TOKEN secret to your GitHub repository:

1. Go to repository Settings → Secrets and variables → Actions
2. Add new repository secret: `SONAR_TOKEN`
3. Get the token from SonarCloud → My Account → Security

#### 2. "Project not found"

**Solution**: Ensure the project key matches:

```properties
# In sonar-project.properties
sonar.projectKey=your_github_username_repository_name
sonar.organization=your_github_username
```

#### 3. Coverage reports not found

**Solution**: Ensure coverage is generated before SonarCloud scan:

```yaml
- name: Generate coverage
  run: |
    pytest --cov=app --cov-report=xml
    npm run test:coverage

- name: SonarQube Scan
  uses: SonarSource/sonarqube-scan-action@v5.0.0
```

### Quality Gate Failures

#### 1. Low Code Coverage

**Solutions**:
- Add unit tests for uncovered code
- Remove dead code
- Exclude generated files from coverage

#### 2. Code Smells

**Solutions**:
- Refactor complex functions
- Remove code duplication
- Follow naming conventions
- Add proper error handling

#### 3. Security Hotspots

**Solutions**:
- Review flagged security issues
- Use parameterized queries
- Validate user inputs
- Avoid hardcoded secrets

## Best Practices

### 1. Development Workflow

1. **Write tests first** (TDD approach)
2. **Run quality checks locally** before committing
3. **Use pre-commit hooks** to catch issues early
4. **Review SonarCloud reports** regularly
5. **Address quality issues** promptly

### 2. Code Review Process

1. **Check quality metrics** in PR reviews
2. **Ensure tests pass** and coverage is maintained
3. **Review SonarCloud analysis** results
4. **Address reviewer feedback** before merging

### 3. Continuous Improvement

1. **Monitor quality trends** over time
2. **Update quality rules** as needed
3. **Share knowledge** about quality practices
4. **Celebrate quality improvements**

## Resources

- [SonarCloud Documentation](https://docs.sonarcloud.io/)
- [Python Code Quality Tools](https://realpython.com/python-code-quality/)
- [ESLint Rules](https://eslint.org/docs/rules/)
- [TypeScript Best Practices](https://typescript-eslint.io/rules/)
- [React Testing Best Practices](https://kentcdodds.com/blog/common-mistakes-with-react-testing-library)