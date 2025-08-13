"""
WhatsApp Webhook API - Main application file
"""
import decimal
from fastapi import FastAPI, Request, Response, HTTPException, Query, Form
from fastapi.responses import PlainTextResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import json
from fastapi import FastAPI,BackgroundTasks, Request, HTTPException, Depends
import asyncio
from datetime import datetime
from assistant.graph.create_graph import create_graph
from assistant.images.image_to_text import ImageToText
from config import settings
from loguru import logger
from models.db import Payment
from models.session import get_session
from utils.models import WebhookRequest, SecurityVerification, SecurityVerificationResponse, SecurityQuestionResponse
from services.whatsapp_service import whatsapp_service
from services.redis_service import redis_service
from assistant.tools.tool_functions import (
    generate_security_verification_link,
    verify_security_answer,
    get_user_security_question,
    get_alternative_security_questions,
    verify_security_answer_flexible,
)
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
import os

from openai import OpenAI
import io
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from utils.utils import download_image, ogg2mp3, process_background_tasks, send_whatsapp_message

app = FastAPI(title=settings.API_TITLE, version=settings.API_VERSION)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="services/templates"), name="static")

# Initialize templates
templates = Jinja2Templates(directory="services/templates")

# Initialize serializer
serializer = URLSafeTimedSerializer(os.environ["SECRET_KEY"])

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
client = OpenAI()
@app.get("/")
async def root():
    return {"message": "WhatsApp with FastAPI and Webhooks"}


def add_plus_sign(number):
    # Convert to string if it's a number
    number_str = str(number)
    
    # Check if the string already starts with a '+' sign
    if number_str.startswith('+'):
        return number_str
    else:
        # Add the '+' sign at the beginning
        return '+' + number_str
    
