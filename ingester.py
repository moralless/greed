#! /usr/bin/env python3

# -*- coding: utf-8 -*-

import re
import argparse
import time
import csv
import sys
from bs4 import BeautifulSoup


iataMatcher = re.compile("%B\d*\^[A-Z\/ ]*\^[a-zA-Z0-9 ]*\?", re.IGNORECASE)
iataData = re.compile("(?P<startSentinel>%)"
                      "(?P<formatCode>[A-Z])"
                      "(?P<accountNumber>[0-9]{1,19})"
                      "(?P<fieldSeparator>\^)"
                      # "(?P<countryCode>[0-9]{3})"
                      "(?P<accountHolder>[A-Z\/ ]{2,26})"
                      "(?P<fieldSeperator>\^)"
                      "(?P<expiryDate>[0-9]{4})"
                      "(?P<serviceCode>[0-9]{3})"
                      "(?P<pvv>[0-9]{5})"
                      "(?P<discretionary>[0-9A-Z ]*)"
                      "(?P<endSentinel>\?)", re.IGNORECASE)
abaMatcher = re.compile(";\d*\=\d*\?", re.IGNORECASE)
abaData = re.compile("(?P<startSentinel>\;)"
                     "(?P<accountNumber>[0-9]{1,19})"
                     "(?P<fieldSeparator>\=)"
                     # "(?P<countryCode>[0-9]{3})"
                     "(?P<expiryDate>[0-9]{4})"
                     "(?P<serviceCode>[0-9]{3})"
                     "(?P<pvv>[0-9]{5})"
                     "(?P<discretionaryData>[0-9A-Z]*)"
                     "(?P<endSentinel>\?)", re.IGNORECASE)


def getText(keyfile):
    """
    Extracts text from specified input file
    @params:
        keyfile   - Required  : file to process (file)
    """
    try:
        soup = BeautifulSoup(keyfile, "html.parser")
        for script in soup(["script", "style"]):
            script.extract()
        return soup.get_text()
    except:
        return ""


def print_progress(iteration, total, prefix='', suffix='', decimals=1, bar_length=50):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : number of decimals in percent complete (Int)
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


def main():
    '''Entry point if called as an executable'''

    # record start time for benchmarking
    start_time = time.perf_counter()

    # parse argument vector
    parser = argparse.ArgumentParser(description="extract payment card information"
                                     " from MSR swipes recorded in keystroke logs")
    parser.add_argument("file", nargs="+",
                        help="file or files to extract tracks from")
    parser.add_argument("-o", "--output", type=argparse.FileType('w'),
                        help="path to output file", default=sys.stdout)
    parser.add_argument("-d", "--database", action="store_true",
                        help="import tracks to database")
    parser.add_argument("-c", "--console", action="store_true",
                        help="output to console")
    parser.add_argument("-v", "--verbose", action="count", default=0,
                        help="increase output verbosity")
    args = parser.parse_args()

    iataTracks = []
    abaTracks = []
    numFiles = len(args.file)
    print("Extracting tracks from input files:")
    print_progress(0, numFiles)
    for i, iFile in enumerate(args.file):
        currentFile = open(iFile)
        haystack = getText(currentFile)
        iataTracks.extend(iataMatcher.findall(haystack))
        abaTracks.extend(abaMatcher.findall(haystack))
        currentFile.close()
        print_progress(i + 1, numFiles)
    # remove duplicates
    iataTracks = set(iataTracks)
    abaTracks = set(abaTracks)

    # parse tracks and output
    if args.console:
        writer = csv.writer(args.output, quoting=csv.QUOTE_ALL, delimiter=',')
        for track in iataTracks:
            trackData = iataData.search(track)
            if trackData:
                writer.writerow(trackData.groups())

    if args.database:
        import sqlite3 as sqlite

        try:
            dbConnection = sqlite.connect('rippem.db')
            cur = dbConnection.cursor()

            cur.executescript("""
                    DROP TABLE IF EXISTS cards;
                    CREATE TABLE cards(
                    iataTrack TEXT,
                    accountNumber INT,
                    accountHolder TEXT,
                    expiryDate INT,
                    serviceCode INT,
                    pvv INT,
                    discretionary TEXT);
                    """)

            numTracks = len(iataTracks)
            print("Writing tracks to database:")
            print_progress(0, numTracks)
            for i, track in enumerate(iataTracks):
                trackData = iataData.search(track)
                if trackData:
                    cur.execute("""
                        INSERT INTO cards VALUES(
                        :iataTrack,
                        :accountNumber,
                        :accountHolder,
                        :expiryDate,
                        :serviceCode,
                        :pvv,
                        :discretionary)
                        """,
                                {"iataTrack": track,
                                 "accountNumber": trackData.group('accountNumber'),
                                 "accountHolder": trackData.group('accountHolder'),
                                 "expiryDate": trackData.group('expiryDate'),
                                 "serviceCode": trackData.group('serviceCode'),
                                 "pvv": trackData.group('pvv'),
                                 "discretionary": trackData.group('discretionary')
                                 })
                print_progress(i+1, numTracks)
            dbConnection.commit()

        except:
            print("Incompatible database!")
            if dbConnection:
                dbConnection.rollback()
            sys.exit(1)

        finally:
            if dbConnection:
                dbConnection.close()

    # print debugging information
    if args.verbose >= 1:
        print("\nFound " +
              str(len(iataTracks)) + " IATA tracks and " +
              str(len(abaTracks)) + " ABA tracks in " +
              str(len(args.file)) + " files")
    if args.verbose >= 2:
        print("in " + str(time.perf_counter() - start_time) + " seconds")


if __name__ == "__main__":
    main()
