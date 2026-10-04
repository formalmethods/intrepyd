# The REST service of intrepyd, served by gunicorn on port 8000.
#
# Nothing is compiled, nor built from the sources: the image installs the
# linux wheel of intrepyd from dist/, which holds the intrepid library, so
# build the wheel first. The release workflow uses the wheel it has just
# checked; locally:
#   make -f Makefile.docker docker_build
#
# The service itself, app/ and intrepid.py, is not part of the wheel: it is
# copied next to it, and its requirements are the rest group of
# pyproject.toml, which needs pip 25.1 or newer.

FROM python:3.13-slim

ARG VERSION=unknown
LABEL org.opencontainers.image.title="intrepyd" \
      org.opencontainers.image.description="REST service of the intrepyd simulator and model checkers" \
      org.opencontainers.image.source="https://github.com/formalmethods/intrepyd" \
      org.opencontainers.image.url="https://github.com/formalmethods/intrepyd" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.licenses="BSD-3-Clause AND LicenseRef-Intrepid AND MIT"

COPY dist/ /tmp/dist/
COPY pyproject.toml /tmp/pyproject.toml
RUN set -e; \
    wheels=$(ls /tmp/dist/intrepyd-*-manylinux_*_x86_64.whl 2>/dev/null || true); \
    [ "$(echo "$wheels" | grep -c .)" -eq 1 ] || \
        { echo "Error: dist/ must hold exactly one linux wheel of intrepyd, it has: $wheels"; exit 1; }; \
    pip install --no-cache-dir --root-user-action=ignore --upgrade 'pip>=25.1'; \
    cd /tmp && pip install --no-cache-dir --root-user-action=ignore "$wheels" --group rest; \
    rm -fr /tmp/dist /tmp/pyproject.toml

RUN useradd -ms /bin/bash intrepid
WORKDIR /home/intrepid
COPY --chown=intrepid:intrepid app app
COPY --chown=intrepid:intrepid intrepid.py docker/app.sh ./
USER intrepid

EXPOSE 8000
ENTRYPOINT [ "./app.sh" ]
