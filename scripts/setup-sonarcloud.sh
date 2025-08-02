#!/bin/bash

# SonarCloud Setup Script for Japanese Stock Analysis Platform
# This script helps configure SonarCloud for code quality analysis

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if required tools are installed
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if git is available
    if ! command -v git &> /dev/null; then
        log_error "Git is not installed. Please install Git first."
        exit 1
    fi
    
    # Check if we're in a git repository
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        log_error "Not in a Git repository. Please run this script from your project root."
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Function to get repository information
get_repo_info() {
    log_info "Getting repository information..."
    
    # Get remote URL
    REMOTE_URL=$(git config --get remote.origin.url)
    
    # Extract owner and repo name from GitHub URL
    if [[ $REMOTE_URL =~ github\.com[:/]([^/]+)/([^/]+)(\.git)?$ ]]; then
        REPO_OWNER="${BASH_REMATCH[1]}"
        REPO_NAME="${BASH_REMATCH[2]}"
        REPO_NAME="${REPO_NAME%.git}"  # Remove .git suffix if present
    else
        log_error "Could not parse GitHub repository URL: $REMOTE_URL"
        exit 1
    fi
    
    log_info "Repository Owner: $REPO_OWNER"
    log_info "Repository Name: $REPO_NAME"
    
    # Set project key
    PROJECT_KEY="${REPO_OWNER}_${REPO_NAME}"
    log_info "SonarCloud Project Key: $PROJECT_KEY"
}

# Function to update sonar-project.properties
update_sonar_config() {
    log_info "Updating sonar-project.properties..."
    
    SONAR_FILE="sonar-project.properties"
    
    if [ ! -f "$SONAR_FILE" ]; then
        log_error "sonar-project.properties not found. Please ensure you're in the project root."
        exit 1
    fi
    
    # Create backup
    cp "$SONAR_FILE" "${SONAR_FILE}.backup"
    log_info "Created backup: ${SONAR_FILE}.backup"
    
    # Update project key and organization
    sed -i.tmp "s/sonar.projectKey=.*/sonar.projectKey=$PROJECT_KEY/" "$SONAR_FILE"
    sed -i.tmp "s/sonar.organization=.*/sonar.organization=$REPO_OWNER/" "$SONAR_FILE"
    
    # Clean up temporary file
    rm -f "${SONAR_FILE}.tmp"
    
    log_success "Updated sonar-project.properties with:"
    log_info "  Project Key: $PROJECT_KEY"
    log_info "  Organization: $REPO_OWNER"
}

# Function to display setup instructions
show_setup_instructions() {
    log_info "SonarCloud Setup Instructions:"
    echo ""
    echo "1. Go to https://sonarcloud.io and sign in with your GitHub account"
    echo ""
    echo "2. Import your repository:"
    echo "   - Click 'Analyze new project'"
    echo "   - Select your GitHub organization: $REPO_OWNER"
    echo "   - Choose repository: $REPO_NAME"
    echo ""
    echo "3. Get your SonarCloud token:"
    echo "   - Go to My Account → Security"
    echo "   - Generate a new token"
    echo "   - Copy the token"
    echo ""
    echo "4. Add the token to GitHub Secrets:"
    echo "   - Go to your GitHub repository"
    echo "   - Settings → Secrets and variables → Actions"
    echo "   - Click 'New repository secret'"
    echo "   - Name: SONAR_TOKEN"
    echo "   - Value: [paste your SonarCloud token]"
    echo ""
    echo "5. Verify the configuration:"
    echo "   - Project Key: $PROJECT_KEY"
    echo "   - Organization: $REPO_OWNER"
    echo ""
    log_success "Setup instructions displayed!"
}

# Function to validate current configuration
validate_config() {
    log_info "Validating current configuration..."
    
    SONAR_FILE="sonar-project.properties"
    
    if [ ! -f "$SONAR_FILE" ]; then
        log_error "sonar-project.properties not found"
        return 1
    fi
    
    # Check if project key is set correctly
    CURRENT_KEY=$(grep "^sonar.projectKey=" "$SONAR_FILE" | cut -d'=' -f2)
    CURRENT_ORG=$(grep "^sonar.organization=" "$SONAR_FILE" | cut -d'=' -f2)
    
    if [ "$CURRENT_KEY" = "$PROJECT_KEY" ]; then
        log_success "Project key is correctly set: $CURRENT_KEY"
    else
        log_warning "Project key mismatch. Expected: $PROJECT_KEY, Found: $CURRENT_KEY"
    fi
    
    if [ "$CURRENT_ORG" = "$REPO_OWNER" ]; then
        log_success "Organization is correctly set: $CURRENT_ORG"
    else
        log_warning "Organization mismatch. Expected: $REPO_OWNER, Found: $CURRENT_ORG"
    fi
    
    # Check if source paths exist
    if [ -d "backend/app" ]; then
        log_success "Backend source directory found: backend/app"
    else
        log_warning "Backend source directory not found: backend/app"
    fi
    
    if [ -d "frontend/src" ]; then
        log_success "Frontend source directory found: frontend/src"
    else
        log_warning "Frontend source directory not found: frontend/src"
    fi
}

# Function to test SonarCloud connection (if token is available)
test_connection() {
    log_info "Testing SonarCloud connection..."
    
    if [ -z "$SONAR_TOKEN" ]; then
        log_warning "SONAR_TOKEN environment variable not set. Skipping connection test."
        log_info "To test connection, set SONAR_TOKEN and run: $0 test"
        return 0
    fi
    
    # Try to get project information
    RESPONSE=$(curl -s -u "$SONAR_TOKEN:" \
        "https://sonarcloud.io/api/projects/search?projects=$PROJECT_KEY" \
        -w "%{http_code}")
    
    HTTP_CODE="${RESPONSE: -3}"
    BODY="${RESPONSE%???}"
    
    if [ "$HTTP_CODE" = "200" ]; then
        log_success "Successfully connected to SonarCloud!"
        log_info "Project found: $PROJECT_KEY"
    else
        log_error "Failed to connect to SonarCloud (HTTP $HTTP_CODE)"
        log_info "Please check your SONAR_TOKEN and project configuration"
    fi
}

# Main function
main() {
    echo "🔍 SonarCloud Setup Script"
    echo "=========================="
    echo ""
    
    check_prerequisites
    get_repo_info
    
    case "${1:-setup}" in
        "setup")
            update_sonar_config
            show_setup_instructions
            ;;
        "validate")
            validate_config
            ;;
        "test")
            validate_config
            test_connection
            ;;
        "help"|"-h"|"--help")
            echo "Usage: $0 [command]"
            echo ""
            echo "Commands:"
            echo "  setup     Update configuration and show setup instructions (default)"
            echo "  validate  Validate current configuration"
            echo "  test      Test SonarCloud connection (requires SONAR_TOKEN)"
            echo "  help      Show this help message"
            echo ""
            echo "Environment Variables:"
            echo "  SONAR_TOKEN  Your SonarCloud token (for testing connection)"
            ;;
        *)
            log_error "Unknown command: $1"
            echo "Run '$0 help' for usage information"
            exit 1
            ;;
    esac
    
    echo ""
    log_success "SonarCloud setup script completed!"
}

# Run main function with all arguments
main "$@"