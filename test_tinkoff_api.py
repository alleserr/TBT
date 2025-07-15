from tinkoff.invest import Client
import os
from dotenv import load_dotenv

load_dotenv()
token = os.getenv('TINKOFF_API_TOKEN')
print('Token:', token[:8]+'...')

with Client(token) as client:
    accounts = client.users.get_accounts()
    print('Accounts:', accounts) 