"""Command-line entry point for the Ascend Optimizer MVP."""

from .data_loader import SchemaValidationError, load_datasets


def main() -> None:
    """Validate the frozen input datasets and report their current size."""

    try:
        datasets = load_datasets()
    except (FileNotFoundError, SchemaValidationError) as exc:
        raise SystemExit(f"Dataset validation failed: {exc}") from exc

    print("Ascend Optimizer MVP data validation passed.")
    print(f"Strategies: {datasets.strategy_count}")
    print(f"Snapshot rows: {datasets.snapshot_count}")


if __name__ == "__main__":
    main()
