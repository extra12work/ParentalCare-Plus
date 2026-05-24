# ParentalCare+
A privacy-first, local-endpoint governance agent designed to provide digital safety for minors while fostering trust and autonomy.

## 🚀 Overview
ParentalCare+ is an advanced endpoint security application built in Python that moves away from traditional, authoritarian "silent kill" parental controls. Instead, it utilizes a **Micro-Negotiation Protocol** to manage digital screen time and content safety.

## ✨ Key Features
- **Zero-Cloud Privacy:** All telemetry, logs, and evidence remain on the local machine using an encrypted SQLite database.
- **Micro-Negotiation Protocol:** Intercepts process termination to allow minors to formally request time extensions.
- **Anti-Tampering Watchdog:** A concurrent background daemon that prevents bypass attempts via Task Manager.
- **Heuristic Threat Detection:** Uses Levenshtein distance algorithms to detect phishing sites locally.
- **Distributed Control:** Integration with Telegram Bot API for real-time remote parental approval.

## 🛠️ Tech Stack
- **Language:** Python 3.x
- **GUI:** CustomTkinter & Matplotlib
- **Persistence:** SQLite & SQLAlchemy
- **System Control:** psutil, uiautomation, keyboard
- **Networking:** Telegram Bot API, requests

## 📂 Project Structure
- `app/controllers/`: Core logic (Security Engine, Web Filter, Keylogger)
- `app/ui/`: CustomTkinter interface components
- `app/models/`: Database schema and ORM models
- `data/`: Local SQLite database and JSON configuration files

## 🛡️ Academic Disclaimer
This project was developed as a B.Tech Major Project in Information Technology and is intended for educational purposes regarding endpoint governance and HCI research.