@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks,db: AsyncSession = Depends(get_session)):
    incoming_msg = ''
    try:
        content_type = request.headers.get('content-type', '')
        logger.info(f"Received content type: {content_type}")
        transaction_data = None
        form_data = None
        if 'application/json' in content_type:
            transaction_data = await request.json()
            logger.info(f"Received JSON data: {transaction_data}")
            if "customer_number1" in transaction_data:
                customer_number = transaction_data['customer_number']
                phone_number = transaction_data['phone_number']
                incoming_msg = f"created account successfully,this is the customer number{customer_number}"
                logger.info(f"Received message from {phone_number}: {incoming_msg}")
                
                # Get previous message time for security checks (BEFORE saving current time)
                previous_message_time = await redis_service.get_last_message_time(phone_number)
                
                # Track current message time
                last_message_time = datetime.now()
                await redis_service.save_last_message_time(phone_number, last_message_time)
                
                response = await create_graph(phone_number, incoming_msg, previous_message_time)
                logger.info(f"Generated response for {phone_number}: {response}")
                await send_whatsapp_message(phone_number, response)

                if transaction_data:
                    # Process your transaction logic here
                    return {"status": "success", "message": "Transaction processed"}
            else:
                incoming_msg = "I'm done verification... secret name is yah, continue"
                phone_number = add_plus_sign(transaction_data['mobile_number'])
                # phone_number1 ='+'+ transaction_data['mpesa_number']
                location = ''
                logger.info(f"Received message from {phone_number}: {incoming_msg}")
                
                # Get previous message time for security checks (BEFORE saving current time)
                previous_message_time = await redis_service.get_last_message_time(phone_number)
                
                # Track current message time
                last_message_time = datetime.now()
                await redis_service.save_last_message_time(phone_number, last_message_time)
                
                response = await create_graph(phone_number, incoming_msg, previous_message_time)
                
                logger.info(f"Generated response for {phone_number}: {response}")
                await send_whatsapp_message(phone_number, response)
                # await send_whatsapp_message(phone_number1, response)

                if transaction_data:

                    return {"status": "success", "message": "Transaction processed"}
                
        elif 'application/x-www-form-urlencoded' in content_type or 'multipart/form-data' in content_type:
            form_data = await request.form()
            logger.info(f"Received form data: {form_data}")
            
            phone_number = form_data.get('From', '').replace('whatsapp:', '')
            whatsapp_user = form_data.get("ProfileName")
            logger.info(f"Whatsapp user: {whatsapp_user}")
            
            # Check if the message contains media (voice note or image)
            if 'MediaUrl0' in form_data:
                media_url = form_data['MediaUrl0']
                media_type = form_data['MediaContentType0']
                logger.info(f"Media URL: {media_url}\nMedia Content type: {media_type}")
                
                # Handle audio messages
                if media_type.startswith('audio'):
                    logger.info(f"Received voice message from {phone_number}")
                    try:
                        mp3_data = await ogg2mp3(media_url)
                        file_obj = io.BytesIO(mp3_data)
                        file_obj.name = "audio.mp3"  # OpenAI needs filename
                        
                        transcription = client.audio.transcriptions.create(
                            model="whisper-1",
                            file=file_obj
                        )

                        print(transcription.text)
                        incoming_msg = transcription.text
                        logger.info(f"Transcribed voice message: {incoming_msg}")
                    except Exception as e:
                        logger.error(f"Voice processing error: {str(e)}")
                        await send_whatsapp_message(
                            phone_number, 
                            "I'm sorry, I couldn't process your voice message. Please try sending it again."
                        )
                        return ""
                
                # Handle image messages
                elif media_type.startswith('image'):
                    logger.info(f"Received image from {phone_number}")
                    try:
                        # Download the image
                        image_data = await download_image(media_url)
                        
                        # Initialize ImageToText analyzer
                        image_analyzer = ImageToText()
                        
                        # Analyze the image
                        image_description = await image_analyzer.analyze_image(image_data)
                        logger.info(f"Image description: {image_description}")
                        
                        incoming_msg = image_description
                        logger.info(f"Analyzed image: {incoming_msg}")
                    except Exception as e:
                        logger.error(f"Image processing error: {str(e)}")
                        await send_whatsapp_message(
                            phone_number, 
                            "I'm sorry, I couldn't process your image. Please try sending it again."
                        )
                        return ""
                
                # Handle other media types
                else:
                    logger.info(f"Received unsupported media type: {media_type}")
                    await send_whatsapp_message(
                        phone_number, 
                        "I can only process voice messages and images. Please send a text message, voice note, or image."
                    )
                    return ""
                
                location = ''

                if not phone_number or not incoming_msg:
                    return ""
                    
                logger.info(f"Processing message from {phone_number}: {incoming_msg}")
                
                # Get previous message time for security checks (BEFORE saving current time)
                previous_message_time = await redis_service.get_last_message_time(phone_number)
                
                # Track current message time for media messages
                last_message_time = datetime.now()
                await redis_service.save_last_message_time(phone_number, last_message_time)
                
                response = await create_graph(phone_number, incoming_msg, previous_message_time)
                logger.info(f"Generated response for {phone_number}: {response}")                    
                if not response:
                    await send_whatsapp_message(phone_number, "I apologize, could you rephrase that?")
                    return ""
                    
                logger.info(f"Generated response for {phone_number}: {response}")
                
                # Send response
                await send_whatsapp_message(phone_number, response)
                
                # Add background tasks
                background_tasks.add_task(
                    process_background_tasks,
                    phone_number,
                    incoming_msg,
                    response,
                    whatsapp_user,
                )

            else:
                # Handle text messages
                incoming_msg = form_data.get('Body', '').strip()
                location = ''
                if not phone_number or not incoming_msg:
                    return ""
                    
                logger.info(f"Processing message from {phone_number}: {incoming_msg}")
                
                # Get previous message time for security checks (BEFORE saving current time)
                previous_message_time = await redis_service.get_last_message_time(phone_number)
                
                # Track current message time
                last_message_time = datetime.now()
                await redis_service.save_last_message_time(phone_number, last_message_time)
                
                response = await create_graph(phone_number, incoming_msg, previous_message_time)
                logger.info(f"Generated response for {phone_number}: {response}")                       
                if not response:
                    await send_whatsapp_message(phone_number, "I apologize, could you rephrase that?")
                    return ""
                    
                logger.info(f"Generated response for {phone_number}: {response}")
                
                # Send response
                await send_whatsapp_message(phone_number, response)
                
                # Add background tasks
                background_tasks.add_task(
                    process_background_tasks,
                    phone_number,
                    incoming_msg,
                    response,
                    whatsapp_user,
                )

    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        return ""
