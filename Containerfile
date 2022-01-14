FROM registry.fedoraproject.org/fedora:34
MAINTAINER Tomas Kopecek <tkopecek@redhat.com>

RUN dnf -y install mariadb postgresql && \
    dnf -y clean all

ADD www /opt/www
ADD dump.sh /opt
ADD requirements.txt /opt

RUN python3 -m venv /opt/venv && \
    . /opt/venv/bin/activate && \
    pip install -r /opt/requirements.txt

EXPOSE 5000
ENTRYPOINT /opt/www/entrypoint.sh
