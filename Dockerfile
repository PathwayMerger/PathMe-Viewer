FROM python:3.6.5
MAINTAINER Daniel Domingo Fernandez "daniel.domingo.fernandez@scai.fraunhofer.de"

RUN apt-get update
RUN apt-get -y upgrade && apt-get -y install vim

RUN mkdir /home/pathme_viewer /data /data/logs

RUN groupadd -r pathme && useradd --no-log-init -r -g pathme pathme
RUN chown -R pathme /home/pathme_viewer && chgrp -R pathme /home/pathme_viewer
 

RUN pip3 install --upgrade pip
RUN pip3 install gunicorn

COPY . /opt/pathme_viewer
WORKDIR /opt/pathme_viewer
RUN chown -R pathme /opt/pathme_viewer && chgrp -R pathme /opt/pathme_viewer && chmod +x /opt/pathme_viewer/src/bin/*

RUN chown -R pathme /data && chgrp -R pathme /data

RUN pip3 install .

ENV PATH="/home/pathme_viewer/.local/bin:$PATH"

# User 
USER pathme

ENTRYPOINT ["/opt/pathme_viewer/src/bin/bootstrap.sh"]
#CMD ["tail", "-f", "/proc/meminfo"]