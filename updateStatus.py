import json
import requests
from bs4 import BeautifulSoup
import boto3


client = boto3.resource('dynamodb')
table = client.Table('Status')


def lambda_handler(event, context):
    URL = 'http://ncov.mohw.go.kr/'
    page = requests.get(URL)
    soup = BeautifulSoup(page.content, 'html.parser')
    krTable = soup.find('ul', class_='liveNum').find_all('li')
    krConfirm = int(krTable[0].find('span', class_='num').contents[1].replace(',', ''))
    krIncrement = int(krTable[0].find('span', class_='before').text.strip('전일대비 (+)'))
    krCured = int(krTable[1].find('span', class_='num').text.replace(',', ''))
    krMonitor = int(krTable[2].find('span', class_='num').text.replace(',', ''))
    krDeath = int(krTable[3].find('span', class_='num').text.replace(',', ''))
    formatDate = soup.find('span', class_='livedate').text[1:13].split('.')
    updatedDate = f'{formatDate[0]}월 {formatDate[1]}일 {formatDate[2].strip()}'

    table.update_item(
        Key={'region': '국내'},
        UpdateExpression='SET confirm = :confirm, #increment = :increment, cured = :cured, monitor = :monitor, death = :death, #reference = :reference, updatedDate = :updatedDate',
        ExpressionAttributeNames={
            '#reference': 'reference',
            '#increment': 'increment'
        },
        ExpressionAttributeValues={
            ':confirm': krConfirm,
            ':increment': krIncrement,
            ':cured': krCured,
            ':monitor': krMonitor,
            ':death': krDeath,
            ':reference': 'http://ncov.mohw.go.kr/',
            ':updatedDate': updatedDate
        }
    )

    krMap = soup.find('div', {'id': 'main_maplayout'}).find_all('button')
    for button in krMap:
        region = button.find('span', class_='name').text
        confirm = int(button.find('span', class_='num').text.replace(',', ''))
        increment = int(button.find('span', class_='before').text.strip('(+)'))

        table.update_item(
            Key={'region': region},
            UpdateExpression='SET confirm = :confirm, #increment = :increment, #reference = :reference, updatedDate = :updatedDate',
            ExpressionAttributeNames={
                '#reference': 'reference',
                '#increment': 'increment'
            },
            ExpressionAttributeValues={
                ':confirm': confirm,
                ':increment': increment,
                ':reference': 'http://ncov.mohw.go.kr/',
                ':updatedDate': updatedDate
            }
        )

    return {
        'statusCode': 200,
        'body': json.dumps('Status Update Complete!')
    }
