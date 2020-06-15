<p align="center">
  <img src="https://camo.githubusercontent.com/745c6ad37a844ec4f3d533e299ab5756107f99e8/68747470733a2f2f6269786279646576656c6f706572732e636f6d2f6465762f646f63732d6173736574732f7265736f75726365732f6465762d67756964652f62697862795f6c6f676f5f6769746875622d31313232313934303037303237383032383336392e706e67">
</p>

# 빅스비 개발자 INSIGHT [코로나 알림]

안녕하세요, 빅스비 마스터 최준입니다.

영상에서 보여드린 AWS Lambda 파일 그대로 제공되니 참고하세요~

---

## Lambda &harr; DynamoDB 함수

#### updateStatus.py

우선 파이썬의 Beautiful Soup 라이브러리를 사용하여 질병관리본부 웹사이트의 HTML을 확인합니다.

```py
URL = 'http://ncov.mohw.go.kr/'
page = requests.get(URL)
soup = BeautifulSoup(page.content, 'html.parser')
```

```html
<ul class="liveNum">
  <li>
    <strong class="tit">확진환자</strong>
    <span class="num"><span class="mini">(누적)</span>12,121</span>
    <span class="before">전일대비 (+ 37)</span>
  </li>
  <li>
    <em class="sign">=</em>
    <strong class="tit"
      >완치<br /><span class="mini_tit">(격리해제)</span></strong
    >
    <span class="num">10,730</span>
    <span class="before">(+ 12)</span>
  </li>
  <li>
    <em class="sign">+</em>
    <strong class="tit"
      >치료 중<br /><span class="mini_tit">(격리 중)</span></strong
    >
    <span class="num">1,114</span>
    <span class="before">(+ 25)</span>
    <a class="help" id="liveNum_help" href="">?</a>
  </li>
  <li>
    <em class="sign">+</em>
    <strong class="tit">사망</strong>
    <span class="num">277</span>
    <span class="before">(+ 0)</span>
  </li>
</ul>
```

필요한 정보가 포함된 HTML 태그를 찾아 Beautiful Soup으로 값을 저장합니다. 날짜 같은 경우는 "OO월 OO일 OO시 기준" 형식으로 저장하기 위해 추가 포맷을 적용했습니다.

```py
krTable = soup.find('ul', class_='liveNum').find_all('li')
krConfirm = int(krTable[0].find('span', class_='num').contents[1].replace(',', ''))
krIncrement = int(krTable[0].find('span', class_='before').text.strip('전일대비 (+)'))
krCured = int(krTable[1].find('span', class_='num').text.replace(',', ''))
krMonitor = int(krTable[2].find('span', class_='num').text.replace(',', ''))
krDeath = int(krTable[3].find('span', class_='num').text.replace(',', ''))
formatDate = soup.find('span', class_='livedate').text[1:13].split('.')
updatedDate = f'{formatDate[0]}월 {formatDate[1]}일 {formatDate[2].strip()}'
```

저장된 값을 DynamoDB에 입력하면 됩니다. 해당 문서의 Primary Key 값을 `Key`에 입력하고, Value는 `UpdateExpression`과 `ExpressionAttributeValues`를 통해 입력하면 됩니다. 여기서 **reference**와 **increment**는 DynamoDB에서 별도로 지정된 Variable과 동일하기 때문에 `ExpressionAttributeNames`를 통해 임시 Variable을 따로 선정해야 합니다.

```py
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
```

#### updatePatients.py

*updateStatus.py*와 동일하게 Beautiful Soup을 활용하여 확진자 정보를 스크래핑 할 수 있습니다. 한 가지 다른점은 확진 날짜를 **Timestamp**으로 변경하여 Table에 입력할 시, Lambda Timezone이 기본적으로 UTC로 설정되어 있어, `getTS(month, date)` 함수를 생성해 보았습니다.

```py
def getTS(month, date):
  now = datetime.datetime(2020, month, date)
  tz = pytz.timezone('Asia/Seoul')
  seoul = now.replace(tzinfo=pytz.utc).astimezone(tz).timestamp()
  return int(seoul) - 9 * 3600
```

