from datetime import datetime, timedelta
import re
from typing import Any, List, Dict
from bs4 import BeautifulSoup
import requests
from requests.adapters import Retry, HTTPAdapter
from sqlalchemy.orm.session import Session
from sqlalchemy import text as RAW_SQL
from db import HotelRate, PromoCode, get_engine


BASE_URL = 'https://reservations.universalorlando.com/ibe/default.aspx?hgID=641'
FORECAST_RANGE_DAYS = 14


REQ = requests.Session()
retries = Retry(total=3, backoff_factor=1)
REQ.mount('http://', HTTPAdapter(max_retries=retries))


def refresh_data() -> int:
    deals = []
    promo_codes = [pc.code for pc in PromoCode.get_all()]

    # querying stays of up to 7 nights from today until today + (max range)
    earliest_date = datetime.now() + timedelta(hours=2)
    latest_date = earliest_date + timedelta(days=FORECAST_RANGE_DAYS - 1)
    max_nights = 7

    # big ugly while loop yay
    check_in = earliest_date
    while check_in <= latest_date:
        check_in_fmt = datetime.strftime(check_in, '%m/%d/%Y')
        for night_count in range(1, max_nights+1):
            for promo in promo_codes:
                print(f"Querying {night_count}-night stays checking-in on {check_in_fmt} with promo code '{promo}'")
                try:
                    check_out = check_in + timedelta(days=night_count)
                    full_url = f"{BASE_URL}&checkin={check_in_fmt}&nights={night_count}&promo={promo}"
                    resp = REQ.get(full_url)
                    resp.raise_for_status()
                except requests.exceptions.Timeout:
                    print(f"Request timed out from {full_url}")
                    continue
                except requests.exceptions.HTTPError:
                    print(f"Got status code {resp.status_code} from {full_url}")
                    continue
                soup = BeautifulSoup(resp.text, 'html.parser')
                hotel_cards = soup.find_all('div', {'class':'ws-property-item'})
                for card in hotel_cards:
                    hotel_name = card.find('a', {'class': 'wsName'}).text
                    rate_text = card.find('span', {'class': 'ws-number'}).text
                    nightly_rate = float(re.search('\d+', rate_text).group(0))
                    result = HotelRate(
                        hotel_name = hotel_name,
                        check_in_date = check_in,
                        check_out_date = check_out,
                        search_url = full_url,
                        promo_code = promo,
                        nightly_rate = nightly_rate,
                    )
                    deals.append(result)
        # while loop increment
        check_in += timedelta(days=1)
    # end while loop
    print(len(deals))

    with Session(get_engine(echo=False)) as session:
        session.execute(RAW_SQL(f"DELETE FROM {HotelRate.__tablename__};"))
        session.add_all(deals)
        session.commit()

    return len(deals)



def populate_dataframe(promo_code_description:str=None) -> List[Dict[str, Any]]:
    with Session(get_engine(echo=False)) as session:
        sql = f"""
            SELECT
                (CAST(JULIANDAY(hr.check_out_date) AS INTEGER) - CAST(JULIANDAY(hr.check_in_date) AS INTEGER)) * CAST(hr.nightly_rate AS INTEGER) AS total_cost
                ,hr.hotel_name
                ,(CAST(JULIANDAY(hr.check_out_date) AS INTEGER) - CAST(JULIANDAY(hr.check_in_date) AS INTEGER)) AS num_nights
                ,pc.description
                ,SUBSTR(CAST(hr.check_in_date AS VARCHAR), 0, 11) AS check_in_date
                ,SUBSTR(CAST(hr.check_out_date AS VARCHAR), 0, 11) AS check_out_date
                ,CAST(hr.nightly_rate AS INTEGER) AS nightly_rate
                ,'['||hr.search_url||']('||hr.search_url||')' AS search_url
            FROM {HotelRate.__tablename__} AS hr
            INNER JOIN {PromoCode.__tablename__} AS pc
                ON hr.promo_code = pc.code
            {f'WHERE pc.description = "{promo_code_description}"' if promo_code_description else ''}
            ORDER BY
                pc.description
                ,(CAST(JULIANDAY(hr.check_out_date) AS INTEGER) - CAST(JULIANDAY(hr.check_in_date) AS INTEGER)) * CAST(hr.nightly_rate AS INTEGER) --total cost calculation from above, without string formatting
                ,(CAST(JULIANDAY(hr.check_out_date) AS INTEGER) - CAST(JULIANDAY(hr.check_in_date) AS INTEGER)) --num nights calculation from above
                ,hr.check_in_date
                ,hr.check_out_date
                ,hr.hotel_name
        """
        res = session.execute(RAW_SQL(sql))
        return [row._asdict() for row in res.all()]
