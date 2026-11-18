FROM eclipse-temurin:11-jre-jammy@sha256:fc9ca245d0e3c125085fd9d12c5cb4fa7aaa68f419ad0f035ef5f75bd37f90e2 AS tool-fetch
ARG HADOOP_VERSION=3.3.6
ARG SPARK_VERSION=3.5.3
ARG PROXY_CA_CERT=""
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && if [ -n "$PROXY_CA_CERT" ]; then printf '%s\n' "$PROXY_CA_CERT" > /usr/local/share/ca-certificates/build-proxy-ca.crt && update-ca-certificates; fi \
    && curl -fsSL "https://archive.apache.org/dist/hadoop/common/hadoop-${HADOOP_VERSION}/hadoop-${HADOOP_VERSION}.tar.gz" -o /tmp/hadoop.tgz \
    && tar -xzf /tmp/hadoop.tgz -C /opt \
    && mv "/opt/hadoop-${HADOOP_VERSION}" /opt/hadoop \
    && rm /tmp/hadoop.tgz \
    && curl -fsSL "https://archive.apache.org/dist/spark/spark-${SPARK_VERSION}/spark-${SPARK_VERSION}-bin-hadoop3.tgz" -o /tmp/spark.tgz \
    && tar -xzf /tmp/spark.tgz -C /opt \
    && mv "/opt/spark-${SPARK_VERSION}-bin-hadoop3" /opt/spark \
    && rm /tmp/spark.tgz \
    && rm -rf /var/lib/apt/lists/*

FROM eclipse-temurin:11-jre-jammy@sha256:fc9ca245d0e3c125085fd9d12c5cb4fa7aaa68f419ad0f035ef5f75bd37f90e2
ENV DEBIAN_FRONTEND=noninteractive \
    HADOOP_HOME=/opt/hadoop \
    SPARK_HOME=/opt/spark \
    JAVA_HOME=/opt/java/openjdk \
    HADOOP_CONF_DIR=/opt/hadoop/etc/hadoop \
    HADOOP_LOG_DIR=/tmp/hadoop-logs \
    YARN_LOG_DIR=/tmp/hadoop-logs \
    YARN_CONF_DIR=/opt/hadoop/etc/hadoop \
    PATH=/opt/spark/bin:/opt/spark/sbin:/opt/hadoop/bin:/opt/hadoop/sbin:$PATH \
    PYSPARK_PYTHON=/usr/bin/python3
RUN apt-get update && apt-get install -y --no-install-recommends \
      bash ca-certificates curl python3 python3-pip procps tini netcat-openbsd \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r hadoop && useradd -r -g hadoop -d /home/hadoop hadoop \
    && mkdir -p /hadoop/dfs/name /hadoop/dfs/data /tmp/hadoop-yarn /tmp/hadoop-logs /workspace/data
COPY --from=tool-fetch /opt/hadoop /opt/hadoop
COPY --from=tool-fetch /opt/spark /opt/spark
COPY docker/hadoop/conf/ /opt/hadoop/etc/hadoop/
COPY docker/hadoop/entrypoint.sh /usr/local/bin/hadoop-entrypoint
RUN chmod +x /usr/local/bin/hadoop-entrypoint \
    && chown -R hadoop:hadoop /opt/hadoop /opt/spark /hadoop /tmp/hadoop-yarn /tmp/hadoop-logs /workspace
WORKDIR /workspace
USER hadoop
ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/hadoop-entrypoint"]
CMD ["bash"]
