# Twilio Campaign Manager

Desktop application for sending bulk personalized WhatsApp messages via Twilio Content API. Built with Python, CustomTkinter, and the Twilio SDK.

## Features

- **Multi-threaded sending** — send thousands of messages with pause/resume/cancel/retry
- **Content Templates** — use Twilio-approved WhatsApp content templates with variable substitution
- **Recipient import** — CSV, Excel, JSON, or paste data; auto-detect phone column and map variables
- **Results & export** — view delivery status per recipient, check real-time status from Twilio, export to CSV/Excel
- **i18n** — full Spanish and English UI, toggle in sidebar
- **Dashboard** — campaign stats, delivery rates, performance metrics
- **Encrypted credentials** — Fernet+PBKDF2 encrypted storage for Twilio secrets

## Requirements

- Python 3.10+
- Twilio Account with WhatsApp-approved Content Template and Sender number
- `pip install -r requirements.txt`

## Setup

1. Clone the repo
2. Install dependencies: `pip install -r requirements.txt`
3. Run the app: `python main.py`
4. Go to **Settings** → enter your Twilio credentials and Default Sender (`whatsapp:+57XXXXXXXXX`)
5. Click **Save Settings**, then **Test Connection**

## Usage

1. **Templates** → create templates with your Twilio Content SID and variables
2. **Campaigns** → create a campaign linked to a template, import recipients
3. **Map columns** → map imported columns to template variables
4. **Send** → start sending with real-time progress
5. **Results** → refresh delivery status to see delivered/undelivered/read

## Tech Stack

Python, CustomTkinter, Twilio SDK, SQLite (WAL mode), ThreadPoolExecutor, Fernet encryption
