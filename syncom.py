#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import sys
import time
import logging
import argparse
import requests
import logging.config
import lxml.html as html
import lxml.etree as etree
from datetime import datetime
from urllib.parse import urljoin
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

# regex that matches a comunicato's filename
filename_regex = re.compile(r"^\d+[ _]*-.*\.pdf$")

# log levels
log_level = [logging.ERROR, logging.INFO]

def requests_retry_session(backoff_factor=1, status_forcelist=(500, 502, 504)):
    session = requests.Session()
    retry = Retry(
        total=None,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def login(sesh, username, password):
    logging.info("Eseguo il login")

    # obtain csrf token from login page
    r = sesh.get("https://nuvola.madisoft.it/login")
    if r.status_code != 200: raise Exception("error while fetching login page")
    csrf_token = html.fromstring(r.content).xpath("//input[@name='_csrf_token']/@value")

    # perform log in and check if it's successful
    r = sesh.post(
        "https://nuvola.madisoft.it/login_check",
        data={"_csrf_token": csrf_token, "_username": username, "_password": password},
        headers={"Origin": "https://nuvola.madisoft.it", "Referer": "https://nuvola.madisoft.it/login"}
    )
    if "credenziali" in r.content.decode():
        logging.critical("Credenziali errate")
        exit(1)

    logging.info("Login effettuato")

def main():
    # setup argument parser
    parser = argparse.ArgumentParser(description="Semplice script per scaricare periodicamente i comunicati da nuvola.madisoft.it")
    parser.add_argument("username", metavar="USER", type=str, help="nome utente per il registro")
    parser.add_argument("password", metavar="PASS", type=str, help="password per il registro")
    parser.add_argument("-d", metavar="directory", type=str, default=".", help="directory dove salvare i comunicati (default: .)")
    parser.add_argument("-c", metavar=("nome", "url"), action='append', type=str, nargs=2, help="categoria di comunicati")
    parser.add_argument("-l", metavar="log_file", type=str, default="syncom.log", help="file di log")
    parser.add_argument("-v", "--verbose", action="count", default=0, help="output verboso")

    # parse arguments
    args = parser.parse_args()

    # error out if no category is specified
    if not args.c:
        parser.error("Nessuna categoria specificata!")

    # initialize logging
    logging.config.dictConfig({
        "formatters": {
            "default": {
                "format": "[%(asctime)s %(levelname)s] %(message)s",
                "style": "%",
                "datefmt": "%d/%m/%Y %H:%M:%S",
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "level": log_level[args.verbose],
            },
            "file": {
                "backupCount": 10,
                "class": "logging.handlers.RotatingFileHandler",
                "filename": args.l,
                "formatter": "default",
                "maxBytes": 1 << 20,
                "level": logging.ERROR,
            },
        },
        "root": {
            "handlers": [
                "console",
                "file",
            ],
            "level": logging.NOTSET,
        },
        "version": 1,
    })

    # parse categories
    categories = {name:url for (name, url) in args.c}
    logging.info(f"Categorie: {categories}")

    try:
        with requests_retry_session() as sesh:
            # perform login
            login(sesh, args.username, args.password)

            # sync comunicati every 5 minutes
            while True:
                # login again if session has expired
                r = sesh.get("https://nuvola.madisoft.it")
                if "credenziali" in r.content.decode():
                    logging.info("Accesso scaduto...")
                    login(sesh, args.username, args.password)

                logging.info("Scarico i nuovi comunicati")
                # iterate over all types of comunicati
                for category, url in categories.items():
                    # add root directory
                    directory = os.path.join(args.d, category)

                    # create category's directory if it doesn't exist yet
                    if not os.path.exists(directory):
                        logging.info(f"Cartella {directory} non esistente. Creazione in corso...")
                        os.makedirs(directory)

                    # get & parse comunicati's list
                    r = sesh.get(url)

                    # iterate over the links
                    for elem in html.fromstring(r.content).xpath("/html/body/div[1]/div[1]/div/div/div[4]/div/form/div[2]/table/tbody")[0].iterlinks():
                        try:
                            # open comunicato's page
                            comunicato_link = elem[2]
                            r = sesh.get(comunicato_link)

                            # extract date, links and filenames from page
                            dl_page = html.fromstring(r.content)
                            pdf_links = dl_page.xpath("//a[contains(@class, 'download-wrapper')]/@href")
                            filenames = dl_page.xpath("//*[contains(@class, 'file-name')]/div/text()")
                            date = datetime.strptime(dl_page.xpath("/html/body/div[1]/div[1]/div/div/div[2]/div[1]/div[1]/div[2]")[0].text.strip(), "%d/%m/%Y")

                            # find the comunicato among the files using the regex
                            filename, pdf_link = next(filter(lambda p: filename_regex.match(p[0]), zip(filenames, pdf_links)))

                            # "pdf_link" is relative
                            pdf_link = urljoin("https://nuvola.madisoft.it", pdf_link)

                            # download and save the file if it doesn't exist
                            file_path = os.path.join(directory, filename)
                            if not os.path.isfile(file_path):
                                r = sesh.get(pdf_link)
                                with open(file_path, "wb") as f:
                                    logging.info(f"Salvataggio del file {file_path} in corso...")
                                    f.write(r.content)
                                    logging.info("File salvato con successo!")

                                # set file creation date
                                os.utime(file_path, (time.time(), date.timestamp()))
                        # discard invalid links
                        except requests.exceptions.MissingSchema:
                            pass
                        # log missing comunicato files
                        except StopIteration:
                            logging.error(f"Impossibile estrarre il comunicato al link {comunicato_link}")

                # sleep for 5 minutes
                logging.info("Attendo 5 minuti...")
                time.sleep(300)
    except KeyboardInterrupt:
        logging.info("Uscita...")
        exit(0)

if __name__ == "__main__":
    # print program info
    print(f"syncom {__version__}")
    print(__copyright__)
    print()

    # emergency recovery
    while True:
        try:
            main()
        # log any unhandled exception
        except Exception as e:
            logging.exception(e)
