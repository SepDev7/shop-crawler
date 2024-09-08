import asyncio
import aiohttp
from bs4 import BeautifulSoup
from django.db import transaction
from .models import Car
import json

async def fetch_page(session, url):
    async with session.get(url) as response:
        content_type = response.headers.get('Content-Type', '')
        if 'application/json' in content_type:
            return await response.json()
        elif 'text/html' in content_type:
            html_content = await response.text()
            soup = BeautifulSoup(html_content, 'html.parser')
            script_tag = soup.find('script', type='application/json')
            if script_tag:
                json_data = json.loads(script_tag.string)
                return json_data
            else:
                return None
        else:
            return None

@transaction.atomic
async def save_to_db(cars):
    if not cars:
        return
    Car.objects.bulk_create([Car(**car) for car in cars])

async def scrape_page(session, url, semaphore):
    async with semaphore:
        data = await fetch_page(session, url)
        if data is None:
            return

        cars = []
        for ad in data.get('data', {}).get('ads', []):
            detail = ad.get('detail')
            price_info = ad.get('price')
            
            if detail and price_info:
                title = detail.get('title')
                price = price_info.get('price')
                image_url = detail.get('image')
                
                if title and price and image_url:
                    car = {
                        'title': title,
                        'price': price,
                        'image_url': image_url
                    }
                    cars.append(car)
        
        await save_to_db(cars)

async def main():
    semaphore = asyncio.Semaphore(10)

    async with aiohttp.ClientSession() as session:
        tasks = []

        for _ in range(1, 80):
            url = f"https://bama.ir/cad/api/search?vehicle=pride&pageIndex={_}"
            tasks.append(scrape_page(session, url, semaphore))
        await asyncio.gather(*tasks)
