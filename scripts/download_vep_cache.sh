#!/bin/bash
# Download VEP cache with resume support
# Run inside worker container: docker-compose exec worker bash /app/scripts/download_vep_cache.sh
#
# If download breaks, just run again - it will resume from where it left off

set -e

CACHE_DIR="/app/vep_cache"
VEP_VERSION=113
CACHE_URL="https://ftp.ensembl.org/pub/release-${VEP_VERSION}/variation/indexed_vep_cache/homo_sapiens_vep_${VEP_VERSION}_GRCh38.tar.gz"
CACHE_FILE="$CACHE_DIR/homo_sapiens_vep_${VEP_VERSION}_GRCh38.tar.gz"

echo "=== VEP Cache Download Script ==="
echo "Cache directory: $CACHE_DIR"
echo "This will download ~23GB, please be patient..."
echo ""

mkdir -p "$CACHE_DIR"
cd "$CACHE_DIR"

# Check if already extracted
if [ -d "homo_sapiens/${VEP_VERSION}_GRCh38" ]; then
    echo "VEP cache already exists!"
    ls -la "homo_sapiens/${VEP_VERSION}_GRCh38" | head -10
    exit 0
fi

# Download with resume support (-C -)
echo "Downloading VEP cache (with resume support)..."
echo "If connection breaks, run this script again to resume."
echo ""
curl -C - -O "$CACHE_URL"

echo ""
echo "Extracting cache (this takes a while)..."
tar -xzf "homo_sapiens_vep_${VEP_VERSION}_GRCh38.tar.gz"

echo "Cleaning up..."
rm -f "homo_sapiens_vep_${VEP_VERSION}_GRCh38.tar.gz"

echo ""
echo "=== VEP cache installed successfully ==="
echo "Cache location: $CACHE_DIR/homo_sapiens/${VEP_VERSION}_GRCh38"
ls -la "$CACHE_DIR/homo_sapiens/${VEP_VERSION}_GRCh38" | head -20
