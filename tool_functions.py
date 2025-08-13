from loguru import logger

import os
from sqlalchemy import select
from models.session import get_session

from datetime import datetime, timedelta
from typing import Dict, Optional, List
from twilio.rest import Client
from itsdangerous import URLSafeTimedSerializer
from decimal import Decimal

import time
import logging
from typing import Any
import random
import string

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from models.onboarding import OnboardingRecord
from models.session import get_session
import hashlib
import random
import string
from datetime import date

from models.db import (
    OnboardingRecord, Loan, LoanPayment, LoanStatus, LoanType, PaymentStatus,
    Savings, SavingsWithdrawal
)

from loguru import logger
from config import settings
from models.db import ComplainStatus, Complaint, Conversation, OTPManagement, Payment, Loan, LoanPayment, LoanStatus, LoanType, PaymentStatus
from utils.utils import ElevenLabsClient, text_to_whatsapp_audio_whisper, send_service_notification_email
from services.whatsapp_service import whatsapp_service
from services.verification.mail import EmailService

TWILIO_NUMBER = settings.twilio_number
TWILIO_NUM = settings.twilio_sender_phone
BACKEND_URL = settings.backend_url
serializer = URLSafeTimedSerializer(os.environ["SECRET_KEY"])

# Simulated user database for security question verification
SIMULATED_USERS_DB = {
    "+233559158793": {
        "name": "Gideon Gyimah",
        "phone_number": "+233559158793",
        "id_number": "GH-123456789-0",
        "date_of_birth": "1985-03-15",
        "security_question_1": "What was the name of your first pet?",
        "security_answer_1": "buddy",
        "security_question_2": "What is your favorite color?",
        "security_answer_2": "blue",
        "security_question_3": "What was the name of your first school?",
        "security_answer_3": "st_peters",
        "account_number": "1234567890",
        "email": "gideon.gyimah@email.com"
    },
    "+233559158794": {
        "name": "Sarah Johnson",
        "phone_number": "+233559158794", 
        "id_number": "GH-987654321-1",
        "date_of_birth": "1990-07-22",
        "security_question_1": "In which city were you born?",
        "security_answer_1": "accra",
        "security_question_2": "What is your mother's maiden name?",
        "security_answer_2": "williams",
        "security_question_3": "What was your childhood nickname?",
        "security_answer_3": "sarah_bear",
        "account_number": "0987654321",
        "email": "sarah.johnson@email.com"
    },
    "233557158456": {
        "name": "Michael Chen",
        "phone_number": "233557158456",
        "id_number": "GH-456789123-2", 
        "date_of_birth": "1988-11-08",
        "security_question_1": "What was your mother's maiden name?",
        "security_answer_1": "williams",
        "security_question_2": "What is your favorite food?",
        "security_answer_2": "rice",
        "security_question_3": "What was the name of your first car?",
        "security_answer_3": "toyota_camry",
        "account_number": "4567891230",
        "email": "michael.chen@email.com"
    }
}



async def send_payment_message(number: str, merchant_name: str, amount: float, sender_balance: Decimal = None) -> str:

    """
    Send payment notification to sender
    Args:
        number: Recipient's phone number
        merchant_name: Name of the merchant
        amount: Amount transferred
    """
    try:
        logger.info(f"Received number-sender: {number}")
        # Convert to string if it's a number
        number_str = str(number)
        
        # Check if the string already starts with a '+' sign
        if number_str.startswith('+'):
            clean_number = number_str
            logger.info("Plus sign is present in sender number")
        else:
            clean_number = f"+{number_str}"
            logger.info("Plus sign is not present in sender number, plus added")
            
        logger.info(f"Number to receive sending message: {clean_number}")     
        
        # Initialize Twilio client
        client = Client(
            os.getenv("TWILIO_ACCOUNT_SID"), 
            os.getenv("TWILIO_AUTH_TOKEN")
        )
        
        logger.info(f"Sending payment message to {clean_number}")
        # logger.info(f"The twilio number {TWILIO_NUM}")
        
        # Send WhatsApp message with payment details
        client.messages.create(
            body=f"You've sent an amount of {amount} to {merchant_name}",
            from_='+18289009639',  # Your Twilio WhatsApp number
            to=clean_number
        )
        
        logger.info(f"Payment message sent successfully to {clean_number}")
        return "Payment message sent successfully"   
    except Exception as e:
        logger.error(f"Error sending payment message: {str(e)}")
        raise


# async def send_whatsapp_audio_message(phone_number:str, text_response:str) -> Dict[str, str]:
#     """
#     respond to user with audio using WhatsApp Cloud API
#     Args:
#             phone_number: Recipient's whatsapp number
#             text_response: Text to convert to speech
#     Returns: 
#             audio only, don't add any extra text to the tool mesage, the only text should "play audio"...Avoid adding text like 'Please check your WhatsApp'
#     """
#     try:
#         if "+" in phone_number:
#             clean_number = phone_number
#             logger.info("Plus sign is present")
#         else:
#             clean_number = f"+{phone_number}"
#             logger.info("Plus sign is not present, plus added")

#         # Generate S3 URL for the audio
#         s3_audio_url = await text_to_whatsapp_audio_whisper(text_response)
        
#         # Import WhatsApp service
#         from services.whatsapp_service import whatsapp_service
        
#         logger.info(f"Sending audio to {clean_number}")
        
#         # Send audio message via WhatsApp Cloud API
#         result = await (
#             to=clean_number,
#             audio_url=s3_audio_url
#         )
        
#         logger.info(f"Audio sent successfully to {clean_number}")
#         return "tell user 'play audio'"
    
#     except Exception as e:
#         logger.error(f"Error sending WhatsApp audio message: {str(e)}")
#         raise

async def send_whatsapp_audio_message(phone_number:str, text_response:str) -> Dict[str, str]:
    """
    respond to user with audio
    Args:
            phone_number: Recipient's whatsapp number
            text_response: Text to convert to speech
    Returns: 
            audio only, don't add any extra text to the tool mesage, the only text should "play audio"...Avoid adding text like 'Please check your WhatsApp'
    """
    try:
        if "+" in phone_number:
            clean_number = phone_number
            logger.info("Plus sign is present")
        else:
            clean_number = f"+{phone_number}"
            logger.info("Plus sign is not present, plus added")

        # Generate S3 URL for the audio
        s3_audio_url = await text_to_whatsapp_audio_whisper(text_response)
        
        # Initialize Twilio client
        client = Client(
            os.getenv("TWILIO_ACCOUNT_SID"), 
            os.getenv("TWILIO_AUTH_TOKEN")
        )
        logger.info(f"Sending audio to {clean_number}")
        logger.info(f"The twilio number {TWILIO_NUMBER}")
        # Send WhatsApp message with audio
        message = client.messages.create(
            media_url=[s3_audio_url],
            from_=f"whatsapp:{TWILIO_NUMBER}",  # Your Twilio WhatsApp number
            to=f"whatsapp:{clean_number}"
        )
        logger.info(f"Audio sent successfully to {clean_number}")
        return "tell user 'play audio'"
    
    except Exception as e:
        logger.error(f"Error sending WhatsApp audio message: {str(e)}")
        raise


async def create_complaint(
    name:str, email:str, complaint_type:str, description:str, Mobile_Number:str
) -> Optional[Dict]:
    """Create a new complaint for user
    Args:
            name: Name of the user creating the complaint
            email: Email address of the user creating the complaint
            complaint_type: Type of complaint
            description: Description of the complaint
            Mobile_Number: -> customer mobile number with "+" and country code from customer profile
    """
    try:
        if "+" in Mobile_Number:
            clean_number = Mobile_Number
            logger.info("Plus sign is present")
        else:
            clean_number = f"+{Mobile_Number}"
            logger.info("Plus sign is not present, plus added")
        logger.info(f"clean number {clean_number}")
        
        async with get_session() as db:
            # Get the latest conversation using first() instead of scalar_one_or_none()
            stmt = select(Conversation).where(
                Conversation.phone_number == clean_number
            ).order_by(Conversation.created_at.desc()).limit(1)
            
            result = await db.execute(stmt)
            latest_conversation = result.scalar_one_or_none()  # Now safe to use scalar_one_or_none() because of limit(1)
            
            complaint = Complaint(
                name=name,
                email=email,
                phone_number=Mobile_Number,
                complaint_type=complaint_type,
                description=description,
                status=ComplainStatus.pending,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                conversation_id=latest_conversation.id if latest_conversation else None
            )
            
            db.add(complaint)
            await db.commit()
            await db.refresh(complaint)
        
            return {
                "id": complaint.id,
                "reference_number": f"COMP-{complaint.id:06d}",
                "name": complaint.name,
                "email": complaint.email,
                "phone_number": complaint.phone_number,
                "complaint_type": complaint.complaint_type,
                "status": complaint.status.value,
                "created_at": complaint.created_at.isoformat(),
                "message": "Complaint registered successfully. Our team will contact you soon."
            }
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating complaint: {str(e)}")
        raise
    finally:
        await db.close()

