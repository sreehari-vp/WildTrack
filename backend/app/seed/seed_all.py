from backend.app.seed.mongodb_seed import seed_mongodb
from backend.app.seed.postgres_seed import seed_postgres


def main() -> None:
    seed_postgres()
    seed_mongodb()
    print("WildTrack database seed complete.")


if __name__ == "__main__":
    main()
