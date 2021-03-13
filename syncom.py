#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import argparse
import lxml.html as html
import lxml.etree as etree
import requests
from urllib.parse import urljoin

def main():
    # setup argument parser
    parser = argparse.ArgumentParser(description="Semplice script per scaricare periodicamente i comunicati da nuvola.madisoft.it")
    parser.add_argument("username", metavar="USER", type=str, help="nome utente per il registro")
    parser.add_argument("password", metavar="PASS", type=str, help="password per il registro")
    parser.add_argument("-c", metavar=("nome", "url"), action='append', type=str, nargs=2, help="categoria di comunicati")

    # parse arguments
    args = parser.parse_args()

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
            # create category's directory if it doesn't exist yet
            if not os.path.exists(category):
                os.makedirs(category)

            # get & parse comunicati's list
            r = sesh.get(url)

            # iterate over the links
            for elem in html.fromstring(r.content).xpath("/html/body/div[1]/div[1]/div/div/div[4]/div/form/div[2]/table/tbody")[0].iterlinks():
                try:
                    # open comunicato's page
                    r = sesh.get(elem[2])

                    # extract link to pdf and original filename from page
                    dl_page = html.fromstring(r.content)
                    pdf_link = dl_page.xpath("//a[contains(@class, 'download-wrapper')]/@href")[0]
                    pdf_link = urljoin("https://nuvola.madisoft.it", pdf_link)
                    name = dl_page.xpath("//*[contains(@class, 'file-name')]/div/text()")[0]
                    print(f"{name}\t{pdf_link}")

                    # download and save the file
                    r = sesh.get(pdf_link)
                    with open(os.path.join(category, name), "wb") as f:
                        f.write(r.content)
                # discard invalid links
                except requests.exceptions.MissingSchema:
                    pass
    # TODO handle ANY errors at all

if __name__ == "__main__":
    main()
