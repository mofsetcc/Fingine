#!/usr/bin/env node

/**
 * Frontend Dependencies Validation Script
 * Checks for common issues with frontend dependencies and ESLint configuration
 */

const fs = require('fs');
const path = require('path');

function validatePackageJson(packagePath) {
    console.log('🔍 Validating package.json...');

    if (!fs.existsSync(packagePath)) {
        console.log('❌ package.json not found');
        return false;
    }

    let packageJson;
    try {
        packageJson = JSON.parse(fs.readFileSync(packagePath, 'utf8'));
    } catch (error) {
        console.log('❌ Invalid JSON in package.json:', error.message);
        return false;
    }

    console.log('✅ package.json is valid JSON');

    // Check for required ESLint dependencies
    const requiredEslintDeps = [
        '@typescript-eslint/eslint-plugin',
        '@typescript-eslint/parser',
        'eslint',
        'eslint-plugin-react',
        'eslint-plugin-react-hooks'
    ];

    const allDeps = {
        ...packageJson.dependencies || {},
        ...packageJson.devDependencies || {}
    };

    let missingDeps = [];
    for (const dep of requiredEslintDeps) {
        if (!allDeps[dep]) {
            missingDeps.push(dep);
        }
    }

    if (missingDeps.length > 0) {
        console.log('❌ Missing ESLint dependencies:', missingDeps.join(', '));
        return false;
    } else {
        console.log('✅ All required ESLint dependencies found');
    }

    // Check for required scripts
    const requiredScripts = ['build', 'lint'];
    const scripts = packageJson.scripts || {};

    let missingScripts = [];
    for (const script of requiredScripts) {
        if (!scripts[script]) {
            missingScripts.push(script);
        }
    }

    if (missingScripts.length > 0) {
        console.log('⚠️ Missing scripts:', missingScripts.join(', '));
    } else {
        console.log('✅ All required scripts found');
    }

    return true;
}

function validateEslintConfig(configPath) {
    console.log('🔍 Validating ESLint configuration...');

    const possibleConfigs = [
        '.eslintrc.js',
        '.eslintrc.json',
        '.eslintrc.yaml',
        '.eslintrc.yml',
        'eslint.config.js'
    ];

    let configFile = null;
    for (const config of possibleConfigs) {
        const fullPath = path.join(configPath, config);
        if (fs.existsSync(fullPath)) {
            configFile = fullPath;
            break;
        }
    }

    if (!configFile) {
        console.log('❌ No ESLint configuration file found');
        return false;
    }

    console.log('✅ ESLint config found:', path.basename(configFile));

    try {
        if (configFile.endsWith('.js')) {
            // For .js config files, we can't easily validate without executing
            const content = fs.readFileSync(configFile, 'utf8');
            if (content.includes('@typescript-eslint/recommended')) {
                console.log('✅ TypeScript ESLint config detected');
            }
            if (content.includes('plugin:react/recommended')) {
                console.log('✅ React ESLint config detected');
            }
        } else if (configFile.endsWith('.json')) {
            const config = JSON.parse(fs.readFileSync(configFile, 'utf8'));
            console.log('✅ ESLint config is valid JSON');

            if (config.extends && config.extends.includes('@typescript-eslint/recommended')) {
                console.log('✅ TypeScript ESLint config detected');
            }
        }
    } catch (error) {
        console.log('⚠️ Could not validate ESLint config content:', error.message);
    }

    return true;
}

function validateTsConfig(tsConfigPath) {
    console.log('🔍 Validating TypeScript configuration...');

    if (!fs.existsSync(tsConfigPath)) {
        console.log('⚠️ tsconfig.json not found');
        return false;
    }

    try {
        const tsConfig = JSON.parse(fs.readFileSync(tsConfigPath, 'utf8'));
        console.log('✅ tsconfig.json is valid JSON');

        if (tsConfig.compilerOptions) {
            console.log('✅ Compiler options found');

            if (tsConfig.compilerOptions.jsx) {
                console.log('✅ JSX support configured');
            }

            if (tsConfig.compilerOptions.strict) {
                console.log('✅ Strict mode enabled');
            }
        }

        return true;
    } catch (error) {
        console.log('❌ Invalid JSON in tsconfig.json:', error.message);
        return false;
    }
}