async def update_complaint(
    email:str,
    update_data:dict
) -> Optional[Dict]:
    """Update complaint by user email
    Args:
            email: Email address of the user used to create the complaint
            update_data: Dictionary containing fields to update
    """
    try:
        async with get_session() as db:
            # Use select() instead of query()
            stmt = select(Complaint).where(Complaint.email == email)
            result = await db.execute(stmt)
            complaint = result.scalar_one_or_none()
            
            if not complaint:
                return None
            
            for field, value in update_data.items():
                if hasattr(complaint, field):
                    setattr(complaint, field, value)
            
            complaint.updated_at = datetime.utcnow()
            await db.commit()
            await db.refresh(complaint)
        
            return {
                "id": complaint.id,
                "name": complaint.name,
                "email": complaint.email,
                "phone_number": complaint.phone_number,
                "complaint_type": complaint.complaint_type,
                "description": complaint.description,
                "status": complaint.status,
                "created_at": complaint.created_at,
                "updated_at": complaint.updated_at
            }
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating complaint: {str(e)}")
        raise

async def get_complaints_by_email(
    email:str
) -> Optional[Dict]:
    """Get complaints by user email 
    Args:
            email: Email address of the user used to create the complaint
    """
    try:
        async with get_session() as db:
            # Use select() instead of query()
            stmt = select(Complaint).where(
                Complaint.email == email
            ).order_by(Complaint.created_at.desc())
            result = await db.execute(stmt)
            complaints = result.scalars().all()
            
            return [{
                "id": complaint.id,
                "name": complaint.name,
                "email": complaint.email,
                "phone_number": complaint.phone_number,
                "complaint_type": complaint.complaint_type,
                "description": complaint.description,
                "status": complaint.status,
                "created_at": str(complaint.created_at),
                "updated_at": str(complaint.updated_at)
            } for complaint in complaints]
    except Exception as e:
        logger.error(f"Error getting complaints: {str(e)}")
        raise



elevenlabs_client = ElevenLabsClient()

# async def create_instant_batch_call(

#     phone_numbers: str,  # Comma-separated list of phone numbers
#  # Optional comma-separated list of first messages
#     call_reason: str , # Optional comma-separated list of prompts
#     item_and_user_details: str, 
#     user_number: str,  # Identifier for the batch call
#  # Pass the ElevenLabsClient instance
# ) -> Dict[str, Any]:
#     """
#     Create an instant batch call that will be scheduled for immediate execution.
    
#     Args:
#         otp:  OTP code to be sent to users for verification
#         phone_numbers:  phone number of user to verify

    
#     Returns:
#         Dict containing the complete API response from ElevenLabs
        
#     Raises:
#         HTTPException: If validation fails or API request fails
#     """
#     try:
#         languages = 'en' 
#         first_messages = f"Please enter the OTP {otp} to verify your identity"  
#         prompts = f"Say: 'Your OTP is {otp}. I will repeat this slowly 3 times.' Then say clearly and slowly: 'First: {otp}. Second: {otp}. Third: {otp}. Goodbye.' End call immediately. Speak slowly and do not respond to questions."
#         call_name = "Instant Batch Call" 
#         agent_id = "agent_01jwc75ftwfbd9mn8h8rkz742f"
#         agent_phone_number_id = "phnum_01jvvht41wf1aty70pk0vj74mj"
#         # Parse phone numbers
#         phone_number_list = [num.strip() for num in phone_numbers.split(",") if num.strip()]
#         if not phone_number_list:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="No valid phone numbers provided"
#             )
        
#         num_recipients = len(phone_number_list)
        
#         # Parse optional languages, first messages, and prompts
#         language_list = [lang.strip() for lang in languages.split(",")] if languages else [None] * num_recipients
#         first_message_list = [msg.strip() for msg in first_messages.split(",")] if first_messages else [None] * num_recipients
#         prompt_list = [prompt.strip() for prompt in prompts.split(",")] if prompts else [None] * num_recipients
        
#         # # Validate list lengths if optional fields are provided
#         # if languages and len(language_list) != num_recipients:
#         #     raise HTTPException(
#         #         status_code=status.HTTP_400_BAD_REQUEST,
#         #         detail=f"Number of languages ({len(language_list)}) must match number of phone numbers ({num_recipients})"
#         #     )
#         # if first_messages and len(first_message_list) != num_recipients:
#         #     raise HTTPException(
#         #         status_code=status.HTTP_400_BAD_REQUEST,
#         #         detail=f"Number of first messages ({len(first_message_list)}) must match number of phone numbers ({num_recipients})"
#         #     )
#         # if prompts and len(prompt_list) != num_recipients:
#         #     raise HTTPException(
#         #         status_code=status.HTTP_400_BAD_REQUEST,
#         #         detail=f"Number of prompts ({len(prompt_list)}) must match number of phone numbers ({num_recipients})"
#         #     )
            
#         # Create recipients list with optional nested data
#         recipients = []
#         for i, phone in enumerate(phone_number_list):
#             agent_override_data = {}
#             if language_list[i] is not None and language_list[i] != "":
#                 agent_override_data["language"] = language_list[i]
#             if first_message_list[i] is not None and first_message_list[i] != "":
#                 agent_override_data["first_message"] = first_message_list[i]
#             if prompt_list[i] is not None and prompt_list[i] != "":
#                 agent_override_data["prompt"] = {"prompt": prompt_list[i]}
            
#             client_data = None
#             if agent_override_data:
#                 client_data = {
#                     "conversation_config_override": {
#                         "agent": agent_override_data
#                     }
#                 }
            
#             recipient_payload = {
#                 "phone_number": phone,
#                 "conversation_initiation_client_data": client_data
#             }
#             recipients.append(recipient_payload)
        
#         # Set scheduled time to current time + 30 seconds
#         scheduled_time_unix = int(time.time()) + 1
        
#         # Validate that elevenlabs_client is provided
#         if elevenlabs_client is None:
#             raise HTTPException(
#                 status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#                 detail="ElevenLabs client not provided"
#             )
        
#         # Log the request for debugging
#         logger.info(f"Creating instant batch call with name: {call_name}, agent_id: {agent_id}, recipients: {recipients}")
        
#         # Get the full API response
#         api_response = await elevenlabs_client.create_batch_call(
#             call_name=call_name,
#             agent_id=agent_id,
#             agent_phone_number_id=agent_phone_number_id,
#             recipients=recipients,
#             scheduled_time_unix=scheduled_time_unix
#         )
#         logger.info(f"API response: {api_response}")
        
#         # Log the response for debugging
#         logger.info(f"Instant batch call creation response: {api_response}")
        
#         # Return the complete API response
#         return {
#             "success": True,
#             "identifier": identifier,
#             "message": "Instant batch call created successfully",
#         }
        
#     except Exception as e:
#         logger.error(f"Failed to create instant batch call: {str(e)}")
#         # Re-raise HTTPExceptions or wrap unexpected errors
#         if isinstance(e, HTTPException):
#             raise e
#         else:
#             raise HTTPException(
#                 status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#                 detail=f"Failed to create instant batch call: {str(e)}"
#             )
        





async def request_user_location(phone_number: str, body_text: str = None) -> Dict[str, Any]:
    """Request user's location via WhatsApp location request message"""
    try:
        # Clean phone number
        if "+" in phone_number:
            clean_number = phone_number
        else:
            clean_number = f"+{phone_number}"
        
        # Send location request via WhatsApp
        result = await whatsapp_service.send_location_request(clean_number, body_text)
        
        if result.get('error'):
            return {
                "error": f"Failed to send location request: {result.get('error', {}).get('message', 'Unknown error')}"
            }
        
        return {
            "success": True,
            "message": "Location request sent successfully. The user will receive a message with a 'Send Location' button.",
            "phone_number": clean_number,
            "whatsapp_message_id": result.get('messages', [{}])[0].get('id') if result.get('messages') else None
        }
        
    except Exception as e:
        logger.error(f"Error requesting user location: {str(e)}")
        return {"error": str(e)}

