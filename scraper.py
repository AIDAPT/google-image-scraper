from selenium import webdriver 
from selenium.webdriver.common.by import By 
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.service import Service as ChromeService 
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager 
import time 
import base64
import requests

from doctr.models import ocr_predictor
from doctr.io import DocumentFile
from fuzzysearch import find_near_matches

import os

os.add_dll_directory(r"C:\Program Files\GTK3-Runtime Win64\bin")


def is_receipt(file_path):
    ocr_model = ocr_predictor(pretrained=True)
    ocr_result = ocr_model(DocumentFile.from_images(file_path))

    for page in ocr_result.pages:
        for block in page.blocks:
            for line in block.lines:
                for word in line.words:
                    print(word.value)
                    if len(find_near_matches(word.value, "TOTALE", max_l_dist=2) +
                           find_near_matches(word.value, "IVA", max_l_dist=0, max_insertions=0) +
                           find_near_matches(word.value, "EURO", max_l_dist=0)) > 0:
                        return True

    return False
 
options = webdriver.ChromeOptions() 
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-gpu')
options.add_argument('--disable-web-security')
options.add_argument('--allow-running-insecure-content')
options.add_argument('--allow-cross-origin-auth-prompt')
driver = webdriver.Chrome(service=ChromeService( 
	ChromeDriverManager().install()), options=options)  

# load target website 
tripurl = "https://www.tripadvisor.it/Restaurants-g187768-Italy.html"
 
def isRegion(url):
    driver.get(url)
    try:
        driver.find_element(By.ID,'EATERY_SEARCH_RESULTS')
        return False
    except:    
        return True

def getUrls(url):
    print('check ' + url) 
    driver.get(url)
    places = driver.find_elements(By.CLASS_NAME, 'geo_image') 
    urls = []
    for place in places:
        if place is not None:        
            links = place.find_elements(By.TAG_NAME, 'a')
            for link in links:
                href = link.get_property('href')
                urls.append(href)
    return urls


def scraperRestaurant(url):            
    print('check '+url) 
    driver.get(url)
    restaurantContainer = driver.find_element(By.ID,'EATERY_SEARCH_RESULTS')
    time.sleep(1)
    rowContainer = restaurantContainer.find_elements(By.TAG_NAME,'div')
    restaurants = []
    for row in rowContainer:
        data = row.get_attribute('data-clicksource')
        if data == 'Photo':
            parent = row.find_element(By.XPATH, '..')
            href = parent.get_property('href')
            restaurants.append(href)
    return restaurants            

            
def getRestaurantPhotos(url):
    print('check '+url) 
    driver.get(url+'#photos')
    scroll = 5000
    for i in range(3):
        driver.execute_script("window.scrollBy(0, " + str(scroll) +");")
        scroll_height = driver.execute_script("return document.body.scrollHeight;") 
        time.sleep(5)
        
    album = driver.find_elements(By.CLASS_NAME, 'albumGridItem')
    print(str(i) + ' - ' +  str(scroll_height)+' - '+ str(len(album)))        
    photos = []
    for elem in album:
        photo = elem.find_element(By.TAG_NAME, 'img')
        src = photo.get_attribute('src')
        if src is not None:
            photos.append(src)
    return photos


def analyzePhotos(photos):    
    for photo in photos:
        ext = str(photo).split('.')
        ext.reverse()
        ext = ext[0]
        if ext is not None:
            name = str(round(time.time() * 1000))+ '.'+ext
            print(photo + ' => ' + name)
            try:
                r = requests.get(photo, timeout=3, allow_redirects=True )
                path = 'output/' + name
                with open(path, 'wb') as f:
                    f.write(r.content)
                if not is_receipt(path):
                    os.remove(path)
            except: 
                print('fail '+photo)

def start():
    urls = getUrls(tripurl)
    restaurants = []
    for url in urls:
        if not isRegion(url):
            restaurants = scraperRestaurant(url)
            with open('source/restaurants.txt', 'a') as fp:
                for item in restaurants:
                    # write each item on a new line
                    fp.write("%s\n" % item)
                print('Done, add' + str(len(restaurants)) + ' lines')
                
def startAnalyze():
    with open('source/restaurants.txt', 'r') as fp:
        for item in fp:
            restaurant = item[:-1]
            photos = getRestaurantPhotos(restaurant)            
            analyzePhotos(photos)    
        print('Done')
        
def extractExt(link):    
    ext = str(link).split('.')
    ext.reverse()
    ext = ext[0]
    return ext

def getImageSrc(i, click = True):
    if i == 0:          
        time.sleep(0.5)   
        src = driver.find_element(By.XPATH, '//*[@id="Sva75c"]/div[2]/div/div[2]/div[2]/div[2]/c-wiz/div/div/div/div[3]/div[1]/a/img[1]').get_attribute('src')
    else:
        if click:
            elem = driver.find_element(By.XPATH, '//*[@id="Sva75c"]/div[2]/div/div[2]/div[2]/div[2]/c-wiz/div/div/div/div[2]/div/div[2]/div[1]/div/a[2]')
            elem.click()     
        time.sleep(0.05)
        elem = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="Sva75c"]/div[2]/div/div[2]/div[2]/div[2]/c-wiz/div/div/div/div[3]/div[1]/a/img[1]'))
        )   
        src = elem.get_attribute('src')
        if src is not None:
            if src[0:4] == 'data' or src[0:34] == 'https://encrypted-tbn0.gstatic.com':
                src = getImageSrc(i, False)                
                #ext = str(src).split(';base64')[0].split('/')[1]
    return src

def googleSearch():
    url = 'https://www.google.com/search?q=site%3Atripadvisor.com+receipt&tbm=isch&ved=2ahUKEwigu_Kj6Mz-AhXoh_0HHe9jCe0Q2-cCegQIABAA&oq=site%3Atripadvisor.com+receipt&gs_lcp=CgNpbWcQA1C2CFiGJGD5JmgBcAB4AYAB6wOIAe0NkgEKMTAuMS4wLjEuMZgBAKABAaoBC2d3cy13aXotaW1nwAEB&sclient=img&ei=69tLZOCZOOiP9u8P78el6A4#imgrc=gx4S1W_sRDa7EM'
    driver.get(url)
    elem = WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.XPATH, '//*[@id="yDmH0d"]/c-wiz/div/div/div/div[2]/div[1]/div[4]/div[1]/div[1]/form[2]/div/div/button/span'))
    )    
    elem.click()
    elem = WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.XPATH, '//*[@id="islrg"]/div[1]/div[1]/a[1]/div[1]/img'))
    )   
    elem.click()    
    imgs = []    
    i = 0
    while i < 100:  
        src = getImageSrc(i)
        i+=1                      
        ext = extractExt(src)
        try:
            r = requests.get(src, timeout=3, allow_redirects=True )
            name = str(round(time.time() * 1000))+ '.'+ext
            path = 'output/' + name
            with open(path, 'wb') as f:
                f.write(r.content)        
        except: 
            print('fail '+src)
            #if ext == 'jpeg' or ext == 'jpg':
            #    name = str(round(time.time() * 1000))+ '.'+ext
            #    imgs.append(src)
            #    path = 'output/' + name                
            #    with open(path, 'wb') as f:                    
            #        f.write(base64.urlsafe_b64decode(src.split(',')[1]))
            #        #if not is_receipt(path):
            #        #    os.remove(path)

        
            
    #print(imgs)
    
#start()    
#startAnalyze()

googleSearch()
            