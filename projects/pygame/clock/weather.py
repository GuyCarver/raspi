
import requests
from bs4 import BeautifulSoup

locprefix = 'https://weather.com/weather/today/l/'
locsuffix = ':4:US'

def get( aZip ):
  loc = locprefix + str(aZip) + locsuffix
  page = requests.get(loc)
  soup = BeautifulSoup(page.content, 'html.parser')
  temp = 0
  cond = ''
  tempdiv = soup.find_all('div', class_='today_nowcard-temp')
  if len(tempdiv):
    tempdivspan = tempdiv[0].find_next()
    tempstr = tempdivspan.text[:-1] #Get temperature text and remove deg symbol.
    temp = int(tempstr)

  conddiv = soup.find_all('div', class_='today_nowcard-phrase')
  if len(conddiv):
    cond = conddiv[0].text

  return (temp, cond)


#print('Weather is:', get(21774))
#print('Weather in Rockville is:', get('20850'))
