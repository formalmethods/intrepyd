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
ADD --chown=intrepid:intrepid intrepyd intrepyd
ADD --chown=intrepid:intrepid app app
COPY --chown=intrepid:intrepid .intrepid/PLATFORM .intrepid/PLATFORM
COPY --chown=intrepid:intrepid requirements.txt setup.py setup.cfg VERSION MANIFEST.in LICENSE.md CREDITS.md README.md intrepid.py docker/app.sh ./

RUN test -f intrepyd/libintrepid.so || \
        { echo 'intrepyd/libintrepid.so is missing: run "make fetch_intrepid" first'; exit 1; } && \
    pip install --no-cache-dir --user . && \
    rm -fr intrepyd .intrepid build intrepyd.egg-info setup.py setup.cfg VERSION MANIFEST.in requirements.txt

EXPOSE 8000
ENTRYPOINT [ "./app.sh" ]