# @app.get("/webhook")
# async def verify_webhook(
#     hub_mode: str = Query(..., alias="hub.mode"),
#     hub_challenge: str = Query(..., alias="hub.challenge"),
#     hub_verify_token: str = Query(..., alias="hub.verify_token")
# ):
#     """Verify webhook endpoint for WhatsApp"""
#     logger.info(f"Webhook verification attempt - Mode: {hub_mode}, Token: {hub_verify_token}")
    
#     if hub_mode and hub_verify_token == settings.WEBHOOK_VERIFY_TOKEN:
#         logger.success(f"Webhook verified successfully with challenge: {hub_challenge}")
#         return PlainTextResponse(content=hub_challenge)
#     else:
#         logger.error(f"Webhook verification failed - Invalid token or mode")
#         raise HTTPException(status_code=403, detail="Forbidden")


# @app.post("/webhook")
# async def webhook_handler(request: Request):
#     """Handle incoming webhook messages from WhatsApp"""
#     logger.info("Received webhook request")
    
#     # Parse the JSON payload
#     try:
#         raw_body = await request.body()
#         payload = json.loads(raw_body.decode())
#         webhook_request = WebhookRequest(**payload)
#     except Exception as e:
#         logger.error(f"Failed to parse webhook payload: {str(e)}")
#         raise HTTPException(status_code=400, detail="Invalid JSON payload")
    
#     if not webhook_request.entry or len(webhook_request.entry) == 0:
#         logger.error("Invalid webhook request - No entries")
#         raise HTTPException(status_code=400, detail="Invalid Request")

#     changes = webhook_request.entry[0].changes

#     if not changes or len(changes) == 0:
#         logger.error("Invalid webhook request - No changes")
#         raise HTTPException(status_code=400, detail="Invalid Request")

#     value = changes[0].value
#     statuses = value.statuses[0] if value.statuses else None
#     messages = value.messages[0] if value.messages else None

#     if statuses:
#         # Handle message status
#         logger.info(f"Message status update - ID: {statuses.id}, Status: {statuses.status}")

#     if messages:
#         logger.info(f"Received message - Type: {messages.type}, From: {messages.from_}")
        
#         # 1. React to the message
#         await whatsapp_service.send_reaction(messages.from_, messages.id, "👍")
#         # 2. Mark as read and send typing indicator
#         await whatsapp_service.mark_message_as_read(messages.id)
#         await whatsapp_service.send_typing_indicator(messages.id)
#         await asyncio.sleep(2)
        
#         # Handle received messages
#         if messages.type == 'text':
#             await message_handler.handle_text_message(messages, messages.from_)

#         elif messages.type == 'audio':
#             await message_handler.handle_audio_message(messages, messages.from_)

#         elif messages.type == 'image':
#             await message_handler.handle_image_message(messages, messages.from_)

#         elif messages.type == 'location':
#             try:
#                 await message_handler.handle_location_message(messages, messages.from_)
#             except Exception as e:
#                 logger.error(f"Error handling location message from {messages.from_}: {str(e)}")
#                 # Don't let location errors crash the application
#                 try:
#                     await whatsapp_service.send_message(
#                         messages.from_, 
#                         "Thank you for sharing your location. I've received it and will use it to better assist you."
#                     )
#                 except Exception as send_error:
#                     logger.error(f"Failed to send fallback message: {str(send_error)}")

#         elif messages.type == 'interactive':
#             await message_handler.handle_interactive_message(messages, messages.from_)

#     logger.success("Webhook processed successfully")
#     return {"status": "Webhook processed"}





@app.get("/verify-security", response_class=HTMLResponse)
async def verify_security_page(request: Request):
    """Serve the security question verification page"""
    return templates.TemplateResponse("verify_pin.html", {"request": request})

