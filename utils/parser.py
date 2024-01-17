import  traceback
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup
from utils.utils import get_current_time, get_requests, print_template


def parsing_sitemap(DOMAIN):
    url = f'{DOMAIN}/seo/sitemap/'

    response = get_requests(url)
    if not response:
        return False

    catalog_links = []
    tree = ET.ElementTree(ET.fromstring(response.content))
    root = tree.getroot()
    locs = root.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc")
    for loc in locs:
        if "https://steelx.ru/catalog/" in loc.text:
            catalog_links.append(loc.text)
    return catalog_links


def parsing_pagination(soup):
    pagination = soup.find('div', 'default-pagination__pages')
    if pagination:
        pagination_pages = pagination.find_all('a')
        second_page = int(pagination_pages[0].get_text(strip=True))
        last_page = int(pagination_pages[-1].get_text(strip=True))

        return True, range(second_page, last_page + 1)
    return False, []


def parsing_products_on_page(soup):
    products_links = []
    products_wrapper = soup.find_all('tbody', 'catalog-list2')
    for element in products_wrapper:
        onclick = element.find('h2').get('onclick')
        if 'window.location=' in onclick:
            products_links.append(onclick[17:-2])
    return products_links if len(products_links) > 0 else False


def parsing_page(url):
    response = get_requests(url)
    if not response:
        return False

    soup = BeautifulSoup(response.text, 'html.parser')
    return parsing_products_on_page(soup)


def parsing_product_page(url):
    try:
        response = get_requests(url)
        if not response:
            print_template(f'Error (HTTP) parsing product {url}')
            return False

        soup = BeautifulSoup(response.content, 'html.parser')

        product_item = soup.find('div', 'catalog_el')
        if not product_item:
            print_template(f'Key element "catalog_el" not found on page {url})')
            return False

        product = {}
        product['Время парсинга (мск)'] = get_current_time()
        product['URL товара'] = url

        breadcrumbs = soup.find('div', 'breadcrumbs')
        if not breadcrumbs:
            print_template(f'Key element "breadcrumbs" not found on page {url})')
            return False

        product['Наименование'] = soup.find('div', 'main_h1').get_text(strip=True).replace('\xa0', ' ')
        breadcrumbs_items = breadcrumbs.find_all('span', itemprop="itemListElement")
        if breadcrumbs_items:
            if len(breadcrumbs_items) > 1:
                product['Раздел'] = breadcrumbs_items[1].get_text(strip=True)
            if len(breadcrumbs_items) == 3:
                product['Категория'] = breadcrumbs_items[2].get_text(strip=True)
            if len(breadcrumbs_items) == 4:
                product['Категория'] = breadcrumbs_items[3].get_text(strip=True)

        price = product_item.find('div', 'cost_lable')
        product['Цена'] = price.get_text(strip=True).replace('\xa0', ' ') if price else None

        unit = None
        brief = product_item.find('div', 'cel_brief')

        if brief:
            for element_p in brief.find_all('p'):
                strong_element = element_p.find('strong')
                if strong_element:
                    text_p = element_p.get_text(strip=True).replace('\xa0', ' ').replace(' ', '')
                    if 'Ценауказаназа' in text_p:
                        unit = text_p.replace('Ценауказаназа', '')
                        break
        if not unit:
            cost_label = product_item.find('div', 'cost_label')
            if cost_label:
                cost_label.decompose()

                cel_cost_new = product_item.find('div', 'cel_cost_new')
                if cel_cost_new:
                    text_cel_cost_new = cel_cost_new.get_text(strip=True).replace('/', '')
                    if text_cel_cost_new:
                        unit = text_cel_cost_new

        product['Единица измерения'] = unit

        if brief:
            specblocks = brief.find_all('div', 'specblock')
            for specblock in specblocks:
                key = specblock.find('strong')
                if not key:
                    continue

                key = key.get_text(strip=True).replace('\xa0', ' ')
                value = specblock.get_text(separator=' ', strip=True).replace('\xa0', ' ').replace(key, '').strip()
                if not value:
                    strip = key.split(':')
                    if len(strip) > 1:
                        key = strip[0].strip()
                        value = str(strip[1:]).strip()
                product[key] = value

        cel_addon_form = product_item.find('div', 'cel_addon_form')
        if cel_addon_form:
            field_cont = cel_addon_form.find('div', 'field_cont')
            if field_cont:
                addon_name = field_cont.find('select').get('data-placeholder')
                if addon_name and addon_name is not None:
                    addon_options = field_cont.find_all('option')
                    product[addon_name] = [option.get_text(strip=True).lower() for option in addon_options]

        tabs = soup.find('div', 'tabs_cont section')
        if tabs:
            tabs_elements = tabs.select('ul.tabs li')
            for index, li in enumerate(tabs_elements):
                if li.get_text(strip=True) == 'Характеристики':
                    box_index = index
                    break
            else:
                box_index = None

            if box_index is not None:
                tabs_content = tabs.find('div', 'tabs_content')
                if tabs_content:
                    boxs = tabs_content.find_all('div', 'box')
                    if len(boxs) > box_index:
                        table = boxs[box_index].find('table')
                        if table:
                            headers = [header.get_text(separator=' ', strip=True).replace('\xa0', ' ') for header in
                                       table.select('thead th')]
                            data = []
                            for row in table.select('tbody tr'):
                                row_data = [cell.get_text(separator=' ', strip=True).replace('\xa0', ' ') for cell in
                                            row.find_all('td')]
                                data.append(row_data)

                            for row in data:
                                for i, cell in enumerate(row):
                                    product[headers[i]] = cell
        return product
    except Exception as ex:
        print(print_template(f'Error: {ex} ({url})'))
        return False

