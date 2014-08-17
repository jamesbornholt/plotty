First, make sure you have a version of python 2.7 (the subversion doesn't matter):
    $ python --version
    Python 2.7.3
Also make sure you have pip installed (version and path don't matter):
    $ pip --version
    pip 1.0 from /usr/lib/python2.7/dist-packages (python 2.7)
If not, run:
    $ sudo easy_install pip
and try pip again.

Install prerequisites:
    Django:
        $ sudo pip install django==1.2.3
    Gnuplot:
        Use a package manager (brew on OS X, apt-get on Ubuntu):
            $ brew install gnuplot
            or
            $ sudo apt-get install gnuplot
        Or compile manually:
            $ wget https://downloads.sourceforge.net/project/gnuplot/gnuplot/4.6.5/gnuplot-4.6.5.tar.gz
            $ tar xzf gnuplot-4.6.5.tar.gz
            $ cd gnuplot-4.6.5
            $ ./configure
            $ make
            $ sudo make install

Set up the plotty directory:
    $ hg clone ssh://squirrel.moma//home/mercurial/all/shared/plotty
    $ cd plotty
    $ mkdir cache
    $ mkdir cache/csv
    $ mkdir cache/graph
    $ mkdir cache/log
    $ chmod -R a+rw cache
    $ mkdir log

Initialise the database:
    $ python manage.py syncdb
    $ python install_defaults.py

Get a log folder to test with:
    $ scp -r squirrel.moma:/home/james/plotty/test-tip/log/rvm-1046 log/

Run the server:
    $ python manage.py runserver

Go to http://localhost:8000 in your browser and try it out.
