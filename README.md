# 📚 PubMed Alert

**English** · [中文](README.zh.md) · [日本語](README.ja.md)

Subscribe to new PubMed articles by keyword / journal / author, and get them emailed to you —
instantly or as a digest — annotated with the official JCR impact factor and quartile.

> Built for small-scale personal or small-group use, running locally, with no user-registration
> system. To move it to your own server later, just copy the folder over and install
> dependencies — no code changes needed.

---

## Features

- 🔍 Search new PubMed articles by keyword / journal / author (or write a raw advanced query)
- 📧 Sends notification emails via your own Gmail account
- ⏱ Each subscription has its own frequency: instant / daily / every 3 days / weekly digest
- 🏷 Emails are annotated with the official JCR impact factor and quartile (Q1–Q4)
- 🌐 A simple web UI to manage subscriptions (create/edit/delete, poll now, view articles)
- 🌏 Interface available in English / Chinese / Japanese — switch anytime, top-right corner
- ⚙️ Gmail and the NCBI API key are configured on the web Settings page (password encrypted at
  rest) — no config files to edit by hand

---

## Quick Start

### Option 1 — Run it yourself with Python

```bash
cd pubmed_alert
pip install -r requirements.txt
python run.py
```

Then open **http://127.0.0.1:8000** in your browser. The local database is created
automatically on first run.

### Option 2 — Use a pre-built program (no Python needed)

If someone shared a `PubMedAlert.exe` (Windows) or `PubMedAlert` (Mac) with you, just
double-click it — your browser opens automatically. See "Sharing with non-technical users"
below if you're the one building and sharing it.

### Configure Gmail sending

Open the app, click **Settings** in the top nav, fill in your Gmail address and App Password
(see below), then save. Use the "Send test email" button to verify it works.

---

## Gmail Setup

Gmail won't let a program send mail using your regular login password — you need a dedicated
**App Password**.

1. Open [myaccount.google.com/security](https://myaccount.google.com/security) and make sure
   **2-Step Verification** is turned on (required for App Passwords).
2. Open [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) and
   create a new App Password (name it anything, e.g. "PubMed Alert").
3. Copy the generated 16-character password into the Settings page, along with your Gmail
   address, then save.

⚠️ The password is stored encrypted in the local database. Never share `data/subscriptions.db`
or `data/app_secret.key`, and never paste the password into chat logs or screenshots.

---

## Impact Factor / JCR Quartile (optional)

PubMed itself has no impact-factor or quartile data. The official **Journal Citation Reports
(JCR)** is a paid Clarivate product, normally accessed via an institutional subscription. This
project never scrapes or bypasses that paywall — you need your own access.

1. Export that year's "Journal Impact Factor" report as a PDF from your institution's Web of
   Science / JCR access.
2. Place it in this project's `data/` folder.
3. Run:
   ```bash
   pip install pdfplumber
   python scripts/parse_jcr_pdf.py "data/JCR Journal Impact Factor 2026.pdf"
   ```
4. Restart the app — the yellow banner on the homepage disappears once it picks up the data.

Skipping this doesn't break anything else — emails just omit the impact-factor/quartile badge.
Re-export once a year when JCR updates. This is per-person: everyone generates their own cache
file from their own subscription access; nothing is shared or committed to git.

---

## How to Use

1. Open the homepage and click **New Subscription**.
2. Fill in keywords / journals / authors (one per line, any combination — leave blank to skip).
   For complex queries, use the "Advanced: raw PubMed query" field, which overrides the three
   above.
3. Fill in the recipient email and frequency, then save.
4. Click **Poll now** to search immediately — see results under **View articles** without
   waiting for the scheduled job.

A brand-new subscription's first check sends the **10 most relevant** articles from the **last
5 years**; every check after that only sends newly-published articles.

**Frequency semantics:**
- **immediate** — sends an email as soon as new articles are found.
- **daily / every_3_days / weekly** — batches newly-found articles into one digest email when
  due; if nothing new was found, no email is sent.

---

## Sharing with Non-Technical Users

If someone doesn't have (or doesn't want) Python, package the app into a standalone executable
with the scripts in `packaging/`. They just double-click the file and a browser tab opens
automatically — nothing else to install. **Each person runs their own independent copy**, with
its own database and Gmail config.

Building must happen on the target OS (PyInstaller can't cross-compile):

```powershell
# On Windows — produces dist\windows\PubMedAlert.exe
powershell -ExecutionPolicy Bypass -File packaging\build_windows.ps1
```

```bash
# On a Mac — produces dist/mac/PubMedAlert
chmod +x packaging/build_mac.sh
./packaging/build_mac.sh
```

Send just that one file. Recipients should put it in a new, empty folder (not Downloads or a
zip) before double-clicking — a `data/` folder appears next to it for the database. **macOS**:
Gatekeeper blocks unsigned programs, so the first run must be right-click → Open in Finder, not
a plain double-click.

Each recipient configures their own Gmail App Password and, optionally, their own JCR data —
see the sections above.
