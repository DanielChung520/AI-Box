"""
CODE PURPOSE: Reference implementation for dictConfig + structlog.configure() integration
Created: 2026-03-04
Source: structlog 25.5.0 documentation + verified imports
Pattern: "Rendering using structlog-based formatters within logging" (most powerful)

KEY POINTS:
1. logging.config.dictConfig() FIRST, then structlog.configure() — ORDER MATTERS
2. ProcessorFormatter acts as the bridge between stdlib logging and structlog
3. foreign_pre_chain handles stdlib logging.getLogger() calls through structlog formatters
4. Each domain logger uses propagate=False to prevent double-logging to system.log
5. Both structlog.get_logger() and logging.getLogger() route through the same pipeline
"""

import logging
import logging.config
import structlog
from logging.handlers import RotatingFileHandler
from pathlib import Path

# ============================================================================
# PART 1: Define the dictConfig dictionary
# ============================================================================
# This configures the STDLIB logging system with ProcessorFormatter
# as the formatter class for both console and file handlers

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,  # CRITICAL: don't break existing logger instances
    
    # ========================================================================
    # Formatters: These define HOW to render log entries
    # ========================================================================
    "formatters": {
        # Console formatter: colored output for development
        # - Uses ConsoleRenderer for human-readable output
        # - foreign_pre_chain handles stdlib loggers (logging.getLogger())
        "console": {
            "()": structlog.stdlib.ProcessorFormatter,
            "processors": [
                # Remove internal structlog meta-keys from console output
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                # Human-readable rendering with colors
                structlog.dev.ConsoleRenderer(colors=True),
            ],
            # These processors run on stdlib logging entries BEFORE the main chain
            # They mirror the structlog processor chain but for foreign loggers
            "foreign_pre_chain": [
                # Add log level name (e.g., "info", "warning")
                structlog.stdlib.add_log_level,
                # Add logger name (e.g., "database.arangodb")
                structlog.stdlib.add_logger_name,
                # Add ISO 8601 timestamp
                structlog.processors.TimeStamper(fmt="iso"),
                # Extract thread/process info from LogRecord and add to event dict
                structlog.stdlib.ExtraAdder(),
            ],
        },
        
        # File formatter: JSON output for production/log aggregation
        # - Uses JSONRenderer for machine-readable output
        # - Same foreign_pre_chain as console to ensure consistency
        "json": {
            "()": structlog.stdlib.ProcessorFormatter,
            "processors": [
                # Remove meta-keys for cleaner JSON
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                # Machine-readable JSON rendering (no colors)
                structlog.processors.JSONRenderer(),
            ],
            "foreign_pre_chain": [
                structlog.stdlib.add_log_level,
                structlog.stdlib.add_logger_name,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.stdlib.ExtraAdder(),
            ],
        },
    },
    
    # ========================================================================
    # Handlers: These define WHERE log entries go (stdout, file, etc.)
    # ========================================================================
    "handlers": {
        # Console handler: streams to stdout with colored formatting
        "console": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "console",
            "stream": "ext://sys.stdout",
        },
        
        # System log file: captures all system events (FastAPI, MCP, etc.)
        # Using RotatingFileHandler: max 512KB per file, keep 4 backups
        "system_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "INFO",
            "formatter": "json",
            "filename": "logs/system.log",
            "maxBytes": 524288,  # 512 KB
            "backupCount": 4,
        },
        
        # Worker-specific log file: captures RQ worker activity
        "worker_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "DEBUG",
            "formatter": "json",
            "filename": "logs/worker.log",
            "maxBytes": 524288,
            "backupCount": 4,
        },
        
        # Vectorization-specific log file
        "vectorization_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "DEBUG",
            "formatter": "json",
            "filename": "logs/vectorization.log",
            "maxBytes": 524288,
            "backupCount": 4,
        },
        
        # Graph extraction-specific log file
        "graph_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "DEBUG",
            "formatter": "json",
            "filename": "logs/graph.log",
            "maxBytes": 524288,
            "backupCount": 4,
        },
        
        # Agent management-specific log file
        "agent_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "DEBUG",
            "formatter": "json",
            "filename": "logs/agent.log",
            "maxBytes": 524288,
            "backupCount": 4,
        },
    },
    
    # ========================================================================
    # Loggers: These map logger NAMES to handlers and levels
    # ========================================================================
    "loggers": {
        # ROOT logger: catches everything not matched by specific loggers
        # Routes to both console (all levels) and system_file (INFO+)
        "": {
            "level": "DEBUG",
            "handlers": ["console", "system_file"],
            "propagate": True,  # Root can propagate to itself
        },
        
        # DOMAIN-SPECIFIC LOGGERS: each with propagate=False to prevent double-logging
        
        # WORKER DOMAIN: RQ workers, task scheduling
        # Logger names: workers, database.rq, services.api.tasks
        "workers": {
            "level": "DEBUG",
            "handlers": ["console", "worker_file"],
            "propagate": False,  # CRITICAL: don't also log to system.log
        },
        "database.rq": {
            "level": "DEBUG",
            "handlers": ["console", "worker_file"],
            "propagate": False,
        },
        "services.api.tasks": {
            "level": "DEBUG",
            "handlers": ["console", "worker_file"],
            "propagate": False,
        },
        
        # VECTORIZATION DOMAIN: ChromaDB, Qdrant, embedding services
        "database.chromadb": {
            "level": "DEBUG",
            "handlers": ["console", "vectorization_file"],
            "propagate": False,
        },
        "database.qdrant": {
            "level": "DEBUG",
            "handlers": ["console", "vectorization_file"],
            "propagate": False,
        },
        "services.api.services.embedding_service": {
            "level": "DEBUG",
            "handlers": ["console", "vectorization_file"],
            "propagate": False,
        },
        "services.api.services.vector_store_service": {
            "level": "DEBUG",
            "handlers": ["console", "vectorization_file"],
            "propagate": False,
        },
        "services.api.services.qdrant_vector_store_service": {
            "level": "DEBUG",
            "handlers": ["console", "vectorization_file"],
            "propagate": False,
        },
        
        # GRAPH EXTRACTION DOMAIN: KA, ArangoDB, KG services
        "kag": {
            "level": "DEBUG",
            "handlers": ["console", "graph_file"],
            "propagate": False,
        },
        "database.arangodb": {
            "level": "DEBUG",
            "handlers": ["console", "graph_file"],
            "propagate": False,
        },
        "agents.builtin.knowledge_ontology_agent": {
            "level": "DEBUG",
            "handlers": ["console", "graph_file"],
            "propagate": False,
        },
        "services.api.services.kg_extraction_service": {
            "level": "DEBUG",
            "handlers": ["console", "graph_file"],
            "propagate": False,
        },
        "genai.api.services.kg_builder_service": {
            "level": "DEBUG",
            "handlers": ["console", "graph_file"],
            "propagate": False,
        },
        
        # AGENT MANAGEMENT DOMAIN: Orchestrator, registries, MoE
        "agents.orchestrator": {
            "level": "DEBUG",
            "handlers": ["console", "agent_file"],
            "propagate": False,
        },
        "agents.builtin.orchestrator_manager": {
            "level": "DEBUG",
            "handlers": ["console", "agent_file"],
            "propagate": False,
        },
        "agents.builtin.registry_manager": {
            "level": "DEBUG",
            "handlers": ["console", "agent_file"],
            "propagate": False,
        },
        "agents.builtin.moe_agent": {
            "level": "DEBUG",
            "handlers": ["console", "agent_file"],
            "propagate": False,
        },
        "agents.services.registry": {
            "level": "DEBUG",
            "handlers": ["console", "agent_file"],
            "propagate": False,
        },
        "llm.moe": {
            "level": "DEBUG",
            "handlers": ["console", "agent_file"],
            "propagate": False,
        },
        
        # KA-AGENT (SPECIAL): Knowledge Acquisition Agent
        "agents.builtin.ka_agent": {
            "level": "DEBUG",
            "handlers": ["console", "agent_file"],
            "propagate": False,
        },
    },
}


