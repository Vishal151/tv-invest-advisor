"""M2: the request_id bound by RequestIDMiddleware must reach stdlib log records."""

import logging

import structlog


def _make_record() -> logging.LogRecord:
    return logging.LogRecord("app.test", logging.INFO, __file__, 1, "hello", None, None)


def test_request_id_filter_injects_bound_contextvar():
    from app.main import RequestIDLogFilter

    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id="req-abc")
    record = _make_record()

    assert RequestIDLogFilter().filter(record) is True
    assert record.request_id == "req-abc"
    structlog.contextvars.clear_contextvars()


def test_request_id_filter_defaults_to_dash_outside_requests():
    from app.main import RequestIDLogFilter

    structlog.contextvars.clear_contextvars()
    record = _make_record()

    RequestIDLogFilter().filter(record)
    assert record.request_id == "-"


def test_root_logger_handlers_carry_request_id_filter():
    """The filter must actually be attached, so every log line gets a request_id."""
    import app.main  # noqa: F401 — triggers _configure_logging()
    from app.main import RequestIDLogFilter

    handlers = logging.getLogger().handlers
    assert handlers, "root logger must have at least one handler"
    assert any(
        any(isinstance(f, RequestIDLogFilter) for f in h.filters) for h in handlers
    ), "RequestIDLogFilter must be attached to a root handler"
