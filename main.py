import lxml.html as html
import requests

def main():
    r = requests.get("https://nuvola.madisoft.it/login")
    if r.status_code != 200: die("error while fetching login page")

def die(reason):
    raise Exception(reason)

if __name__ == "__main__":
    main()