@app.get("/api/get-security-question")
async def get_security_question(request: Request):
    """Get user's security questions from token"""
    try:
        token = request.query_params.get("token")
        if not token:
            return JSONResponse(
                status_code=400, 
                content={"error": "Missing verification token"}
            )
        logger.info(f"Received security question request with token: {token}")
        # Decode token
        try:
            token_data = serializer.loads(token, max_age=1800)  # 30 minutes expiry
            logger.info(f"Decoded token data: {token_data}")
        except SignatureExpired:
            return JSONResponse(
                status_code=400,
                content={"error": "Verification link has expired. Please request a new link"}
            )
        except BadSignature:
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid verification link"}
            )
        # Extract mobile number from token
        mobile_number = token_data.get("mobile_number")
        if not mobile_number:
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid token data"}
            )
        # Get security questions
        result = await get_user_security_question(mobile_number)
        if result.get("error"):
            return JSONResponse(
                status_code=404,
                content={"error": result["error"]}
            )
        return SecurityQuestionResponse(
            success=True,
            user_name=result["user_name"],
            security_question_1=result["security_question_1"],
            security_question_2=result["security_question_2"],
            phone_number=result["phone_number"]
        )
    except Exception as e:
        logger.error(f"Error getting security questions: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": "Unable to process your request. Please try again."}
        )

@app.post("/api/verify-security")
async def verify_security(request: Request, security_data: SecurityVerification):
    """Verify user's security question answers"""
    try:
        token = request.query_params.get("token")
        if not token:
            return JSONResponse(
                status_code=400, 
                content={"error": "Missing verification token"}
            )
        logger.info(f"Received security verification request with token: {token}")
        # Decode token
        try:
            token_data = serializer.loads(token, max_age=1800)  # 30 minutes expiry
            logger.info(f"Decoded token data: {token_data}")
        except SignatureExpired:
            return JSONResponse(
                status_code=400,
                content={"error": "Verification link has expired. Please request a new link"}
            )
        except BadSignature:
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid verification link"}
            )
        # Extract mobile number from token
        mobile_number = token_data.get("mobile_number")
        if not mobile_number:
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid token data"}
            )
        # Verify security answers
        result = await verify_security_answer(
            mobile_number, 
            security_data.security_answer_1, 
            security_data.security_answer_2
        )
        if result.get("error"):
            return JSONResponse(
                status_code=400,
                content={"error": result["message"]}
            )
        # Simulate user sending message to agent (triggering the flow)
        try:
            incoming_msg = (
                f"Security verification successful for {result['user_details']['name']} "
                f"with answers: {security_data.security_answer_1}, {security_data.security_answer_2}"
            )
            phone_number = mobile_number if mobile_number.startswith("+") else f"+{mobile_number}"
            logger.info(f"Simulating user message to agent for {phone_number}: {incoming_msg}")
            ai_response = await create_graph(phone_number, incoming_msg)
            if ai_response:
                await send_whatsapp_message(phone_number, ai_response)
                logger.info(f"AI response sent to {phone_number}: {ai_response[:100]}...")
            else:
                logger.warning(f"No AI response generated for {phone_number}")
            logger.info(f"Security verification completed for {phone_number}. User can now interact with the agent.")
        except Exception as agent_error:
            logger.error(f"Failed to process verification completion: {str(agent_error)}")
        return SecurityVerificationResponse(
            success=True,
            message="Security verification successful! Please check your WhatsApp for further instructions."
        )
    except Exception as e:
        logger.error(f"Error in security verification: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": "Unable to process your request. Please try again."}
        )


@app.get("/payment", response_class=HTMLResponse)
async def payment_page(request: Request):
    return templates.TemplateResponse("payment_form2.html", {"request": request})

