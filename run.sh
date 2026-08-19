#!/bin/zsh
cd ~/weibull-reliability-dashboard
source venv/bin/activate
export SSL_CERT_FILE=$(python -c "import certifi; print(certifi.where())")
streamlit run app.py
