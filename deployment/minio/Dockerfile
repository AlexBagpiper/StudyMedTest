# MinIO from GitHub release when Docker Hub pull is blocked (Reg.ru / some VPS).
# Pin tag to match restored xl meta on existing volumes.
ARG MINIO_RELEASE=RELEASE.2025-09-07T16-13-09Z
FROM alpine:3.20

ARG MINIO_RELEASE
RUN apk add --no-cache ca-certificates curl \
    && curl -fsSL \
      "https://github.com/minio/minio/releases/download/${MINIO_RELEASE}/minio.linux-amd64.${MINIO_RELEASE}" \
      -o /usr/local/bin/minio \
    && chmod +x /usr/local/bin/minio

EXPOSE 9000 9001
ENTRYPOINT ["/usr/local/bin/minio"]
CMD ["server", "/data", "--console-address", ":9001"]
