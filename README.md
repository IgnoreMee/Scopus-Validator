# Scopus Journal Validator Pipeline 🔍

An automated web scraping and data processing tool designed to quickly verify the active status and coverage years of academic journals on Scopus. 

## Features
* **Single Search UI:** Instantly verify individual ISSNs via a Streamlit web interface.
* **Bulk Processing Engine:** Upload an Excel (`.xlsx`) file containing multiple ISSNs, and the bot will process them sequentially in the background.
* **Format Validation:** Built-in Regex checking to prevent pipeline crashes from malformed data inputs.
* **Auto-Export:** Generates a downloadable Excel report with appended scraping results.

## Tech Stack
* **Frontend:** Streamlit
* **Automation Engine:** Selenium WebDriver (Chrome)
* **Data Processing:** Pandas

## Setup & Installation

**1. Clone the repository or download the folder.**

**2. Set up a Python Virtual Environment**
It is highly recommended to run this inside a virtual environment to manage dependencies.
```bash
python -m venv venv