# ChessCode MCP Server — Pre-Deployment Quality Improvements

## Summary of Improvements

This document describes the critical improvements made to the ChessCode MCP server to prepare it for production deployment and YouTube monetization.

### What's New

#### 1. **Startup Validation** (`startup_validator.py`)
- **Purpose:** Catch configuration errors early before the MCP server starts
- **Features:**
  - Validates API keys (Claude, Ollama, etc.)
  - Checks database and output directory writeability
  - Verifies TTS backend availability
  - Fails fast with clear error messages
  
**Usage:** Automatically called when `mcp_server.py` starts. No manual action needed.

#### 2. **Improved MCP Server** (`mcp_server.py`)
- **Purpose:** Enhanced reliability and error handling
- **Changes:**
  - Added comprehensive type hints (Python 3.10+ compatible)
  - Thread-safe job registry with locking (`_jobs_lock`)
  - Better subprocess error handling in `_launch_job()`
  - Proper logging configuration with file output
  - Graceful error recovery (logs errors instead of crashing)
  - Added `__all__` exports for clean module interface

**Before:** Subprocess crashes could crash the entire MCP server  
**After:** Subprocess errors are caught, logged, and returned cleanly to the user

#### 3. **Backend Resilience** (`backend_resilience.py`)
- **Purpose:** Automatic fallback chains and timeout protection
- **Features:**
  - LLM fallback: Claude → Ollama (if available)
  - TTS fallback: Configured backend → gTTS
  - Timeout protection (configurable per call)
  - Structured error logging with fallback tracking
  
**Usage:**
```python
from backend_resilience import resilient_llm_call, resilient_tts_call

# These automatically try fallbacks if primary fails
text = resilient_llm_call(system_prompt, user_prompt, timeout_seconds=60)
audio = resilient_tts_call("Hello world", language="en", timeout_seconds=30)
```

#### 4. **Job Registry Manager** (`job_registry.py`)
- **Purpose:** Prevent memory leaks and resource exhaustion
- **Features:**
  - Bounded job history (default: 100 jobs)
  - Max queue size enforcement (default: 50 jobs)
  - Automatic cleanup of completed/old jobs
  - Job archival to disk for historical records
  - Thread-safe with built-in locking
  
**Configuration:**
```python
from job_registry import JobRegistry, JOB_HISTORY_LIMIT, MAX_QUEUE_SIZE

registry = JobRegistry(max_history=100, max_queue=50)
registry.add(job_id, job_data)
status = registry.get_queue_status()
# {'total_jobs': 5, 'max_queue': 50, 'queue_full': False, 'utilization_percent': 10}
```

#### 5. **Enhanced Job Monitor** (`job_monitor.py`)
- **Purpose:** Better visibility into pipeline state
- **New Endpoints:**
  - `/health` - JSON health check
  - `/metrics` - Prometheus-compatible metrics
  - `/` - Job list dashboard (improved)
  - `/job/{id}` - Live progress page (existing)

**Health Check Example:**
```bash
curl http://localhost:8765/health
# {"status": "ok", "total_jobs": 5, "running_jobs": 2, "completed_jobs": 3}
```

**Metrics Example:**
```bash
curl http://localhost:8765/metrics
# chesscode_jobs_running 2
# chesscode_jobs_total 5
# chesscode_jobs_completed 3
```

#### 6. **Better Type Hints**
- Added comprehensive type hints to:
  - `mcp_server.py` - Full type annotations
  - `tts_backends/base.py` - Better docstrings
  - `llm_backends/base.py` - Better docstrings

**Benefit:** IDE autocomplete, type checking with `mypy`, self-documenting code

#### 7. **Improved Backend Interfaces**
- `__all__` exports in all backend modules
- Better docstrings with argument/return documentation
- Clear abstract method specifications

---

## Deployment Checklist

Before running the MCP server in production:

- [ ] Set `ANTHROPIC_API_KEY` (or configure Ollama as fallback)
- [ ] Set `TTS_BACKEND` (Kokoro recommended for offline operation)
- [ ] Ensure `output` directory exists and is writable
- [ ] Ensure `logs` directory exists and is writable
- [ ] Review `.env` file for correct settings
- [ ] Test startup: `python mcp_server.py` (should show startup validation)
- [ ] Open browser to `http://localhost:8765/health` to verify job monitor is running
- [ ] Configure Claude Desktop with MCP server path

