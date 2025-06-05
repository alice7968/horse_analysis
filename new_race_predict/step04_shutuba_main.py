from shutuba_url_scraper import get_race_urls_for_date
from shutuba_html_scraper import  save_race_pages_from_urls
from shutuba_csv_scraper import make_shutuba_csv
from py2slack import send_slack

def main(date_str): 
    get_race_urls_for_date(date_str)
    save_race_pages_from_urls(date_str)
    make_shutuba_csv(date_str)
        
if __name__ == "__main__":
    date_str = input("日付を8桁（YYYYMMDD）で入力してください: ")
    send_slack("{date}の処理を始めます".format(date=date_str))
    main(date_str)
    send_slack("{date}の処理が終わりました".format(date=date_str))