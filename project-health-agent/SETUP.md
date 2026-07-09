# Setup Guide

This guide will walk you through setting up the Project Health Agent on your local Windows machine. 

## Prerequisites
Before you begin, ensure you have the following installed on your system:
- **Python 3.11** (or higher)
- **Node.js** (v18 or higher)
- **npm** (comes with Node.js)
- A **Google Gemini API Key** (or Anthropic API Key)

---

## 1. Backend Setup

The backend is built with FastAPI and runs on Python. 

1. **Open a terminal (PowerShell)** and navigate to the backend directory:
   ```powershell
   cd project-health-agent\backend
   ```

2. **Create a Virtual Environment**:
   ```powershell
   python -m venv venv
   ```

3. **Activate the Virtual Environment**:
   ```powershell
   .\venv\Scripts\activate
   ```
   *(You should see `(venv)` appear at the start of your terminal prompt).*

4. **Install Python Dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```

5. **Configure Environment Variables**:
   - Copy `.env.example` to a new file named `.env`:
     ```powershell
     copy .env.example .env
     ```
   - Open the `.env` file in your code editor.
   - Set `ANTHROPIC_API_KEY` to your Gemini Flash 2.5 API key (or Anthropic key). *(Note: The application has been configured to route through the Gemini provider despite the variable name).*

6. **Start the Backend Server**:
   ```powershell
   uvicorn app.main:app --reload
   ```
   The backend is now running at `http://127.0.0.1:8000`. Leave this terminal open.

---

## 2. Frontend Setup

The frontend is a React application built with Vite and Tailwind CSS.

1. **Open a NEW terminal** (keep the backend terminal running).
2. **Navigate to the frontend directory**:
   ```powershell
   cd project-health-agent\frontend
   ```

3. **Install Node Modules**:
   ```powershell
   npm install
   ```

4. **Start the Frontend Development Server**:
   ```powershell
   npm run dev
   ```

5. **View the Application**:
   Open your browser and navigate to `http://localhost:5174`.
   - If port `5173` is already in use, the app will now start on `5174` instead.

---

## 3. How to Use the Application

1. **Upload a Project**:
   - On the Dashboard, click the **"Upload Project Plan"** button.
   - Select an `.xlsx` or `.xls` project plan file. 
   - *(Note: Ensure your spreadsheet has standard headers like "Status", "Budget", "Critical", etc., so the heuristic mapper can find your data).*
2. **Run Analysis**:
   - Once the project appears on the dashboard as an "Unanalyzed" card, hover over its name to rename it, or click **"View Details"**.
   - Inside the Project Detail view, click the glowing **"Run Initial Analysis"** or **"Run Weekly Analysis"** button.
   - The system will crunch the numbers, the UI will display a scanning sequence, and the results will smoothly animate onto the screen.
3. **Generate Monthly Report**:
   - Back on the main Dashboard, click **"Generate Monthly Deck"**.
   - The backend will synthesize all project histories and trigger a download of an auto-generated `.pptx` presentation.
