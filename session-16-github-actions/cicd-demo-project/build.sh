#!/bin/bash
# Packages the application into build/ with build metadata (uploaded as a CI artifact).
set -euo pipefail

VERSION="${APP_VERSION:-$(git rev-parse --short HEAD 2>/dev/null || echo dev)}"

echo "================================="
echo "Starting Application Build ($VERSION)"
echo "================================="
rm -rf build
mkdir -p build
cp -r app requirements.txt build/
find build -name '__pycache__' -prune -exec rm -rf {} +

cat > build/build-info.txt <<INFO
Application: Session 16 Calculator API
Version: ${VERSION}
Build Status: SUCCESS
Build Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)
Built By: ${GITHUB_ACTOR:-local}
Run: ${GITHUB_RUN_NUMBER:-local}
INFO

tar -czf "calculator-${VERSION}.tar.gz" -C build .
mv "calculator-${VERSION}.tar.gz" build/

echo ""
echo "Build files:"
ls -la build
echo ""
echo "Build completed successfully."
