import json
import boto3
import decimal

client = boto3.resource('dynamodb')
table = client.Table('Patients')


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            if abs(o) % 1 > 0:
                return float(o)
            else:
                return int(o)
        return super(DecimalEncoder, self).default(o)


def lambda_handler(event, context):
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
    else:
        params = event['queryStringParameters']
        if 'province' not in params:
            print('ayoo')
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
