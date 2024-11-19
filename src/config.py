"""
Configuration settings for Selfspy
"""

import os

DATA_DIR = os.path.expanduser('~/.selfspy')
DBNAME = 'selfspy.sqlite'
LOCK_FILE = 'selfspy.pid'
LOCK = None

# Activity threshold in seconds
ACTIVE_SECONDS = 180

# Encryption settings
DIGEST_NAME = 'password.digest'