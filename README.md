# 📚 PubMed Alert

**English** · [中文](README.zh.md) · [日本語](README.ja.md)

Subscribe to new PubMed articles by keyword / journal / author, and get them emailed to you —
instantly or as a digest — annotated with the official JCR impact factor and quartile.

> Built for small-scale personal or small-group use — run it locally or deploy it to your own
> server, no code changes needed either way. Multiple people can each register their own account
> and keep their own subscriptions and sender email separate from everyone else's.

---

## Features

- 🔍 Search new PubMed articles by keyword / journal / author (or write a raw advanced query) —
  separate multiple entries with a newline, comma, 、, or semicolon
- 📧 Sends notification emails via your own email account (Gmail / QQ Mail / 163 Mail / Outlook, or any other SMTP mailbox)
- ⏱ Each subscription has its own frequency: instant / daily / every 3 days / weekly digest
- 🏷 Emails are annotated with the official JCR impact factor and quartile (Q1–Q4)
- 🌐 A simple web UI to manage subscriptions (create/edit/delete, poll now, view articles), with a
  search box and 1–5 star reading-priority ratings for saved articles
- 📑 Export any subscription's articles or your whole reading list as an RIS citation file
  (EndNote / Zotero / Mendeley compatible)
- 📄 Open-access full-text PDF links, added automatically when available (via Unpaywall)
- 🔁 A note when the same article matches more than one of your subscriptions, so you know it's
  not a mistake if you see it twice
- 💾 One-click JSON export/backup of your subscriptions and discovered articles
- 🌏 Interface available in English / Chinese / Japanese — switch anytime, top-right corner
- ⚙️ The sender account and the NCBI API key are configured on the web Settings page (password
  encrypted at rest) — no config files to edit by hand
- 🔐 Multiple people can register their own accounts — each only sees/manages their own
  subscriptions, with their own independent sender email settings

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

### Register an account

Whether run locally or as a packaged app, the first thing you'll see is a registration page —
a **username**, email, password, and an **invite code**. You don't need to invent the invite code
yourself: one is auto-generated on first launch and saved to `data/invite_code.txt` — open that
file and copy it in. After submitting, you'll get a verification code by email (valid 10 minutes)
— enter it to finish registering. That email is sent via a **system sender account** the deployer
configures in `.env` (`SYSTEM_SENDER_EMAIL`/`SYSTEM_SENDER_PASSWORD`/etc., see the comments in
`.env`) — separate from your own personal sender-email settings — so it must be set up first or
registration will fail.

If this device already has subscriptions/settings from before (e.g. upgrading from an older
version), **the first account to successfully register adopts all of that pre-existing data
automatically** — so register your own account first right after upgrading, before sharing the
invite code with anyone else. After that, everyone registers their own account and can't see
each other's subscriptions.

Log in with either your username or email. Forgot your password? Use the "Forgot password?"
link on the login page — also reset via an emailed verification code.

### Configure the sender account

Once registered/logged in, click **Settings** in the top nav, pick your provider from the
**Email provider** dropdown (Gmail / QQ Mail / 163 Mail / Outlook, or "Custom" to fill in an SMTP
server by hand), fill in your address and password/auth code (see below), then save. Use the
"Send test email" button to verify it works. Each account's sender settings are independent and
don't affect anyone else's.

---

## Email Setup

⚠️ The password is stored encrypted in the local database. Never share `data/subscriptions.db`
or `data/app_secret.key`, and never paste the password into chat logs or screenshots.

### Gmail

Gmail won't let a program send mail using your regular login password — you need a dedicated
**App Password**.

