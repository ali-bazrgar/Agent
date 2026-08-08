# Phase 11 — Deployment Specification

## Overview
SuperAgent supports three primary deployment modes sharing a single unified backend and frontend architecture:
1. **Local Desktop Mode**: Standalone execution with embedded FastAPI/Node runtime and local SQLite persistence.
2. **Web Deployment Mode**: Containerized or cloud-hosted web deployment behind an ingress proxy (e.g. Nginx/Cloud Run).
3. **Docker Deployment Mode**: Production-ready container deployment via Docker Compose with persistent database and storage volumes.

## Docker Deployment Architecture
- **Dockerfile**: Multi-stage build supporting Python 3.11 and Node.js runtime with all dependencies.
- **docker-compose.yml**: Configures persistent volumes (`/app/data`), environment variables, health checks, and port mapping (`3000`).
- **Health Checks**: Automated probes on `/api/v1/health` ensuring all subsystems and database engines are operational.
