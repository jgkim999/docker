# Docker Compose

## Docker install

https://docs.docker.com/engine/install/

[docker-compose.yml](./docker-compose.yml)

```bash
docker-compose up -d
```

## Portainer

https://www.portainer.io/

## MySQL

[MySql](https://www.mysql.com/)

Image
- [mysql](https://hub.docker.com/_/mysql)

Port
- 3306

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

Image
- [rabbitmq](https://hub.docker.com/_/rabbitmq)

Port
- 5672/15672

User/Password
- user/1234

URL
- http://localhost:15672

## Redis

[Redis](https://redis.io/)

Image
- [redis](https://hub.docker.com/_/redis)

Port
- 6379/6380

## Prometheus

[Prometheus](https://prometheus.io/)

Image
- [prometheus](https://hub.docker.com/r/prom/prometheus)

Port
- 9090

URL
- http://localhost:9090

## Grapana

[Grapana](https://grafana.com/)

Image
- [grapana](https://hub.docker.com/r/grafana/grafana)

Port
- 3000

User/Password
- admin/admin

URL
- http://localhost:3000/login

## Influxdb

[Influxdb](https://www.influxdata.com/)

Image
- [influxdb](https://hub.docker.com/_/influxdb)

Port
- 8086

URL
- http://localhost:8086

## Redis benchmarek

```bash
> redis-benchmark -t set,lpush -n 100000 -q

SET: 66445.18 requests per second, p50=0.423 msec
GET: 66577.89 requests per second, p50=0.423 msec
INCR: 66720.05 requests per second, p50=0.423 msec
LPUSH: 66418.70 requests per second, p50=0.423 msec
RPUSH: 66471.69 requests per second, p50=0.423 msec
LPOP: 66299.80 requests per second, p50=0.431 msec
RPOP: 66476.10 requests per second, p50=0.423 msec
SADD: 66992.70 requests per second, p50=0.423 msec
HSET: 66067.66 requests per second, p50=0.423 msec
SPOP: 66997.19 requests per second, p50=0.423 msec
ZADD: 66247.10 requests per second, p50=0.423 msec
ZPOPMIN: 66822.59 requests per second, p50=0.423 msec
LPUSH (needed to benchmark LRANGE): 66106.96 requests per second, p50=0.431 msec
LRANGE_100 (first 100 elements): 51069.92 requests per second, p50=0.527 msec
LRANGE_300 (first 300 elements): 27719.26 requests per second, p50=0.911 msec
LRANGE_500 (first 500 elements): 20118.70 requests per second, p50=1.239 msec
LRANGE_600 (first 600 elements): 17676.28 requests per second, p50=1.399 msec
MSET (10 keys): 65445.03 requests per second, p50=0.447 msec
XADD: 66058.93 requests per second, p50=0.431 msec
```
