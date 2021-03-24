#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# syncom
# Semplice script per scaricare periodicamente i comunicati da nuvola.madisoft.it
#
# Copyright (C) 2021 Antonio Napolitano
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import os
import re
import sys
import time
import logging
import argparse
import requests
import unicodedata
import logging.config
import lxml.html as html
import lxml.etree as etree
from datetime import datetime
from urllib.parse import urljoin
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

__author__ = "Antonio Napolitano"
__copyright__ = f"Copyright (C) 2021 {__author__}"
__license__ = "GNU General Public License 3"

# __version__ is already defined when this script is packaged
if not "__version__" in vars():
    __version__ = "git-source"

# regex that matches a comunicato's filename
filename_regex = re.compile(r"^\d+[ _]*-.*\.pdf$")

# log levels
log_level = [logging.ERROR, logging.INFO]

# base path for data (this way of getting it is to ensure that it works also when packaged)
try:
    # PyInstaller creates a temp folder and stores path in _MEIPASS
    base_path = sys._MEIPASS
except Exception:
    base_path = os.path.abspath(".")

# read error pdf file
with open(os.path.join(base_path, "error.pdf"), "rb") as error_pdf_file:
    error_pdf = error_pdf_file.read()

def slugify(value, allow_unicode=False):
    """
    Taken from https://github.com/django/django/blob/master/django/utils/text.py
    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single dashes. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Convert to lowercase. Also strip leading and
    trailing whitespace, dashes, and underscores.
    """
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize('NFKC', value)
    else:
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value.lower())
    return re.sub(r'[-\s]+', '-', value).strip('-_')

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
        sys.exit(1)

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

                            try:
                                # find the comunicato among the files using the regex
                                filename, pdf_link = next(filter(lambda p: filename_regex.match(p[0]), zip(filenames, pdf_links)))

                                # "pdf_link" is relative
                                pdf_link = urljoin("https://nuvola.madisoft.it", pdf_link)

                                # download the file
                                r = sesh.get(pdf_link)
                                pdf = r.content
                            # handle missing comunicato files by saving a special pdf file
                            except StopIteration:
                                logging.error(f"Impossibile estrarre il comunicato al link {comunicato_link}")

                                # construct a filename from the page title
                                title = dl_page.xpath("/html/body/div[1]/div[1]/div/div/div[1]/div[1]/h3")[0].text
                                filename = slugify(title) + ".pdf"
                                pdf = error_pdf

                            # download and save the file if it doesn't exist
                            file_path = os.path.join(directory, filename)
                            if not os.path.isfile(file_path):
                                with open(file_path, "wb") as f:
                                    logging.info(f"Salvataggio del file {file_path} in corso...")
                                    f.write(pdf)
                                    logging.info("File salvato con successo!")

                                # set file creation date
                                os.utime(file_path, (time.time(), date.timestamp()))
                        # discard invalid links
                        except requests.exceptions.MissingSchema:
                            pass

                # sleep for 5 minutes
                logging.info("Attendo 5 minuti...")
                time.sleep(300)
    except KeyboardInterrupt:
        logging.info("Uscita...")
        sys.exit(0)

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
