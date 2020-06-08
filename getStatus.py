import json
import boto3
import decimal

client = boto3.resource('dynamodb')
table = client.Table('Status')


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            if abs(o) % 1 > 0:
                return float(o)
            else:
                return int(o)
        return super(DecimalEncoder, self).default(o)


def lambda_handler(event, context):
    region = event['queryStringParameters']['region']

    response = table.get_item(
        Key={'region': region}
    )

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

    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json'
        },
        'body': json.dumps(item, indent=4, cls=DecimalEncoder)
    }
