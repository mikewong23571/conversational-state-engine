"""FastAPI application entry point."""

from api import create_app

app = create_app()


def main() -> None:
    import uvicorn  # type: ignore

    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