# ============================================================================
# PART 2: Configure stdlib logging with dictConfig
# ============================================================================
# THIS RUNS FIRST. It sets up the Python logging system.
def setup_logging():
    """Initialize stdlib logging via dictConfig."""
    logging.config.dictConfig(LOGGING_CONFIG)


# ============================================================================
# PART 3: Configure structlog
# ============================================================================
# THIS RUNS SECOND (after setup_logging).
# It configures structlog to use stdlib's LoggerFactory underneath,
# so structlog.get_logger() calls also route through the logging handlers.
def setup_structlog():
    """Configure structlog to use stdlib logging."""
    
    # Shared processors that run for both structlog and stdlib loggers
    # (They appear in foreign_pre_chain for stdlib, and in the main chain for structlog)
    shared_processors = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
    ]
    
    structlog.configure(
        processors=shared_processors + [
            # Convert event dict to format that ProcessorFormatter understands
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        # Use stdlib's logging.Logger underneath (not PrintLogger)
        logger_factory=structlog.stdlib.LoggerFactory(),
        # Use BoundLogger for API compatibility with logging.Logger
        wrapper_class=structlog.stdlib.BoundLogger,
        # Freeze configuration after first logger creation
        cache_logger_on_first_use=True,
    )


# ============================================================================
# PART 4: Initialize both systems
# ============================================================================
# IMPORTANT: MUST call setup_logging() BEFORE setup_structlog()
def initialize_logging():
    """Initialize the complete logging system."""
    setup_logging()      # Set up stdlib logging first
    setup_structlog()    # Then configure structlog


# ============================================================================
# PART 5: Example usage
# ============================================================================
if __name__ == "__main__":
    # Initialize the complete logging system
    initialize_logging()
    
    # Create logs directory if it doesn't exist
    Path("logs").mkdir(exist_ok=True)
    
    # Example 1: Using structlog.get_logger()
    # This will route through stdlib handlers because of LoggerFactory()
    log_structlog = structlog.get_logger("agents.builtin.ka_agent")
    log_structlog.info("example_from_structlog", user="alice", action="create_ontology")
    
    # Example 2: Using stdlib logging.getLogger()
    # This will ALSO route through the same pipeline with ProcessorFormatter
    log_stdlib = logging.getLogger("database.arangodb")
    log_stdlib.info("example_from_stdlib")
    
    # Example 3: Domain logger with propagate=False
    # This goes to worker_file, NOT to system_file (because propagate=False)
    log_worker = logging.getLogger("database.rq")
    log_worker.debug("rq_worker_event", extra={"job_id": "123", "status": "running"})
    
    print("\n✓ All examples logged successfully.")

