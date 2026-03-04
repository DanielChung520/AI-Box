# 代碼功能說明: 日誌配置模組煙霧測試 — 驗證 6 頻道路由正確性
# 創建日期: 2026-03-04
# 創建人: Daniel Chung
# 最後修改日期: 2026-03-04

"""
Smoke tests for system/logging_config.py — verifies the 6-channel
structlog/dictConfig logging system routes messages to the correct
domain log files.
"""

from __future__ import annotations

import json
import logging
import logging.config
from pathlib import Path

import pytest
import structlog


# ---------------------------------------------------------------------------
# Fixture: isolated tmp_log_dir
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_log_dir(tmp_path: Path):
    """
    Override LOG_DIR to use a temporary directory for isolation.

    Patches the module-level LOG_DIR *and* all handler filenames in the
    dictConfig dict so that setup_logging() writes to tmp_path instead
    of the production logs/ directory.
    """
    import system.logging_config as lc

    original_log_dir = lc.LOG_DIR
    original_filenames: dict[str, str] = {}

    # 1. Patch LOG_DIR
    lc.LOG_DIR = tmp_path

    # 2. Patch every RotatingFileHandler filename in _LOGGING_CONFIG
    for handler_name, handler_cfg in lc._LOGGING_CONFIG["handlers"].items():
        if "filename" in handler_cfg:
            original_filenames[handler_name] = handler_cfg["filename"]
            log_basename = Path(handler_cfg["filename"]).name
            handler_cfg["filename"] = str(tmp_path / log_basename)

    # 3. Also patch the independent service log paths
    original_frontend = lc.FRONTEND_LOG_PATH
    original_mcp = lc.MCP_SERVER_LOG_PATH
    lc.FRONTEND_LOG_PATH = tmp_path / "frontend.log"
    lc.MCP_SERVER_LOG_PATH = tmp_path / "mcp_server.log"

    # 4. Reset structlog caching so fresh loggers are created
    structlog.reset_defaults()

    # 5. Call setup_logging() with patched paths
    lc.setup_logging()

    yield tmp_path

    # --- Teardown: restore originals and clean up handlers ---
    lc.LOG_DIR = original_log_dir
    lc.FRONTEND_LOG_PATH = original_frontend
    lc.MCP_SERVER_LOG_PATH = original_mcp
    for handler_name, orig_fn in original_filenames.items():
        lc._LOGGING_CONFIG["handlers"][handler_name]["filename"] = orig_fn

    # Close and remove ALL handlers to prevent pollution between tests
    root = logging.getLogger()
    for h in root.handlers[:]:
        h.close()
        root.removeHandler(h)
    for name in list(logging.Logger.manager.loggerDict.keys()):
        lgr = logging.getLogger(name)
        for h in lgr.handlers[:]:
            h.close()
            lgr.removeHandler(h)

    # Reset structlog
    structlog.reset_defaults()


def _flush_all_handlers() -> None:
    """Flush all logging handlers to ensure bytes are written to disk."""
    root = logging.getLogger()
    for h in root.handlers:
        h.flush()
    for name in list(logging.Logger.manager.loggerDict.keys()):
        lgr = logging.getLogger(name)
        for h in lgr.handlers:
            h.flush()


def _read_log(tmp_dir: Path, filename: str) -> str:
    """Read a log file, returning empty string if it doesn't exist."""
    path = tmp_dir / filename
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


# ---------------------------------------------------------------------------
# Test 1: setup_logging() runs without error
# ---------------------------------------------------------------------------


def test_setup_logging_no_error(tmp_log_dir: Path) -> None:
    """setup_logging() runs without any exception."""
    # If we got here, setup_logging() already ran in the fixture.
    # Just verify that the log directory exists and some log files were created.
    assert tmp_log_dir.exists()


# ---------------------------------------------------------------------------
# Test 2: Worker routing
# ---------------------------------------------------------------------------


def test_worker_routing(tmp_log_dir: Path) -> None:
    """database.rq.queue logger writes to worker.log."""
    lgr = logging.getLogger("database.rq.queue")
    lgr.info("WORKER_ROUTING_TEST")
    _flush_all_handlers()

    content = _read_log(tmp_log_dir, "worker.log")
    assert "WORKER_ROUTING_TEST" in content


# ---------------------------------------------------------------------------
# Test 3: Vectorization routing
# ---------------------------------------------------------------------------


def test_vectorization_routing(tmp_log_dir: Path) -> None:
    """database.chromadb.client logger writes to vectorization.log."""
    lgr = logging.getLogger("database.chromadb.client")
    lgr.info("VECT_ROUTING_TEST")
    _flush_all_handlers()

    content = _read_log(tmp_log_dir, "vectorization.log")
    assert "VECT_ROUTING_TEST" in content


# ---------------------------------------------------------------------------
# Test 4: Graph Extraction routing
# ---------------------------------------------------------------------------


def test_graph_extraction_routing(tmp_log_dir: Path) -> None:
    """kag.ontology_selector logger writes to graph_extraction.log."""
    lgr = logging.getLogger("kag.ontology_selector")
    lgr.info("GRAPH_ROUTING_TEST")
    _flush_all_handlers()

    content = _read_log(tmp_log_dir, "graph_extraction.log")
    assert "GRAPH_ROUTING_TEST" in content


