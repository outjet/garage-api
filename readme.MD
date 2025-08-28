# Garage API

A lightweight Flask API to control a garage door with a Raspberry Pi’s GPIO pins.

## Features
- JWT authentication (short-lived tokens for extra safety)  
- REST endpoints for door control (`/up`, `/down`, `/status`)  
- Buzzer support for alerts  
- Health check endpoint (`/health`)  
- Runs with Gunicorn behind any reverse proxy (nginx, Caddy, Traefik, etc.)  

---

## Endpoints

| Method | Path               | Auth                | Description               |
|--------|--------------------|---------------------|---------------------------|
| POST   | `/api/token`       | Basic (user/pass)   | Get a JWT (1 hour expiry) |
| GET    | `/api/door/status` | Bearer JWT          | Check door status         |
| POST   | `/api/door/up`     | Bearer JWT          | Trigger door up           |
| POST   | `/api/door/down`   | Bearer JWT          | Trigger door down         |
| GET    | `/health`          | None                | Basic health check        |

---

## Quickstart

```bash
git clone git@github.com:outjet/garage-api.git
cd garage-api

# create venv
python3 -m venv venv
. venv/bin/activate

# install deps
pip install -r requirements.txt

# configure
cp .env.example .env   # edit with real values

# run (development only)
python app.py