async def generate_security_verification_link(
    customer_name: str, 
    mobile_number: str
) -> Optional[Dict]:
    """
    Send a structured security verification message with CTA URL button and image header
    Args:
        customer_name: customer name from profile
        mobile_number: customer mobile number (e.g 233558158591)
    Returns:
        Dictionary with success status and message details
    """
    try:
        # Create and encrypt token
        token = serializer.dumps(
            {"customer_name": customer_name, "mobile_number": mobile_number}
        )

        # Log the generated token and data
        logger.info(f"Generated security verification token: {token}")
        logger.info(f"Token data: {customer_name} and {mobile_number}")

        # Create the verification link
        verification_link = f"{BACKEND_URL}/verify-security?token={token}"

        # # Asset image URL for the header
        # header_image_url = "https://support.rebrandly.com/hc/article_attachments/17480600761373"

        # # Clean phone number for sending
        # if mobile_number.startswith('+'):
        #     clean_number = mobile_number
        # else:
        #     clean_number = f"+{mobile_number}"

        # # Send structured CTA URL button message
        # result = await whatsapp_service.send_cta_url_button(
        #     to=clean_number,
        #     header_image_url=header_image_url,
        #     body_text=f"Hello {customer_name}! To verify your identity, please tap the button below to answer your security question. This helps us ensure your account security.",
        #     button_text="Verify Identity",
        #     button_url=verification_link,
        #     footer_text="Secure verification process - expires in 30 minutes"
        # )

        # if result.get('messages'):
        #     logger.info(
        #         f"Security verification message sent successfully"
        #     )
        #     return {
        #         "success": True,
        #         "message": "Security verification message sent successfully",

        #     }
        # else:
        #     logger.error(f"Failed to send security verification message to {mobile_number}")
        #     return {
        #         "error": True,
        #         "message": "Failed to send security verification message",
        #         "details": result
        #     }
        return {
            "success": True,
            "message": "send the link to the user",
            "verification_link": verification_link
        }

    except Exception as e:
        # Create a detailed error response instead of raising the exception
        error_message = str(e)
        error_type = type(e).__name__

        logger.error(
            f"Error sending security verification message: {error_type} - {error_message}"
        )

    # Return a structured error response the agent can understand and handle
    return {
        "error": True,
        "message": f"Failed to send security verification message: {error_message}",
        "error_type": error_type,
        "data": f"data: {customer_name} and {mobile_number}",
    }

async def get_user_security_question(mobile_number: str) -> Dict[str, Any]:
    """
    Get user's security questions for verification
    Args:
        mobile_number: Customer's mobile number
    Returns:
        Dictionary with both security questions and user name
    """
    try:
        # Clean phone number
        if mobile_number.startswith('+'):
            clean_number = mobile_number
        else:
            clean_number = f"+{mobile_number}" if not mobile_number.startswith('+') else mobile_number
        # Look up user in simulated database
        user_data = SIMULATED_USERS_DB.get(clean_number)
        if not user_data:
            return {
                "error": True,
                "message": "User not found in our records. Please check your mobile number."
            }
        return {
            "success": True,
            "user_name": user_data["name"],
            "security_question_1": user_data["security_question_1"],
            "security_question_2": user_data["security_question_2"],
            "security_question_3": user_data["security_question_3"],
            "phone_number": user_data["phone_number"]
        }
    except Exception as e:
        logger.error(f"Error getting security questions: {str(e)}")
        return {
            "error": True,
            "message": f"Failed to retrieve security questions: {str(e)}"
        }

async def get_alternative_security_questions(mobile_number: str, exclude_question: str = None) -> Dict[str, Any]:
    """
    Get alternative security questions for verification (excludes one question)
    Args:
        mobile_number: Customer's mobile number
        exclude_question: Question to exclude (1, 2, or 3)
    Returns:
        Dictionary with alternative security questions and user name
    """
    try:
        # Clean phone number
        if mobile_number.startswith('+'):
            clean_number = mobile_number
        else:
            clean_number = f"+{mobile_number}" if not mobile_number.startswith('+') else mobile_number
        # Look up user in simulated database
        user_data = SIMULATED_USERS_DB.get(clean_number)
        if not user_data:
            return {
                "error": True,
                "message": "User not found in our records. Please check your mobile number."
            }
        
        # Determine which questions to return based on exclude_question
        if exclude_question == "1":
            return {
                "success": True,
                "user_name": user_data["name"],
                "security_question_1": user_data["security_question_2"],
                "security_question_2": user_data["security_question_3"],
                "security_answer_1": user_data["security_answer_2"],
                "security_answer_2": user_data["security_answer_3"],
                "phone_number": user_data["phone_number"]
            }
        elif exclude_question == "2":
            return {
                "success": True,
                "user_name": user_data["name"],
                "security_question_1": user_data["security_question_1"],
                "security_question_2": user_data["security_question_3"],
                "security_answer_1": user_data["security_answer_1"],
                "security_answer_2": user_data["security_answer_3"],
                "phone_number": user_data["phone_number"]
            }
        elif exclude_question == "3":
            return {
                "success": True,
                "user_name": user_data["name"],
                "security_question_1": user_data["security_question_1"],
                "security_question_2": user_data["security_question_2"],
                "security_answer_1": user_data["security_answer_1"],
                "security_answer_2": user_data["security_answer_2"],
                "phone_number": user_data["phone_number"]
            }
        else:
            # Default: return questions 1 and 2
            return {
                "success": True,
                "user_name": user_data["name"],
                "security_question_1": user_data["security_question_1"],
                "security_question_2": user_data["security_question_2"],
                "security_answer_1": user_data["security_answer_1"],
                "security_answer_2": user_data["security_answer_2"],
                "phone_number": user_data["phone_number"]
            }
    except Exception as e:
        logger.error(f"Error getting alternative security questions: {str(e)}")
        return {
            "error": True,
            "message": f"Failed to retrieve alternative security questions: {str(e)}"
        }

async def verify_security_answer(mobile_number: str, security_answer_1: str, security_answer_2: str) -> Dict[str, Any]:
    """
    Verify user's answers to both security questions
    Args:
        mobile_number: Customer's mobile number
        security_answer_1: Answer to first security question
        security_answer_2: Answer to second security question
    Returns:
        Dictionary with verification result and user details
    """
    try:
        # Clean phone number
        if mobile_number.startswith('+'):
            clean_number = mobile_number
        else:
            clean_number = f"+{mobile_number}" if not mobile_number.startswith('+') else mobile_number
        # Look up user in simulated database
        user_data = SIMULATED_USERS_DB.get(clean_number)
        if not user_data:
            return {
                "error": True,
                "message": "User not found in our records. Please check your mobile number."
            }
        # Check if both answers match (case-insensitive)
        expected_1 = user_data["security_answer_1"].lower().strip()
        expected_2 = user_data["security_answer_2"].lower().strip()
        provided_1 = security_answer_1.lower().strip()
        provided_2 = security_answer_2.lower().strip()
        if expected_1 == provided_1 and expected_2 == provided_2:
            # Verification successful
            return {
                "success": True,
                "message": "Security verification successful!",
                "user_details": {
                    "name": user_data["name"],
                    "phone_number": user_data["phone_number"],
                    "id_number": user_data["id_number"],
                    "date_of_birth": user_data["date_of_birth"],
                    "account_number": user_data["account_number"],
                    "email": user_data["email"]
                }
            }
        else:
            return {
                "error": True,
                "message": "Incorrect security answers. Please try again."
            }
    except Exception as e:
        logger.error(f"Error in security verification: {str(e)}")
        return {
            "error": True,
            "message": f"Verification failed: {str(e)}"
        }

async def verify_security_answer_flexible(mobile_number: str, security_answer_1: str, security_answer_2: str, question_combination: str = "1,2") -> Dict[str, Any]:
    """
    Verify user's answers to security questions with flexible combination support
    Args:
        mobile_number: Customer's mobile number
        security_answer_1: Answer to first security question
        security_answer_2: Answer to second security question
        question_combination: Which questions are being answered (e.g., "1,2", "1,3", "2,3")
    Returns:
        Dictionary with verification result and user details
    """
    try:
        # Clean phone number
        if mobile_number.startswith('+'):
            clean_number = mobile_number
        else:
            clean_number = f"+{mobile_number}" if not mobile_number.startswith('+') else mobile_number
        # Look up user in simulated database
        user_data = SIMULATED_USERS_DB.get(clean_number)
        if not user_data:
            return {
                "error": True,
                "message": "User not found in our records. Please check your mobile number."
            }
        
        # Parse question combination
        questions = question_combination.split(',')
        if len(questions) != 2:
            return {
                "error": True,
                "message": "Invalid question combination. Please provide exactly 2 questions."
            }
        
        # Get expected answers based on question combination
        if questions == ["1", "2"]:
            expected_1 = user_data["security_answer_1"].lower().strip()
            expected_2 = user_data["security_answer_2"].lower().strip()
        elif questions == ["1", "3"]:
            expected_1 = user_data["security_answer_1"].lower().strip()
            expected_2 = user_data["security_answer_3"].lower().strip()
        elif questions == ["2", "3"]:
            expected_1 = user_data["security_answer_2"].lower().strip()
            expected_2 = user_data["security_answer_3"].lower().strip()
        else:
            return {
                "error": True,
                "message": "Invalid question combination. Please use 1,2 or 1,3 or 2,3."
            }
        
        # Check if both answers match (case-insensitive)
        provided_1 = security_answer_1.lower().strip()
        provided_2 = security_answer_2.lower().strip()
        
        if expected_1 == provided_1 and expected_2 == provided_2:
            # Verification successful
            return {
                "success": True,
                "message": "Security verification successful!",
                "user_details": {
                    "name": user_data["name"],
                    "phone_number": user_data["phone_number"],
                    "id_number": user_data["id_number"],
                    "date_of_birth": user_data["date_of_birth"],
                    "account_number": user_data["account_number"],
                    "email": user_data["email"]
                }
            }
        else:
            return {
                "error": True,
                "message": "Incorrect security answers. Please try again or use the 'regenerate' option for different questions."
            }
    except Exception as e:
        logger.error(f"Error in flexible security verification: {str(e)}")
        return {
            "error": True,
            "message": f"Verification failed: {str(e)}"
        }

