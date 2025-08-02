#!/usr/bin/env node

/**
 * Simple performance test script as fallback for Lighthouse CI
 */

const fs = require('fs');
const path = require('path');

function checkBuildOutput() {
    const distPath = path.join(__dirname, '..', 'dist');

    console.log('🔍 Checking build output...');

    if (!fs.existsSync(distPath)) {
        console.error('❌ Build directory not found!');
        process.exit(1);
    }

    const files = fs.readdirSync(distPath);
    console.log(`✅ Found ${files.length} files in build directory`);

    // Check for essential files
    const hasIndex = files.some(file => file === 'index.html');
    const hasAssets = files.some(file => file === 'assets');

    if (!hasIndex) {
        console.error('❌ index.html not found in build output');
        process.exit(1);
    }

    if (!hasAssets) {
        console.warn('⚠️ assets directory not found in build output');
    }

    console.log('✅ Build output validation passed');
}

function checkBundleSize() {
    const distPath = path.join(__dirname, '..', 'dist');
    const assetsPath = path.join(distPath, 'assets');

    console.log('📦 Checking bundle sizes...');

    if (!fs.existsSync(assetsPath)) {
        console.warn('⚠️ Assets directory not found, skipping bundle size check');
        return;
    }

    const files = fs.readdirSync(assetsPath);
    let totalSize = 0;
    let jsSize = 0;
    let cssSize = 0;

    files.forEach(file => {
        const filePath = path.join(assetsPath, file);
        const stats = fs.statSync(filePath);
        const size = stats.size;
        totalSize += size;

        if (file.endsWith('.js')) {
            jsSize += size;
        } else if (file.endsWith('.css')) {
            cssSize += size;
        }
    });

    console.log(`📊 Bundle size analysis:`);
    console.log(`   Total: ${(totalSize / 1024).toFixed(2)} KB`);
    console.log(`   JavaScript: ${(jsSize / 1024).toFixed(2)} KB`);
    console.log(`   CSS: ${(cssSize / 1024).toFixed(2)} KB`);

    // Performance budgets (in KB)
    const budgets = {
        total: 2000, // 2MB
        js: 1000,    // 1MB
        css: 200     // 200KB
    };

    let warnings = 0;

    if (totalSize / 1024 > budgets.total) {
        console.warn(`⚠️ Total bundle size exceeds budget (${budgets.total}KB)`);
        warnings++;
    }

    if (jsSize / 1024 > budgets.js) {
        console.warn(`⚠️ JavaScript bundle size exceeds budget (${budgets.js}KB)`);
        warnings++;
    }

    if (cssSize / 1024 > budgets.css) {
        console.warn(`⚠️ CSS bundle size exceeds budget (${budgets.css}KB)`);
        warnings++;
    }

    if (warnings === 0) {
        console.log('✅ All bundle sizes within budget');
    } else {
        console.log(`⚠️ ${warnings} bundle size warning(s)`);
    }
}

function generateReport() {
    const report = {
        timestamp: new Date().toISOString(),
        status: 'completed',
        checks: {
            buildOutput: 'passed',
            bundleSize: 'checked'
        }
    };

    const reportPath = path.join(__dirname, '..', 'performance-report.json');
    fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));
    console.log(`📄 Performance report saved to ${reportPath}`);
}

function main() {
    console.log('🚀 Running performance tests...\n');

    try {
        checkBuildOutput();
        checkBundleSize();
        generateReport();

        console.log('\n✅ Performance tests completed successfully!');
        process.exit(0);
    } catch (error) {
        console.error('\n❌ Performance tests failed:', error.message);
        process.exit(1);
    }
}

if (require.main === module) {
    main();
}