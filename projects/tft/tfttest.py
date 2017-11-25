import logging
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG) #CHANGE TO DEBUG TO SEE MORE
logging.basicConfig(level=logging.DEBUG)

handler = logging.FileHandler('fbtft.log')
handler.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

log.addHandler(handler)

log.info("Define modules...")
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(23, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
import sys,pygame,time,subprocess,os,datetime,urllib2
from pygame.locals import *
import re
from netcheck import *
net=netcheck("https://www.google.com")
log.debug("Define modules...OK")

log.info("Setting /dev/fb1...")
os.putenv('SDL_FBDEV','/dev/fb1') #Which framebuffer?
pygame.init()
log.debug("Setting /dev/fb1...OK")

''' Defines '''
log.debug("Define fonts, colors")
deleteme = pygame.font.SysFont('mono', 20, bold=True)
clockfont = pygame.font.SysFont('mono',16,bold=True)
sfont = pygame.font.SysFont('mono',17, bold=True)
ssfont = pygame.font.SysFont('mono',14, bold=True)

csfont = pygame.font.SysFont('Arial',10, bold=True)
mfont = pygame.font.SysFont('mono',20, bold=False)
bfont = pygame.font.SysFont('mono',30, bold=False)

size = w, h = 160, 128
log.info("Starting in " + str(size))
screen = pygame.display.set_mode(size)
pygame.mouse.set_visible(False)
log.debug("Starting...OK")

### RGB Colors
black = 0,0,0
white = 255,255,255
red = 255,0,0
dred = 127,0,0
green = 0,255,0
blue = 0,0,255
goodgrade = 0,255,190
### Custom Colors
bg = 50,65,60

theme = 2
log.info("Selected theme: " + str(theme))
'''
themes:
    1. Standard green
    2. green changed

    3. Standard red
    4. red changed

    5. Standard blue
    6. blu changed
'''
if theme > 6:
    theme = 1
if theme == 1:
    green = 80,210,155
    dgreen = 60,155,120
elif theme == 2:
    green = 60, 155, 120
    dgreen = 80, 210, 155
elif theme == 3:
    green = 127,0,0
    dgreen = 255,0,0
elif theme == 4:
    green = 255,0,0
    dgreen = 127,0,0
elif theme == 5:
    green = 0,0,127
    dgreen = 0,0,255
elif theme == 6:
    green = 0,0,255
    dgreen = 0,0,127
log.debug("Used theme: " + str(theme))
''' end of defines '''

wi=screen.get_width()
he=screen.get_height()
log.debug("Resolution: " + str(wi) + "x" + str(he))
def filelen(fname):
    with open(fname) as f:
        for i, l in enumerate(f):
            pass
    return i
def notification(showorhide):

    upio =  pygame.image.load('/home/pi/scr/t.png')
    if showorhide == "1":
        for x in xrange(1,40,10):
            pygame.draw.circle(screen,dgreen,[160,64],x)
            screen.blit(upio,(160-x,48))
            pygame.display.update()
            time.sleep(0.1)
    elif showorhide == "2":
        for x in xrange(1,40,10):
            pygame.draw.rect(screen,bg,[125,32,35,64])
            pygame.draw.circle(screen,green,[160,64],31-x)
            screen.blit(upio,(130+x,48))
            pygame.display.update()
            time.sleep(0.1)
def animation():
    defa1= 0
    defa2= 160
    defa3 = 128
    defa4 = defa1
    detaillevel = 10
    for x in xrange(1,25):
        defa3 = defa3 - detaillevel
        pygame.draw.line(screen,dgreen,[0,defa3],[160,128])
        pygame.display.update()
        time.sleep(0.01)
def nameofdayweek(n):

    names=['Mon','Tue','Wed','Thu','Fri','Sat','Sun']
    time=datetime.datetime.now()
    wkd=time.weekday()
    if n == "nsd": #Next school day
        if wkd > 4:
            wkd=0
    else:
        wkd = wkd + int(n)
        if wkd > 6:
            wkd = wkd - 7
    log.debug("Day of week: " + names[wkd])
    try:
        return names[wkd]
    except:
        return "Can't return more days than 8"

def somactive():
    log.debug("Somactive?")
    fsom = "/home/pi/AIOKS/forwwwsom.txt"
    factive = open(fsom)
    factivel = factive.readlines()
    factives = factivel[0]
    factive.close()
    if factives == "som yes":
        log.debug("Somactive? Yes")
        return True
    else:
        log.debug("Somactive? Nope")
        return False
def bluactive():
    log.debug("Bluactive?")
    fsom = "/home/pi/AIOKS/forwwwblu.txt"
    factive = open(fsom)
    factivel = factive.readlines()
    factives = factivel[0]
    factive.close()
    if factives == "blu yes":
        log.debug("Bluactive? Yes")
        return True
    else:
        return False
        log.debug("Bluactive? Nope")
def debugl():
    defa1 = 0
    defa2 = 160
    defa3 = 128
    defa4 = defa1
    detaillevel = 10
    for x in xrange(1,16):
        defa1 = defa1 + detaillevel
        pygame.draw.line(screen,red,[0,defa1],[160,128])
        defa2=defa2-detaillevel
        pygame.draw.line(screen,dred,[0,0],[defa2,128])

        defa3 = defa3 - detaillevel
        pygame.draw.line(screen,blue,[0,0],[160,defa3])
        defa4=defa4+detaillevel
        pygame.draw.line(screen,white,[defa4,0],[160,128])
        pygame.display.update()
        time.sleep(0.1)
    time.sleep(1.5)
def startup():
##
    log.info("Startup, debug")
    version = '1.0.0'
    log.info("Version: " + version)
    debugbg = 0,0,0
    debugfr = 0,255,0
    debugfont = pygame.font.SysFont('console',14, bold=True)
    screen.fill(debugbg)
    pygame.display.flip()
    l=debugfont.render("Ver " + version,1,(debugfr))
    lp = (0,0)
    screen.blit(l,lp)
    l=debugfont.render("Running on RPi",1,(debugfr))
    lp = (0,15)
    screen.blit(l,lp)

    pygame.display.update()
    time.sleep(1)
    screen.fill(debugbg)
    pygame.display.flip()
    #debugl()

##
    screen.fill(bg)
    pygame.display.flip()
    ab=wi/2-45
    bb=he/2-10
    ae=wi/2+10
    be=he/2-35
    pygame.draw.rect(screen,green,(ab,bb,ae,be))

    ab=wi/2-45
    bb=he/2+10

    ae=wi/2+10
    be=he/2-55
    pygame.draw.rect(screen,dgreen,(ab,bb,ae,be))
    l=deleteme.render("KACZPER",1,(white))
    lp = l.get_rect(centerx=wi/2, centery=he/2)
    screen.blit(l,lp)
    pygame.display.update()
    time.sleep(1)


def drawtime():
    log.info("Draw time!")
    ab=wi/2+30 ### clock begin
    bb=he/2-65
    ae=wi/2+30
    be=he/2-45
    pygame.draw.rect(screen,green,(ab,bb,ae,be))
    ab=wi/2+30
    bb=he/2-48
    ae=wi/2+30
    be=he/2-60
    pygame.draw.rect(screen,dgreen,(ab,bb,ae,be)) ###clock end

    time=datetime.datetime.now()
    h=time.hour
    m=time.minute
    if m < 10:
        m = "0" + str(m)
    time_to_draw = str(h) + ":" + str(m)
    l=clockfont.render(time_to_draw,1,(white))
    lp= (wi/2+30, he/2-65)
    screen.blit(l,lp)
    pygame.display.update()
def clear():
    log.info("Clear screen")
    screen.fill(bg)
    pygame.display.update()

def drawmenu():
    log.info("Draw menu")
    ab=wi/2+30 ### clock begin
    bb=he/2-65
    ae=wi/2+30
    be=he/2-45
    pygame.draw.rect(screen,green,(ab,bb,ae,be))
    ab=wi/2+30
    bb=he/2-48
    ae=wi/2+30
    be=he/2-60
    pygame.draw.rect(screen,dgreen,(ab,bb,ae,be)) ###clock end

    ab=wi-wi ### name of menu
    bb=he-28
    ae=wi/2+10#->
    be=he-108
    pygame.draw.rect(screen,green,(ab,bb,ae,be))

    ab=wi-wi#->
    bb=he-8 #120
    ae=wi/2+10#->
    be=he
    pygame.draw.rect(screen,dgreen,(ab,bb,ae,be)) ###menu end

    pygame.display.update()
def menuloc(nr):
    log.info("Location get")
    menuimg=pygame.image.load('/home/pi/scr/location/a'+str(nr)+'.png')
    screen.blit(menuimg,(wi-68,he-8))
def menu1():
    log.info("Menu 1")
    l=sfont.render("Services",1,(white)) ### text
    ab=wi-wi+3
    bb=he-28
    lp=(ab,bb)
    screen.blit(l,lp) ### end text
    menuloc(1) ### nr

    somico=pygame.image.load("/home/pi/scr/somico.png")
    screen.blit(somico,(0,0))
    if somactive() == True:
    #x=False #deleteme
    #if x == True:
        somstatus=pygame.image.load("/home/pi/scr/active.png")
        screen.blit(somstatus,(32,0))
    else:
        somstatus=pygame.image.load("/home/pi/scr/off.png")
        screen.blit(somstatus,(32,0))

    bluico=pygame.image.load("/home/pi/scr/bluico.png")
    screen.blit(bluico,(0,35))
    if bluactive() == True:
    #if x==True:
        blustatus=pygame.image.load("/home/pi/scr/active.png")
        screen.blit(blustatus,(32,35))
    else:
        blustatus=pygame.image.load("/home/pi/scr/off.png")
        screen.blit(blustatus,(32,35))
    pygame.display.update()
def menu2():
    log.info("Menu 2")
    l=sfont.render("Som Plan",1,(white))
    ab=wi-wi+3
    bb=he-28
    lp=(ab,bb)
    screen.blit(l,lp)
    menuloc(2)

    ab=0 ### day
    bb=0
    ae=40
    be=17
    pygame.draw.rect(screen,green,(ab,bb,ae,be))

    ab=0 ### day begin
    bb=17
    ae=40
    be=5
    pygame.draw.rect(screen,dgreen,(ab,bb,ae,be))
    l=sfont.render(str(nameofdayweek("nsd")),1,(white))
    ab=5
    bb=0
    lp=(ab,bb)
    screen.blit(l,lp)

    targe = open(somles)
    targel = targe.readlines()
    #rooster
    for x in xrange(0,filelen(somles)):
        l=csfont.render("-"+targel[x],1,(white))
        #l=csfont.render(str(x) + ". TEST" + str(x),1,(white))
        b=20+x*10
        ab=wi-wi
        bb=he-he+b
        lol=0
        lp=(ab,bb)
        screen.blit(l,lp)
    targe.close()
    pygame.display.update()
def menu3():
    log.info("Menu 3")
    l=sfont.render("Som HW",1,(white))
    ab=wi-wi+3
    bb=he-28
    lp=(ab,bb)
    screen.blit(l,lp)
    menuloc(3)
    pygame.display.update()

    ab=0 ### day
    bb=0
    ae=40
    be=17
    pygame.draw.rect(screen,green,(ab,bb,ae,be))

    ab=0 ### day begin
    bb=17
    ae=40
    be=5
    pygame.draw.rect(screen,dgreen,(ab,bb,ae,be))
    l=sfont.render("Mon",1,(white))
    ab=5
    bb=0
    lp=(ab,bb)
    screen.blit(l,lp)

    #homework
    for x in xrange(1,9):
        l=csfont.render(str(x) + ". 221 - Wou - Gescheidenis" + str(x),1,(white))
        b=10+x*10
        ab=wi-wi
        bb=he-he+b
        lol=0
        lp=(ab,bb)
        screen.blit(l,lp)
    pygame.display.update()
login = "154355"
passs = "UY963ze[+"
school = "hethooghuis"
nr = "19XH"
somgrades = "grades.bk"
somgem = "grades.gem"
somles = "les.som"
def menu4():
    log.info("Menu 4")
    l=ssfont.render("Som Grades",1,(white))
    ab=wi-wi+3
    bb=he-25
    lp=(ab,bb)
    screen.blit(l,lp)
    menuloc(4)
    pygame.display.update()


    ab=0 ### gem
    bb=0
    ae=40
    be=17
    pygame.draw.rect(screen,green,(ab,bb,ae,be))

    ab=0 ### newset end
    bb=17
    ae=40
    be=5
    pygame.draw.rect(screen,dgreen,(ab,bb,ae,be))
    ### count gem
    targett = open(somgrades)
    targetl = targett.readlines()
    newest=targetl[0]
    fou = re.findall('([\d.]+)',newest)
    fou = str(fou).replace("]","")
    fou = str(fou).replace("[","")
    fou = str(fou).replace("'","")

    geme = fou

    if geme >= 5.5:
        l=sfont.render(str(geme),1,(goodgrade))
    else:
        l=sfont.render(str(geme),1,(red))
    ab=5
    bb=0
    lp=(ab,bb)
    screen.blit(l,lp)

    #grades
    targett = open(somgrades)
    target_l = targett.readlines()
    for x in xrange(0,7):
        l=csfont.render("-"+target_l[x][:-1],1,(white))
        b=10+x*10
        ab=wi-wi
        bb=he-he+b+15
        lol=0
        lp=(ab,bb)
        screen.blit(l,lp)
    targett.close()
    pygame.display.update()
def menu5():
    log.info("Menu 5")
    l=ssfont.render("News",1,(white))
    ab=wi-wi+3
    bb=he-25
    lp=(ab,bb)
    screen.blit(l,lp)
    menuloc(5)
    notification("1")
    time.sleep(0.5)
    notification("2")
    pygame.display.update()
startup()
tn = 2
trs = 2
lastm = 5
x = 5
def callbackk(channel):
    print '###########################################Click!'
    global lastm
    global tn
    tn=time.time()+30
    if lastm == 5:
        animation()
        clear()
        drawmenu()
        drawtime()
        menu1()
        lastm = 1
    elif lastm == 1:
        animation()#
        clear()
        drawmenu()
        drawtime()
        menu2()
        lastm = 2
    elif lastm == 2:
        animation()#
        clear()
        drawmenu()
        drawtime()
        menu3()
        lastm = 3
    elif lastm == 3:
        animation()#
        clear()
        drawmenu()
        drawtime()
        menu4()
        lastm = 4
    elif lastm == 4:
        animation()#
        clear()
        drawmenu()
        drawtime()
        menu5()
        lastm = 5
GPIO.add_event_detect(23, GPIO.RISING, callback=callbackk, bouncetime=1700)
while True:
    log.debug(">>>>>>>>>>>Begin of loop")
    drawtime()

    if tn < time.time():
        log.debug("Time up!")
        tn=time.time()+30
        if lastm == 5:
            animation()
            clear()
            drawmenu()
            drawtime()
            menu1()
            lastm = 1
            x = 1
        elif lastm == 1:
            animation()#
            clear()
            drawmenu()
            drawtime()
            menu2()
            lastm = 2
            x = 1
        elif lastm == 2:
            animation()#
            clear()
            drawmenu()
            drawtime()
            menu3()
            lastm = 3
            x = 4
        elif lastm == 3:
            animation()#
            clear()
            drawmenu()
            drawtime()
            menu4()
            lastm =4
        elif lastm == 4:
            animation()#
            clear()
            drawmenu()
            drawtime()
            menu5()
            lastm=5
    else:
        hmt = time.time() - tn
        log.debug("Time left " + str(hmt))

    if trs < time.time():
        log.info("Refreshing grades!")
        if net.checkurl() == True:

            lestime = datetime.datetime.now() #les
            schedulle = 0 #les
            if lestime.weekday() == 6: #les
                schedulle = 2 #les
            elif lestime.weekday() == 7:
                schedulle = 1
            target = open(somgrades, 'w+')
            targetgem = open(somgem, 'w+')
            for grade in som.getgrades():
                target.write(grade["vak"].title() + " (" + grade["resultaat"] + ")\n")
                ### count gem
                gem1 = grade["resultaat"]
                if gem1 == "V":
                    targetgem.write("7.0 O\n")
                elif gem1 == "O":
                    targetgem.write("5.0 O\n")
                elif gem1 == "G":
                    targetgem.write("8.0 O\n")
                else:
                    targetgem.write(gem1+" O\n")
                ### end gem
            target.close()
        trs=time.time()+300
    else:
        tls = time.time() - trs
        log.info("No need to refresh grades.. [TL:" +str(tls)+"]")

    time.sleep(5)