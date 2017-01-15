import requests
from bs4 import BeautifulSoup
import logging
import re
from collections import defaultdict
from time import sleep
from requests.exceptions import Timeout, ConnectionError
import sys


logging.basicConfig(level='INFO')
logger = logging.getLogger(__name__)

def fetch_afisha_page():
    return requests.get('http://www.afisha.ru/msk/schedule_cinema/').content


def count_cinema_shows(film):
    return len(film.find_all('td', {'class': 'b-td-item'}))


def get_film_title(film):
    return film.find('h3', {'class': 'usetags'}).text


def parse_page(page):
    return BeautifulSoup(page, 'lxml')


def parse_afisha_list(raw_html):
    film_cinemas = defaultdict(dict)
    parsed_afisha_page = parse_page(raw_html)
    films_list = parsed_afisha_page.find_all('div', {'class': 'object'})
    for film in films_list:
        film_title = get_film_title(film)
        cinema_shows = count_cinema_shows(film)
        film_cinemas[film_title]['cinema_shows'] = cinema_shows
    return film_cinemas


def find_film_id_in_search_response(search_response):
    return re.search(r'\d+', search_response.url).group(0)


def find_rating(parsed_rating_page):
    return parsed_rating_page.find('kp_rating').text


def find_votes_number(parsed_rating_page):
    return parsed_rating_page.find('kp_rating').get('num_vote')


def fetch_movie_rating_and_votes_number(kinopoisk_session, film_id):
    rating_page = kinopoisk_session.get('https://rating.kinopoisk.ru/{film_id}.xml'.format(film_id=film_id)).content
    parsed_rating_page = parse_page(rating_page)
    kp_rating = find_rating(parsed_rating_page)
    number_of_votes = find_votes_number(parsed_rating_page)
    return [kp_rating, number_of_votes]


def fetch_movie_info(movie_title):
    kinopoisk_session = requests.Session()
    sleep(10)
    payload = {'first': 'yes', 'kp_query': movie_title}
    headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36'}
    try:
        search_response = kinopoisk_session.get('https://www.kinopoisk.ru/index.php', params=payload, headers=headers, timeout=10)
    except (Timeout, ConnectionError):
        sys.exit('No connection to kinopoisk.ru try later.')
    film_id = find_film_id_in_search_response(search_response)
    rating_and_votes_number = fetch_movie_rating_and_votes_number(kinopoisk_session, film_id)
    return rating_and_votes_number


def update_films_cinemas_list_with_rating_and_votes(films_cinemas_list, movie_title, rating_and_votes):
    films_cinemas_list[movie_title]['rating'] = rating_and_votes[0]
    films_cinemas_list[movie_title]['votes_number'] = rating_and_votes[1]


def get_films_rating_and_votes_number(films):
    for film_title in list(films.keys()):
        rating_and_votes_number = fetch_movie_info(film_title)
        update_films_cinemas_list_with_rating_and_votes(films_cinemas_list, film_title, rating_and_votes_number)


def sort_films_by_rating(films_list):
    return sorted(films_list.items(), key=lambda film: film[1]['rating'], reverse=True)


def film_is_not_arthouse(film):
    min_number_of_cinema_shows = 30
    return film[1]['cinema_shows'] > min_number_of_cinema_shows


def output_movies_to_console(films, count):
    for film in films[:count]:
        if film_is_not_arthouse(film):
            print('Title: {0} | Rating: | {1} Votes number: | {2} Cinema shows: {3}'.format(film[0],
                                                                                      film[1]['rating'],
                                                                                      film[1]['votes_number'],
                                                                                      film[1]['cinema_shows']))


if __name__ == '__main__':
    afisha_page = fetch_afisha_page()
    films_cinemas_list = parse_afisha_list(afisha_page)
    get_films_rating_and_votes_number(films_cinemas_list)
    sorted_films_list = sort_films_by_rating(films_cinemas_list)
    output_movies_to_console(sorted_films_list, 10)