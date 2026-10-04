FROM python:3.13-slim

ENV FLASK_APP=intrepid.py

RUN useradd -ms /bin/bash intrepid

WORKDIR /home/intrepid
USER intrepid
ENV PATH="/home/intrepid/.local/bin:${PATH}"

# Nothing is compiled here: the intrepid library comes prebuilt, and must be
# fetched into intrepyd/ before building the image, with
#   make fetch_intrepid
# .intrepid/PLATFORM records which platform it is for; setup.py needs it.
# The REST service, app/ and intrepid.py, is not part of the package: it stays
# in the working directory, and its requirements are the rest group of
# pyproject.toml, which needs pip 25.1 or newer.
ADD --chown=intrepid:intrepid intrepyd intrepyd
ADD --chown=intrepid:intrepid app app
COPY --chown=intrepid:intrepid .intrepid/PLATFORM .intrepid/PLATFORM
COPY --chown=intrepid:intrepid pyproject.toml setup.py VERSION LICENSE.md CREDITS.md intrepid.py docker/app.sh ./
COPY --chown=intrepid:intrepid docs/pypi.md docs/pypi.md

RUN test -f intrepyd/libintrepid.so || \
        { echo 'intrepyd/libintrepid.so is missing: run "make fetch_intrepid" first'; exit 1; } && \
    pip install --no-cache-dir --user --upgrade 'pip>=25.1' && \
    pip install --no-cache-dir --user . --group rest && \
    rm -fr intrepyd .intrepid build intrepyd.egg-info docs pyproject.toml setup.py VERSION

EXPOSE 8000
ENTRYPOINT [ "./app.sh" ]
