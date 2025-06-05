"""
race_urlディレクトリに含まれるURLを利用して、htmlを取得する
"""
import datetime
import pytz
now_datetime = datetime.datetime.now(pytz.timezone('Asia/Tokyo'))

import requests
from bs4 import BeautifulSoup

import time
import os
from os import path
OWN_FILE_NAME = path.splitext(path.basename(__file__))[0]

OWNDIR = os.path.dirname(os.path.abspath(__file__))
PARENTDIR = os.path.dirname(OWNDIR)
RACE_URL_DIR = PARENTDIR + "/race_url"

import logging
logger = logging.getLogger(__name__) #ファイルの名前を渡す

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36'  # 確認したユーザーエージェントに置換
} #ユーザーエージェント偽装


def my_makedirs(path):
    if not os.path.isdir(path):
        os.makedirs(path)

def get_race_html():
    # 去年までのデータ
    for year in range(2020, now_datetime.year):
        for month in range(1, 13):
                get_race_html_by_year_and_mon(year,month)
    # 今年のデータ
    for year in range(now_datetime.year, now_datetime.year+1):
        for month in range(1, now_datetime.month+1):
                get_race_html_by_year_and_mon(year,month)

def get_race_html_by_year_and_mon(year,month):
    with open(RACE_URL_DIR+"/"+str(year)+"-"+str(month)+".txt", "r") as f:
        save_dir = "race_html/"+str(year)+"/"+str(month)
        my_makedirs(save_dir)
        urls = f.read().splitlines()

        file_list = os.listdir(save_dir) # get all file names

        # 取得すべき数と既に保持している数が違う場合のみ行う
        if len(urls) != len(file_list):
            logger.info("getting htmls ("+str(year) +" "+ str(month) + ")")
            for url in urls:
                list = url.split("/")
                race_id = list[-2]
                save_file_path = save_dir+"/"+race_id+'.html'
                if not os.path.isfile(save_file_path): # まだ取得していなければ取得
                    response = requests.get(url, headers=headers)
                    response.encoding = response.apparent_encoding # https://qiita.com/nittyan/items/d3f49a7699296a58605b
                    html = response.text
                    time.sleep(0.6) 
                    with open(save_file_path, 'w', encoding='utf-8') as file:
                        file.write(html)
            logging.info("saved " + str(len(urls)) +" htmls ("+str(year) +" "+ str(month) + ")")
        else:
            logging.info("already have " + str(len(urls)) +" htmls ("+str(year) +" "+ str(month) + ")")


if __name__ == '__main__':
    formatter = "%(asctime)s [%(levelname)s]\t%(message)s" # フォーマットを定義
    logging.basicConfig(filename='logfile/'+OWN_FILE_NAME+'.logger.log', level=logging.INFO, format=formatter)

    logger.info("start get race html!")
    get_race_html()
