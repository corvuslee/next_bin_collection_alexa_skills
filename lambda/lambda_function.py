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
from datetime import date, timedelta

from ask_sdk_model.interfaces.alexa.presentation.apl import RenderDocumentDirective

# from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.dispatch_components import AbstractExceptionHandler

# from ask_sdk_core.handler_input import HandlerInput
from ask_sdk.standard import StandardSkillBuilder

# from ask_sdk_model import Response

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Connect to DynamoDB
ddb_table_name = os.environ.get("DYNAMODB_PERSISTENCE_TABLE_NAME")
ddb_resource = boto3.resource("dynamodb")
table = ddb_resource.Table(ddb_table_name)

# Other variables
start_day = date.today()
calendar_file = 'calendars/main.csv'
write_calendar = False


# Read from CSV file to list of dict
def read_csv(filename):
    with open(filename, newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        return list(reader)


def write_calendar_to_ddb(calendar_file):
    # Read the calendar from CSV
    bin_collections = read_csv(calendar_file)
    # Get the last item in the calendar
    last_item = bin_collections[-1]
    # Get the last_item from DynamoDB
    response = table.get_item(Key={"id": last_item["id"]})
    # If response is empty, write the calendar to DynamoDB
    if "Item" not in response:
        # Batch write all items to DynamoDB
        print("Writing the calendar to DynamoDB")
        with table.batch_writer() as batch:
            for bin_collection in bin_collections:
                batch.put_item(Item=bin_collection)


def get_next_bin_collection_info(start_day):
    id = start_day - timedelta(days=start_day.weekday())  # Start of the week
    res = table.get_item(Key={"id": str(id)})
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
        res["Item"]["bin_type"],
        date.fromisoformat(res["Item"]["collection_date"]).strftime("%A, %Y-%m-%d"),
    )


class LaunchRequestHandler(AbstractRequestHandler):
    """Handler for Skill Launch."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool

        return ask_utils.is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response

        # Manual trigger to update the calendar in DynamoDB
        if write_calendar:
            write_calendar_to_ddb(calendar_file)

        # The main part
        bin_type, collection_date = get_next_bin_collection_info(start_day)
        speak_output = f"{bin_type} will be collected on {collection_date}"

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
