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

import json
import boto3
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


logger.debug(f"boto3.__version_: {boto3.__version__}")

s3_client = boto3.client('s3')

def lambda_handler(event, context):
    logger.debug(f"boto3.__version_: {boto3.__version__}")
    logger.debug(f"BDA_EVENT_RECEIVED: {event}")

    # TODO implement
    #read BDA_invocation_Id from the event
    bda_invocation_details = event['detail']
    logger.info('bda_invocation_details: ', bda_invocation_details)
    bda_invocation_id = bda_invocation_details['job_id']
    logger.info('bda_invocation_id: ', bda_invocation_id)

    job_status = bda_invocation_details['job_status']
    logger.info('job_status: ', job_status)

    output_s3_location = bda_invocation_details['output_s3_location']
    logger.info('output_s3_location: ', output_s3_location)

    bucket_name = output_s3_location['s3_bucket']
    logger.info('bucket_name:', bucket_name)

    bda_output_path = output_s3_location['name']
    logger.info('bda_output_path: ', bda_output_path)

    bda_result_suffix = '/custom_output/0/result.json'
    bda_result_object_key = bda_output_path+''+bda_result_suffix
    logger.info(bda_result_object_key)
    
    response = s3_client.get_object(Bucket=bucket_name, Key=bda_result_object_key)
    data = response['Body'].read().decode('utf-8')
    json_data = json.loads(data)
    logger.info(json_data)

    results = json_data['inference_result']
    logger.info('results: ', results)

    confidence_results = process_explainability_info(json_data)
    logger.info('confidence_results: ', confidence_results)

    return {
        'statusCode': 200,
        'body': results
    }

def process_explainability_info(json_response):
    """
    Process and print explainability information from the JSON response
    """
    try:
        explainability_info = json_response['explainability_info'][0]
        results = {}

        # Process each field in explainability_info
        for field, data in explainability_info.items():
            # Get confidence if it exists
            if 'confidence' in data:
                results[f"{field}_confidence"] = data['confidence']

            # Get success if it exists
            if 'success' in data:
                results[f"{field}_success"] = data['success']

            # Get value if it exists
            if 'value' in data:
                results[f"{field}_value"] = data['value']

        # Print results in a formatted way
        # print("\nExplainability Information:")
        # print("-" * 50)
        #
        # # Print confidence values
        # print("\nConfidence Scores:")
        confidence_scores = {k: v for k, v in results.items() if k.endswith('_confidence')}

        return confidence_scores

    except KeyError as e:
        logger.error(f"Error: Missing key in JSON response: {e}")
        return None
    except Exception as e:
        logger.error(f"Error processing explainability info: {e}")
        return None