# Setup script for the OSINT Threat Monitoring prototype (Windows PowerShell)
# Run with: .\setup.ps1

Write-Host "=== OSINT Threat Monitoring - Environment Setup ===" -ForegroundColor Cyan

# Create virtual environment
Write-Host "`n[1/4] Creating virtual environment..." -ForegroundColor Yellow
python -m venv venv
if (-not $?) { Write-Host "ERROR: Failed to create venv. Is Python installed?" -ForegroundColor Red; exit 1 }

# Activate
Write-Host "[2/4] Activating virtual environment..." -ForegroundColor Yellow
.\venv\Scripts\Activate.ps1

# Install dependencies
Write-Host "[3/4] Installing Python dependencies..." -ForegroundColor Yellow
pip install --upgrade pip --quiet
pip install -r requirements.txt

# Download NLP models
Write-Host "[4/4] Downloading NLP models..." -ForegroundColor Yellow
python -m spacy download en_core_web_sm
python -c "import nltk; nltk.download('vader_lexicon', quiet=True); nltk.download('punkt', quiet=True); nltk.download('stopwords', quiet=True); print('NLTK data downloaded.')"

Write-Host "`n=== Setup complete! ===" -ForegroundColor Green
Write-Host "Activate the venv with: .\venv\Scripts\Activate.ps1" -ForegroundColor Cyan
Write-Host "Then launch Jupyter with: jupyter notebook notebooks/threat_monitoring.ipynb" -ForegroundColor Cyan
