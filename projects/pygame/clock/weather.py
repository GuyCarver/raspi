
import requests
from bs4 import BeautifulSoup
from time import sleep

locprefix = 'https://weather.com/weather/today/l/'
locsuffix = ':4:US'

tempdivname='CurrentConditions--primary--2SVPh'
conditiondivname = 'CurrentConditions--phraseValue--2Z18W'

#NOTE: As of 6-11-21 this is really broken. They changed it completely and now
# all I see is temperatures in an array for hourly values.

def get( aZip ):
  temp = 0
  cond = ''
  loc = locprefix + str(aZip) + locsuffix
  #Set this to true to save the web page text to a file for examination.
  savepage = False

  #We sometimes get different data that we can't parse, so iterate and keep re-trying.
  for x in range(0, 1):
    page = requests.get(loc)
    if savepage:
      savepage = False
      with open('weather.txt', 'w') as f:
        f.write(str(page.content))

    soup = BeautifulSoup(page.content, 'html.parser')

    tempdiv = soup.find_all('div', class_=tempdivname)
    if len(tempdiv):
      span = tempdiv[0]
#      print(span.contents[0].text)
      tempstr = span.contents[0].text #Get temperature text and remove deg symbol.
      temp = int(tempstr[:-1])

      conddiv = soup.find_all('div', class_=conditiondivname)
      if len(conddiv):
        span = conddiv[0]
#        print(span)
        cond = span.text
      break
    else:
      print('not found')

#    print('try', x)
    sleep(3.0)                                    #Wait 3 seconds before trying again.

#    if temp == 0:
#     print(soup)
#     print("Temp Error:", page.status_code)

  return (temp, cond)


def getspans( aZip ):
  tempSpan = None
  condSpan = None

  loc = locprefix + str(aZip) + locsuffix
  #Set this to true to save the web page text to a file for examination.
  savepage = False

  #We sometimes get different data that we can't parse, so iterate and keep re-trying.
  for x in range(0, 1):
    page = requests.get(loc)
    if savepage:
      savepage = False
      with open('weather.txt', 'w') as f:
        f.write(str(page.content))

    soup = BeautifulSoup(page.content, 'html.parser')

    tempdiv = soup.find_all('div', class_=tempdivname)
    if len(tempdiv):
      tempSpan = tempdiv[0]

      conddiv = soup.find_all('div', class_=conditiondivname)
      if len(conddiv):
        condSpan = conddiv[0]
      break

  return (tempSpan, condSpan)

#print('Weather is:', get(21774))
#print('Weather in Rockville is:', get('20878'))
