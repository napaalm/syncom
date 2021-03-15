#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import argparse
import lxml.html as html
import lxml.etree as etree
import requests
from urllib.parse import urljoin

# regex that matches a comunicato's filename
filename_regex = re.compile(r"^\d+[ _]*-.*\.pdf$")

def main():
    # setup argument parser
    parser = argparse.ArgumentParser(description="Semplice script per scaricare periodicamente i comunicati da nuvola.madisoft.it")
    parser.add_argument("username", metavar="USER", type=str, help="nome utente per il registro")
    parser.add_argument("password", metavar="PASS", type=str, help="password per il registro")
    parser.add_argument("-d", metavar="directory", type=str, default=".", help="directory dove salvare i comunicati (default: .)")
    parser.add_argument("-c", metavar=("nome", "url"), action='append', type=str, nargs=2, help="categoria di comunicati")

    # parse arguments
    args = parser.parse_args()

    # error out if no category is specified
    if not args.c:
        parser.error("nessuna categoria specificata!")

    # parse categories
    categories = {name:url for (name, url) in args.c}

    with requests.Session() as sesh:
        # obtain csrf token from login page
        r = sesh.get("https://nuvola.madisoft.it/login")
        if r.status_code != 200: raise Exception("error while fetching login page")
        csrf_token = html.fromstring(r.content).xpath("//input[@name='_csrf_token']/@value")

        # perform log in and check if it's successful
        r = sesh.post(
            "https://nuvola.madisoft.it/login_check",
            data={"_csrf_token": csrf_token, "_username": args.username, "_password": args.password},
            headers={"Origin": "https://nuvola.madisoft.it", "Referer": "https://nuvola.madisoft.it/login"}
        )
        if "credenziali" in r.content.decode(): parser.error("credenziali errate")

        # iterate over all types of comunicati
        for category, url in categories.items():
            # add root directory
            directory = os.path.join(args.d, category)

            # create category's directory if it doesn't exist yet
            if not os.path.exists(directory):
                os.makedirs(directory)

            # get & parse comunicati's list
            r = sesh.get(url)

            # iterate over the links
            for elem in html.fromstring(r.content).xpath("/html/body/div[1]/div[1]/div/div/div[4]/div/form/div[2]/table/tbody")[0].iterlinks():
                try:
                    # open comunicato's page
                    r = sesh.get(elem[2])

                    # extract links and filenames from page
                    dl_page = html.fromstring(r.content)
                    pdf_links = dl_page.xpath("//a[contains(@class, 'download-wrapper')]/@href")
                    filenames = dl_page.xpath("//*[contains(@class, 'file-name')]/div/text()")

                    # find the comunicato among the files using the regex
                    filename, link = next(filter(lambda p: filename_regex.match(p[0]), zip(filenames, pdf_links)))

                    # download and save the file if it doesn't exist
                    file_path = os.path.join(directory, filename)
                    if not os.path.isfile(file_path):
                        # "link" is relative
                        r = sesh.get(urljoin("https://nuvola.madisoft.it", link))
                        with open(file_path, "wb") as f:
                            f.write(r.content)
                # discard invalid links
                except requests.exceptions.MissingSchema:
                    pass
    # TODO handle ANY errors at all

if __name__ == "__main__":
    main()
