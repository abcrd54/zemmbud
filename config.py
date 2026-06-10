import os
import random
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

def load_cookies():
    cookies = []
    try:
        with open("cookies.txt", "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    if "|" in line:
                        cookies.extend([c.strip() for c in line.split("|") if c.strip()])
                    else:
                        cookies.append(line)
    except FileNotFoundError:
        print("cookies.txt tidak ditemukan!")
    return cookies

def get_random_cookie(cookies):
    return random.choice(cookies) if cookies else None

def parse_cookie_string(cookie_str):
    cookies = {}
    for item in cookie_str.split(";"):
        item = item.strip()
        if "=" in item:
            name, value = item.split("=", 1)
            cookies[name.strip()] = value.strip()
    return cookies
