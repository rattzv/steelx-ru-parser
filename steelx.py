import os
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor

from utils.exporter import convert_to_json, remove_old_data, save_to_sqlite
from utils.parser import parsing_product_page, parsing_sitemap
from utils.utils import check_reports_folder_exist, get_requests, print_template, random_sleep


os.environ['PROJECT_ROOT'] = os.path.dirname(os.path.abspath(__file__))


def start(workers_count):
    DOMAIN = 'https://steelx.ru'
    try:
        reports_folder = check_reports_folder_exist()

        if not reports_folder:
            return False

        print_template(f"Parse links to products from the sitemap...")

        product_links = parsing_sitemap(DOMAIN)
        if not product_links and len(product_links) > 0:
            print_template(f"Error request the main product page link, cancel!")
            return

        print_template(f'Found {len(product_links)} links in the sitemap file, starting to parse products...')

        with ThreadPoolExecutor(max_workers=workers_count) as executor:
            results_parsing_product_page = executor.map(parsing_product_page, product_links)

        products_to_save = []
        for result in results_parsing_product_page:
            if result:
                products_to_save.append(result)

        save_to_sqlite(products_to_save, reports_folder)
    except Exception as ex:
        print_template(f'Error: {ex}')
        return False


if __name__ == '__main__':
    reports_folder = check_reports_folder_exist()
    if reports_folder:
        remove_old_data(reports_folder)

        workers_count = 15

        start(workers_count)

        total_count = convert_to_json(reports_folder)
        print(f"Total count: {total_count}")