async def generate_payment_link(
    customer_name: str, 
    mobile_number: str
) -> Optional[Dict]:
    """
    Send a structured payment link message with CTA URL button and image header
    Args:
        customer_name: customer name from profile
        mobile_number: customer mobile number (e.g 233558158591)
    Returns:
        Dictionary with success status and message details
    """
    try:
        # Create and encrypt token for payment
        token = serializer.dumps(
            {"customer_name": customer_name, "mobile_number": mobile_number, "type": "payment"}
        )

        # Log the generated token and data
        logger.info(f"Generated payment token: {token}")
        logger.info(f"Payment token data: {customer_name} and {mobile_number}")

        # Create the payment link (you can customize this URL)
        payment_link = f"{BACKEND_URL}/payment?token={token}"

        # Asset image URL for the header (using the same security icon for now)
        # header_image_url = "https://support.rebrandly.com/hc/article_attachments/17480600761373"

        # # Clean phone number for sending
        # if mobile_number.startswith('+'):
        #     clean_number = mobile_number
        # else:
        #     clean_number = f"+{mobile_number}"

        # # Send structured CTA URL button message
        # result = await whatsapp_service.send_cta_url_button(
        #     to=clean_number,
        #     header_image_url=header_image_url,
        #     body_text=f"Hello {customer_name}! Your payment is ready. Please tap the button below to complete your secure payment. This link is valid for 30 minutes.",
        #     button_text="Pay Now",
        #     button_url=payment_link,
        #     footer_text="Secure payment process - expires in 30 minutes"
        # )

        # if result.get('messages'):
        #     logger.info(
        #         f"Payment link message sent successfully"
        #     )
        #     return {
        #         "success": True,
        #         "message": "Payment link message sent to user successfully",
               
        #     }
        # else:
        #     logger.error(f"Failed to send payment link message to {mobile_number}")
        #     return {
        #         "error": True,
        #         "message": "Failed to send payment link message",
        #         "details": result
        #     }
        return {
            "success": True,
            "message": "Payment link message sent successfully",
            "payment_link": payment_link
        }

    except Exception as e:
        # Create a detailed error response instead of raising the exception
        error_message = str(e)
        error_type = type(e).__name__

        logger.error(
            f"Error sending payment link message: {error_type} - {error_message}"
        )

    # Return a structured error response the agent can understand and handle
    return {
        "error": True,
        "message": f"Failed to send payment link message: {error_message}",
        "error_type": error_type,
        "data": f"data: {customer_name} and {mobile_number}",
    }


async def activate_user_account(payment_reference: str) -> Dict[str, Any]:
    """
    Activate user account by verifying payment reference code
    Args:
        payment_reference: Payment reference code to verify
    Returns:
        Dictionary with activation result
    """
    try:
        # Clean the reference code
        clean_reference = payment_reference.strip()
        
        if not clean_reference:
            return {
                "error": True,
                "message": "Payment reference code is required"
            }
        
        # Check if payment reference exists in database
        async with get_session() as db:
            stmt = select(Payment).where(Payment.reference_code == clean_reference)
            result = await db.execute(stmt)
            payment = result.scalar_one_or_none()
            
            if payment:
                # Payment reference exists - account activated
                logger.info(f"Account activated successfully for payment reference: {clean_reference}")
                return {
                    "success": True,
                    "message": "Account activated successfully! Your payment has been verified and your account is now active.",
                    "payment_reference": clean_reference,
                    "payment_amount": str(payment.amount),
                    "payment_currency": payment.currency,
                    "payment_date": payment.payment_date.isoformat() if payment.payment_date else None
                }
            else:
                # Payment reference not found
                logger.warning(f"Invalid payment reference code: {clean_reference}")
                return {
                    "error": True,
                    "message": "Invalid payment reference code. Please check your reference code and try again."
                }
                
    except Exception as e:
        logger.error(f"Error activating user account: {str(e)}")
        return {
            "error": True,
            "message": f"Failed to activate account: {str(e)}"
        }

async def get_user_details_by_name(name: str) -> dict:
    """
    Retrieve user details from SIMULATED_USERS_DB by name (case-insensitive).
    Excludes account number for security purposes.
    Args:
        name: The user's name to search for.
    Returns:
        Dict with user details if found, else error message.
    """
    try:
        for user in SIMULATED_USERS_DB.values():
            if user["name"].lower() == name.lower():
                # Create a copy of user details without account number
                user_details = user.copy()
                user_details.pop("account_number", None)  # Remove account number
                
                return {
                    "success": True,
                    "user_details": user_details
                }
        return {
            "error": True,
            "message": f"No user found with name: {name}"
        }
    except Exception as e:
        return {"error": True, "message": str(e)}

async def get_user_account_number(name: str) -> dict:
    """
    Retrieve only the account number from SIMULATED_USERS_DB by name (case-insensitive).
    Args:
        name: The user's name to search for.
    Returns:
        Dict with account number if found, else error message.
    """
    try:
        for user in SIMULATED_USERS_DB.values():
            if user["name"].lower() == name.lower():
                return {
                    "success": True,
                    "account_number": user["account_number"],
                    "user_name": user["name"]
                }
        return {
            "error": True,
            "message": f"No user found with name: {name}"
        }
    except Exception as e:
        return {"error": True, "message": str(e)}

async def create_account_confirmation(name: str) -> dict:
    """
    Dummy function to confirm account creation after user confirmation.
    Args:
        name: The user's name.
    Returns:
        Success message.
    """
    return {"success": True, "message": f"Account creation confirmed for {name}."}


async def generate_otp(mobile_number: str) -> dict:
    """
    Generate a 6-digit OTP code for a user via SMS and store it in the database.
    
    Args:
        mobile_number: Customer's mobile number in our system (e.g., +233559158793)
        
    Returns:
        Dictionary with a unique identifier for the OTP or an error message.
    """
    if "+" in mobile_number:
        clean_number = mobile_number
        logger.info("Plus sign is present")
    else:
        clean_number = f"+{mobile_number}"
        logger.info("Plus sign is not present, plus added")


    async with get_session() as db:
        try:
            # Clear any existing unexpired OTPs for this number
            stmt = select(OTPManagement).where(
                OTPManagement.mobile_number == mobile_number,
                OTPManagement.expires_at > datetime.utcnow(),
                OTPManagement.is_used == False
            )
            result = await db.execute(stmt)
            existing_otps = result.scalars().all()
            for otp_record in existing_otps:
                await db.delete(otp_record)

            # Generate a 6-digit OTP
            otp = ''.join(random.choices(string.digits, k=6))
            timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
            identifier = f"{mobile_number}_{timestamp}"

            # Create an OTP record with 5-minute expiration
            new_otp = OTPManagement(
                identifier=identifier,
                otp_code=otp,
                expires_at=datetime.utcnow() + timedelta(minutes=5),
                mobile_number=mobile_number
            )
            db.add(new_otp)
            await db.commit()

            # Send the OTP via SMS using Twilio
            try:
                client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))
                client.messages.create(
                    body=f'Your OTP code is: {otp}. Valid for 5 minutes.',
                    from_=TWILIO_NUM,
                    to=mobile_number
                )
                logger.info(f"OTP sent to {mobile_number}")
            except Exception as sms_error:
                logger.error(f"Failed to send OTP: {str(sms_error)}")
                await db.delete(new_otp)
                await db.commit()
                return {"error": "Failed to send OTP message. Please try again."}

            return {
                "identifier": identifier,
                "message": "OTP sent successfully. Please check your messages."
            }
        except Exception as e:
            await db.rollback()
            logger.error(f"Error generating OTP: {str(e)}")
            return {"error": f"Failed to generate OTP: {str(e)}"}
        
