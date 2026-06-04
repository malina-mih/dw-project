from app.database import ensure_indexes, get_database
from app.repository import WarehouseRepository
from app.sample_data import ingest_payload, sample_payload


def main() -> None:
    db = get_database()
    ensure_indexes(db)
    counts = ingest_payload(WarehouseRepository(db), sample_payload())
    print(f"Inserted: {counts}")


if __name__ == "__main__":
    main()