1. Open [myaccount.google.com/security](https://myaccount.google.com/security) and make sure
   **2-Step Verification** is turned on (required for App Passwords).
2. Open [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) and
   create a new App Password (name it anything, e.g. "PubMed Alert").
3. Copy the generated 16-character password into the "Password / Auth code" field on the
   Settings page, along with your Gmail address, then save.

### QQ Mail / 163 Mail

Neither accepts your regular login password for sending mail — you need to enable SMTP access
in the webmail settings and generate a **client authorization code**, then use that code (not
your login password) in the "Password / Auth code" field.

- QQ Mail: log into webmail → Settings → Account → enable "POP3/SMTP service" → verify via SMS
  to generate the authorization code.
- 163 Mail: log into webmail → Settings → POP3/SMTP/IMAP → enable the service → generate a
  client authorization password.

Once you pick the matching provider on the Settings page, the SMTP host and port are filled in
automatically — you only need to enter the email address and that authorization code.

### Outlook / Microsoft 365

Your normal Outlook login password works (if the account has two-factor auth enabled, generate
an app password instead at [account.microsoft.com/security](https://account.microsoft.com/security)).

### Other providers

Pick "Custom" from the **Email provider** dropdown on the Settings page, then fill in that
provider's SMTP host and port by hand, checking "Use SSL" or not based on its docs — port 465
usually needs SSL, port 587 usually needs STARTTLS (leave unchecked). Check that provider's own
SMTP setup documentation for the exact values.

---

## Impact Factor / JCR Quartile

PubMed itself has no impact-factor or quartile data. This project ships with a pre-parsed
snapshot of the official **Journal Citation Reports (JCR)** data (`data/jcr_cache.csv`), used
automatically — nothing to set up.

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
5 years** plus the **20 most recent** overall (overlaps deduplicated) as a "starter" batch —
both the web UI and the email tag which article(s) are "most relevant" vs. "most recent"; every
check after that only sends newly-published articles.

**Frequency semantics:**
- **immediate** — sends an email as soon as new articles are found.
- **daily / every_3_days / weekly** — batches newly-found articles into one digest email when
  due; if nothing new was found, no email is sent.

**Reading list**: from any subscription's "View articles" page, save articles you're interested
in to a unified reading list spanning all your subscriptions (there's a nav link for it) — mark
them read, remove them, rate them 1–5 stars, search by title/journal/author, or export the whole
list (or a single subscription's articles) as an RIS citation file. Alert emails also include a
"select articles to add to your reading list" link that needs no login — it opens a (also
login-free) page listing that email's articles with checkboxes, so you can pick which ones to
save in one submission. That email link only appears once the deployer sets `APP_BASE_URL` in
`.env` (the app can't otherwise know its own externally-reachable address); without it, emails
still send normally, just without that link.

**Open-access full text**: when a newly-found article has a free full-text PDF available (looked
up via [Unpaywall](https://unpaywall.org/)), a link to it is shown next to the article on the web
and in the email — no setup needed. If the same article happens to match more than one of your
subscriptions, both emails still get sent, but each is annotated with a small note so you know
it's not a mistake.

**Personal backup**: the Settings page has an "Export my data (backup)" button that downloads all
your subscriptions and discovered articles as a single JSON file, for your own backup/records.

**Closing the browser tab ≠ quitting the app**: it needs to keep running in the background to
check and send on your configured schedule. Closing the browser tab alone doesn't stop it —
that's expected, nothing to worry about. To actually stop it: for the packaged app, `Cmd+Q` or
right-click its Dock icon → Quit; for `python run.py`, go back to that terminal and press
`Ctrl+C`. Either way, reopening it later is always safe — if it's already running in the
background, it just brings the browser back to it instead of erroring or starting a second copy.

---

## Sharing with Non-Technical Users

If someone doesn't have (or doesn't want) Python, package the app into a standalone executable
with the scripts in `packaging/`. They just double-click the file and a browser tab opens
automatically — nothing else to install. **Each person runs their own independent copy**, with
its own database; alternatively, deploy the app to one server and have everyone register their
own account there instead (see "Register an account" above) — both work, pick whichever fits
better: separate computers each running their own copy, or one shared address everyone logs into.

⚠️ If deploying to a server for multiple people: **don't expose it directly to the public
internet**. Since registration is open (anyone who knows the address and has the invite code can
sign up), you still need Tailscale / an SSH tunnel / a VPN — some way to restrict who can even
reach the address. The invite code is an extra safety net, not a replacement for that network
isolation.

Building must happen on the target OS (PyInstaller can't cross-compile):

```powershell
# On Windows — produces dist\windows\PubMedAlert.exe
powershell -ExecutionPolicy Bypass -File packaging\build_windows.ps1
```

```bash
# On a Mac — produces dist/mac/PubMedAlert.app and dist/mac/PubMedAlert.zip
chmod +x packaging/build_mac.sh
./packaging/build_mac.sh
```

**Windows**: send just the `PubMedAlert.exe` file. Recipients should put it in a new, empty
folder (not Downloads or a zip) before double-clicking — a `data/` folder appears next to it for
the database.

**Mac**: send the `PubMedAlert.zip` file (not the unzipped `.app` — zipping keeps its internal
structure intact). Recipients: unzip → right-click `PubMedAlert.app` → "Open" → confirm "Open"
again in the security prompt. After that it's a normal Mac app — plain double-clicking works,
**no terminal window appears**, and the browser opens automatically. The one-time right-click is
unavoidable without a paid Apple Developer signature ($99/year); the build script does apply a
local ad-hoc signature, which at least avoids the more confusing "app is damaged" error that
unsigned apps otherwise hit on Apple Silicon.

Each recipient configures their own sender account password/auth code and, optionally, their own JCR data —
see the sections above.
