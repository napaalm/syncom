#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import lxml.html as html
import lxml.etree as etree
import requests
from urllib.parse import urljoin

FEED = "paste url here"

def main():
    # setup argument parser
    parser = argparse.ArgumentParser(description="Semplice script per scaricare periodicamente i comunicati da nuvola.madisoft.it")
    parser.add_argument("username", metavar="USER", type=str, help="nome utente per il registro")
    parser.add_argument("password", metavar="PASS", type=str, help="password per il registro")

    # parse arguments
    args = parser.parse_args()

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

        # get & parse rss feed
        r = sesh.get(FEED)

        for item in etree.fromstring(r.content).find("channel").iterchildren("item"):
            # get link to download page for each item
            page_link = item.find("link").text
            r = sesh.get(page_link)
            try:
                # extract link to pdf and original filename from page
                dl_page = html.fromstring(r.content)
                pdf_link = dl_page.xpath("//a[contains(@class, 'download-wrapper')]/@href")[0]
                pdf_link = urljoin("https://nuvola.madisoft.it", pdf_link)
                name = dl_page.xpath("//*[contains(@class, 'file-name')]/div/text()")[0]
                print(f"{name}\t{pdf_link}")
            except: pass
    # TODO handle ANY errors at all

if __name__ == "__main__":
    main()
