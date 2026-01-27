flowbook — a framework for flexible data flows.

## License

Apache License 2.0



## Running Postgres with Docker Compose

```sh
docker compose -f infra/compose.postgres.yml --env-file infra/.env.postgres down -v
docker compose -f infra/compose.postgres.yml --env-file infra/.env.postgres up -d
docker compose -f infra/compose.postgres.yml --env-file infra/.env.postgres logs -f
```