---

## Lambda &harr; API Gateway 함수

#### getStatus.py

현황을 불러오는 경우, 단 하나의 문서(지역)를 불러오기 떄문에 API 요청에서 입력될 `region` query 값과 **GET_ITEM**을 통해 처리합니다.

```py
region = event['queryStringParameters']['region']
response = table.get_item(
    Key={'region': region}
)
```

유저가 요청하는 지역에 대한 정보가 없을 경우를 대비해 `try-except` 에러 핸들링도 포함합니다.

```py
try:
  item = response['Item']
except KeyError as err:
  print(err)
  return {
      'statusCode': 400,
      'headers': {
          'Content-Type': 'application/json'
      },
      'body': json.dumps('No patients found in region')
  }
```

#### getPatients.py

확진자를 불러오는 경우, API 요청에서 입력되는 query 값에 따라 다음과 같이 경우의 수를 고려해야 합니다.

- Query 값 없이 요청할 경우: (예. "확진자 알려줘")

  ```py
  if 'queryStringParameters' not in event:
    response = table.query(
        IndexName='status-patientID-index',
        KeyConditionExpression='#status = :status',
        ExpressionAttributeNames={
            '#status': 'status'
        },
        ExpressionAttributeValues={
            ':status': '입원'
        }
    )
  ```

- 일반 도시로 Query 요청할 경우: (예. "수원 확진자 알려줘")

  ```py
  else:
    params = event['queryStringParameters']
    if 'province' not in params:
        response = table.query(
            IndexName='city-patientID-index',
            KeyConditionExpression='city = :city',
            FilterExpression='#status = :status',
            ExpressionAttributeNames={
                '#status': 'status'
            },
            ExpressionAttributeValues={
                ':city': params['city'],
                ':status': '입원'
            }
        )
  ```

- 주요 행정 구역으로 Query 요청할 경우: (예. "경기도 확진자 알려줘")

  ```py
    elif 'city' not in params:
    response = table.query(
        KeyConditionExpression='province = :province',
        FilterExpression='#status = :status',
        ExpressionAttributeNames={
            '#status': 'status'
        },
        ExpressionAttributeValues={
            ':province': params['province'],
            ':status': '입원'
        }
    )
  ```

- 주요 행정 구역/도시 모두 포함하여 Query 요청할 경우: (예. "경기도 수원 확진자 알려줘")

  ```py
    else:
      response = table.query(
          KeyConditionExpression='province = :province',
          FilterExpression='#status = :status AND city = :city',
          ExpressionAttributeNames={
              '#status': 'status'
          },
          ExpressionAttributeValues={
              ':city': params['city'],
              ':province': params['province'],
              ':status': '입원'
          }
      )
  ```

마지막으로 유저가 요청하는 지역에 대한 정보가 없을 경우를 대비해 `if-else` 에러 핸들링도 포함합니다.

```py
if len(response['Items']) == 0:
  return {
      'statusCode': 400,
      'headers': {
          'Content-Type': 'application/json'
      },
      'body': json.dumps('No patients found in region')
  }
else:
  return {
      'statusCode': 200,
      'headers': {
          'Content-Type': 'application/json'
      },
      'body': json.dumps(response['Items'], indent=4, cls=DecimalEncoder)
  }
```

한 가지 주의해야할 점은, DynamoDB 데이터를 파이썬을 통해 JSON 형태로 불러오면 수치 값이 Decimal로 인식이 됩니다. 이러한 값을 Integer 혹은 Float로 변경하기 위해 **DecimalEncoder(json.JSONEncoder)** 라는 Class를 생성해 사용했습니다.

```py
class DecimalEncoder(json.JSONEncoder):
  def default(self, o):
      if isinstance(o, decimal.Decimal):
          if abs(o) % 1 > 0:
              return float(o)
          else:
              return int(o)
      return super(DecimalEncoder, self).default(o)
```
