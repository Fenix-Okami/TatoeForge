"""TatoeForge - An ETL pipeline for Tatoeba data with multiprocessing support."""

__version__ = "0.1.0"

__all__ = ["ETLPipeline"]


def __getattr__(name):
    """Load heavier ETL dependencies only when requested."""
    if name == "ETLPipeline":
        from tatoeforge.etl import ETLPipeline

        return ETLPipeline
    raise AttributeError(f"module 'tatoeforge' has no attribute {name!r}")
