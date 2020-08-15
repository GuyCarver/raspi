
import requests
from bs4 import BeautifulSoup
from time import sleep

locprefix = 'https://weather.com/weather/today/l/'
locsuffix = ':4:US'

# tempdivname = '_-_-components-src-organism-TodayDetailsCard-TodayDetailsCard--feelsLikeTemp--2x1SW'
tempdivname = '_-_-components-src-organism-CurrentConditions-CurrentConditions--primary--2DOqs'
conddivname = '_-_-components-src-organism-CurrentConditions-CurrentConditions--phraseValue--mZC_p'

def get( aZip ):
  temp = 0
  cond = ''
  loc = locprefix + str(aZip) + locsuffix

  #We sometimes get different data that we can't parse, so iterate and keep re-trying.
  for x in range(0, 4):
    page = requests.get(loc)
    soup = BeautifulSoup(page.content, 'html.parser')

#'today_nowcard-temp'
#'today_nowcard-phrase'

#these tags contain the data when there is now nowcard, but I don't know how to get it.
#  It's not a 'div'
#  'getSunV3CurrentObservationsUrlConfig'
#  'temperature'
#  'wxPhraseShort'

    tempdiv = soup.find_all('div', class_=tempdivname)
    if len(tempdiv):
      span = tempdiv[0]
      tempstr = span.contents[0].text[:-1] #Get temperature text and remove deg symbol.
      temp = int(tempstr)

      conddiv = soup.find_all('div', class_=conddivname)
      if len(conddiv):
        cond = conddiv[0].text

      break

#    print('try', x)
    sleep(3.0)                                    #Wait 3 seconds before trying again.

  if temp == 0:
    print(soup)
    print("Temp Error:", page.status_code)

  return (temp, cond)


#print('Weather is:', get(21774))
#print('Weather in Rockville is:', get('20850'))
