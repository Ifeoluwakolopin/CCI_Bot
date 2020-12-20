import requests
from datetime import date as dt
from bs4 import BeautifulSoup

def cci_sermons():

    headers = {
    'user-agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36'
    }

    base_url = 'http://ccing.org/sermons/'
    r = requests.get(base_url, headers=headers)
    soup = BeautifulSoup(r.text, 'html.parser')
    sermons_section = soup.find_all('article')
    sermons = []

    for sermon in sermons_section[0:4]:
        try:
            image = sermon.find('img').get('src')
            title = sermon.find('h3', {'class':'cmsmasters_sermon_title entry-title'}).find('a').text
            link = sermon.find('h3', {'class':'cmsmasters_sermon_title entry-title'}).find('a').get('href')
            download = sermon.find('a', {'class':'cmsmasters_sermon_media_item cmsmasters_theme_icon_sermon_download'}).get('href')
            video = sermon.find('a', {'class':'cmsmasters_sermon_media_item cmsmasters_theme_icon_sermon_video'}).get('href')  
            sermons.append({
                "title":title,
                "download":download,
                "video":video,
                "link":link,
                "image":image})
        except:
            sermons.append({
                "title":title,
                "download":download,
                "link":link,
                "image":image,
                "video":None})
    return sermons

def t30():

    headers = {
    'user-agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36'
    }

    base = 'http://triumph30.org'
    r = requests.get(base, headers=headers)
    soup = BeautifulSoup(r.text, 'html.parser')
    
    title = soup.find('h3', {'class':'entry-title td-module-title'}).find('a').text
    link = soup.find('h3', {'class':'entry-title td-module-title'}).find('a').get('href')
    image = soup.find('div', {'class':'td-module-thumb'}).find('img').get('src')
    excerpt = soup.find('div', {'class':'td-excerpt'}).text.strip()
    date = str(dt.today())

    d = {"title":title,
        "link":link,
        "image":image,
        "date":date,
        "excerpt":excerpt}

    return d

print(t30())