# ---------------------------------------------------------------------------
# Test 5: Agent Management routing
# ---------------------------------------------------------------------------


def test_agent_management_routing(tmp_log_dir: Path) -> None:
    """agents.orchestrator.orchestrator logger writes to agent_management.log."""
    lgr = logging.getLogger("agents.orchestrator.orchestrator")
    lgr.info("AGMT_ROUTING_TEST")
    _flush_all_handlers()

    content = _read_log(tmp_log_dir, "agent_management.log")
    assert "AGMT_ROUTING_TEST" in content


# ---------------------------------------------------------------------------
# Test 6: KA-Agent routing
# ---------------------------------------------------------------------------


def test_ka_agent_routing(tmp_log_dir: Path) -> None:
    """agents.builtin.ka_agent.agent logger writes to ka_agent.log."""
    lgr = logging.getLogger("agents.builtin.ka_agent.agent")
    lgr.info("KA_ROUTING_TEST")
    _flush_all_handlers()

    content = _read_log(tmp_log_dir, "ka_agent.log")
    assert "KA_ROUTING_TEST" in content


# ---------------------------------------------------------------------------
# Test 7: structlog routing
# ---------------------------------------------------------------------------


def test_structlog_routing(tmp_log_dir: Path) -> None:
    """structlog.get_logger('workers.tasks') writes valid JSON to worker.log."""
    sl = structlog.get_logger("workers.tasks")
    sl.info("STRUCTLOG_ROUTE_TEST", k="v")
    _flush_all_handlers()

    content = _read_log(tmp_log_dir, "worker.log")
    assert "STRUCTLOG_ROUTE_TEST" in content

    # Find the line containing the marker and parse as JSON
    lines = [l for l in content.strip().splitlines() if "STRUCTLOG_ROUTE_TEST" in l]
    assert len(lines) >= 1, "Expected at least one line with STRUCTLOG_ROUTE_TEST"
    data = json.loads(lines[0])
    assert data["event"] == "STRUCTLOG_ROUTE_TEST"


# ---------------------------------------------------------------------------
# Test 8: System catches unmatched
# ---------------------------------------------------------------------------


def test_system_catches_unmatched(tmp_log_dir: Path) -> None:
    """Unmatched logger (some.random.module) writes to system.log."""
    lgr = logging.getLogger("some.random.module")
    lgr.info("SYS_ROUTING_TEST")
    _flush_all_handlers()

    content = _read_log(tmp_log_dir, "system.log")
    assert "SYS_ROUTING_TEST" in content


# ---------------------------------------------------------------------------
# Test 9: No propagation leak
# ---------------------------------------------------------------------------


def test_no_propagation_leak(tmp_log_dir: Path) -> None:
    """Domain logger writes do NOT appear in system.log (propagate=False)."""
    # Write to each domain
    logging.getLogger("database.rq.queue").info("LEAK_CHECK_WORKER")
    logging.getLogger("database.chromadb.client").info("LEAK_CHECK_VECT")
    logging.getLogger("kag.ontology_selector").info("LEAK_CHECK_GRAPH")
    logging.getLogger("agents.orchestrator.orchestrator").info("LEAK_CHECK_AGMT")
    logging.getLogger("agents.builtin.ka_agent.agent").info("LEAK_CHECK_KA")
    _flush_all_handlers()

    system_content = _read_log(tmp_log_dir, "system.log")
    assert "LEAK_CHECK_WORKER" not in system_content
    assert "LEAK_CHECK_VECT" not in system_content
    assert "LEAK_CHECK_GRAPH" not in system_content
    assert "LEAK_CHECK_AGMT" not in system_content
    assert "LEAK_CHECK_KA" not in system_content


# ---------------------------------------------------------------------------
# Test 10: JSON format in file
# ---------------------------------------------------------------------------


def test_json_format_in_file(tmp_log_dir: Path) -> None:
    """Log lines in domain files are valid JSON (json.loads succeeds)."""
    lgr = logging.getLogger("database.rq.queue")
    lgr.info("JSON_FORMAT_CHECK")
    _flush_all_handlers()

    content = _read_log(tmp_log_dir, "worker.log")
    lines = [l for l in content.strip().splitlines() if "JSON_FORMAT_CHECK" in l]
    assert len(lines) >= 1, "Expected at least one line with JSON_FORMAT_CHECK"

    for line in lines:
        data = json.loads(line)
        assert "event" in data
        assert data["event"] == "JSON_FORMAT_CHECK"


# ---------------------------------------------------------------------------
# Test 11: setup_mcp_server_logging preserved
# ---------------------------------------------------------------------------


def test_mcp_server_logging_preserved(tmp_log_dir: Path) -> None:
    """setup_mcp_server_logging() returns a Logger instance."""
    import system.logging_config as lc

    result = lc.setup_mcp_server_logging()
    assert isinstance(result, logging.Logger)


# ---------------------------------------------------------------------------
# Test 12: setup_frontend_logging preserved
# ---------------------------------------------------------------------------


def test_frontend_logging_preserved(tmp_log_dir: Path) -> None:
    """setup_frontend_logging() returns a Logger instance."""
    import system.logging_config as lc

    result = lc.setup_frontend_logging()
    assert isinstance(result, logging.Logger)
