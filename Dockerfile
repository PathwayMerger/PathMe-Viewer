FROM python:3.6.5
MAINTAINER Daniel Domingo Fernandez "daniel.domingo.fernandez@scai.fraunhofer.de"

RUN apt-get update
RUN apt-get -y upgrade && apt-get -y install vim p7zip-full

RUN mkdir /home/pathme_viewer /data /data/logs /home/.pathme /home/.pathme/kegg /home/.pathme/reactome /home/.pathme/wikipathways /home/pathme

# Create pathme user
RUN groupadd -r pathme && useradd --no-log-init -r -g pathme pathme

# permission pathme user
RUN chown -R pathme /home/pathme_viewer && chgrp -R pathme /home/pathme_viewer
RUN chown -R pathme /home/.pathme && chgrp -R pathme /home/.pathme
RUN chown -R pathme /home/pathme && chgrp -R pathme /home/pathme

RUN pip3 install --upgrade pip
RUN pip3 install gunicorn

COPY . /opt/pathme_viewer
WORKDIR /opt/pathme_viewer

# Add permission to edit folders
RUN chown -R pathme /opt/pathme_viewer && chgrp -R pathme /opt/pathme_viewer && chmod +x /opt/pathme_viewer/src/bin/*
RUN chown -R pathme /data && chgrp -R pathme /data

RUN pip3 install .

# Add --user python modules to PATH
ENV PATH="/home/pathme_viewer/.local/bin:$PATH"

EXPOSE 5000

# When zipping files in macOS: https://apple.stackexchange.com/questions/239578/compress-without-ds-store-and-macosx

# Download KEGG pickles (Update link if the file is replaced)
ADD https://drive.google.com/uc?authuser=0&id=1zWojODXwQO07t4MGLh6sPNa_-VaxxqNN&export=download /home/pathme/.pathme/kegg/bel.zip
RUN 7z x /home/pathme/.pathme/kegg/bel.zip

# Download Reactome pickles (Update link if the file is replaced)
ADD https://owncloud.scai.fraunhofer.de/index.php/s/dfSdkjAizqgqoj7/download /home/pathme/.pathme/reactome/bel.zip
RUN 7z x /home/pathme/.pathme/reactome/bel.zip

# Download WikiPathways pickles (Update link if the file is replaced)
ADD https://drive.google.com/uc?authuser=0&id=1Gn5CBtwwgCv-pLb7eDd5NNPfGWtuOapd&export=download /home/pathme/.pathme/wikipathways/bel.zip
RUN 7z x /home/pathme/.pathme/wikipathways/bel.zip

# Load data
RUN python3 -m pathme_viewer manage load --yes

# User (only to run bootstrap.sh)
USER pathme

ENTRYPOINT ["/opt/pathme_viewer/src/bin/bootstrap.sh"]
