# -*- coding: utf-8 -*-

# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
# Licensed under the Amazon Software License  http://aws.amazon.com/asl/

# This sample demonstrates handling intents from an Alexa skill using the Alexa Skills Kit SDK for Python.
# Please visit https://alexa.design/cookbook for additional examples on implementing slots, dialog management,
# session persistence, api calls, and more.
# This sample is built using the handler classes approach in skill builder.

import logging
import ask_sdk_core.utils as ask_utils
import json
import csv
import os
import boto3
import botocore
from datetime import date, timedelta

from ask_sdk_model.interfaces.alexa.presentation.apl import RenderDocumentDirective
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.dispatch_components import AbstractExceptionHandler
from ask_sdk.standard import StandardSkillBuilder

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# DynamoDB resources
ddb_resource = boto3.resource("dynamodb")
ddb_table_name = os.environ.get("DYNAMODB_PERSISTENCE_TABLE_NAME")
table = ddb_resource.Table(ddb_table_name)

# S3 resources
s3_client = boto3.client("s3")
s3_resource = boto3.resource("s3")
bucket_name = os.environ.get("S3_PERSISTENCE_BUCKET")
s3_key = "inbox/main.csv"

# Other variables
today = date.today()
calendar_file = "/tmp/main.csv"


def read_csv(filename):
    """
    Read a CSV file into a list of dictionaries
    """
    with open(filename, newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        return list(reader)


def parse_calendar_file(bucket_name, s3_key, calendar_file):
    """
    Download the calendar file from S3 and parse it into a list of dictionaries
    """
    # Check if S3 object exists
    try:
        s3_client.head_object(Bucket=bucket_name, Key=s3_key)
    except botocore.exceptions.ClientError as e:
        if e.response["Error"]["Code"] == "404":
            # File doesn't exist, return empty list
            print(f"{bucket_name}/{s3_key} not found in S3")
            return []
        else:
            # Something else has gone wrong.
            raise
    else:
        # File exists, download it
        s3_client.download_file(bucket_name, s3_key, calendar_file)
        # Copy the S3 file to the processed folder
        copy_source = {"Bucket": bucket_name, "Key": s3_key}
        s3_resource.meta.client.copy(
            copy_source, bucket_name, f"processed/{s3_key.split('/')[-1]}"
        )
        # Delete the original file
        s3_resource.Object(bucket_name, s3_key).delete()
        # Read the file into a list of dictionaries
        return read_csv(calendar_file)


def write_calendar_to_ddb(calendar_file):
    """
    Write the calendar file (if exists) to DynamoDB
    """
    # Read the calendar file
    bin_collections = parse_calendar_file(bucket_name, s3_key, calendar_file)
    # If there are items to write to DynamoDB
    if bin_collections:
        # Batch write all items to DynamoDB
        print("Writing the calendar to DynamoDB")
        with table.batch_writer() as batch:
            for bin_collection in bin_collections:
                batch.put_item(Item=bin_collection)


def get_bin_collection_info(input_date):
    """
    Get the bin collection info from DynamoDB
    """
    id = input_date - timedelta(days=input_date.weekday())  # Start of the week
    response = table.get_item(Key={"id": str(id)})
    """
    {
        "Item": [
            {
                "id": "2023-01-23",
                "collection_date": "2023-01-26",
                "bin_type": "Recycling bin"
            }
        ]
    }
    """
    return (
        response["Item"]["bin_type"],
        date.fromisoformat(response["Item"]["collection_date"])
    )


class LaunchRequestHandler(AbstractRequestHandler):
    """Handler for Skill Launch."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool

        return ask_utils.is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response

        # Write calendar to DynamoDB
        write_calendar_to_ddb(calendar_file)
        # Get the bin collection info for this week
        bin_type, collection_date = get_bin_collection_info(today)
        # If the collection date is in the past
        if collection_date < today:
            # Get the bin collection info for next week
            bin_type, collection_date = get_bin_collection_info(
                today + timedelta(days=7)
            )
        # Get the speech text
        speak_output = f"{bin_type} will be collected on {collection_date.strftime('%A, %Y-%m-%d')}"

        # ====================================================================
        # Add a visual with Alexa Layouts
        # ====================================================================
        # Import an Alexa Presentation Language (APL) template
        with open("./documents/APL_simple.json") as apl_doc:
            apl_simple = json.load(apl_doc)

            if (
                ask_utils.get_supported_interfaces(handler_input).alexa_presentation_apl
                is not None
            ):
                handler_input.response_builder.add_directive(
                    RenderDocumentDirective(
                        document=apl_simple,
                        datasources={
                            "myData": {
                                # ====================================================================
                                # Set a headline and subhead to display on the screen if there is one
                                # ====================================================================
                                "Title": bin_type,
                                "Subtitle": collection_date,
                            }
                        },
                    )
                )

        return handler_input.response_builder.speak(speak_output).response


class HelloWorldIntentHandler(AbstractRequestHandler):
    """Handler for Hello World Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("HelloWorldIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "Hello World!"

        return (
            handler_input.response_builder.speak(speak_output)
            # .ask("add a reprompt if you want to keep the session open for the user to respond")
            .response
        )


class HelpIntentHandler(AbstractRequestHandler):
    """Handler for Help Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "You can say hello to me! How can I help?"

        return (
            handler_input.response_builder.speak(speak_output)
            .ask(speak_output)
            .response
        )


class CancelOrStopIntentHandler(AbstractRequestHandler):
    """Single handler for Cancel and Stop Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AMAZON.CancelIntent")(
            handler_input
        ) or ask_utils.is_intent_name("AMAZON.StopIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "Goodbye!"

        return handler_input.response_builder.speak(speak_output).response


class FallbackIntentHandler(AbstractRequestHandler):
    """Single handler for Fallback Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AMAZON.FallbackIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In FallbackIntentHandler")
        speech = (
            "Hmm, I'm not sure. You can say Hello or Help. What would you like to do?"
        )
        reprompt = "I didn't catch that. What can I help you with?"

        return handler_input.response_builder.speak(speech).ask(reprompt).response


class SessionEndedRequestHandler(AbstractRequestHandler):
    """Handler for Session End."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response

        # Any cleanup logic goes here.

        return handler_input.response_builder.response


class IntentReflectorHandler(AbstractRequestHandler):
    """The intent reflector is used for interaction model testing and debugging.
    It will simply repeat the intent the user said. You can create custom handlers
    for your intents by defining them above, then also adding them to the request
    handler chain below.
    """

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("IntentRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        intent_name = ask_utils.get_intent_name(handler_input)
        speak_output = "You just triggered " + intent_name + "."

        return (
            handler_input.response_builder.speak(speak_output)
            # .ask("add a reprompt if you want to keep the session open for the user to respond")
            .response
        )


class CatchAllExceptionHandler(AbstractExceptionHandler):
    """Generic error handling to capture any syntax or routing errors. If you receive an error
    stating the request handler chain is not found, you have not implemented a handler for
    the intent being invoked or included it in the skill builder below.
    """

    def can_handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> bool
        return True

    def handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> Response
        logger.error(exception, exc_info=True)

        speak_output = "Sorry, I had trouble doing what you asked. Please try again."

        return (
            handler_input.response_builder.speak(speak_output)
            .ask(speak_output)
            .response
        )


# The SkillBuilder object acts as the entry point for your skill, routing all request and response
# payloads to the handlers above. Make sure any new handlers or interceptors you've
# defined are included below. The order matters - they're processed top to bottom.


sb = StandardSkillBuilder()

sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(HelloWorldIntentHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_request_handler(FallbackIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())
# make sure IntentReflectorHandler is last so it doesn't override your custom intent handlers
sb.add_request_handler(IntentReflectorHandler())
sb.add_exception_handler(CatchAllExceptionHandler())

lambda_handler = sb.lambda_handler()
