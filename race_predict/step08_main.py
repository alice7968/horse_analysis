from step01_get_race_url import get_race_url
from step02_get_race_html import get_race_html
from step03_make_csv_from_html import make_csv_from_html
from step04_horse_data_clean import horse_data_cleaner
from step05_race_data_clean import race_data_cleaner
from step06_get_horse_parents import get_horse_parents_urls, get_race_horse_htmls
from step07_merge_parents_data import merge_parents_data

import sys
import traceback
import requests
import os
from os import path
OWN_FILE_NAME = path.splitext(path.basename(__file__))[0]

OWNDIR = os.path.dirname(os.path.abspath(__file__))
PARENTDIR = os.path.dirname(OWNDIR)

HTML_DIR = PARENTDIR + "/race_horse_id_htmls"
CSV_OUTPUT_PATH = PARENTDIR + "/horse_pedigree_extracted.csv"


input_folder = PARENTDIR  # race-*.csvが置かれているディレクトリ
output_file = "final_cleaned_race_data.csv"

import logging
logger = logging.getLogger(__name__) #ファイルの名前を渡す

from py2slack import send_slack


def send_slack_notification(message):
    send_slack(message)

def update():
    get_race_url()
    get_race_html()
    make_csv_from_html()
    horse_data_cleaner()
    race_data_cleaner(input_folder, output_file)
    get_horse_parents_urls()
    get_race_horse_htmls()
    merge_parents_data()


if __name__ == '__main__':
    try:
        formatter_func = "%(asctime)s - %(module)s.%(funcName)s [%(levelname)s]\t%(message)s" # フォーマットを定義
        logging.basicConfig(filename='logfile/'+OWN_FILE_NAME+'.logger.log', level=logging.INFO, format=formatter_func)
        logger.info("start updating!")
        update()
        send_slack_notification(OWN_FILE_NAME+" end!")
    except Exception as e:
        t, v, tb = sys.exc_info()
        for str in traceback.format_exception(t,v,tb):
            str = "\n"+str
            logger.error(str)
            send_slack_notification(str)
