#!/usr/bin/env python3
"""
Скрипт для автоматического поиска контактов веб-студий
Использует встроенные библиотеки Python (no external dependencies)
"""

import re
import csv
import time
import urllib.request
import urllib.error
from html.parser import HTMLParser
from typing import Dict, List, Optional
from urllib.parse import urljoin
import logging
import ssl

# SSL fix для Windows
ssl._create_default_https_context = ssl._create_unverified_context

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Список студий (оставшиеся 25 после топ-5)
STUDIOS = [
    "Далее",
    "Оджетто",
    "Digital Lab",
    "Greensight",
    "Интаро",
    "Космос-Веб",
    "Only",
    "Terabit Digital",
    "Факт",
    "Oxem",
    "CHIPSA",
    "AWG",
    "Progressive Media",
    "Uplab",
    "Цифровой Элемент",
    "Escape Tech",
    "Purrweb",
    "Braind",
    "е—б эдженси",
    "Red Collar",
    "Вебпрактик",
    "Молния",
    "АБВ сайт",
    "MEDIA WORKS",
    "startmedia",
]

# Email уже найденные (из предыдущего поиска)
FOUND_CONTACTS = {
    "ITECH": {"email": "hi@itech-group.ru", "phone": "+7 495 255 03 37"},
    "Liqium": {"email": "Info@liqium.ru", "phone": "+7 495 545 42 35"},
    "AGIMA": {"email": "info@agima.ru", "phone": "+7 495 981-01-85"},
    "idaproject": {"email": "do@idaproject.com", "phone": "+7 (495) 646-09-06"},
    "АЭРО": {"email": "contact@aeroidea.ru", "phone": "+7 (495) 120-12-38"},
}

class ContactScraper:
    def __init__(self):
        self.email_pattern = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
        self.phone_pattern = re.compile(r'(?:\+7|8)[\s\(-]?\d{3}[\s\)-]?\d{3}[\s\)-]?\d{2}[\s\)-]?\d{2}')
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

    def fetch_page(self, url: str, timeout: int = 10) -> Optional[str]:
        """Скачивает страницу с URL"""
        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=timeout) as response:
                content = response.read()
                return content.decode('utf-8', errors='ignore')
        except Exception as e:
            logger.debug(f"Ошибка загрузки {url}: {e}")
            return None

    def find_website(self, studio_name: str) -> Optional[str]:
        """Попытка найти сайт студии"""
        logger.info(f"Поиск сайта для: {studio_name}")

        # Стандартные домены
        possible_domains = [
            f"https://{studio_name.lower()}.ru",
            f"https://www.{studio_name.lower()}.ru",
            f"https://{studio_name.lower().replace(' ', '')}.ru",
            f"https://www.{studio_name.lower().replace(' ', '')}.ru",
            f"https://{studio_name.lower().replace(' ', '-')}.ru",
            f"https://www.{studio_name.lower().replace(' ', '-')}.ru",
        ]

        for url in possible_domains:
            try:
                req = urllib.request.Request(url, method='HEAD', headers=self.headers)
                response = urllib.request.urlopen(req, timeout=5)
                if response.status < 400:
                    logger.info(f"✓ Найден сайт: {url}")
                    return url
            except:
                pass

        return None

    def extract_contacts(self, text: str) -> Dict[str, Optional[str]]:
        """Извлекает email и телефоны из текста"""
        contacts = {"email": None, "phone": None}

        # Ищем email
        emails = self.email_pattern.findall(text)
        if emails:
            # Исключаем системные email
            filtered = [e for e in emails if not any(x in e.lower() for x in ['noreply', 'no-reply', 'info@example'])]
            if filtered:
                contacts["email"] = filtered[0]
            else:
                contacts["email"] = emails[0]

        # Ищем телефон
        phones = self.phone_pattern.findall(text)
        if phones:
            contacts["phone"] = phones[0]

        return contacts

    def scrape_contacts(self, url: str) -> Dict[str, Optional[str]]:
        """Парсит email и телефоны со страницы"""
        contacts = {"email": None, "phone": None}

        try:
            # Скачиваем главную страницу
            page_content = self.fetch_page(url)
            if not page_content:
                return contacts

            # Ищем ссылку на контакты
            contact_links = re.findall(r'href=["\']([^"\']*(?:kontakt|contact|about|svyaz)[^"\']*)["\']',
                                      page_content, re.IGNORECASE)

            for link in contact_links:
                contact_url = urljoin(url, link)
                contact_page = self.fetch_page(contact_url)
                if contact_page:
                    contact_data = self.extract_contacts(contact_page)
                    if contact_data["email"] or contact_data["phone"]:
                        return contact_data

            # Если не найдено на странице контактов, ищем на главной
            main_contacts = self.extract_contacts(page_content)
            if main_contacts["email"] or main_contacts["phone"]:
                return main_contacts

            return contacts

        except Exception as e:
            logger.error(f"Ошибка при скрейпинге {url}: {e}")
            return contacts

    def process_studio(self, studio_name: str) -> Dict:
        """Полный процесс поиска контактов для студии"""
        logger.info(f"\n=== Обработка: {studio_name} ===")

        # Проверяем если уже найдено
        if studio_name in FOUND_CONTACTS:
            logger.info(f"✓ Уже найдено в базе")
            return {"studio": studio_name, **FOUND_CONTACTS[studio_name]}

        # Ищем сайт
        website = self.find_website(studio_name)
        if not website:
            logger.warning(f"✗ Сайт не найден")
            return {"studio": studio_name, "email": None, "phone": None, "website": None}

        # Парсим контакты
        contacts = self.scrape_contacts(website)

        result = {
            "studio": studio_name,
            "website": website,
            "email": contacts["email"],
            "phone": contacts["phone"]
        }

        if contacts["email"]:
            logger.info(f"✓ Email: {contacts['email']}")
        if contacts["phone"]:
            logger.info(f"✓ Телефон: {contacts['phone']}")

        if not contacts["email"] and not contacts["phone"]:
            logger.warning(f"✗ Контакты не найдены")

        time.sleep(1)  # Вежливая задержка между запросами
        return result

def save_to_csv(data: List[Dict], filename: str = "web_studios_contacts.csv"):
    """Сохраняет результаты в CSV"""
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['studio', 'website', 'email', 'phone'])
        writer.writeheader()
        writer.writerows(data)
    logger.info(f"\n✓ Результаты сохранены в {filename}")

def main():
    """Главная функция"""
    logger.info(f"Начало поиска контактов для {len(STUDIOS) + len(FOUND_CONTACTS)} студий...")

    scraper = ContactScraper()
    results = []

    # Добавляем уже найденные контакты
    for studio_name, contacts in FOUND_CONTACTS.items():
        results.append({
            "studio": studio_name,
            "website": "найдено вручную",
            **contacts
        })

    # Обрабатываем остальные студии
    for studio in STUDIOS:
        result = scraper.process_studio(studio)
        results.append(result)

    # Сохраняем результаты
    save_to_csv(results)

    # Статистика
    found_emails = sum(1 for r in results if r.get('email'))
    found_phones = sum(1 for r in results if r.get('phone'))
    logger.info(f"\n📊 ИТОГО:")
    logger.info(f"  Email найдено: {found_emails}/{len(results)}")
    logger.info(f"  Телефоны найдено: {found_phones}/{len(results)}")
    logger.info(f"\n✓ Откройте файл web_studios_contacts.csv в Excel")

if __name__ == "__main__":
    main()
