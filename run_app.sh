#!/usr/bin/env bash
# ==============================================================================
# Script Peluncur Aplikasi Streamlit Inspeksi & Grading Smartphone AI
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo "============================================================"
echo "🚀 Memulai Aplikasi Streamlit Inspeksi Cacat Smartphone AI..."
echo "============================================================"

# Cek Python Environment
if [ -f "$ROOT_DIR/.venv/bin/streamlit" ]; then
    STREAMLIT_CMD="$ROOT_DIR/.venv/bin/streamlit"
elif command -v streamlit &> /dev/null; then
    STREAMLIT_CMD="streamlit"
else
    echo "❌ Error: Streamlit tidak ditemukan. Silakan jalankan: pip install -r requirements.txt"
    exit 1
fi

echo "Direktori Kerja: $SCRIPT_DIR"
echo "Menggunakan Streamlit: $STREAMLIT_CMD"
echo "Port: 8501"
echo "Buka browser Anda di: http://localhost:8501"
echo "============================================================"

cd "$SCRIPT_DIR"
exec "$STREAMLIT_CMD" run app.py --server.port 8501 --server.address 0.0.0.0