async def verify_otp(identifier: str, otp_code: str) -> dict:
    """
    Verify OTP for account creation

    Args:
        identifier: OTP identifier (format: mobile_number_timestamp)
        otp_code: OTP code provided by the user
    
    Returns:
        Dictionary containing the customer's name and a success message if OTP is valid,
        otherwise an error message.
    """
    logger.info('Initializing verify OTP and get name')
    
    async with get_session() as db:
        try:
            # Query OTP record
            stmt = select(OTPManagement).where(OTPManagement.identifier == identifier)
            result = await db.execute(stmt)
            otp_record = result.scalar_one_or_none()
            
            if not otp_record:
                return {"error": "Invalid OTP identifier. Please request a new OTP."}

            if datetime.utcnow() > otp_record.expires_at:
                await db.delete(otp_record)
                await db.commit()
                return {"error": "OTP has expired. Please request a new OTP."}

            if otp_record.is_used:
                return {"error": "This OTP has already been used. Please request a new OTP."}

            if otp_record.otp_code != otp_code:
                return {"error": "Incorrect OTP code. Please try again."}
                
            # Extract mobile number from identifier
            mobile_number = otp_record.mobile_number
            logger.info(f"mobile number: {mobile_number}")
            
            # Mark OTP as used
            otp_record.is_used = True
            await db.commit()

            return {
                "message": "OTP verified successfully."
            }
        except Exception as e:
            await db.rollback()
            logger.error(f"Error verifying OTP: {str(e)}")
            return {"error": f"Error verifying OTP: {str(e)}"}

async def send_email_verification_code(email: str) -> dict:
    """
    Send a verification code to the user's email address using EmailService.
    Args:
        email: The user's email address.
    Returns:
        Dictionary with success status and message details.
    """
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_username = os.getenv("SMTP_USERNAME")
    sender_email = os.getenv("FROM_EMAIL")
    smtp_password = os.getenv("SMTP_PASSWORD")
    if not all([smtp_server, smtp_port, sender_email, smtp_password]):
        return {"error": True, "message": "SMTP configuration is incomplete."}
    email_service = EmailService(
        smtp_server=smtp_server,
        smtp_port=smtp_port,
        smtp_username=smtp_username or sender_email,
        sender_email=sender_email,
        password=smtp_password,
    )
    try:
        result = await email_service.send_verification_message(email)
        if result:
            return {"success": True, "message": "Verification email sent successfully."}
        else:
            return {"error": True, "message": "Failed to send verification email."}
    except Exception as e:
        return {"error": True, "message": str(e)}

async def verify_email_code(email: str, code: str) -> dict:
    """
    Verify the code sent to the user's email address using EmailService (TOTP logic).
    Args:
        email: The user's email address.
        code: The code provided by the user.
    Returns:
        Dictionary with verification result.
    """
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_username = os.getenv("SMTP_USERNAME")
    sender_email = os.getenv("FROM_EMAIL")
    smtp_password = os.getenv("SMTP_PASSWORD")
    if not all([smtp_server, smtp_port, sender_email, smtp_password]):
        return {"error": True, "message": "SMTP configuration is incomplete."}
    email_service = EmailService(
        smtp_server=smtp_server,
        smtp_port=smtp_port,
        smtp_username=smtp_username or sender_email,
        sender_email=sender_email,
        password=smtp_password,
    )
    try:
        # The TOTP is stateless, so we just verify the code
        valid = await email_service.verify_otp(code)
        if valid:
            return {"success": True, "message": "Email verified successfully."}
        else:
            return {"error": True, "message": "Invalid or expired verification code."}
    except Exception as e:
        return {"error": True, "message": str(e)}

async def generate_security_password_pin_link(user_phone_number: str = None) -> dict:
    """
    Generate a secure link to the set_security_password_pin form, optionally with a user-specific token.
    Args:
        user_phone_number: Optional user phone number to encode in the token
    Returns:
        Dictionary with the link
    """
    import os
    BACKEND_URL = os.getenv("BACKEND_URL", "https://f80ecbdaae8f.ngrok-free.app")
    serializer = URLSafeTimedSerializer(os.environ["SECRET_KEY"])
    if user_phone_number:
        token = serializer.dumps({"user_phone_number": user_phone_number})
        link = f"{BACKEND_URL}/set-security-password-pin?token={token}"
    else:
        link = f"{BACKEND_URL}/set-security-password-pin"
    return {"success": True, "link": link}

class OnboardingRecordInput(BaseModel):
    # Personal info
    first_name: str
    last_name: str
    gender: str
    dob: date
    nationality: str
    id_number: str
    phone: str
    email: EmailStr
    # Employment
    employment_type: str
    employer_name: Optional[str] = None
    institution: Optional[str] = None
    employer_address: Optional[str] = None
    employment_date: Optional[date] = None
    nature_of_employment: Optional[str] = None
    designation: Optional[str] = None
    # Self-employment
    business_name: Optional[str] = None
    business_type: Optional[str] = None
    business_location: Optional[str] = None
    business_address: Optional[str] = None
    monthly_income: Optional[float] = None
    # Emergency contact
    emergency_contact_name: str
    emergency_contact_relationship: str
    emergency_contact_phone: str
    emergency_contact_address: str
    emergency_contact_town: str
    # Account type/services
    account_type: str
    monthly_contribution: float
    sms_alert: bool
    mobile_banking: bool
    card: bool
    terms_accepted: bool
    # Security questions
    security_question_1: str
    security_answer_1: str
    security_question_2: str
    security_answer_2: str
    security_question_3: str
    security_answer_3: str
    # Credentials
    password: str
    pin: str

