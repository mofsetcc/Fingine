#!/usr/bin/env node
/**
 * Frontend test automation script.
 * Provides comprehensive test execution with coverage reporting.
 */

const { execSync, spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

// Colors for console output
const colors = {
    reset: '\x1b[0m',
    red: '\x1b[31m',
    green: '\x1b[32m',
    yellow: '\x1b[33m',
    blue: '\x1b[34m',
    magenta: '\x1b[35m',
    cyan: '\x1b[36m',
};

function log(message, color = colors.reset) {
    console.log(`${color}${message}${colors.reset}`);
}

function runCommand(command, options = {}) {
    try {
        const result = execSync(command, {
            stdio: 'pipe',
            encoding: 'utf8',
            ...options,
        });
        return { success: true, output: result };
    } catch (error) {
        return {
            success: false,
            output: error.stdout || error.message,
            error: error.stderr || error.message
        };
    }
}

function runUnitTests(options = {}) {
    log('🧪 Running unit tests...', colors.blue);

    const jestArgs = ['--passWithNoTests'];

    if (options.verbose) {
        jestArgs.push('--verbose');
    }

    if (options.coverage) {
        jestArgs.push('--coverage');
        jestArgs.push('--coverageReporters=text');
        jestArgs.push('--coverageReporters=html');
        jestArgs.push('--coverageReporters=lcov');
    }

    if (options.watch) {
        jestArgs.push('--watch');
    }

    if (options.updateSnapshots) {
        jestArgs.push('--updateSnapshot');
    }

    const command = `npx jest ${jestArgs.join(' ')}`;
    const result = runCommand(command);

    if (result.success) {
        log('✅ Unit tests passed!', colors.green);
        if (options.coverage) {
            log('📊 Coverage report generated in coverage/', colors.cyan);
        }
        return true;
    } else {
        log('❌ Unit tests failed!', colors.red);
        console.log(result.output);
        if (result.error) {
            console.error(result.error);
        }
        return false;
    }
}

function runLinting() {
    log('🔍 Running linting checks...', colors.blue);

    // Run ESLint
    log('Checking code quality with ESLint...', colors.cyan);
    const eslintResult = runCommand('npx eslint src/ --ext .ts,.tsx,.js,.jsx');
    if (!eslintResult.success) {
        log('❌ ESLint issues found!', colors.red);
        console.log(eslintResult.output);
        return false;
    }

    // Run Prettier check
    log('Checking code formatting with Prettier...', colors.cyan);
    const prettierResult = runCommand('npx prettier --check src/');
    if (!prettierResult.success) {
        log('❌ Code formatting issues found!', colors.red);
        console.log(prettierResult.output);
        log('💡 Run "npm run format" to fix formatting issues', colors.yellow);
        return false;
    }

    // Run TypeScript type checking
    log('Running TypeScript type checking...', colors.cyan);
    const tscResult = runCommand('npx tsc --noEmit');
    if (!tscResult.success) {
        log('❌ TypeScript type errors found!', colors.red);
        console.log(tscResult.output);
        return false;
    }

    log('✅ Linting checks passed!', colors.green);
    return true;
}

function runBuildTest() {
    log('🏗️  Testing production build...', colors.blue);

    const result = runCommand('npm run build');
    if (result.success) {
        log('✅ Production build successful!', colors.green);

        // Check if build artifacts exist
        const distPath = path.join(process.cwd(), 'dist');
        if (fs.existsSync(distPath)) {
            const files = fs.readdirSync(distPath);
            log(`📦 Build artifacts: ${files.length} files generated`, colors.cyan);
        }

        return true;
    } else {
        log('❌ Production build failed!', colors.red);
        console.log(result.output);
        return false;
    }
}

function runSecurityAudit() {
    log('🔒 Running security audit...', colors.blue);

    const result = runCommand('npm audit --audit-level=moderate');
    if (result.success) {
        log('✅ No security vulnerabilities found!', colors.green);
        return true;
    } else {
        log('⚠️  Security vulnerabilities found:', colors.yellow);
        console.log(result.output);
        log('💡 Run "npm audit fix" to fix automatically fixable issues', colors.yellow);
        // Don't fail on audit issues, just warn
        return true;
    }
}

function generateTestReport() {
    log('📋 Generating test report...', colors.blue);

    // Run tests with JUnit reporter for CI
    const jestArgs = [
        '--coverage',
        '--coverageReporters=lcov',
        '--coverageReporters=cobertura',
        '--testResultsProcessor=jest-junit',
        '--passWithNoTests'
    ];

    const command = `npx jest ${jestArgs.join(' ')}`;
    const result = runCommand(command, {
        env: {
            ...process.env,
            JEST_JUNIT_OUTPUT_DIR: './test-results',
            JEST_JUNIT_OUTPUT_NAME: 'junit.xml'
        }
    });

    if (result.success) {
        log('✅ Test report generated!', colors.green);
        log('📄 JUnit XML: test-results/junit.xml', colors.cyan);
        log('📄 Coverage: coverage/lcov.info', colors.cyan);
        return true;
    } else {
        log('❌ Failed to generate test report!', colors.red);
        console.log(result.output);
        return false;
    }
}

function checkDependencies() {
    log('📦 Checking dependencies...', colors.blue);

    // Check if node_modules exists
    if (!fs.existsSync('node_modules')) {
        log('❌ node_modules not found! Run "npm install" first.', colors.red);
        return false;
    }

    // Check for outdated packages
    const outdatedResult = runCommand('npm outdated --json');
    if (outdatedResult.output && outdatedResult.output.trim()) {
        try {
            const outdated = JSON.parse(outdatedResult.output);
            const outdatedCount = Object.keys(outdated).length;
            if (outdatedCount > 0) {
                log(`⚠️  ${outdatedCount} outdated packages found`, colors.yellow);
                log('💡 Run "npm update" to update packages', colors.yellow);
            }
        } catch (e) {
            // Ignore JSON parse errors
        }
    }

    log('✅ Dependencies check completed!', colors.green);
    return true;
}

function main() {
    const args = process.argv.slice(2);
    const options = {
        unit: args.includes('--unit'),
        lint: args.includes('--lint'),
        build: args.includes('--build'),
        security: args.includes('--security'),
        all: args.includes('--all'),
        verbose: args.includes('--verbose') || args.includes('-v'),
        coverage: !args.includes('--no-coverage'),
        watch: args.includes('--watch'),
        updateSnapshots: args.includes('--update-snapshots'),
        report: args.includes('--report'),
    };

    // If no specific test type is specified, run all
    if (!options.unit && !options.lint && !options.build && !options.security) {
        options.all = true;
    }

    log('🚀 Starting frontend test suite...', colors.magenta);

    let success = true;

    // Check dependencies first
    success &= checkDependencies();

    if (options.unit || options.all) {
        success &= runUnitTests({
            verbose: options.verbose,
            coverage: options.coverage,
            watch: options.watch,
            updateSnapshots: options.updateSnapshots,
        });
    }

    if (options.lint || options.all) {
        success &= runLinting();
    }

    if (options.build || options.all) {
        success &= runBuildTest();
    }

    if (options.security || options.all) {
        success &= runSecurityAudit();
    }

    if (options.report) {
        success &= generateTestReport();
    }

    if (success) {
        log('\n🎉 All tests and checks passed!', colors.green);
        process.exit(0);
    } else {
        log('\n💥 Some tests or checks failed!', colors.red);
        process.exit(1);
    }
}

// Show help if requested
if (process.argv.includes('--help') || process.argv.includes('-h')) {
    console.log(`
Frontend Test Runner

Usage: node scripts/test.js [options]

Options:
  --unit              Run unit tests only
  --lint              Run linting checks only
  --build             Test production build only
  --security          Run security audit only
  --all               Run all tests and checks (default)
  --verbose, -v       Verbose output
  --no-coverage       Skip coverage reporting
  --watch             Run tests in watch mode
  --update-snapshots  Update Jest snapshots
  --report            Generate test report for CI
  --help, -h          Show this help message

Examples:
  node scripts/test.js --unit --coverage
  node scripts/test.js --lint
  node scripts/test.js --all --verbose
  node scripts/test.js --watch
`);
    process.exit(0);
}

if (require.main === module) {
    main();
}

module.exports = {
    runUnitTests,
    runLinting,
    runBuildTest,
    runSecurityAudit,
    generateTestReport,
};