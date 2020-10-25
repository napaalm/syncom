#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import lxml.html as html
import lxml.etree as etree
import requests
from urllib.parse import urljoin

FEED = "paste url here"

def main():
    with requests.Session() as sesh:
        # obtain csrf token from login page
        r = sesh.get("https://nuvola.madisoft.it/login")
        if r.status_code != 200: die("error while fetching login page")
        csrf_token = html.fromstring(r.content).xpath("//input[@name='_csrf_token']/@value")
        # perform log in
        r = sesh.post(
            "https://nuvola.madisoft.it/login_check",
            data={"_csrf_token":csrf_token, "_username":"", "_password":""},
            headers={"Origin":"https://nuvola.madisoft.it", "Referer":"https://nuvola.madisoft.it/login"}
        )
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

def die(reason):
    raise Exception(reason)

if __name__ == "__main__":
    main()