@app.post("/api/process-payment")
async def process_payment(request: Request):
    try:
        payment_data = await request.json()
    except Exception as e:
        logger.error(f"Error reading JSON: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    # Mask sensitive data (e.g., show only last 4 digits of card, hide CVV)
    masked_card = "XXXX XXXX XXXX " + payment_data["cardNumber"][-4:]
    safe_data = {**payment_data, "cardNumber": masked_card, "cvv": "***"}
    
    logger.info("Payment received:")
    logger.info(json.dumps(safe_data, indent=2))
    logger.info(f"Reference code: {payment_data['referenceCode']}")
    transaction_info ={"name": payment_data["firstName"] + " " + payment_data["lastName"], "amount": payment_data["amount"]}
    # Convert amount to Decimal (ensure the format is correct)
    try:
        amount = decimal.Decimal(payment_data["amount"])
    except Exception as e:
        logger.error(f"Error converting amount: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid amount format")

    # Create new Payment record.
    # Note: Set customer_id appropriately. Here we use 1 for demonstration.
    new_payment = Payment(
        card_number = safe_data["cardNumber"],
        first_name = payment_data["firstName"],
        last_name = payment_data["lastName"],
        expiry_month = payment_data["expiryMonth"],
        expiry_year = payment_data["expiryYear"],
        cvv = safe_data["cvv"],
        reference_code = payment_data["referenceCode"],
        amount = amount,
        currency = payment_data["currency"],
        payment_method = "Card",  # Adjust if needed.
        status = "Completed"      # Or "Pending", based on your business logic.
    )

    try:
        async with get_session() as db:
            db.add(new_payment)
            await db.commit()
            await db.refresh(new_payment)
            logger.info(f"Payment record saved with ID: {new_payment.id}")
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving payment: {str(e)}")
        raise HTTPException(status_code=500, detail="Error saving payment to database")
    finally:
        await db.close()
    # await send_webhook_transaction(transaction_info)
    return JSONResponse({"status": "success", "reference": payment_data["referenceCode"]})
# @app.post("/api/verify-pin")

@app.get("/api/get-alternative-security-questions")
async def get_alternative_security_questions_api(request: Request):
    """Get alternative security questions from token"""
    try:
        token = request.query_params.get("token")
        exclude_question = request.query_params.get("exclude")
        
        if not token:
            return JSONResponse(
                status_code=400, 
                content={"error": "Missing verification token"}
            )
        
        if not exclude_question or exclude_question not in ["1", "2", "3"]:
            return JSONResponse(
                status_code=400, 
                content={"error": "Invalid exclude question parameter. Must be 1, 2, or 3"}
            )
            
        logger.info(f"Received alternative security question request with token: {token}, exclude: {exclude_question}")
        
        # Decode token
        try:
            token_data = serializer.loads(token, max_age=1800)  # 30 minutes expiry
            logger.info(f"Decoded token data: {token_data}")
        except SignatureExpired:
            return JSONResponse(
                status_code=400,
                content={"error": "Verification link has expired. Please request a new link"}
            )
        except BadSignature:
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid verification link"}
            )
        
        # Extract mobile number from token
        mobile_number = token_data.get("mobile_number")
        if not mobile_number:
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid token data"}
            )
        
        # Get alternative security questions
        result = await get_alternative_security_questions(mobile_number, exclude_question)
        if result.get("error"):
            return JSONResponse(
                status_code=404,
                content={"error": result["message"]}
            )
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "user_name": result["user_name"],
                "security_question_1": result["security_question_1"],
                "security_question_2": result["security_question_2"],
                "phone_number": result["phone_number"]
            }
        )
    except Exception as e:
        logger.error(f"Error getting alternative security questions: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": "Unable to process your request. Please try again."}
        )

