import scrapy, os, logging, time, json
from scrapyrealestate.proxies import *
from scrapy.spiders import CrawlSpider, Rule
from urllib.request import urlopen
from scrapy.linkextractors import LinkExtractor
from datetime import datetime
from bs4 import BeautifulSoup
#from items import ScrapyrealestateItem # ERROR (es confundeix amb items al 192.168.1.100)
from scrapyrealestate.items import ScrapyrealestateItem
from scrapy_playwright.page import PageMethod
from fake_useragent import UserAgent


scrolling_script = """
    const scrolls = 8
    let scrollCount = 0
    let height = 500
    
    // scroll down and then wait for 0.5s
    const scrollInterval = setInterval(() => {
      window.scrollTo(0, height)
      scrollCount++
      height += 500
    
      if (scrollCount === numScrolls) {
        clearInterval(scrollInterval)
      }
    }, 500)
    """


class FotocasaSpider(scrapy.Spider):
    name = "fotocasa"
    allowed_domains = ["fotocasa.es"]

    ua = UserAgent()
    useragent = ua.random   

    
    def start_requests(self):
        #start_urls = [url + '?ordenado-por=fecha-publicacion-desc' for url in self.start_urls]
        logging.info(self.start_urls)

        yield scrapy.Request(self.start_urls,meta={
                    'playwright': True,
                    'playwright_viewport_size': '1740,434',
                    'playwright_page_methods':[
                    PageMethod("wait_for_selector", '#didomi-notice-agree-button'),
                    PageMethod("click", '#didomi-notice-agree-button'),
                    PageMethod("wait_for_selector", "main.re-SearchPage-wrapper"),
                    PageMethod("evaluate", scrolling_script),
                    PageMethod("wait_for_selector", "article:nth-child(10)"),  # 10 per page
                ],

                    
                }, headers={'User-Agent': self.useragent})
           

    def parse(self, response):
        # Import items
        items = ScrapyrealestateItem()
        


        # Necessary in order to create the whole link towards the website
        default_url = 'https://fotocasa.es'
        # Passem la resposta a text amb BeautifulSoup
        soup = BeautifulSoup(response.text, 'lxml')

        # Agafem els div de tots els habitatges de la pàgina
        # <div class="item-info-container"><a aria-level="2" class="item-link" href="/inmueble/95416252/?xtmc=2_1_08030&amp;xtcr=0" role="heading" title="Piso en calle de Concepción Arenal, Sant Andreu, Barcelona">Piso en calle de Concepción Arenal, Sant Andreu, Barcelona</a><div class="price-row"><span class="item-price h2-simulated">800<span class="txt-big">€/mes</span></span></div><span class="item-detail">3 <small>hab.</small></span><span class="item-detail">60 <small>m²</small></span><span class="item-detail">Planta 3ª <small>exterior con ascensor</small></span><span class="item-detail"><small class="txt-highlight-red">5 horas</small></span><div class="item-description description"><p class="ellipsis">Piso con salón luminoso y habitación doble soleada. Dispone de tres habitaciones: una doble y dos individuales. Baño y cocina en perfecto...</p></div><div class="item-toolbar"><span class="icon-phone item-not-clickable-phone">935 437 953</span><a class="icon-phone phone-btn item-clickable-phone" href="tel:+34 935437953" target="_blank"><span>Llamar</span></a><button class="icon-chat email-btn action-email fake-anchor"><span>Contactar</span></button><button class="favorite-btn action-fav fake-anchor" data-role="add" data-text-add="Guardar" data-text-remove="Favorito" title="Guardar"><i class="icon-heart" role="image"></i><span>Guardar</span></button><button class="icon-delete trash-btn action-discard fake-anchor" data-role="add" data-text-remove="Descartar" rel="nofollow" title="Descartar"></button></div></div>
        # flats = response.css('div.item-info-container')
        # div --> class="item-info-container"
        # flats = soup.find_all("div", {"class": "re-Searchresult-itemRow"})
        flats = soup.find_all("article")  # Canvi de div - 10/11/2021
        logging.warning(f'flats: {len(flats)}')

        # div --> class="pagination" --> ul --> li --> class="next"
        try:
            next_page = soup.find("div", {"class": "pagination"}).find("a", {"class": "icon-arrow-right-after"})['href']
        except:
            next_page = ""
        # Iterem per cada numero d'habitatge de la pàgina i agafem les dades
        for nflat in range(len(flats)):
            # Validem i agafem l'enllaç (ha de ser el link del habitatge)
            # a --> class="item-link" --> href
            # href = flats[nflat].find("a", {"class": "item-link"})['href']
            try:
                # href = flats[nflat].find("a", {"class": "re-CardPackMinimal-slider"}, href=True)['href']
                href = flats[nflat].find("a", {"class": "re-CardPackAdvance-info-container"}, href=True)[
                    'href']  # Canvi de div - 10/11/2021
                logging.warning(f'href: {href}')

            except:
                break;  # Si no troba res sortim del bucle

            try:
                title = flats[nflat].find("span", {"class": "re-CardTitle"}).text.strip()
            except:
                title = ''

            try:
                id = href.split('/')[6]
            except:
                id = ''

            # span --> class="item-price h2-simulated" --> span .text
            try:
                price = flats[nflat].find("span", {"class": "re-CardPrice"}).text.strip()
            except:
                price = ''

            # span --> class="item-detail" --> [nflat] --> span .text
            try:
                rooms = flats[nflat].find_all("span", {"class": "re-CardFeatures-feature"})[0].text.strip()
            except:
                rooms = ''

            try:
                m2 = flats[nflat].find("span", {"class": "re-CardFeaturesWithIcons-feature-icon--surface"}).text.strip()
            except:
                m2 = ''

            # Hi ha pisos sense data o planta. Per evitar problemes assignem variable buida si hi ha error.
            try:
                floor = flats[nflat].find_all("span", {"class": "re-CardFeatures-feature"})[5].text.strip()
            except:
                floor = ""
            try:
                post_time = flats[nflat].find_all("span", {"class": "re-CardFeatures-feature"})[5].text.strip()
            except:
                post_time = ""

            # Add items
            items['id'] = id
            items['title'] = title
            items['town'] = ''
            items['price'] = price
            items['rooms'] = rooms
            items['m2'] = m2
            items['floor'] = floor
            items['post_time'] = post_time
            items['href'] = default_url + href
            items['site'] = 'fotocasa'

            yield items

    # Overriding parse_start_url to get the first page
    parse_start_url = parse