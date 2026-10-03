#!/bin/bash
source venv/bin/activate
export FLASK_APP=intrepid.py
export FLASK_ENV=development
flask run
exit 0