@app.post("/api/verify-security-flexible")
async def verify_security_flexible(request: Request):
    """Verify user's security question answers with flexible combination support"""
    try:
        token = request.query_params.get("token")
        if not token:
            return JSONResponse(
                status_code=400, 
                content={"error": "Missing verification token"}
            )
        
        # Parse request body
        try:
            body = await request.json()
            security_answer_1 = body.get("security_answer_1")
            security_answer_2 = body.get("security_answer_2")
            security_answer_3 = body.get("security_answer_3")
            question_combination = body.get("question_combination", "1,2")
        except Exception as e:
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid request body"}
            )
        
        if not security_answer_1 or not security_answer_2:
            return JSONResponse(
                status_code=400,
                content={"error": "Security answers are required"}
            )
        
        logger.info(f"Received flexible security verification request with token: {token}, combination: {question_combination}")
        
        # Decode token
        try:
            token_data = serializer.loads(token, max_age=1800)  # 30 minutes expiry
            logger.info(f"Decoded token data: {token_data}")
        except SignatureExpired:
            return JSONResponse(
                status_code=400,
                content={"error": "Verification link has expired. Please request a new link"}
            )
        except BadSignature:
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid verification link"}
            )
        
        # Extract mobile number from token
        mobile_number = token_data.get("mobile_number")
        if not mobile_number:
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid token data"}
            )
        
        # Verify security answers with flexible combination
        result = await verify_security_answer_flexible(
            mobile_number, 
            security_answer_1, 
            security_answer_2, 
            question_combination
        )
        
        if result.get("error"):
            return JSONResponse(
                status_code=400,
                content={"error": result["message"]}
            )
        
        # Simulate user sending message to agent (triggering the flow)
        try:
            incoming_msg = (
                f"Security verification successful for {result['user_details']['name']} "
                f"with combination: {question_combination}"
            )
            phone_number = mobile_number if mobile_number.startswith("+") else f"+{mobile_number}"
            logger.info(f"Simulating user message to agent for {phone_number}: {incoming_msg}")
            
            # Get previous message time for security checks (BEFORE saving current time)
            previous_message_time = await redis_service.get_last_message_time(phone_number)
            
            # Track current message time for security verification
            last_message_time = datetime.now()
            await redis_service.save_last_message_time(phone_number, last_message_time)
            
            ai_response = await create_graph(phone_number, incoming_msg, previous_message_time)
            if ai_response:
                await send_whatsapp_message(phone_number, ai_response)
                logger.info(f"AI response sent to {phone_number}: {ai_response[:100]}...")
            else:
                logger.warning(f"No AI response generated for {phone_number}")
            logger.info(f"Security verification completed for {phone_number}. User can now interact with the agent.")
        except Exception as agent_error:
            logger.error(f"Failed to process verification completion: {str(agent_error)}")
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Security verification successful! Please check your WhatsApp for further instructions."
            }
        )
    except Exception as e:
        logger.error(f"Error in flexible security verification: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": "Unable to process your request. Please try again."}
        )

@app.get("/set-security-password-pin", response_class=HTMLResponse)
async def set_security_password_pin_page(request: Request, token: str = None):
    """Serve the set security questions, password, and pin form"""
    return templates.TemplateResponse("set_security_password_pin.html", {"request": request, "token": token})

@app.post("/api/set-security-password-pin")
async def set_security_password_pin(request: Request):
    """Receive and process security questions, password, and pin from the form"""
    try:
        data = await request.json()
        # Log or process the data as needed
        logger.info(f"Received security/password/pin setup: {data}")
        # Here you would save to DB or trigger next onboarding step
        incoming_msg = f"Security questions, password, and pin setup: {data}"
        phone_number = "+233559158793"
        logger.info(f"Simulating user message to agent for {phone_number}: {incoming_msg}")
        
        # Get previous message time for security checks (BEFORE saving current time)
        previous_message_time = await redis_service.get_last_message_time(phone_number)
        
        # Track current message time for security setup
        last_message_time = datetime.now()
        await redis_service.save_last_message_time(phone_number, last_message_time)
        
        ai_response = await create_graph(phone_number, incoming_msg, previous_message_time)
        if ai_response:
            await send_whatsapp_message(phone_number, ai_response)
            logger.info(f"AI response sent to {phone_number}: {ai_response[:100]}...")
        return {"success": True, "message": "Details submitted successfully!"}
    except Exception as e:
        logger.error(f"Error processing security/password/pin setup: {str(e)}")
        return {"success": False, "error": "Failed to process details. Please try again."}

if __name__ == "__main__":
    import uvicorn
    
    # Configure loguru
    logger.remove()  # Remove default handler
    logger.add(
        "logs/whatsapp_webhook.log",
        rotation="10 MB",
        retention="7 days",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}"
    )
    logger.add(
        lambda msg: print(msg, end=""),
        level="INFO",
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    
    # Validate audio configuration
    from config import validate_audio_config
    validate_audio_config()
    
    logger.info("Starting WhatsApp Webhook Server...")
    uvicorn.run(app, host=settings.HOST, port=settings.PORT) 