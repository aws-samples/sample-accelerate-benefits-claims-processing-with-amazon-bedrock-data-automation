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
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)

BLUE_PRINT_NAME_CHECK = "US-Bank-Check"
BLUE_PRINT_NAME_RECEIPT = "Receipt"


logger.debug('boto3.__version_: ', boto3.__version__)

 # Initialize the Bedrock Agent Runtime client
bedrock_agent_runtime = boto3.client(service_name="bedrock-agent-runtime")

s3_client = boto3.client('s3')

eventbridge = boto3.client('events')

dynamodb = boto3.client('dynamodb')

def lambda_handler(event, context):
    logger.debug('boto3.__version_: ', boto3.__version__)
    logger.info('BDA_EVENT_RECEIVED: ',event)

    # TODO implement
    #read BDA_invocation_Id from the event
    bda_invocation_details = event['detail']
    logger.info(f"bda_invocation_details: {bda_invocation_details}")
    bda_invocation_id = bda_invocation_details['job_id']
    logger.info(f"bda_invocation_id: {bda_invocation_id}")

    job_status = bda_invocation_details['job_status']
    logger.info(f"job_status: {job_status}")

    object_key = bda_invocation_details['input_s3_object']['name']

    output_s3_location = bda_invocation_details['output_s3_location']
    logger.info(f"output_s3_location: {output_s3_location}")

    bucket_name = output_s3_location['s3_bucket']
    logger.info(f"bucket_name: {bucket_name}")

    bda_output_path = output_s3_location['name']
    logger.info(f"bda_output_path: {bda_output_path}")
  
    bda_result_suffix = '/custom_output/0/result.json'
    bda_result_object_key = bda_output_path+''+bda_result_suffix
    logger.info(bda_result_object_key)
    
    response = s3_client.get_object(Bucket=bucket_name, Key=bda_result_object_key)
    data = response['Body'].read().decode('utf-8')
    json_data = json.loads(data)
    logger.info(json_data)

    blue_print_name = json_data['matched_blueprint']['name']
    logger.info(f"blue_print_name: {blue_print_name}")

    results = json_data['inference_result']
    logger.info(f"results: {results}")

    update_in_dynamodb(bda_invocation_id, object_key, job_status, results, blue_print_name)

    confidence_results = process_explainability_info(json_data)
    logger.info(f"confidence_results: ', {confidence_results}")

    approval_response = validateBenefitClaim(results, blue_print_name)
    logger.info(f"approval response: ',{approval_response}")

    detail = {
        'bda_invocation_id': bda_invocation_id,
        'inference_result': results,
        'validation_result': approval_response
    }

    eventbridge.put_events(
        Entries=[
            {
                'Source': 'benefit-claim-validation-function',
                'DetailType': 'Benefit Claim Validation Completed',
                'Detail': json.dumps(detail)
            }
        ]
    )
    logger.info('event published to eventbridge')
    
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

def update_in_dynamodb(invocation_id, object_key, status, inference_result, blue_print_name):
    table_name = os.getenv('BDA_TABLE_NAME')
    logger.info(f"Table Name: {table_name}")
    logger.info(f"invocationId: {invocation_id}")
    logger.info(f"inference_result: {inference_result}")
    inference_result_str = json.dumps(inference_result)
    key = {
        'invocationId': {'S': invocation_id},
        'fileName': {'S': object_key}
    }
    update_expression = f"SET #status = :status, #inferenceResult = :inferenceResult, #bluePrintName = :bluePrintName"
    expression_names = {
        '#status': 'status',
        '#inferenceResult' : 'inferenceResult',
        '#bluePrintName': 'bluePrintName'
    }
    expression_values = {
        ':status': {'S': status},
        ':inferenceResult': {'S': inference_result_str},
        ':bluePrintName': {'S': blue_print_name}
    }    
    try:
        dynamodb.update_item(
            TableName=table_name,
            Key = key,
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_values,
            ExpressionAttributeNames=expression_names,
            ReturnValues="UPDATED_NEW"
        )
    except Exception as e:
        logger.error(f"Error:, {e}")

def validateBenefitClaim(claimReceiptData, blue_print_name):
    # Define the input for the retrieve_and_generate request
    # receipt =   {"benefitClaimsReceipt": {
    #     "PAYMENTDETAILS":{"TOTAL": 202.97, "SUBTOTAL": 202.97, "TAX": [0], "AMOUNTPAID": 202.97},
    #     "VENDORDETAILS": {"VENDORADDRESS": "670 51 10736 384601 9702", "VENDORPHONE": "", "VENDORNAME": "LOCAL DRUGS"},
    #     "RECEIPT_ID": "", "expire": "True", "RECEIPT_DATE": "07/22/2020",
    #     "LINEITEMS": [{"PRODUCT": "Pain Killer", "QTY": 1, "AMT": 2.99}, {"PRODUCT": "Corona Medication", "QTY": 2, "AMT": 199.98}]
    # }
    # }

    if blue_print_name == BLUE_PRINT_NAME_CHECK:
        context = f"""here is a benefit claim check: ${claimReceiptData}"""
        input_text = f"""${context}. Should claim for this check be approved? Generate your response in JSON format with following fields: decision (approved/not approved/ review needed) and reason (why approved/why not approved/or why review is needed)"""
    elif blue_print_name == BLUE_PRINT_NAME_RECEIPT:
        context = f"""here is a benefit claim receipt: ${claimReceiptData}"""
        input_text = f"""${context}. Should claim for this pharmacy receipt be approved? Generate your response in JSON format with following fields: decision (approved/not approved/ review needed) and reason (why approved/why not approved/or why review is needed)"""
    else:
        context = f"""here is a benefit claim document: ${claimReceiptData}"""
        input_text = f"""${context}. Should claim for this document be approved? Generate your response in JSON format with following fields: decision (approved/not approved/ review needed) and reason (why approved/why not approved/or why review is needed)"""



    kb_id = os.environ['KNOWLEDGE_BASE_ID']
    modelId = os.environ['KNOWLEDGE_BASE_MODEL_ID']
    try:
        # Define the configuration for retrieval and generation
        retrieve_and_generate_config = {
            "knowledgeBaseConfiguration": {
                "knowledgeBaseId": kb_id,
                "modelArn": modelId
            },
            "type": "KNOWLEDGE_BASE"
            # Add any other configurations as needed
        }
        
        # Call the retrieve_and_generate method
        response = bedrock_agent_runtime.retrieve_and_generate(
            input={"text": input_text},
            retrieveAndGenerateConfiguration=retrieve_and_generate_config,
        )
        # Process the response
        validation_response = ""
        if "output" in response and "text" in response["output"]:
            validation_response = response["output"]["text"]
            print("Generated Text:", validation_response)

            if "retrievedReferences" in response:
                print("Retrieved References:")
                for ref in response["retrievedReferences"]:
                    print(f"  - Source: {ref['content']['text']}")
        else:
            print("No output or text found in the response.")
        return validation_response
    except Exception as e:
        logger.error(f"Error:, {e}")
        return validation_response
