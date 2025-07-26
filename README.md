# Docker Compose

## Docker install

[Install](https://docs.docker.com/engine/install/)

[docker-compose.yml](./docker-compose.yml)

```bash
docker-compose up -d
or
docker compose up -d
```

## MySQL

[MySql](https://www.mysql.com/)

Password

- root / 1234

```sql
CREATE USER 'user1'@'%' IDENTIFIED BY '1234';
GRANT ALL PRIVILEGES ON *.* TO 'user1'@'%';
FLUSH PRIVILEGES;
```

For MySQL Exporter

```sql
CREATE USER 'exporter'@'%' IDENTIFIED BY '1234qwer' WITH MAX_USER_CONNECTIONS 3;
GRANT ALL PRIVILEGES ON *.* TO 'exporter'@'%';
FLUSH PRIVILEGES;
```

Keycloak

```sql
CREATE DATABASE IF NOT EXISTS `keycloak`
USE `keycloak`;

CREATE USER 'keycloak'@'%' IDENTIFIED BY '1234';
GRANT ALL PRIVILEGES ON *.* TO 'keycloak'@'%';
FLUSH PRIVILEGES;
```

## RabbitMQ

[RabbitMQ](https://www.rabbitmq.com/)

User/Password

- user/1234

## Grafana

[Grafana](https://grafana.com/)

User/Password

- admin/admin
