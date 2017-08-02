#! /usr/bin/env python3

# -*- coding: utf-8 -*-

import sys
import json
import urllib.request
import sqlite3 as sqlite

def print_progress(iteration, total, prefix='', suffix='', decimals=1, bar_length=50):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        bar_length  - Optional  : character length of bar (Int)
    """
    str_format = "{0:." + str(decimals) + "f}"
    percents = str_format.format(100 * (iteration / float(total)))
    filled_length = int(round(bar_length * iteration / float(total)))
    bar = '█' * filled_length + '-' * (bar_length - filled_length)

    sys.stdout.write('\r%s |%s| %s%s %s' % (prefix, bar, percents, '%', suffix)),

    if iteration == total:
        sys.stdout.write('\n')
    sys.stdout.flush()

# TODO check if structure exist
dbConnection = sqlite.connect('rippem.db')
cur = dbConnection.cursor()
cur.executescript("""
        DROP TABLE IF EXISTS binlist;
        CREATE TABLE binlist(
        prefix INT,
        scheme TEXT,
        type TEXT,
        brand TEXT,
        prepaid TEXT,
        country TEXT,
        bankName TEXT,
        bankURL TEXT,
        bankPhone TEXT,
        bankCity TEXT,
        panLength INT)
        """)

# get bins from current card database
cur.execute("SELECT substr(accountNumber,1,8) FROM cards GROUP BY substr(accountNumber,1,8)")
bins = cur.fetchall()
numBins = len(bins)

# update bins using binlist.net
print_progress(0,numBins)
for i, ibin in enumerate(bins):
    with urllib.request.urlopen("https://lookup.binlist.net/" + str(ibin)[2:-3]) as url:
        data = json.loads(url.read().decode())
        cur.execute("""
                INSERT INTO binlist VALUES(
                :prefix,
                :scheme,
                :type,
                :brand,
                :prepaid,
                :country,
                :bankName,
                :bankURL,
                :bankPhone,
                :bankCity,
                :panLength)
                """,
                {"prefix": data['number'].get('prefix', ''),
                    "scheme": data['scheme'],
                    "type": data['type'],
                    "brand": data['brand'],
                    "prepaid": data['prepaid'],
                    "country": data['country'].get('name', ''),
                    "bankName": data['bank'].get('name', ''),
                    "bankURL": data['bank'].get('url', ''),
                    "bankPhone": data['bank'].get('phone', ''),
                    "bankCity": data['bank'].get('city', ''),
                    "panLength": data['number'].get('length', '')})
    dbConnection.commit()
    print_progress(i + 1,numBins)
dbConnection.close()
