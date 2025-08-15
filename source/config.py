from dotenv import load_dotenv, find_dotenv
import os
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

load_dotenv(find_dotenv())
TOKEN = os.getenv("TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID"))

API_URL_TEMPLATE = "https://store.tildaapi.com/api/getproductslist/?storepartuid=357127554781&recid=754421136&c=1747853475696&getparts=true&getoptions=true&slice={slice_num}&sort%5B"
