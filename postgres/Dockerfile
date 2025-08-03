FROM postgres:17.5

RUN apt-get update && apt-get upgrade -y && \
    ln -sf /usr/share/zoneinfo/Asia/Seoul /etc/localtime && \
    sed -i 's/# ko_KR.UTF-8 UTF-8/ko_KR.UTF-8 UTF-8/' /etc/locale.gen && \
    locale-gen && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

ENV LANG=ko_KR.UTF-8 \
    LC_COLLATE=ko_KR.UTF-8 \
    POSTGRES_INITDB_ARGS=--data-checksums
