# Lindstorm Warehouse Voice Picking System

**ICT Project 2026 — Sagar Kandel**

A voice-guided warehouse picking system where workers use their voice instead of paper or scanners. The system speaks every instruction, listens to the worker's response, and routes them through the warehouse in the correct shelf order automatically.

---

## Table of Contents

- [Overview](#overview)
- [How It Works](#how-it-works)
- [Demo Accounts](#demo-accounts)
- [Installation](#installation)
- [Project Structure](#project-structure)
- [System Architecture](#system-architecture)
- [Smart Routing](#smart-routing)
- [REST API Endpoints](#rest-api-endpoints)
- [Machine Learning](#machine-learning)
- [UIUX Evaluation](#uiux-evaluation)
- [Tech Stack](#tech-stack)
- [APIs Used](#apis-used)
- [Database](#database)
- [Audit Log](#audit-log)

---

## Overview

The Lindstorm Warehouse Voice Picking System is a full-stack web application. Workers open Chrome on their phone and receive voice instructions telling them which shelf to go to, what code to say, and how many products to pick. Both hands stay free at all times.

The supervisor creates orders from a dashboard, monitors live progress, and views machine learning predictions about shelf demand and worker performance.

The system runs three separate Flask servers and one SQLite database — all started with a single command.

---

## How It Works

**Supervisor side:**

1. Open browser at `localhost:5000` and login
2. Go to the Tasks tab and fill in the Create Order form
3. Add shelf locations, confirmation codes, and quantities
4. Multiple locations in one form become one grouped order
5. Click Create All Tasks — all tasks saved to the database
6. Monitor live progress from the dashboard

**Worker side:**

1. Open Chrome on phone at `http://192.168.x.x:5000` on same WiFi
2. Login with worker credentials
3. Phone automatically speaks the first location
4. Walk to the shelf — tap the mic button — say the code from the label
5. System checks the code — if correct it says how many products to pick
6. Pick the products — tap mic — say done
7. System marks task complete and announces the next location immediately
8. When all locations in the order are done — phone says "Order complete. Well done."
9. Next order is announced automatically

**Routing rule:**

The system always completes Row 1 fully before moving to Row 2, and Row 2 fully before Row 3. Within each row it goes shelf number 1, 2, 3 in ascending order. The worker never has to think about where to go next.

```
R01 shelf 1 -> R01 shelf 2 -> R01 shelf 10  (Row 1 fully done)
R02 shelf 3 -> R02 shelf 8                  (Row 2 fully done)
R03 shelf 2 -> R03 shelf 7                  (Row 3 fully done)
```

---

## Demo Accounts

| Role | Username | Password | Full Name |
|---|---|---|---|
| Supervisor | supervisor1 | super123 | Matti Lindstorm |
| Worker | worker1 | worker123 | Sagar Kandel |
| Worker | worker2 | worker456 | Khuman Singh Rana |
| Worker | worker3 | worker789 | Bijay Satyal |

---

## Installation

**Requirements:**
- Python 3.12 or higher
- Google Chrome browser (required for voice features)
- Windows, Mac, or Linux

**Project folder on this machine:**

```
C:\Users\Käyttäjä\Desktop\lindstorm_warehouse
```

**Steps:**

```powershell
# Go to the project folder
cd "C:\Users\Käyttäjä\Desktop\lindstorm_warehouse"

# Create virtual environment
python -m venv venv

# Activate virtual environment
venv\Scripts\activate

# Install dependencies
python -m pip install flask werkzeug requests

# Initialize the database (run once)
python init_db.py

# Start all three servers
python main.py
```

**Open in browser:**
```
Supervisor (PC):   http://localhost:5000
Worker (Phone):    http://192.168.x.x:5000   (replace x.x with your local IP)
```

The terminal will show your exact local IP address when you run `python main.py`.

---

## Project Structure

```
C:\Users\Käyttäjä\Desktop\lindstorm_warehouse\
│
├── main.py              Starts all 3 servers at once
├── frontend_app.py      Web UI — HTML, CSS, JavaScript inside Flask (Port 5000)
├── api_app.py           REST API backend — all system logic (Port 5001)
├── ml_api.py            Machine Learning API (Port 5002)
├── ml_engine.py         ML models — Linear Regression and Weighted Scoring
├── db.py                Database layer — smart routing system lives here
├── init_db.py           Database setup — run this once before starting
├── requirements.txt     Python dependencies
└── README.md            This file
```

The database file `warehouse.db` is created automatically when you run `python init_db.py`.

Database location on this machine:
```
C:\Users\Käyttäjä\Desktop\lindstorm_warehouse\warehouse.db
```

---

## System Architecture

The system has three servers and one database:

```
Browser (Supervisor PC or Worker Phone)
          |
          | HTTP
          v
  Frontend Server  (Port 5000)
  frontend_app.py
  HTML + CSS + JavaScript + Flask
          |
          | REST API calls
     _____|_____
    |           |
    v           v
API Server    ML Server
Port 5001     Port 5002
api_app.py    ml_api.py
Python+Flask  Python+Flask
    |           |
    |___________|
          |
          | read and write
          v
     SQLite Database
     warehouse.db
     ________________
     | tasks         |
     | users         |
     | audit_logs    |
     | pick_log      |
     | worker_stats  |
     |_______________|
```

The browser only communicates with the Frontend server. The Frontend calls the API and ML servers on behalf of the browser. All three servers share the same SQLite database file.

Start all three servers with:
```
python main.py
```

---

## Smart Routing

The routing system is inside `db.py` in three functions:

**parse_location()**

Reads a location name and extracts row and column numbers.

```
R01-10  ->  row = 1, column = 10
R02-05  ->  row = 2, column = 5
R03-02  ->  row = 3, column = 2
```

**_warehouse_sort_locs()**

Sorts tasks in physical warehouse order. Groups by row number, then sorts each row by column number ascending.

```python
# Input  (random order): R03-02, R01-10, R02-05, R01-01, R02-08
# Output (sorted):       R01-01, R01-10, R02-05, R02-08, R03-02
```

**get_next_pending_task()**

Main routing function. Runs every time the worker needs the next task.

Rules in order:
1. If the worker is currently mid-order — only return tasks from that same order
2. If the last completed task belongs to an order that still has pending tasks — stay on that order
3. Only when the current order is 100% done — move to the next order
4. Within any order — always apply warehouse sort (R01 first, then R02, then R03)

The SQL query also sorts at the database level:
```sql
ORDER BY priority DESC, row_num ASC, col_num ASC
```

This guarantees the correct physical order even before Python processes anything.

---

## REST API Endpoints

### Authentication

| Method | Endpoint | Description |
|---|---|---|
| POST | /api/login | Login and receive a session token |
| POST | /api/logout | Logout and clear session |

### Worker Task Flow

| Method | Endpoint | Description |
|---|---|---|
| GET | /api/task/current | Get next pending task for worker |
| POST | /api/task/check-code | Verify the confirmation code |
| POST | /api/task/done | Mark current task as complete |

### Supervisor Task Management

| Method | Endpoint | Description |
|---|---|---|
| GET | /api/tasks | List all tasks |
| POST | /api/tasks/create | Create a new task |
| DELETE | /api/tasks/id | Delete a task |
| POST | /api/task/reset | Reset all tasks to pending |

### Supervisor User Management

| Method | Endpoint | Description |
|---|---|---|
| GET | /api/workers | List all users |
| POST | /api/workers/create | Create new worker account |

### Logs

| Method | Endpoint | Description |
|---|---|---|
| GET | /api/logs | Get audit log entries |

### Machine Learning

| Method | Endpoint | Description |
|---|---|---|
| GET | /ml/demand-forecast | Shelf demand predictions for tomorrow |
| GET | /ml/worker-performance | Worker performance scores for today |
| GET | /ml/health | Check if ML server is running |

---

## Machine Learning

The ML system is inside `ml_engine.py` and exposed through `ml_api.py` on port 5002.

Both models use data already stored in the SQLite database. No internet or external training data is required.

### Model 1 — Demand Forecasting using Linear Regression

Reads the last 7 days of pick history from the `pick_log` table and predicts tomorrow's pick count per shelf location.

Algorithm:

```
x values = day numbers 1 to 7
y values = pick count each day for that location

slope     = sum of (x - x_mean)(y - y_mean) / sum of (x - x_mean) squared
intercept = y_mean - slope * x_mean
prediction for day 8 = slope * 8 + intercept

Positive slope = Rising trend  = supervisor should restock
Zero slope     = Stable        = normal stock level
Negative slope = Falling trend = no action needed
```

Where to see it: Supervisor dashboard -> ML Insights tab -> Demand Forecast table

### Model 2 — Worker Performance using Weighted Scoring

Reads the `worker_stats` table and calculates a daily score from 0 to 100 for each worker based on accuracy and speed.

Algorithm:

```
wrong_rate   = wrong_codes / tasks_completed
wrong_score  = (1 - wrong_rate) * 50          (max 50 points)

avg_time     = total_seconds / tasks_completed
speed_score  = 50 - (avg_time - 60) * 0.3     (max 50 points)

total_score  = wrong_score + speed_score

80 to 100 = Good      (worker performing well)
60 to 79  = Watch     (supervisor should monitor)
0 to 59   = At Risk   (worker needs help)
```

Where to see it: Supervisor dashboard -> ML Insights tab -> Worker Performance table

---

## UIUX Evaluation

This project includes a Heuristic Evaluation using Nielsen's 10 Heuristics as the UI/UX evaluation method (Task Option 5).

Each heuristic was reviewed against every screen of the system.

| Heuristic | Result | Evidence |
|---|---|---|
| H1 — Visibility of system status | PASS | Progress bar, voice feedback, status badges on every task |
| H2 — Match system to real world | PASS | Location names like R01-10 match real shelf labels |
| H3 — User control and freedom | PASS | Logout always visible, keyboard fallback if voice fails |
| H4 — Consistency and standards | PASS | Same design language on every screen |
| H5 — Error prevention | PASS | Confirmation code prevents picking from wrong shelf |
| H6 — Recognition over recall | PASS | Location shown in large text — worker never needs to remember |
| H7 — Flexibility and efficiency | MEDIUM | No shortcut for supervisor to repeat a previous order |
| H8 — Aesthetic and minimalist | PASS | Clean red and white design, only essential information shown |
| H9 — Help recover from errors | PASS | Wrong code — voice speaks error once then stops, no loop |
| H10 — Help and documentation | MAJOR — FIXED | No help page existed. Fixed by adding a Help button to the worker navigation bar |

Result: 8 out of 10 heuristics passed. 1 medium violation. 1 major violation which was fixed during development.

H10 Fix: A question mark Help button was added to the worker navigation bar. Clicking it opens a step-by-step voice guide explaining how to use the system.

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Main language | Python 3.12 | All backend code |
| Web framework | Flask 3.0 | Creates the website and REST API |
| Database | SQLite with WAL mode | Stores all data in one file |
| Frontend | HTML, CSS, JavaScript | Worker and supervisor interfaces |
| Password security | Werkzeug | Hashes passwords before storing |
| Voice output | Web speechSynthesis API | Speaks instructions to worker |
| Voice input | Web SpeechRecognition API | Hears worker voice input |
| ML Model 1 | Linear Regression (custom) | Demand forecasting |
| ML Model 2 | Weighted Scoring (custom) | Worker performance |

---

## APIs Used

| API | Type | Cost | Purpose |
|---|---|---|---|
| speechSynthesis | Chrome built-in | Free | Speaks instructions to the worker |
| SpeechRecognition | Chrome built-in | Free | Hears what the worker says |
| REST API (port 5001) | Built with Flask | Free | All system logic |
| ML API (port 5002) | Built with Flask | Free | Machine learning predictions |

The voice APIs require Google Chrome. They are built into the browser — no API key or payment is needed.

---

## Database

The database is a single SQLite file called `warehouse.db` stored in the project folder. It is created automatically when you run `python init_db.py`.

| Table | Description |
|---|---|
| tasks | All picking tasks — location, code, quantity, status, order ID |
| users | Worker and supervisor accounts with hashed passwords |
| audit_logs | Every action with timestamp, username, and result |
| pick_log | Pick history used by the ML demand forecasting model |
| worker_stats | Daily performance stats per worker used by ML scoring model |

---

## Audit Log

Every action in the system is recorded automatically in the `audit_logs` table. The supervisor can view the last 100 entries in the Audit Log tab.

Actions recorded: login, logout, check_code (correct and wrong), done, create_task, delete_task, reset_all, create_user.

Each entry includes: timestamp, username, role, action, location, code entered, and result. Wrong code entries also automatically increment the worker's daily wrong code count in `worker_stats`, which feeds the ML performance model.

---

## License

MIT License — free to use and modify.

---

*ICT Project 2026 — Sagar Kandel*
