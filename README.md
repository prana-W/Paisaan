# Paisaan

> Your AI-Powered Personal Investment Agent (Simulation & Educational)

Paisaan is an intelligent, multi-agent financial planning system built with LangGraph and FastAPI. It acts as a personal investment agent that gathers your financial profile, researches live market data, and formulates a multi-source investment allocation strategy to project potential gains. 

**Note:** *Paisaan is currently for simulation and educational purposes only. It does not provide certified financial advice or execute real trades.*

## 🚀 What It Does

1. **Intake Profiling:** A conversational AI naturally asks you questions to build a profile of your financial goals, risk tolerance, and investable amount.
2. **Live Market Research:** Based on your preferences, the agent dynamically fetches real-time data for Stocks, Mutual Funds, Bullion (Gold/Silver ETFs), FD Rates, and Market News.
3. **Smart Allocation & Projections:** The agent acts as a financial planner, splitting your investment across various asset classes based on the fetched live data, and calculates projected returns using compound interest over your specified time horizon.
4. **Human-in-the-Loop (HITL):** Paisaan features explicit consent checkpoints. It stops to ask for your permission before conducting market research and before finalizing your investment plan.

## ✨ Current Features

- **LangGraph Agent Architecture:** Complex workflows managed through nested subgraphs (Intake, Market Research, Gains Calculation).
- **Tool Ecosystem:** Integrated tools for DuckDuckGo news/search, Yahoo Finance (stocks/bullion), and `mfapi.in` (mutual funds).
- **Dynamic Gain Calculation:** A unified calculation engine that strictly validates 100% portfolio allocation and projects multi-year compound interest.
- **Beautiful UI:** A React/Vite frontend chatting directly with the LangGraph state machine.

## 🔮 Upcoming Features

- **Razorpay Test Integration:** Simulating the funding of the agent's virtual wallet.
- **Virtual Portfolio:** A sandbox environment for testing the agent's ability to "manage" and track a simulated portfolio over time.

## 🏗️ Architecture

Below is the LangGraph flow of the Paisaan Agent, detailing the orchestration between the main graph and the specialized subgraphs:

![Paisaan Agent Flow](paisaan_agent.png)

## 💻 Running the Project Locally

### Prerequisites
- Docker (for the PostgreSQL database)
- Python 3.10+ (for the FastAPI server)
- Node.js & npm/yarn (for the Vite frontend)
- Google Gemini API Key

### 1. Database Setup
Start a local PostgreSQL instance using Docker:
```bash
docker run --name paisaan-db -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=paisaan -p 5432:5432 -d postgres
```

### 2. Backend Server (Port 9000)
Navigate to the `server` directory, configure your environment, and start the FastAPI server:
```bash
cd server
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Ensure your .env is configured with your database URL and Google API key
# Example: DATABASE_URL=postgresql://postgres:postgres@localhost:5432/paisaan

# Start the server on port 9000
uvicorn app.main:app --reload --port 9000
```

### 3. Frontend (Port 5280)
Navigate to the `frontend` directory, install dependencies, and start the Vite dev server:
```bash
cd frontend
npm install

# Ensure your .env contains the correct backend URL and port:
# VITE_API_URL=http://localhost:9000/api/v1
# VITE_PORT=5280

npm run dev -- --port 5280
```

## 📖 Development Log

For a detailed breakdown of technical decisions, architecture shifts, and feature implementations, please refer to the [DEVLOG.md](DEVLOG.md).
