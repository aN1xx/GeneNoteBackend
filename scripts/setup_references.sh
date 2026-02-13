#!/bin/bash
# Setup script for pipeline reference files
# These files are too large for git (~8GB) and must be downloaded separately

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
REFERENCES_DIR="$PROJECT_DIR/pipeline/references"

echo "=== GeneNote Pipeline References Setup ==="
echo "Target directory: $REFERENCES_DIR"
echo ""

# Check if references already exist
if [ -d "$REFERENCES_DIR/GRCh38" ] && [ "$(ls -A $REFERENCES_DIR/GRCh38 2>/dev/null)" ]; then
    echo "References already exist. Skipping download."
    echo "To re-download, remove $REFERENCES_DIR/GRCh38 first."
    exit 0
fi

echo "Reference files required:"
echo "  - GRCh38/ (Reference genome ~3GB)"
echo "  - gene_intervals/ (BED files for target regions)"
echo "  - Quasar-BRCA_intervals/ (BRCA panel intervals)"
echo "  - primers_Quasar-BRCA/ (Primer sequences)"
echo ""

# Option 1: Copy from existing location (for local development)
if [ -n "$PIPELINE_REFERENCES_SOURCE" ]; then
    echo "Copying from $PIPELINE_REFERENCES_SOURCE..."
    cp -r "$PIPELINE_REFERENCES_SOURCE"/* "$REFERENCES_DIR/"
    echo "Done!"
    exit 0
fi

# Option 2: Download from URL (configure your own source)
# Uncomment and configure if you have references hosted somewhere
# REFERENCES_URL="https://your-storage.com/references.tar.gz"
# echo "Downloading from $REFERENCES_URL..."
# curl -L "$REFERENCES_URL" | tar -xz -C "$REFERENCES_DIR"

echo ""
echo "=== Manual Setup Required ==="
echo ""
echo "Please copy reference files manually:"
echo ""
echo "Option A - Copy from existing pipeline:"
echo "  export PIPELINE_REFERENCES_SOURCE=/path/to/Pipeline_Semi-Auto/references"
echo "  ./scripts/setup_references.sh"
echo ""
echo "Option B - Copy manually:"
echo "  cp -r /path/to/references/* $REFERENCES_DIR/"
echo ""
echo "Required structure:"
echo "  $REFERENCES_DIR/"
echo "  ├── GRCh38/"
echo "  │   ├── GRCh38.fa"
echo "  │   ├── GRCh38.fa.fai"
echo "  │   └── ... (BWA index files)"
echo "  ├── gene_intervals/"
echo "  ├── Quasar-BRCA_intervals/"
echo "  └── primers_Quasar-BRCA/"
