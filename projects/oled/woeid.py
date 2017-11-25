
import json
import requests
from bs4 import BeautifulSoup

def get(  ) :
  #Get the zip code for our IP address.
  response = requests.get('http://ipinfo.io/json')
  data = json.loads(response.content.decode("utf-8"))
  postal=data['postal']

  #Get the woeid for our zip code.
  p = requests.get('http://woeid.rosselliot.co.nz/lookup/' + postal)
  soup = BeautifulSoup(p.content, 'html.parser')
  c0 = list(soup.children)
  html = c0[2]
  body = list(html.children)[3]
  all = soup.find_all('td', class_='woeid')
  #we use the 1st entry.  Hopefully that's the correct one.
  return all[0].text

