FROM ctfd/ctfd:3.5.1
COPY ./plugins /opt/CTFd/CTFd/plugins

USER 0
COPY ./docker-entrypoint.sh /opt/CTFd/docker-entrypoint.sh
RUN chown 1001:1001 /opt/CTFd/docker-entrypoint.sh && chmod +x /opt/CTFd/docker-entrypoint.sh
USER 1001

# Empty file makes CTFd egenrate a key on startup
RUN echo -n >/opt/CTFd/.ctfd_secret_key
