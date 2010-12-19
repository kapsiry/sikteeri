REQUIREMENTS
============

* django (1.2, known not to work on older versions)
* simplejson
* pysqlite, if using Python < 2.5
* gettext

The virtualenv install script installs everything but the Python sqlite
extension.

HOW TO RUN
==========

# Create virtualenv environment
./install-virtualenv.sh

# Create local configuration
cp sikteeri/local_settings.py.template sikteeri/local_settings.py

# Set at least a secret key, preferably a working email address too
$EDITOR sikteeri/local_settings.py

# init virtualenv and set PYTHONPATH=.. (added to activate script in install)
source env/bin/activate

# Compile translations
./run-sikteeri.sh