function fixCommonIssues(frontendPath) {
    console.log('🔧 Attempting to fix common issues...');

    const packageJsonPath = path.join(frontendPath, 'package.json');

    if (!fs.existsSync(packageJsonPath)) {
        console.log('❌ Cannot fix: package.json not found');
        return false;
    }

    let packageJson;
    try {
        packageJson = JSON.parse(fs.readFileSync(packageJsonPath, 'utf8'));
    } catch (error) {
        console.log('❌ Cannot fix: Invalid package.json');
        return false;
    }

    let fixed = false;

    // Add missing ESLint dependencies
    const requiredDeps = {
        'eslint-plugin-react-refresh': '^0.4.4'
    };

    if (!packageJson.devDependencies) {
        packageJson.devDependencies = {};
    }

    for (const [dep, version] of Object.entries(requiredDeps)) {
        if (!packageJson.devDependencies[dep] && !packageJson.dependencies?.[dep]) {
            packageJson.devDependencies[dep] = version;
            console.log(`✅ Added missing dependency: ${dep}`);
            fixed = true;
        }
    }

    // Add missing scripts
    if (!packageJson.scripts) {
        packageJson.scripts = {};
    }

    if (!packageJson.scripts.lint) {
        packageJson.scripts.lint = 'eslint src --ext .ts,.tsx';
        console.log('✅ Added lint script');
        fixed = true;
    }

    if (!packageJson.scripts['type-check']) {
        packageJson.scripts['type-check'] = 'tsc --noEmit';
        console.log('✅ Added type-check script');
        fixed = true;
    }

    if (fixed) {
        // Create backup
        const backupPath = packageJsonPath + '.backup';
        fs.copyFileSync(packageJsonPath, backupPath);
        console.log('📄 Created backup:', path.basename(backupPath));

        // Write updated package.json
        fs.writeFileSync(packageJsonPath, JSON.stringify(packageJson, null, 2) + '\n');
        console.log('✅ Updated package.json');

        return true;
    } else {
        console.log('ℹ️ No fixes needed');
        return false;
    }
}

function main() {
    const args = process.argv.slice(2);
    const frontendPath = args[0] || 'frontend';
    const shouldFix = args.includes('--fix');

    console.log('🔍 Frontend Dependencies Validation Tool');
    console.log('==========================================');
    console.log(`Checking: ${frontendPath}`);
    console.log('');

    if (!fs.existsSync(frontendPath)) {
        console.log('❌ Frontend directory not found:', frontendPath);
        process.exit(1);
    }

    let allValid = true;

    // Validate package.json
    const packageJsonPath = path.join(frontendPath, 'package.json');
    if (!validatePackageJson(packageJsonPath)) {
        allValid = false;
    }

    console.log('');

    // Validate ESLint config
    if (!validateEslintConfig(frontendPath)) {
        allValid = false;
    }

    console.log('');

    // Validate TypeScript config
    const tsConfigPath = path.join(frontendPath, 'tsconfig.json');
    if (!validateTsConfig(tsConfigPath)) {
        allValid = false;
    }

    console.log('');

    // Fix issues if requested
    if (shouldFix) {
        console.log('🔧 Fix mode enabled');
        fixCommonIssues(frontendPath);
        console.log('');
    }

    // Final result
    console.log('==========================================');
    if (allValid) {
        console.log('🎉 Frontend configuration is valid!');
        process.exit(0);
    } else {
        console.log('💥 Frontend configuration has issues');
        if (!shouldFix) {
            console.log('💡 Try running with --fix to auto-fix common issues');
        }
        process.exit(1);
    }
}

if (require.main === module) {
    main();
}

module.exports = { validatePackageJson, validateEslintConfig, validateTsConfig, fixCommonIssues };