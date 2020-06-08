import json
import requests
from bs4 import BeautifulSoup
import datetime
import pytz
import boto3

client = boto3.resource('dynamodb')
table = client.Table('Patients')


def getTS(month, date):
    now = datetime.datetime(2020, month, date)
    tz = pytz.timezone('Asia/Seoul')
    seoul = now.replace(tzinfo=pytz.utc).astimezone(tz).timestamp()
    return int(seoul) - 9 * 3600


def lambda_handler(event, context):
    url = 'http://www.busan.go.kr/corona19/index'
    page = requests.get(url)
    soup = BeautifulSoup(page.content, 'html.parser')
    banner = soup.find('div', class_='banner').find('span', class_='item1').text.split(' ')
    updatedDate = f'질병관리본부 {banner[0]} {banner[1]} {banner[3]} {banner[4]}'
    busanTable = soup.find('div', class_='list_body').find_all('ul')
    for item in busanTable:
        basic = item.find_all('li')[0].text.split('(')
        patientNo = int(basic[0].replace('부산-', '').strip())
        age = 2021-int(basic[1].split('/')[0].replace('년생', ''))
        gender = basic[1].split('/')[1].strip()
        residence = basic[1].split('/')[2].replace(')', '').strip()
        if '외국인' in basic[1]:
            country = '외국'
        else:
            country = '한국'
        hospital = item.find_all('li')[3].text
        if '퇴원' in hospital:
            status = '퇴원'
            hospital = hospital[3:-1]
        elif '사망' in hospital:
            status = '사망'
        else:
            status = '입원'
        formatDate = item.find_all('li')[4].text.split('/')
        confirmDate = f'{int(formatDate[0])}월 {int(formatDate[1])}월'
        timestamp = getTS(int(formatDate[0]), int(formatDate[1]))

        table.update_item(
            Key={
                'province': '부산',
                'patientID': f'부산 {patientNo}',
            },
            UpdateExpression='SET city = :city, patientNo = :patientNo, confirmDate = :confirmDate, #timestamp = :timestamp, gender = :gender, age = :age, country = :country, residence = :residence, hospital = :hospital, #status = :status, updatedDate = :updatedDate',
            ExpressionAttributeNames={
                '#status': 'status',
                '#timestamp': 'timestamp'
            },
            ExpressionAttributeValues={
                ':city': '부산',
                ':patientNo': patientNo,
                ':confirmDate': confirmDate,
                ':timestamp': timestamp,
                ':gender': gender,
                ':age': age,
                ':country': country,
                ':residence': residence,
                ':hospital': hospital,
                ':status': status,
                ':updatedDate': updatedDate
            }
        )

    return {
        'statusCode': 200,
        'body': 'Update Complete'
    }
