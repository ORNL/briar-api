#syntax=docker/dockerfile:1

FROM docker.io/library/ubuntu:24.04
WORKDIR /briar-python
RUN apt-get update -y
RUN apt-get install -y cmake build-essential libglib2.0-0 libsm6 libxrender1 libxext6 curl ffmpeg libgstrtspserver-1.0-0 gstreamer1.0-rtsp libgstrtspserver-1.0-dev gstreamer1.0-plugins-ugly
RUN curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest | tar -xvj bin/micromamba && export MAMBA_ROOT_PREFIX=/micromamba; eval "$(./bin/micromamba shell hook -s posix)";  ./bin/micromamba shell init -s bash -r /micromamba
ARG MAMBA_DOCKERFILE_ACTIVATE=1 
ENV MAMBA_ROOT_PREFIX=/micromamba
ENV PATH=/micromamba/condabin:/briar-python/bin:$PATH
RUN micromamba self-update && micromamba env create -n briar python=3.11 doxygen libprotobuf=5.* libgrpc protobuf gst-python
COPY . .
RUN micromamba run -n briar python -m pip install -U -e .
RUN micromamba run -n briar ./build-proto-stubs.sh

ENV GI_TYPELIB_PATH=/usr/lib/x86_64-linux-gnu/girepository-1.0
ENV GST_PLUGIN_SYSTEM_PATH_1_0=/usr/lib/x86_64-linux-gnu/gstreamer-1.0

ENTRYPOINT ["micromamba", "run", "-n", "briar", "python", "-m", "briar"]
CMD ["status"]