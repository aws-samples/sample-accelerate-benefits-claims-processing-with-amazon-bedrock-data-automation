"""
MIT No Attribution

Copyright 2024 Amazon Web Services

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

import os
import json
import boto3
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize SNS client
sns_client = boto3.client('sns')

def lambda_handler(event, context):
    logger.info("Integration Lambda")
    logger.info(f"Event: {event}")

    # Get the SNS topic ARN from environment variables
    sns_topic_arn = os.environ.get('NOTIFICATION_TOPIC_ARN')
    
    if not sns_topic_arn:
        raise ValueError("NOTIFICATION_TOPIC_ARN environment variable is not set")
   
    # Extract relevant information from the event
    event_detail = event.get('detail', {})
    
    # Create message for SNS notification
    message = {
        'message': 'Benefit claim validation completed',
        'detail': event_detail
    }
    
    # Publish message to SNS topic
    try:
        response = sns_client.publish(
            TopicArn=sns_topic_arn,
            Message=json.dumps(message),
            Subject='Benefit Claim Validation Status'
        )
        logger.info(f"Message published to SNS topic. MessageId: {response['MessageId']}")
    except Exception as e:
        logger.error(f"Error publishing to SNS topic: {str(e)}")
        raise
    
    return {
        'statusCode': 200,
        'body': json.dumps('Message published successfully')
    }
