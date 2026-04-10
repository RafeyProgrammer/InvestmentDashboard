import matplotlib.pyplot as plt
import numpy as np
import requests

"""Objective: Create a program to provide a visual monthly update to our clients portolios
Key requirements:
	- Show m/m change in portfolio value
	- provide p/l for current investments
	- Use Trading212 API
	- Provide visual breakdown of clients assets & any changes during month
	- provide interest earnings on cash
"""

API_KEY = "1372668ZfmqivQMlCDBuCQZfsdQIrDbtWXEk"
url = "https://live.trading212.com/api/v0/equity/account/summary"
headers = {"Authorization": API_KEY}

response = requests.get(url,headers=headers,auth=("forexrafe@gmail.com","__Trader__123"))

if response.status_code == 200:
	data = response.json()
	print(data)
elif response.status_code == 401:
	headers = {"Authorization": f"Bearer{API_KEY}"}
	response = requests.get(url,headers=headers)
	print(response)
else:
	print(f"Error!: {response.status_code}")
	print(response.text)