async def save_onboarding_record(data: OnboardingRecordInput) -> dict:
    """
    Save onboarding record, hash password and pin, generate unique account number, return success and account number.
    """
    def hash_value(val):
        return hashlib.sha256(val.encode()).hexdigest()

    # Generate unique account number (e.g., 10-digit random)
    def generate_account_number():
        return ''.join(random.choices(string.digits, k=10))
    logger.info(f"Saving onboarding record: {data}")

    async with get_session() as db:
        # Ensure unique account number
        for _ in range(5):
            account_number = generate_account_number()
            result = await db.execute(
                select(OnboardingRecord).filter_by(account_number=account_number)
            )
            if not result.scalar():
                break
        else:
            return {"success": False, "error": "Could not generate unique account number."}

        record = OnboardingRecord(
            account_number=account_number,
            created_at=datetime.utcnow(),
            first_name=data.first_name,
            last_name=data.last_name,
            gender=data.gender,
            dob=data.dob,
            nationality=data.nationality,
            id_number=data.id_number,
            phone=data.phone,
            email=data.email,
            employment_type=data.employment_type,
            employer_name=data.employer_name,
            institution=data.institution,
            employer_address=data.employer_address,
            employment_date=data.employment_date,
            nature_of_employment=data.nature_of_employment,
            designation=data.designation,
            business_name=data.business_name,
            business_type=data.business_type,
            business_location=data.business_location,
            business_address=data.business_address,
            monthly_income=data.monthly_income,
            emergency_contact_name=data.emergency_contact_name,
            emergency_contact_relationship=data.emergency_contact_relationship,
            emergency_contact_phone=data.emergency_contact_phone,
            emergency_contact_address=data.emergency_contact_address,
            emergency_contact_town=data.emergency_contact_town,
            account_type=data.account_type,
            monthly_contribution=data.monthly_contribution,
            sms_alert=data.sms_alert,
            mobile_banking=data.mobile_banking,
            card=data.card,
            terms_accepted=data.terms_accepted,
            security_question_1=data.security_question_1,
            security_answer_1=data.security_answer_1,
            security_question_2=data.security_question_2,
            security_answer_2=data.security_answer_2,
            security_question_3=data.security_question_3,
            security_answer_3=data.security_answer_3,
            password_hash=hash_value(data.password),
            pin_hash=hash_value(data.pin)
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
        return {"success": True, "account_number": account_number}


# Loan-related functions

async def create_loan_request(
    member_phone: str,
    loan_type: str,
    loan_amount: float,
    loan_purpose: str,
    loan_term_months: int,
    monthly_income: float,
    collateral_type: str = None,
    collateral_value: float = None,
    collateral_description: str = None,
    guarantor_name: str = None,
    guarantor_phone: str = None,
    guarantor_relationship: str = None,
    guarantor_income: float = None,
    employment_duration_months: int = None,
    employer_name: str = None
) -> dict:
    """
    Create a new loan request for a member
    Args:
        member_phone: Member's phone number
        loan_type: Type of loan (personal, business, education, etc.)
        loan_amount: Requested loan amount
        loan_purpose: Purpose of the loan
        loan_term_months: Loan term in months
        monthly_income: Member's monthly income
        collateral_type: Type of collateral (optional)
        collateral_value: Value of collateral (optional)
        collateral_description: Description of collateral (optional)
        guarantor_name: Name of guarantor (optional)
        guarantor_phone: Phone number of guarantor (optional)
        guarantor_relationship: Relationship to guarantor (optional)
        guarantor_income: Guarantor's monthly income (optional)
        employment_duration_months: Duration of employment in months (optional)
        employer_name: Name of employer (optional)
    Returns:
        Dictionary with loan request details and reference number
    """
    try:
        # Clean phone number
        if member_phone.startswith('+'):
            clean_phone = member_phone
        else:
            clean_phone = f"+{member_phone}"
        
        async with get_session() as db:
            # Find member by phone number
            stmt = select(OnboardingRecord).where(OnboardingRecord.phone == clean_phone)
            result = await db.execute(stmt)
            member = result.scalar_one_or_none()
            
            if not member:
                return {
                    "error": True,
                    "message": "Member not found. Please ensure you have completed the onboarding process."
                }
            
            # Validate loan type
            try:
                loan_type_enum = LoanType(loan_type.lower())
            except ValueError:
                return {
                    "error": True,
                    "message": f"Invalid loan type. Please choose from: {', '.join([lt.value for lt in LoanType])}"
                }
            
            # Calculate loan terms (simplified calculation)
            # In a real system, this would be more complex based on credit score, income, etc.
            interest_rate = Decimal('12.5')  # 12.5% annual interest rate
            monthly_interest_rate = interest_rate / Decimal('12') / Decimal('100')
            
            # Calculate monthly payment using simplified formula
            principal = Decimal(str(loan_amount))
            term_months = Decimal(str(loan_term_months))
            
            if monthly_interest_rate > 0:
                monthly_payment = principal * (monthly_interest_rate * (1 + monthly_interest_rate) ** term_months) / ((1 + monthly_interest_rate) ** term_months - 1)
            else:
                monthly_payment = principal / term_months
            
            total_payable = monthly_payment * term_months
            
            # Generate loan reference
            timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
            loan_reference = f"LOAN{timestamp}{random.randint(1000, 9999)}"
            
            # Create loan record
            loan = Loan(
                loan_reference=loan_reference,
                member_id=member.id,
                loan_type=loan_type_enum,
                loan_amount=principal,
                loan_purpose=loan_purpose,
                loan_term_months=loan_term_months,
                interest_rate=interest_rate,
                monthly_payment=monthly_payment,
                total_payable=total_payable,
                collateral_type=collateral_type,
                collateral_value=collateral_value,
                collateral_description=collateral_description,
                guarantor_name=guarantor_name,
                guarantor_phone=guarantor_phone,
                guarantor_relationship=guarantor_relationship,
                guarantor_income=guarantor_income,
                monthly_income=Decimal(str(monthly_income)),
                employment_duration_months=employment_duration_months,
                employer_name=employer_name,
                status=LoanStatus.PENDING
            )
            
            db.add(loan)
            await db.commit()
            await db.refresh(loan)
            
            return {
                "success": True,
                "message": "Loan request submitted successfully. Our team will review your application.",
                "loan_reference": loan_reference,
                "loan_details": {
                    "loan_type": loan_type_enum.value,
                    "loan_amount": str(loan_amount),
                    "loan_purpose": loan_purpose,
                    "loan_term_months": loan_term_months,
                    "monthly_payment": str(monthly_payment),
                    "total_payable": str(total_payable),
                    "interest_rate": str(interest_rate) + "%"
                },
                "member_name": f"{member.first_name} {member.last_name}",
                "application_date": loan.application_date.isoformat()
            }
            
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating loan request: {str(e)}")
        return {
            "error": True,
            "message": f"Failed to create loan request: {str(e)}"
        }


async def get_loan_status(loan_reference: str = None, member_phone: str = None) -> dict:
    """
    Get loan status by loan reference or member phone number
    Args:
        loan_reference: Loan reference number (optional if member_phone provided)
        member_phone: Member's phone number (optional if loan_reference provided)
    Returns:
        Dictionary with loan status and details
    """
    try:
        async with get_session() as db:
            if loan_reference:
                # Get loan by reference
                stmt = select(Loan).where(Loan.loan_reference == loan_reference)
                result = await db.execute(stmt)
                loan = result.scalar_one_or_none()
                
                if not loan:
                    return {
                        "error": True,
                        "message": "Loan not found with the provided reference number."
                    }
                
                # Get member details
                member_stmt = select(OnboardingRecord).where(OnboardingRecord.id == loan.member_id)
                member_result = await db.execute(member_stmt)
                member = member_result.scalar_one_or_none()
                
            elif member_phone:
                # Clean phone number
                if member_phone.startswith('+'):
                    clean_phone = member_phone
                else:
                    clean_phone = f"+{member_phone}"
                
                # Get member first
                member_stmt = select(OnboardingRecord).where(OnboardingRecord.phone == clean_phone)
                member_result = await db.execute(member_stmt)
                member = member_result.scalar_one_or_none()
                
                if not member:
                    return {
                        "error": True,
                        "message": "Member not found with the provided phone number."
                    }
                
                # Get all loans for member
                stmt = select(Loan).where(Loan.member_id == member.id).order_by(Loan.created_at.desc())
                result = await db.execute(stmt)
                loans = result.scalars().all()
                
                if not loans:
                    return {
                        "success": True,
                        "message": "No loan applications found for this member.",
                        "member_name": f"{member.first_name} {member.last_name}",
                        "loans": []
                    }
                
                # Return all loans for the member
                loan_list = []
                for loan in loans:
                    loan_data = {
                        "loan_reference": loan.loan_reference,
                        "loan_type": loan.loan_type.value,
                        "loan_amount": float(loan.loan_amount),
                        "loan_purpose": loan.loan_purpose,
                        "status": loan.status.value,
                        "application_date": loan.application_date.isoformat(),
                        "monthly_payment": float(loan.monthly_payment),
                        "total_payable": float(loan.total_payable)
                    }
                    
                    if loan.approval_date:
                        loan_data["approval_date"] = loan.approval_date.isoformat()
                    if loan.disbursement_date:
                        loan_data["disbursement_date"] = loan.disbursement_date.isoformat()
                    if loan.rejection_reason:
                        loan_data["rejection_reason"] = loan.rejection_reason
                    
                    loan_list.append(loan_data)
                
                return {
                    "success": True,
                    "message": f"Found {len(loan_list)} loan application(s) for this member.",
                    "member_name": f"{member.first_name} {member.last_name}",
                    "loans": loan_list
                }
            else:
                return {
                    "error": True,
                    "message": "Please provide either loan reference or member phone number."
                }
            
            # Single loan response
            loan_data = {
                "loan_reference": loan.loan_reference,
                "loan_type": loan.loan_type.value,
                "loan_amount": float(loan.loan_amount),
                "loan_purpose": loan.loan_purpose,
                "loan_term_months": loan.loan_term_months,
                "status": loan.status.value,
                "application_date": loan.application_date.isoformat(),
                "monthly_payment": str(loan.monthly_payment),
                "total_payable": str(loan.total_payable),
                "interest_rate": str(loan.interest_rate) + "%"
            }
            
            if loan.approval_date:
                loan_data["approval_date"] = loan.approval_date.isoformat()
            if loan.disbursement_date:
                loan_data["disbursement_date"] = loan.disbursement_date.isoformat()
            if loan.rejection_reason:
                loan_data["rejection_reason"] = loan.rejection_reason
            if loan.notes:
                loan_data["notes"] = loan.notes
            
            return {
                "success": True,
                "message": "Loan status retrieved successfully.",
                "member_name": f"{member.first_name} {member.last_name}",
                "loan": loan_data
            }
            
    except Exception as e:
        logger.error(f"Error getting loan status: {str(e)}")
        return {
            "error": True,
            "message": f"Failed to retrieve loan status: {str(e)}"
        }


async def get_loan_types() -> dict:
    """
    Get available loan types and their basic information
    Returns:
        Dictionary with available loan types and details
    """
    try:
        loan_types_info = {
            "personal": {
                "name": "Personal Loan",
                "max_amount": 50000,
                "max_term": 36,
                "interest_rate": "12.5%",
                "requirements": ["Valid ID", "Proof of income", "Bank statements"]
            },
            "business": {
                "name": "Business Loan",
                "max_amount": 200000,
                "max_term": 60,
                "interest_rate": "15.0%",
                "requirements": ["Business registration", "Financial statements", "Business plan"]
            },
            "education": {
                "name": "Education Loan",
                "max_amount": 100000,
                "max_term": 48,
                "interest_rate": "10.0%",
                "requirements": ["Admission letter", "Fee structure", "Guarantor"]
            },
            "emergency": {
                "name": "Emergency Loan",
                "max_amount": 25000,
                "max_term": 12,
                "interest_rate": "18.0%",
                "requirements": ["Valid ID", "Proof of emergency", "Quick approval"]
            },
            "home_improvement": {
                "name": "Home Improvement Loan",
                "max_amount": 150000,
                "max_term": 60,
                "interest_rate": "13.5%",
                "requirements": ["Property ownership", "Quotes from contractors", "Building permits"]
            },
            "vehicle": {
                "name": "Vehicle Loan",
                "max_amount": 300000,
                "max_term": 72,
                "interest_rate": "14.0%",
                "requirements": ["Vehicle registration", "Insurance", "Down payment"]
            },
            "agriculture": {
                "name": "Agriculture Loan",
                "max_amount": 100000,
                "max_term": 48,
                "interest_rate": "11.0%",
                "requirements": ["Land ownership/lease", "Farming plan", "Market analysis"]
            },
            "other": {
                "name": "Other Loan",
                "max_amount": 75000,
                "max_term": 36,
                "interest_rate": "16.0%",
                "requirements": ["Valid ID", "Proof of income", "Purpose documentation"]
            }
        }
        
        return {
            "success": True,
            "message": "Available loan types retrieved successfully.",
            "loan_types": loan_types_info
        }
        
    except Exception as e:
        logger.error(f"Error getting loan types: {str(e)}")
        return {
            "error": True,
            "message": f"Failed to retrieve loan types: {str(e)}"
        }

async def get_loan_repayment_progress(member_phone: str, loan_reference: str = None) -> dict:
    """
    Get detailed loan repayment progress for a member.
    Shows total paid, remaining balance, completion percentage, and payment history.
    """
    try:
        async with get_session() as db:
            # Find member
            stmt = select(OnboardingRecord).where(OnboardingRecord.phone == member_phone)
            result = await db.execute(stmt)
            member = result.scalar_one_or_none()
            
            if not member:
                return {
                    "success": False,
                    "message": f"Member with phone {member_phone} not found."
                }
            
            # Build query for loans
            if loan_reference:
                # Get specific loan
                stmt = select(Loan).where(
                    Loan.member_id == member.id,
                    Loan.loan_reference == loan_reference
                )
            else:
                # Get all active loans
                stmt = select(Loan).where(
                    Loan.member_id == member.id,
                    Loan.status.in_([LoanStatus.ACTIVE, LoanStatus.DISBURSED])
                )
            
            result = await db.execute(stmt)
            loans = result.scalars().all()
            
            if not loans:
                return {
                    "success": True,
                    "message": "No active loans found for this member.",
                    "member_name": f"{member.first_name} {member.last_name}",
                    "total_outstanding": "0.00",
                    "active_loans": 0,
                    "loans": []
                }
            
            total_outstanding = Decimal('0.00')
            loan_details = []
            
            for loan in loans:
                # Calculate total paid from payments
                payment_stmt = select(LoanPayment).where(
                    LoanPayment.loan_id == loan.id,
                    LoanPayment.payment_status == PaymentStatus.PAID
                ).order_by(LoanPayment.payment_date.desc())
                
                payment_result = await db.execute(payment_stmt)
                payments = payment_result.scalars().all()
                
                total_paid = sum(payment.payment_amount for payment in payments)
                remaining_balance = loan.total_payable - total_paid
                completion_percentage = (total_paid / loan.total_payable * 100) if loan.total_payable > 0 else 0
                
                total_outstanding += remaining_balance
                
                # Get payment history (last 5 payments)
                payment_history = []
                for payment in payments[:5]:
                    payment_history.append({
                        "payment_date": payment.payment_date.strftime("%Y-%m-%d"),
                        "amount": str(payment.payment_amount),
                        "method": payment.payment_method,
                        "status": payment.payment_status.value
                    })
                
                # Calculate next payment date
                next_payment_date = None
                if loan.disbursement_date and len(payments) < loan.loan_term_months:
                    next_payment_date = loan.disbursement_date + timedelta(days=30 * (len(payments) + 1))
                
                # Calculate days overdue
                days_overdue = 0
                if next_payment_date and next_payment_date < datetime.now():
                    days_overdue = (datetime.now() - next_payment_date).days
                
                loan_details.append({
                    "loan_reference": loan.loan_reference,
                    "loan_type": loan.loan_type.value,
                    "loan_amount": float(loan.loan_amount),
                    "total_payable": float(loan.total_payable),
                    "total_paid": float(total_paid),
                    "remaining_balance": float(remaining_balance),
                    "completion_percentage": round(completion_percentage, 2),
                    "payments_made": len(payments),
                    "total_payments": loan.loan_term_months,
                    "next_payment_date": next_payment_date.strftime("%Y-%m-%d") if next_payment_date else None,
                    "days_overdue": days_overdue,
                    "payment_history": payment_history,
                    "status": loan.status.value
                })
            
            return {
                "success": True,
                "message": "Loan repayment progress retrieved successfully.",
                "member_name": f"{member.first_name} {member.last_name}",
                "total_outstanding": float(total_outstanding),
                "active_loans": len(loans),
                "loans": loan_details
            }
            
    except Exception as e:
        logger.error(f"Error getting loan repayment progress: {str(e)}")
        return {
            "success": False,
            "message": f"Error retrieving loan repayment progress: {str(e)}"
        }

async def get_borrowing_capacity(member_phone: str) -> dict:
    """
    Calculate member's borrowing capacity based on income, existing loans, and SACCO policies.
    """
    try:
        async with get_session() as db:
            # Find member
            stmt = select(OnboardingRecord).where(OnboardingRecord.phone == member_phone)
            result = await db.execute(stmt)
            member = result.scalar_one_or_none()
            
            if not member:
                return {
                    "success": False,
                    "message": f"Member with phone {member_phone} not found."
                }
            
            monthly_income = member.monthly_income
            
            # Get active loans
            stmt = select(Loan).where(
                Loan.member_id == member.id,
                Loan.status.in_([LoanStatus.ACTIVE, LoanStatus.DISBURSED])
            )
            result = await db.execute(stmt)
            active_loans = result.scalars().all()
            
            # Calculate total monthly debt payments
            total_monthly_debt = Decimal('0.00')
            total_outstanding_debt = Decimal('0.00')
            
            for loan in active_loans:
                total_monthly_debt += loan.monthly_payment
                
                # Calculate remaining balance
                payment_stmt = select(LoanPayment).where(
                    LoanPayment.loan_id == loan.id,
                    LoanPayment.payment_status == PaymentStatus.PAID
                )
                payment_result = await db.execute(payment_stmt)
                payments = payment_result.scalars().all()
                total_paid = sum(payment.payment_amount for payment in payments)
                remaining_balance = loan.total_payable - total_paid
                total_outstanding_debt += remaining_balance
            
            # Calculate debt-to-income ratio
            debt_to_income_ratio = (total_monthly_debt / monthly_income * 100) if monthly_income > 0 else 0
            
            # SACCO borrowing capacity rules
            max_dti_ratio = 40  # Maximum debt-to-income ratio (40%)
            income_multiplier = 3  # Maximum loan amount = 3x monthly income
            
            # Calculate maximum loan amount
            if debt_to_income_ratio >= max_dti_ratio:
                max_loan_amount = 0
                borrowing_status = "Limited"
                can_borrow = False
            elif debt_to_income_ratio >= 30:
                max_loan_amount = monthly_income * 1
                borrowing_status = "Moderate"
                can_borrow = True
            elif debt_to_income_ratio >= 20:
                max_loan_amount = monthly_income * 2
                borrowing_status = "Good"
                can_borrow = True
            else:
                max_loan_amount = monthly_income * income_multiplier
                borrowing_status = "Excellent"
                can_borrow = True
            
            # Get loan types for recommendations
            loan_types_result = await get_loan_types()
            available_loan_types = loan_types_result.get("loan_types", {})
            
            # Filter recommended loan types based on capacity
            recommended_loan_types = []
            for loan_type, details in available_loan_types.items():
                if details["max_amount"] <= max_loan_amount:
                    recommended_loan_types.append({
                        "type": loan_type,
                        "name": details["name"],
                        "max_amount": min(details["max_amount"], max_loan_amount),
                        "interest_rate": details["interest_rate"]
                    })
            
            # Generate suggestions
            suggestions = []
            if debt_to_income_ratio >= max_dti_ratio:
                suggestions.append("Focus on paying down existing debt before applying for new loans")
                suggestions.append("Consider debt consolidation options")
            elif debt_to_income_ratio >= 30:
                suggestions.append("Consider smaller loan amounts to maintain manageable debt levels")
                suggestions.append("Emergency and personal loans are most suitable")
            elif debt_to_income_ratio >= 20:
                suggestions.append("You have good borrowing capacity")
                suggestions.append("Consider business and vehicle loans for larger amounts")
            else:
                suggestions.append("Excellent borrowing capacity - all loan types available")
                suggestions.append("Consider long-term investments like home improvement loans")
            
            return {
                "success": True,
                "message": "Borrowing capacity analysis completed successfully.",
                "member_name": f"{member.first_name} {member.last_name}",
                "monthly_income": float(monthly_income),
                "total_monthly_debt": float(total_monthly_debt),
                "debt_to_income_ratio": round(debt_to_income_ratio, 2),
                "max_loan_amount": float(max_loan_amount),
                "active_loans_count": len(active_loans),
                "borrowing_status": borrowing_status,
                "recommendations": {
                    "can_borrow": can_borrow,
                    "recommended_loan_types": recommended_loan_types,
                    "suggestions": suggestions
                }
            }
            
    except Exception as e:
        logger.error(f"Error calculating borrowing capacity: {str(e)}")
        return {
            "success": False,
            "message": f"Error calculating borrowing capacity: {str(e)}"
        }

# ============================================================================
# SAVINGS SYSTEM FUNCTIONS
# ============================================================================

async def get_savings_accounts(member_phone: str) -> dict:
    """Get all savings accounts for a member by phone number."""
    try:
        async with get_session() as db:
            stmt = select(OnboardingRecord).where(OnboardingRecord.phone == member_phone)
            result = await db.execute(stmt)
            member = result.scalar_one_or_none()
            
            if not member:
                return {"success": False, "error": "Member not found."}
            
            stmt = select(Savings).where(Savings.member_id == member.id)
            result = await db.execute(stmt)
            accounts = result.scalars().all()
            
            if not accounts:
                return {
                    "success": True,
                    "member_name": f"{member.first_name} {member.last_name}",
                    "total_balance": 0.00,
                    "total_accounts": 0,
                    "accounts": [],
                    "message": "No savings accounts found. Start saving today!"
                }
            
            total_balance = sum(account.current_balance for account in accounts)
            accounts_data = []
            
            for account in accounts:
                accounts_data.append({
                    "account_reference": account.account_reference,
                    "account_name": account.account_name,
                    "savings_type": account.savings_type.value,
                    "current_balance": float(account.current_balance),
                    "interest_rate": float(account.interest_rate),
                    "total_deposits": float(account.total_deposits),
                    "total_withdrawals": float(account.total_withdrawals),
                    "total_interest_earned": float(account.total_interest_earned),
                    "is_active": account.is_active,
                    "is_locked": account.is_locked
                })
            
            return {
                "success": True,
                "member_name": f"{member.first_name} {member.last_name}",
                "total_balance": float(total_balance),
                "total_accounts": len(accounts),
                "accounts": accounts_data
            }
            
    except Exception as e:
        logger.error(f"Error getting savings accounts: {e}")
        return {"success": False, "error": str(e)}



async def add_savings(member_phone: str, amount: float, payment_method: str = "cash") -> dict:
    """Add money to member's savings account."""
    try:
        async with get_session() as db:
            # Find member
            stmt = select(OnboardingRecord).where(OnboardingRecord.phone == member_phone)
            result = await db.execute(stmt)
            member = result.scalar_one_or_none()
            
            if not member:
                return {"success": False, "error": "Member not found."}
            
            # Get or create savings record
            stmt = select(Savings).where(Savings.member_id == member.id)
            result = await db.execute(stmt)
            savings = result.scalar_one_or_none()
            
            if not savings:
                # Create new savings record
                savings = Savings(
                    member_id=member.id,
                    current_balance=Decimal(str(amount)),
                    total_deposits=Decimal(str(amount)),
                    interest_rate=8.00,
                    is_active=True
                )
                db.add(savings)
            else:
                # Update existing savings
                savings.current_balance = savings.current_balance + Decimal(str(amount))
                savings.total_deposits = savings.total_deposits + Decimal(str(amount))
            
            await db.commit()
            await db.refresh(savings)
            
            return {
                "success": True,
                "member_name": f"{member.first_name} {member.last_name}",
                "amount_added": float(amount),
                "new_balance": float(savings.current_balance),
                "payment_method": payment_method,
                "message": f"Successfully added KES {amount:,.2f} to savings!"
            }
            
    except Exception as e:
        logger.error(f"Error adding savings: {e}")
        return {"success": False, "error": str(e)}

async def request_savings_withdrawal(member_phone: str, amount: float, withdrawal_reason: str, withdrawal_method: str) -> dict:
    """Request a withdrawal from member's savings account."""
    try:
        async with get_session() as db:
            # Find member
            stmt = select(OnboardingRecord).where(OnboardingRecord.phone == member_phone)
            result = await db.execute(stmt)
            member = result.scalar_one_or_none()
            
            if not member:
                return {"success": False, "error": "Member not found."}
            
            # Get savings record
            stmt = select(Savings).where(Savings.member_id == member.id)
            result = await db.execute(stmt)
            savings = result.scalar_one_or_none()
            
            if not savings:
                return {"success": False, "error": "No savings account found."}
            
            if not savings.is_active:
                return {"success": False, "error": "Savings account is not active."}
            
            # Check if withdrawal amount is available
            if amount > savings.current_balance:
                return {"success": False, "error": "Insufficient balance for withdrawal."}
            
            # Generate withdrawal reference
            withdrawal_reference = f"WD{datetime.now().strftime('%Y%m%d%H%M%S')}{random.randint(1000, 9999)}"
            
            # Create withdrawal request
            withdrawal = SavingsWithdrawal(
                withdrawal_reference=withdrawal_reference,
                savings_id=savings.id,
                requested_amount=amount,
                withdrawal_reason=withdrawal_reason,
                withdrawal_method=withdrawal_method,
                status="pending"
            )
            
            db.add(withdrawal)
            await db.commit()
            
            return {
                "success": True,
                "member_name": f"{member.first_name} {member.last_name}",
                "withdrawal_reference": withdrawal_reference,
                "requested_amount": float(amount),
                "current_balance": float(savings.current_balance),
                "withdrawal_method": withdrawal_method,
                "status": "pending",
                "message": f"Withdrawal request submitted successfully! Reference: {withdrawal_reference}"
            }
            
    except Exception as e:
        logger.error(f"Error requesting savings withdrawal: {e}")
        return {"success": False, "error": str(e)}

async def get_withdrawal_status(withdrawal_reference: str) -> dict:
    """Get the status of a withdrawal request."""
    try:
        async with get_session() as db:
            # Find withdrawal
            stmt = select(SavingsWithdrawal).where(SavingsWithdrawal.withdrawal_reference == withdrawal_reference)
            result = await db.execute(stmt)
            withdrawal = result.scalar_one_or_none()
            
            if not withdrawal:
                return {"success": False, "error": "Withdrawal request not found."}
            
            # Get member details
            stmt = select(OnboardingRecord).join(Savings).where(Savings.id == withdrawal.savings_id)
            result = await db.execute(stmt)
            member = result.scalar_one_or_none()
            
            return {
                "success": True,
                "withdrawal_reference": withdrawal.withdrawal_reference,
                "member_name": f"{member.first_name} {member.last_name}" if member else "Unknown",
                "requested_amount": float(withdrawal.requested_amount),
                "withdrawal_reason": withdrawal.withdrawal_reason,
                "withdrawal_method": withdrawal.withdrawal_method,
                "status": withdrawal.status,
                "request_date": withdrawal.created_at.isoformat(),
                "approval_date": withdrawal.approval_date.isoformat() if withdrawal.approval_date else None,
                "approved_by": withdrawal.approved_by,
                "rejection_reason": withdrawal.rejection_reason,
                "processing_notes": withdrawal.processing_notes
            }
            
    except Exception as e:
        logger.error(f"Error getting withdrawal status: {e}")
        return {"success": False, "error": str(e)}

async def get_savings_balance(member_phone: str) -> dict:
    """Get savings balance for a member by phone number."""
    try:
        async with get_session() as db:
            # Find member
            stmt = select(OnboardingRecord).where(OnboardingRecord.phone == member_phone)
            result = await db.execute(stmt)
            member = result.scalar_one_or_none()
            
            if not member:
                return {"success": False, "error": "Member not found."}
            
            # Get savings record
            stmt = select(Savings).where(Savings.member_id == member.id)
            result = await db.execute(stmt)
            savings = result.scalar_one_or_none()
            
            if not savings:
                return {
                    "success": True,
                    "member_name": f"{member.first_name} {member.last_name}",
                    "current_balance": 0.00,
                    "total_deposits": 0.00,
                    "total_withdrawals": 0.00,
                    "interest_rate": 8.00,
                    "message": "No savings account found. Start saving today!"
                }
            
            return {
                "success": True,
                "member_name": f"{member.first_name} {member.last_name}",
                "current_balance": float(savings.current_balance),
                "total_deposits": float(savings.total_deposits),
                "total_withdrawals": float(savings.total_withdrawals),
                "interest_rate": float(savings.interest_rate),
                "is_active": savings.is_active
            }
            
    except Exception as e:
        logger.error(f"Error getting savings balance: {e}")
        return {"success": False, "error": str(e)}


async def confirm_payment(payment_reference: str) -> dict:
    """Confirm a payment by reference."""
    try:
        async with get_session() as db:
            # Find payment
            stmt = select(Payment).where(Payment.reference_code == payment_reference)
            result = await db.execute(stmt)
            payment = result.scalar_one_or_none()
            
            if not payment:
                return {"success": False, "error": "Payment not found."}
            
            # Update payment status
            payment.status = "confirmed"
            await db.commit()
            
            return {"success": True, "message": "Payment confirmed successfully."}  
        
    except Exception as e:
        logger.error(f"Error confirming payment: {e}")
        return {"success": False, "error": str(e)}