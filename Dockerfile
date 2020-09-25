FROM python:3

# MAINTAINER Daniel Varab <danielvarab@gmail.com>

# set a directory for the app
# WORKDIR /usr/src/app

RUN cpan install XML::DOM

RUN git -c advice.detachedHead=false clone https://github.com/falcondai/pyrouge/ pyrouge && \
    cd pyrouge && \
    git checkout 9cdbfbda8b8d96e7c2646ffd048743ddcf417ed9 && \
    cd RELEASE-1.5.5/data/WordNet-2.0-Exceptions && \
    ./buildExeptionDB.pl . exc ../WordNet-2.0.exc.db && \
    # cpan install doesn't appear to work inside company networks
    cd /pyrouge && \
    python setup.py build && \
    python setup.py install && \
    pyrouge_set_rouge_path /pyrouge/RELEASE-1.5.5