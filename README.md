# Enterprise Asset & Resource Management ERP (AssetTitan)

This repository contains a full-stack Enterprise Resource Planning (ERP) application built with a FastAPI Python backend, a Vite + Tailwind CSS v4 frontend, and Firebase for data storage and authentication.

---

## 🚀 How to Run the Project Locally

To run the full website, you need to start two separate servers: the **Backend** (FastAPI) and the **Frontend** (Vite). 

Follow these steps every time you want to start the project.

### Step 1: Start the Backend Server
The backend handles API requests and communicates securely with your Firebase database using the `serviceAccountKey.json`.

1. Open a new terminal window.
2. Navigate to the `backend` folder:
   ```bash
   cd backend
   ```
3. Activate your Python virtual environment:
   - **Windows:** `.\venv\Scripts\activate`
   - **Mac/Linux:** `source venv/bin/activate`
4. Start the server:
   ```bash
   uvicorn src.main:app --reload --port 8000
   ```
   *Your backend is now running at `http://localhost:8000`*

### Step 2: Start the Frontend Server
The frontend handles the beautiful User Interface and connects to your local backend.

1. Open a **second, separate** terminal window.
2. Navigate to the `frontend` folder:
   ```bash
   cd frontend
   ```
3. Start the Vite development server:
   ```bash
   npm run dev
   ```
   *Your frontend is now running at `http://localhost:5173`*

### Step 3: View the App
- Open your web browser and go to **[http://localhost:5173](http://localhost:5173)** to use the application.
- To view the interactive Backend API documentation, go to **[http://localhost:8000/docs](http://localhost:8000/docs)**.

---

## 📁 Project Structure

### `/backend`
- Built with **FastAPI** and Python 3.12+.
- Uses Firebase Admin SDK.
- Relies on `.env` for `FIREBASE_PROJECT_ID` and `FIREBASE_STORAGE_BUCKET`.

### `/frontend`
- Built with **Vanilla JS**, HTML, and CSS.
- Uses **Vite** for the build system.
- Styled with **Tailwind CSS v4** featuring a custom glassmorphism design system.
- The router and entry point live in `src/app.js`.

### `/firebase`
- `firestore.rules` — Security rules restricting client-side database writes.
- `firestore.indexes.json` — Composite index definitions for complex dashboard queries.

## 🔒 Firebase Configuration
Make sure the `serviceAccountKey.json` is placed inside the `backend` folder, and the `backend/.env` file is properly configured with your specific project ID.