**Example Claude Desktop Configuration:**
```json
{
  "mcpServers": {
    "chesscode": {
      "command": "python",
      "args": ["C:/path/to/chess channel/mcp_server.py"]
    }
  }
}
```

---

## Monitoring & Debugging

### Health Checks
```bash
# Check if MCP server is responding
curl http://localhost:8765/health

# Check live metrics
curl http://localhost:8765/metrics

# List all jobs
curl http://localhost:8765/

# Check specific job
curl http://localhost:8765/job/{job_id}
```

### Log Files
- **MCP Server:** `mcp_server.log` - Main server log
- **Job Output:** `logs/{job_id}.log` - Individual job logs
- **Archived Jobs:** `logs/archive/` - Metadata for old jobs

### Monitoring Queue Health
The job registry automatically:
1. **Cleans up completed jobs** (removes process handles)
2. **Archives old jobs** (saves metadata to disk)
3. **Prevents queue overflow** (rejects jobs if queue full)
4. **Reports metrics** (via `/metrics` endpoint)

---

## Error Handling Best Practices

### Graceful Degradation
If Claude API is unavailable:
- System automatically tries Ollama
- If Ollama unavailable, raises `BackendError`
- Job continues but uses fallback/dummy output

If ElevenLabs is unavailable:
- System automatically tries Kokoro
- If Kokoro unavailable, falls back to gTTS
- If all fail, uses silent audio (2.0s silence)

### Timeout Protection
All external API calls have timeouts:
- Claude: 60 seconds (configurable)
- TTS: 30 seconds (configurable)
- Default: No timeout (set `timeout_seconds=0`)

---

## Future Improvements (Phase 3+)

Listed in `plan.md`:
1. Worker pool auto-tuning (Stockfish, render workers)
2. Memory usage monitoring and throttling
3. Advanced cache cleanup strategies
4. YouTube upload safety (dry-run mode)
5. Centralized metrics export

---

## Testing

### Quick Smoke Test
```bash
cd "C:\Users\Mr\Desktop\chess channel"
python mcp_server.py
# Should show: "━━━ ChessCode MCP Server — Startup Validation ━━━"
# Then: "✓ Database writable..."
# Then: "✓ Output directory writable..."
# Should not show any ERROR lines
```

### Test with Claude Desktop
1. Add MCP server to Claude Desktop config
2. In Claude, request: "Create a chess analysis video from this PGN..."
3. MCP server should accept the request and return a job_id
4. Open monitor URL in browser (should show live progress)
5. Job should complete without crashes

### Resilience Test
```bash
# Temporarily rename or move your ANTHROPIC_API_KEY in .env
python mcp_server.py
# Should still start (showing warning for Claude)
# Fallback to Ollama should work if configured
# Otherwise, jobs will fail gracefully with clear error message
```

---

## Performance Improvements

- **Thread-safe registry:** No contention on job updates
- **Automatic cleanup:** Memory doesn't grow unbounded
- **Timeout protection:** No hanging requests blocking the server
- **Backend fallback:** Faster recovery from transient failures
- **Early validation:** Bad configs caught at startup (not during job)

---

## Configuration Reference

**Key Environment Variables:**
```bash
# Core APIs
ANTHROPIC_API_KEY=sk-ant-...
TTS_BACKEND=kokoro  # or "elevenlabs" or "gtts"

# Fallbacks
LLM_BACKEND=claude  # or "ollama"
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2

# Paths
OUTPUT_DIR=output
DB_PATH=chesscode.db

# Performance
STOCKFISH_THREADS=4
RENDER_WORKERS=0  # auto-detect
```

**Default Limits:**
```python
JOB_HISTORY_LIMIT = 100      # In-memory job cache
MAX_QUEUE_SIZE = 50          # Max pending jobs
CLEANUP_INTERVAL = 60        # Cleanup every 60s
```

---

## Questions & Support

For issues:
1. Check `mcp_server.log` for errors
2. Verify job-specific log at `logs/{job_id}.log`
3. Check health endpoint: `http://localhost:8765/health`
4. Review this guide's "Error Handling" section

For configuration help:
1. Run `python main.py --test` to check all dependencies
2. Review `.env.example` for all available options
3. Check `startup_validator.py` for validation rules
