"""
MIT No Attribution

Copyright 2025 Amazon Web Services

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE
"""

import json
import boto3
import os
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Get region from boto3 session
region = boto3.session.Session().region_name

# Get account ID using STS
sts_client = boto3.client('sts')
account_id = sts_client.get_caller_identity()["Account"]
bda_profile_arn = f'arn:aws:bedrock:{region}:{account_id}:data-automation-profile/us.data-automation-v1'

bda_runtime = boto3.client(service_name='bedrock-data-automation-runtime')

s3_client = boto3.client('s3')

dynamodb = boto3.client('dynamodb')


def lambda_handler(event, context):
    #logger.debug("Extraction Lambda")

    #print('boto3.__version_: ', boto3.__version__)

    # Get bucket and key from the S3 event
    ingestion_bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']

    logger.info(f"Bucket: {ingestion_bucket}")
    logger.info(f"Key: {key}")

    try:

        bda_project_arn = os.environ.get('BDA_PROJECT_ARN')

        logger.info(f"BDA Project ARN: {bda_project_arn}")

        extraction_bucket = os.environ.get('EXTRACTION_BUCKET_NAME')

        input_bucket_prefix = "s3://" + ingestion_bucket + "/" + key
        output_bucket_prefix = "s3://" + extraction_bucket + "/output"

        logger.info(f"Input bucket prefix: {input_bucket_prefix}")
        logger.info(f"Output bucket prefix: {output_bucket_prefix}")

        # Invoke the data automation project
        response = bda_runtime.invoke_data_automation_async(
            inputConfiguration =
            {
                's3Uri':  input_bucket_prefix
            },
            outputConfiguration = 
            {
                's3Uri': output_bucket_prefix
            },
            dataAutomationConfiguration = 
            { 
                'dataAutomationProjectArn' : bda_project_arn, 
                'stage': "LIVE"
            },
            notificationConfiguration = {
                'eventBridgeConfiguration' : {
                    'eventBridgeEnabled' : True
                }
            },
            dataAutomationProfileArn=bda_profile_arn
        )

        logger.info(f"Response: {response}")
        invocation_arn = response['invocationArn']
        logger.info(f"Invocation ARN: {invocation_arn}")


        store_in_dynamodb(invocation_arn, key, ingestion_bucket, "STARTED")

    except Exception as e:
        logger.error(f"Error:, {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }
    
def store_in_dynamodb(invocation_arn, object_key, bucket_name, status):
    table_name = os.getenv('BDA_TABLE_NAME')
    logger.info(f"Table Name: {table_name}")
    invocation_id = invocation_arn.split('/')[-1]
    logger.info(f"Invocation ID: {invocation_id}")
    try:
        dynamodb.put_item(
            TableName=table_name,
            # TODO: DynamoDB model can be improved
            Item = {
                'invocationId': {'S': invocation_id},
                'invocationArn': {'S': invocation_arn},            
                'fileName': {'S': object_key},            
                'filePath': {'S': f"s3://{bucket_name}/{object_key}"},
                'status': {'S': status}
            }
        )
    except Exception as e:
        logger.error(f"Error:, {e}")
        logger.error(f"Exception while inserting the details into the table:, {table_name}")
        raise e
