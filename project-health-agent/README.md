# Project Health Agent

A full-stack, AI-powered system designed for Professional Services teams that ingests `.xlsx` project plans, dynamically computes auditable RAG statuses using an advanced deterministic engine, leverages LLMs for intelligent reasoning, and auto-generates monthly executive PowerPoint presentations.

## Table of Contents
1. [Overview & End-to-End Flow](#overview--end-to-end-flow)
2. [Tech Stack & Libraries](#tech-stack--libraries)
3. [Architecture Details](#architecture-details)
4. [Signal Extraction Engine](#signal-extraction-engine)
5. [Setup Instructions](#setup-instructions)

---

## Overview & End-to-End Flow

The Project Health Agent acts as a completely automated analyst for your project portfolio. Instead of manually reading dozens of messy Excel sheets, a Project Manager can simply upload them to the system and immediately receive standardized health scores.

### The Complete Flow:
1. **Upload via React UI**: A user navigates to the Dashboard and uploads an `.xlsx` project plan.
2. **Dynamic Ingestion (`loader.py`)**: The FastAPI backend parses the Excel file using `pandas`. It intelligently scans for the correct tab (e.g., "Tracker", "Status", "Data") and wraps the data securely in a buffer for processing.
3. **Smart Schema Mapping (`schema_mapper.py`)**: Because real-world spreadsheets are messy and inconsistent, a heuristic mapper uses a predefined dictionary of common column synonyms (e.g., "Critical ?", "Task Name", "Status Comment", "ETC") to standardize the data against our internal schema.
4. **Database Storage (`models.py`)**: The raw project metadata and its mapped schema are stored in a SQLite database (`project_health.db`) using `SQLModel`.
5. **Signal Extraction Pipeline**: When "Run Analysis" is triggered, 5 independent extractors crunch the data:
   - **Schedule Slippage**: Computes % of overdue tasks and penalizes for critical path delays.
   - **Budget Burn**: Calculates CPI (Earned Value / Actual Cost) and overall burn rate.
   - **Milestone Health**: Calculates SPI and tracks on-time completion percentage.
   - **Blockers**: A deterministic severity-age scoring model that penalizes older, higher-severity issues.
   - **Stakeholder Sentiment**: Classifies free-text status updates via Google's Gemini Flash 2.5 LLM into positive/neutral/negative and aggregates an overall sentiment score.
6. **RAG Classification Engine (`classifier.py`)**: A deterministic mathematical model calculates a final score (0-100) and assigns a Red, Amber, or Green status based on strict thresholds. If data is missing (e.g., a spreadsheet has no budget columns), the engine gracefully degrades, redistributing weights to available signals and outputting a "Data Confidence" percentage.
7. **LLM Reasoning (`reasoning.py`)**: The computed metrics are fed into Gemini Flash 2.5 to generate a grounded, plain-English explanation for the score—explaining *why* the project is healthy or failing based strictly on the math.
8. **Interactive Glassmorphism Dashboard**: The frontend polls this data and renders an incredibly immersive, premium UI utilizing `framer-motion` for staggered reveals, typewriter text effects for the AI output, and interactive background gradients.
9. **Executive Synthesis (`synthesis.py`)**: Once a month, the system analyzes all historical snapshots across the entire portfolio, prompts the LLM to identify cross-project patterns (e.g., "Systemic schedule delays"), and utilizes `python-pptx` to auto-generate a 7-slide `.pptx` presentation.

---

## Tech Stack & Libraries

### Backend
- **Python 3.11+**: Core language.
- **FastAPI**: Provides robust, highly performant REST APIs with native async support and automatic Swagger UI docs.
- **SQLModel & SQLAlchemy**: Serves as the ORM to manage the SQLite database, providing type-safe SQL queries.
- **SQLite**: A lightweight relational database for storing Projects, Snapshots, Blockers, and Monthly Reports.
- **Pandas**: Crucial for heavy data manipulation, reading `.xlsx` files, and processing dataframe logic.
- **Openpyxl**: Engine used by pandas to read Excel documents.
- **Uvicorn**: Lightning-fast ASGI server to run the FastAPI application.
- **APScheduler**: Handles background cron jobs for the automated weekly analysis runs.
- **python-pptx**: Programmatically generates native Microsoft PowerPoint files for the monthly synthesis.
- **Google GenAI / Anthropic SDK**: Used to connect to the Gemini 2.5 Flash model for sentiment analysis and text generation.

### Frontend
- **React 18 & Vite**: Lightning-fast frontend build tooling and UI library.
- **TypeScript**: Ensures type safety across components and API responses.
- **Tailwind CSS**: Utility-first CSS framework used for layout and typography.
- **Framer Motion**: Powers the complex UI interactions, such as the glowing orbs background, typewriter text effects, and the "System Analyzing" sequence.
- **Lucide React**: Premium, consistent icon library used throughout the dashboard.
- **Shadcn UI**: Unstyled, accessible UI components (Cards, Badges, Inputs, Buttons) that were heavily customized to create a dark-mode "Glassmorphism" design system.
- **Recharts**: Renders the historical trend charts for project health scores.
- **React Router DOM**: Handles client-side navigation between the Dashboard and Project Detail views.

---

## Architecture Details

### Why a Hybrid Deterministic + LLM Approach?
Pure-LLM classification is often non-deterministic, hard to audit, and prone to hallucination. By using a **deterministic scoring engine** to compute the RAG color, and an **LLM reasoning layer** to explain the math in plain English, we get the best of both worlds: auditable compliance with project management standards *and* executive-friendly summaries.

### Why EVM (Earned Value Management) for SPI/CPI?
CPI (Cost Performance Index) and SPI (Schedule Performance Index) are industry-standard metrics that normalize performance across projects of varying sizes. A $10k overrun on a $50k project is critical, but trivial on a $5M project. CPI natively accounts for this proportion.

### Graceful Degradation Strategy
Real-world `.xlsx` files are messy. Instead of failing when columns are missing, the system detects missing data, drops the signal, and **redistributes its weight proportionally** across the remaining signals. A `confidence` score (0-100%) is surfaced to the user reflecting data completeness.

### Grounded LLM Reasoning
To prevent hallucinated justifications, the LLM is *never* fed the raw spreadsheet text when determining status. It is only given the structured, computed JSON from the 5 signal extractors.

---

## Setup Instructions
Please refer to the detailed [SETUP.md](./SETUP.md) file in the repository root for step-by-step instructions on running the full-stack application.
