#!/bin/bash
# Download and prepare reference files for the variant calling pipeline
# Run this script once before first deployment
#
# Total size: ~8-10 GB
# Time: ~30-60 min depending on internet speed

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
REFS_DIR="$PROJECT_DIR/pipeline/references"

echo "=== GeneNote Reference Files Download Script ==="
echo "Project directory: $PROJECT_DIR"
echo "References directory: $REFS_DIR"
echo ""

# Create directories
mkdir -p "$REFS_DIR/GRCh38/fasta_and_index"
mkdir -p "$REFS_DIR/GRCh38/index_bwa-mem"

cd "$REFS_DIR/GRCh38/fasta_and_index"

# 1. Download GRCh38 reference genome from Ensembl
echo "=== Step 1/4: Downloading GRCh38 reference genome (~900MB compressed) ==="
if [ ! -f "GRCh38.fa" ]; then
    wget -c "https://ftp.ensembl.org/pub/release-113/fasta/homo_sapiens/dna/Homo_sapiens.GRCh38.dna.primary_assembly.fa.gz" \
        -O GRCh38.fa.gz
    echo "Decompressing..."
    gunzip -k GRCh38.fa.gz
    mv Homo_sapiens.GRCh38.dna.primary_assembly.fa GRCh38.fa 2>/dev/null || true
else
    echo "GRCh38.fa already exists, skipping download"
fi

# 2. Create FASTA index
echo ""
echo "=== Step 2/4: Creating FASTA index ==="
if [ ! -f "GRCh38.fa.fai" ]; then
    samtools faidx GRCh38.fa
else
    echo "GRCh38.fa.fai already exists, skipping"
fi

# 3. Create sequence dictionary for GATK
echo ""
echo "=== Step 3/4: Creating sequence dictionary for GATK ==="
if [ ! -f "GRCh38.dict" ]; then
    gatk CreateSequenceDictionary -R GRCh38.fa
else
    echo "GRCh38.dict already exists, skipping"
fi

# 4. Create BWA index
echo ""
echo "=== Step 4/4: Creating BWA-MEM index (~1 hour) ==="
cd "$REFS_DIR/GRCh38/index_bwa-mem"
if [ ! -f "GRCh38.bwt" ]; then
    echo "This step takes approximately 1 hour..."
    bwa index -p GRCh38 "$REFS_DIR/GRCh38/fasta_and_index/GRCh38.fa"
else
    echo "BWA index already exists, skipping"
fi

echo ""
echo "=== Download complete! ==="
echo ""
echo "Reference files location: $REFS_DIR"
echo ""
echo "Files created:"
ls -lh "$REFS_DIR/GRCh38/fasta_and_index/"
echo ""
ls -lh "$REFS_DIR/GRCh38/index_bwa-mem/"
echo ""
echo "You can now run: docker compose --profile full up -d"
