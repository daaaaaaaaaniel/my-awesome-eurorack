# Linux environment for the pipeline, close to the cloud containers of Sept / early Oct 2026: Ubuntu, mawk as awk,
# GNU coreutils, python3 with openpyxl / xlrd / Pillow, LibreOffice for .ods BOMs. Deliberately no `unzip` binary
# (scripts read zips with Python zipfile). Used to check that a rule change made on macOS leaves Linux output unchanged.
#   docker build -t eurorack-linux -f docker/linux.Dockerfile docker
#   docker run --rm -v "$PWD":/repo -w /repo eurorack-linux python3 data/rerun_rows.py --ids=p01,p217
FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive LANG=C.UTF-8
RUN apt-get update && apt-get install -y --no-install-recommends \
      bash ca-certificates curl git mawk python3 python3-openpyxl python3-xlrd python3-pil \
      poppler-utils libreoffice-calc-nogui \
 && apt-get remove -y unzip || true \
 && rm -rf /var/lib/apt/lists/*
RUN git config --global --add safe.directory /repo
