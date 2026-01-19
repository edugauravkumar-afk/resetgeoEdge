#!/bin/bash
# Script to run the GeoEdge Projects Streamlit Dashboard

# Load environment variables
set -a
source .env
set +a

# Run the Streamlit app
streamlit run streamlit_app.py --server.port 8501 --server.address localhost