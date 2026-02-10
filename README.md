flowbook — a framework for flexible data flows.

## Development

- **CI before commit**: `npm run ci` (lint, typecheck, test) runs automatically via [pre-commit](https://pre-commit.com/). After clone, run:
  ```sh
  poetry install
  pre-commit install
  ```

## License

Apache License 2.0



## Running Postgres with Docker Compose

```sh
docker compose -f infra/compose.postgres.yml --env-file infra/.env.postgres down -v
docker compose -f infra/compose.postgres.yml --env-file infra/.env.postgres up -d
docker compose -f infra/compose.postgres.yml --env-file infra/.env.postgres logs -f
```