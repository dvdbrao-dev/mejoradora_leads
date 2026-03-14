#!/bin/bash
cd ~/openfang
uvicorn scripts.dashboard:app --host 0.0.0.0 --port 8080 --reload

# Para abrir el puerto: sudo ufw allow 8080
