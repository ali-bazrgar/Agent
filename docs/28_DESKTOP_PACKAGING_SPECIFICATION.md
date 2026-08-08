# Phase 11 — Desktop Packaging Specification

## Overview
SuperAgent supports native Windows Desktop operation through a packaged launcher architecture combining the Node.js / Python backend engine with a native webview or bundled browser frontend.

## Packaging Strategy
- **Runtime Bundle**: Standalone Node.js runtime bundling the compiled Express/FastAPI server and SQLite database in the user's local AppData directory (`%APPDATA%/SuperAgent`).
- **Launcher Script**: A lightweight startup wrapper (`launch.bat` / PowerShell script) that starts the local backend daemon on port `3000` and opens the default browser interface.
- **Data Persistence & Updates**: Automatic schema migrations on startup, offline-first operation, and secure configuration storage without overwriting user state during updates.
