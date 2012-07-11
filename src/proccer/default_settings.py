import os

HOST = '0.0.0.0'
PORT = 32154

DEBUG = True
RELOAD = True

SECRET_KEY = os.environ.get('SECRET_KEY', 'This is a bad secret.')
