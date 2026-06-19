# FixMate AI

FixMate AI is a read-only, cross-platform IT support dashboard for Windows and Ubuntu. It combines system health checks, network diagnostics, and a local error-screenshot analyzer with safe, evidence-based guidance.

## Features

- CPU, memory, disk, operating-system, boot-time, and top-process metrics
- Threshold-based system issue detection and health scoring
- Active network interfaces, traffic counters, connectivity, and latency diagnostics
- SQLite history with additive, non-destructive migrations
- Local PNG/JPG/JPEG screenshot analysis up to 5 MB
- OpenCV grayscale, contrast, denoising, and optional threshold preprocessing
- Local Tesseract OCR with editable extracted text
- Deterministic matching against 15 curated Windows and Ubuntu problems
- Confidence scores, matching evidence, and safe troubleshooting steps
- Privacy redaction before OCR text is stored

FixMate AI never requires administrator/root access, executes repairs, scans ports, captures packets, runs screenshot text, or stores uploaded screenshot files.

## Requirements

- Python 3.11 or newer
- Windows 10/11 or a current Ubuntu release
- Tesseract OCR is optional but required for automatic text extraction

The main system-health and network dashboard works normally without Tesseract. The analyzer still permits manual error-text entry when OCR is unavailable.

## Windows setup

Open PowerShell in the `fixmate-ai` directory:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

If your prompt is at `D:\FixMateAI`, first run:

```powershell
cd .\fixmate-ai
```

### Windows Tesseract installation

1. Install a trusted current Windows build of Tesseract OCR.
2. During installation, note the executable path. A common location is:

   ```text
   C:\Program Files\Tesseract-OCR\tesseract.exe
   ```

3. Add the Tesseract directory to `PATH`, or set the explicit command location:

   ```powershell
   setx TESSERACT_CMD "C:\Program Files\Tesseract-OCR\tesseract.exe"
   ```

4. Open a new PowerShell window and verify:

   ```powershell
   tesseract --version
   ```

`TESSERACT_CMD` is useful when Tesseract is installed but intentionally not added to the global `PATH`.

## Ubuntu setup

```bash
sudo apt update
sudo apt install python3.11 python3.11-venv tesseract-ocr
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Verify OCR installation with:

```bash
tesseract --version
```

The `sudo` commands install system packages only; running FixMate AI does not require root privileges.

## Using the Error Screenshot Analyzer

1. Open **Error Screenshot Analyzer** from Streamlit's page navigation.
2. Review the privacy warning and upload a PNG, JPG, or JPEG no larger than 5 MB.
3. Compare the original and processed previews. Disable thresholding if colored text becomes less readable.
4. Select **Extract text with local OCR**, or type the message manually if Tesseract is unavailable.
5. Correct OCR mistakes in the editable text box.
6. Select **Analyze error text** to view ranked reliable matches.

If no result reaches the 60% confidence threshold, the page displays **No reliable match found** and does not invent a solution.

## Network diagnostics

Open the **Network Diagnostics** tab to configure a host, TCP port, short timeout, and high-latency threshold. The test performs one TCP connection; it is not a port scan. Traffic counters are cumulative operating-system counters.

## Tests

```bash
python -m pytest
```

Tests generate images in memory and mock OCR and network operations. They require neither Tesseract nor internet access.

## Data and privacy

History is stored locally in `data/fixmate.db`, which is ignored by Git. Screenshot files and image bytes are never written to the database or filesystem.

Before OCR text is stored, FixMate AI redacts likely:

- Passwords, API keys, tokens, and bearer values
- Email addresses
- Windows and Linux user-specific paths

Redaction is best-effort and cannot guarantee that every personal detail will be recognized. Crop or redact screenshots before upload and avoid screenshots containing secrets. Processing is local, but the editable text remains visible in the current Streamlit session.

## Missing OCR troubleshooting

If the analyzer reports that Tesseract is unavailable:

1. Confirm `tesseract --version` works in a new terminal.
2. Restart Streamlit after installing Tesseract or changing `PATH`.
3. On Windows, set `TESSERACT_CMD` to the complete executable path.
4. Continue by entering the error message manually; the rest of the analyzer does not depend on Tesseract.

## Project structure

- `app.py` — Phase 1 and Phase 2 Streamlit dashboard
- `pages/2_Error_Screenshot_Analyzer.py` — Phase 3 analyzer page
- `src/image_processing.py` — validation and OpenCV preprocessing
- `src/ocr.py` — optional local Tesseract integration
- `src/error_matcher.py` — deterministic confidence-ranked matching
- `src/knowledge_base.py` — trusted JSON loader
- `src/privacy.py` — anonymization and redaction
- `data/error_knowledge_base.json` — curated local troubleshooting entries
- `src/database.py` — additive migrations and persistence for all phases
- `tests/` — simulated, generated, and mocked automated tests

## Current limitations

- OCR accuracy depends on screenshot resolution, font, contrast, language, and Tesseract quality.
- The knowledge base covers common errors but is not a general diagnostic engine.
- Confidence is deterministic heuristic evidence, not a statistical probability.
- Redaction is best-effort; users should remove sensitive information before uploading.
- Connectivity represents one configured TCP target, and network byte counters are cumulative.

