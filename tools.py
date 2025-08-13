import random
import string
from models.session import get_session
from langchain_core.tools import BaseTool
from loguru import logger

import asyncio
from datetime import datetime, date, timedelta
from typing import List, Type, Optional

from pydantic import BaseModel, EmailStr, validator, Field
from sqlalchemy import select
from decimal import Decimal
import json
from itsdangerous import URLSafeTimedSerializer
import os

serializer = URLSafeTimedSerializer(os.environ["SECRET_KEY"])
from assistant.tools.tool_functions import (
    confirm_payment,
    create_complaint,
    generate_otp,
    get_complaints_by_email,
    update_complaint,
    send_whatsapp_audio_message,
    request_user_location,
    generate_security_verification_link,
    verify_otp,
    verify_security_answer,
    get_user_security_question,
    activate_user_account,
    get_user_details_by_name,
    get_user_account_number,
    create_account_confirmation,
    get_alternative_security_questions,
    verify_security_answer_flexible,
    send_email_verification_code,
    verify_email_code,
    generate_security_password_pin_link,
    save_onboarding_record, OnboardingRecordInput,
    create_loan_request,
    get_loan_status,
    get_loan_types,
    get_loan_repayment_progress,
    get_borrowing_capacity,
    get_savings_balance, add_savings, request_savings_withdrawal, get_withdrawal_status
)
from utils.utils import send_escalation_email, create_instant_batch_call


class CreateCustomerInput(BaseModel):
    mobile_number: str = Field(..., description=" user current mobile number to be used to track conversations ")
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: EmailStr
    date_of_birth: Optional[date] = None

    @validator("mobile_number")
    def validate_mobile(cls, v):
        if len(v) < 10:
            raise ValueError("mobile_number must be digits and at least 10 characters")
        return v


class SendWhatsappAudioMessageInput(BaseModel):
    phone_number: str = Field(..., description="Recipient's phone number - whatsapp supported number")
    text_response: str = Field(..., description="Text response to send")



   

class EscalationInput(BaseModel):
    escalating_to: EmailStr = Field(..., description="The email of customer service person or team to escalate the issue to ")
    customer_email: Optional[str] = Field(
        None, description="Customer's email address for follow-up or investigation (optional)"
    )
    customer_name: Optional[str] = Field(None, description="Customer's full name, if gotten from the conversation")
    mobile_number: Optional[str] = Field(None, description="Customer's mobile number with country code if available")
    conversation_summary: str = Field(
        ...,
        description="Brief summary of the conversation or issue being escalated"
    )
    customer_mood: Optional[str] = Field(
        None,
        description="Customer's mood or sentiment during the conversation (e.g., 'frustrated', 'satisfied')"
    )

class ComplaintInput(BaseModel):
    name: str = Field(..., description="Customer's full name")
    email: EmailStr = Field(..., description="Customer's email address")
    complaint_type: str = Field(..., description="Type of complaint (e.g., 'service', 'product')")
    description: str = Field(..., description="Detailed description of the complaint")
    Mobile_Number: str = Field(..., description="Customer's mobile number with country code")

class UpdateComplaintInput(BaseModel):
    email: EmailStr = Field(..., description="Email address of the user used to create the complaint")
    update_data: dict = Field(..., description="Dictionary containing fields to update")

class GetComplaintInput(BaseModel):
    email: EmailStr = Field(..., description="Email address of the user used to get the complaint")



class GenerateOTPInput1(BaseModel):
    mobile_number: str = Field(..., description="Customer's account  mobile number with country code linked to the account (e.g., +233559158793)")

class VerifyOTPInput(BaseModel):
    identifier: str = Field(..., description="OTP identifier received from generate_otp")
    otp_code: str = Field(..., description="6-digit OTP code received via SMS")

# class GenerateOTP_CallInput(BaseModel):
#     mobile_number: str = Field(..., description="Customer's mobile number with country code (e.g., +233559158793)")

class GenerateOTPInput(BaseModel):
    call_reason: str = Field(..., description="The reason for the call, e.g. 'Someone's bag is missing and requesting for FIND MY BAG service'")
    item_and_user_details: str = Field(..., description="item description and details and user details to issue this call")
    user_number: str = Field(..., description="The number of the user making the complaint, e.g. '233558158591'")

class GetSavingsBalanceInput(BaseModel):
    member_phone: str = Field(..., description="The phone number of the member to get the savings balance for")

class AddSavingsInput(BaseModel):
    member_phone: str = Field(..., description="The phone number of the member to add the savings for")
    amount: float = Field(..., description="The amount to add to the savings")
    payment_method: str = Field(..., description="The method of payment to use for the savings")

class RequestSavingsWithdrawalInput(BaseModel):
    member_phone: str = Field(..., description="The phone number of the member to request the savings withdrawal for")
    amount: float = Field(..., description="The amount to withdraw from the savings")
    withdrawal_reason: str = Field(..., description="The reason for the withdrawal")
    withdrawal_method: str = Field(..., description="The method of withdrawal to use for the savings")

class GetWithdrawalStatusInput(BaseModel):
    withdrawal_reference: str = Field(..., description="The reference number of the withdrawal to get the status for")


class SendWhatsappAudioMessage(BaseTool):
    name: str = "send_whatsapp_audio_message"
    description: str = "respond to a user with a WhatsApp audio message."
    args_schema: Type[BaseModel] = SendWhatsappAudioMessageInput
    category: str = "banking"

    def _run(self, phone_number: str, text_response: str, **kwargs):
        return asyncio.get_event_loop().run_until_complete(
            self._arun(phone_number, text_response, **kwargs)
        )

    async def _arun(self, phone_number: str, text_response: str, **kwargs):
        return await send_whatsapp_audio_message(phone_number, text_response)



class EscalationTool(BaseTool):
    name: str = "escalate_issue"
    description: str = "Escalate an issue to a human agent for further assistance and immidiate action."
    args_schema: Type[BaseModel] = EscalationInput

    def _run(
        self,
        escalating_to: str,
        customer_email: Optional[str] = None,
        customer_name: Optional[str] = None,
        mobile_number: Optional[str] = None,
        conversation_summary: str = "",
        customer_mood: Optional[str] = None,
        **kwargs,
    ):
        return asyncio.get_event_loop().run_until_complete(
            self._arun(
                escalating_to,
                customer_email,
                customer_name,
                mobile_number,
                conversation_summary,
                customer_mood,
                **kwargs,
            )
        )
    async def _arun(
        self,
        escalating_to: str,
        customer_email: Optional[str] = None,
        customer_name: Optional[str] = None,
        mobile_number: Optional[str] = None,
        conversation_summary: str = "",
        customer_mood: Optional[str] = None,
        **kwargs,
    ):
        """
        Escalate an issue to a human agent with all relevant details.
        Args:
            escalating_to (str): The customer support or team email to escalate the issue to.
            customer_email (Optional[str]): Customer's email address for follow-up.
            customer_name (Optional[str]): Customer's full name.
            mobile_number (Optional[str]): Customer's mobile number with country code.
            conversation_summary (str): Brief summary of the conversation or issue.
            customer_mood (Optional[str]): Customer's mood during the conversation.
        Returns:
            str: Confirmation message or error details.
        """
        return await send_escalation_email(
            escalating_to=escalating_to,
            customer_email=customer_email,
            customer_name=customer_name,
            mobile_number=mobile_number,
            conversation_summary=conversation_summary,
            customer_mood=customer_mood
        )

class CreateComplaintTool(BaseTool):
    name: str = "create_complaint"
    description: str = "Create a complaint for a customer issue."
    args_schema: Type[BaseModel] = ComplaintInput

    def _run(
        self,
        name: str,
        email: str,
        complaint_type: str,
        description: str,
        Mobile_Number: str,
    ):
        return asyncio.get_event_loop().run_until_complete(
            self._arun(
                name, email, complaint_type, description, Mobile_Number
            )
        )
    async def _arun(
        self,
        name: str,
        email: str,
        complaint_type: str,
        description: str,
        Mobile_Number: str,
    ):
        """
        Create a complaint for a customer issue.
        Args:
            name (str): Customer's full name.
            email (str): Customer's email address.
            complaint_type (str): Type of complaint (e.g., 'service', 'product').
            description (str): Detailed description of the complaint.
            Mobile_Number (str): Customer's mobile number with country code.
        Returns:
            str: Confirmation message or error details.
        """
        return await create_complaint(name, email, complaint_type, description, Mobile_Number)
    
class UpdateComplaintTool(BaseTool):
    name: str = "update_complaint"
    description: str = "Update an existing complaint with new information."
    args_schema: Type[BaseModel] =  UpdateComplaintInput

    def _run(
        self,
        email: str,
        update_data: dict,
    ):
        return asyncio.get_event_loop().run_until_complete(
            self._arun(email, update_data)
        )
    async def _arun(
        self,
        email: str,
        update_data: dict,
    ):
        """
        Update an existing complaint with new information.
        Args:
            email (str): Email address of the user who created the complaint.
            update_data (dict): Dictionary containing fields to update.
        Returns:
            str: Confirmation message or error details.
        """
        return await update_complaint(email, update_data)
class GetComplaintTool(BaseTool):
    name: str = "get_complaint"
    description: str = "Retrieve a complaint by email address."
    args_schema: Type[BaseModel] = GetComplaintInput  # No specific input schema needed for retrieval
    def _run(
        self,
        email: str,
    ):  
        return asyncio.get_event_loop().run_until_complete(
            self._arun(email)
        )
    async def _arun(
        self,
        email: str,
    ):
        """ Retrieve a complaint by email address. 
        Args:
            email (str): Email address of the user who created the complaint.
        Returns:
            str: Complaint details or error message.
        """
        return await get_complaints_by_email(email)
      # No specific input schema needed for escalation




class ReportIssue_Call(BaseTool):
    name: str = "service_issue_call"
    description: str = "Initiate a phone call for supervisor to quickly look for a bag or service request"
    args_schema: Type[BaseModel] = GenerateOTPInput

    def _run(
        self,
        call_reason: str,
        item_and_user_details: str,
        user_number: str,
        **kwargs,
    ):
        return asyncio.get_event_loop().run_until_complete(
            self._arun(call_reason,item_and_user_details,user_number, **kwargs)
        )
    async def _arun(
        self,
        call_reason: str,
        item_and_user_details: str,
        user_number: str,
        **kwargs,
    ):
        """
        Generate a 6-digit OTP code and initiate a phone call to the customer to deliver the OTP.
        Args:
            mobile_number (str): Customer's mobile number with country code.
        Returns:
            dict: Contains the OTP identifier and status of the call.
        """

        return await create_instant_batch_call(call_reason, item_and_user_details, user_number)
    

class RequestLocationInput(BaseModel):
    phone_number: str = Field(..., description="Customer's phone number to send location request to")
    body_text: Optional[str] = Field(None, description="Custom message text for the location request (optional)")

class GeneratePaymentLinkInput(BaseModel):
    customer_name: str = Field(..., description="Customer's full name for the payment link")

class RequestLocationTool(BaseTool):
    name: str = "request_user_location"
    description: str = """
    Request a user's location via WhatsApp location request message.
    This sends an interactive message with a 'Send Location' button that the user can tap to share their current location.
    Use this when you need the user's location for services like delivery, pickup, or location-based assistance.
    """
    args_schema: Type[BaseModel] = RequestLocationInput
    category: str = "location"

    def _run(self, phone_number: str, body_text: Optional[str] = None, **kwargs):
        return asyncio.get_event_loop().run_until_complete(
            self._arun(phone_number, body_text, **kwargs)
        )

    async def _arun(self, phone_number: str, body_text: Optional[str] = None, **kwargs):
        """
        Request user's location via WhatsApp location request message.
        Args:
            phone_number (str): Customer's phone number to send location request to
            body_text (Optional[str]): Custom message text for the location request
        Returns:
            Dict: Result of the location request operation
        """
        return await request_user_location(phone_number, body_text)

class GenerateSecurityLinkInput(BaseModel):
    customer_name: str = Field(..., description="Customer's full name for the security verification link")
    mobile_number: str = Field(..., description="Customer's mobile number with country code (e.g., 233558158591)")

    @validator("mobile_number")
    def validate_mobile(cls, v):
        if len(v) < 10:
            raise ValueError("Mobile number must be at least 10 characters")
        return v

class VerifySecurityAnswerInput(BaseModel):
    mobile_number: str = Field(..., description="Customer's mobile number with country code")
    security_answer: str = Field(..., description="Customer's answer to their security question")

    @validator("mobile_number")
    def validate_mobile(cls, v):
        if len(v) < 10:
            raise ValueError("Mobile number must be at least 10 characters")
        return v

class GetSecurityQuestionInput(BaseModel):
    mobile_number: str = Field(..., description="Customer's mobile number with country code")

    @validator("mobile_number")
    def validate_mobile(cls, v):
        if len(v) < 10:
            raise ValueError("Mobile number must be at least 10 characters")
        return v

class GetAlternativeSecurityQuestionInput(BaseModel):
    mobile_number: str = Field(..., description="Customer's mobile number with country code")
    exclude_question: str = Field(..., description="Question to exclude (1, 2, or 3)")

    @validator("mobile_number")
    def validate_mobile(cls, v):
        if len(v) < 10:
            raise ValueError("Mobile number must be at least 10 characters")
        return v
    
    @validator("exclude_question")
    def validate_exclude_question(cls, v):
        if v not in ["1", "2", "3"]:
            raise ValueError("exclude_question must be 1, 2, or 3")
        return v

class VerifySecurityAnswerFlexibleInput(BaseModel):
    mobile_number: str = Field(..., description="Customer's mobile number with country code")
    security_answer_1: str = Field(..., description="Customer's answer to first security question")
    security_answer_2: str = Field(..., description="Customer's answer to second security question")
    question_combination: str = Field(default="1,2", description="Which questions are being answered (e.g., '1,2', '1,3', '2,3')")

    @validator("mobile_number")
    def validate_mobile(cls, v):
        if len(v) < 10:
            raise ValueError("Mobile number must be at least 10 characters")
        return v
    
    @validator("question_combination")
    def validate_question_combination(cls, v):
        valid_combinations = ["1,2", "1,3", "2,3"]
        if v not in valid_combinations:
            raise ValueError("question_combination must be one of: 1,2, 1,3, 2,3")
        return v

class BankingTools:
    def __init__(self):
        pass

    def create_tools(self) -> List[BaseTool]:
        """Create and return a list of banking tools"""
        return [
            SendWhatsappAudioMessage(),
            ReportIssue_Call(),
            EscalationTool(),
            CreateComplaintTool(),
            UpdateComplaintTool(),
            GetComplaintTool(),
            GeneratePaymentLink(),
            ConfirmPaymentTool(),
            # ActivateAccountTool(),   # Disabled: direct account creation flow
            # GenerateSecurityLinkTool(),
            # VerifySecurityAnswerTool(),  # Disabled: direct account creation flow
            # GetSecurityQuestionTool(),   # Disabled: direct account creation flow
            # GetUserDetailsByNameTool(),  # Disabled: direct account creation flow
            # GetUserAccountNumberTool(),
            # CreateAccountConfirmationTool(),
            GenerateOTPTool(),
            VerifyOTPTool(),
            SendEmailVerificationTool(),
            VerifyEmailCodeTool(),
            GenerateSecurityPasswordPinLinkTool(),
            SaveOnboardingRecordTool(),
            # Loan tools
            CreateLoanRequestTool(),
            GetLoanStatusTool(),
            GetLoanTypesTool(),
            GetLoanRepaymentProgressTool(),
            GetBorrowingCapacityTool(),
            # Savings tools
            GetSavingsBalanceTool(),
            AddSavingsTool(),
            RequestSavingsWithdrawalTool(),
            GetWithdrawalStatusTool()
        ]


class GenerateOTPTool(BaseTool):
    name: str = "generate_otp"
    description: str = "Generate and send a 6-digit OTP code to the customer's account mobile number via SMS for verificatiion"
    args_schema: Type[BaseModel] = GenerateOTPInput1
    category: str = "banking"

    def _run(self, mobile_number: str, **kwargs):
        return asyncio.get_event_loop().run_until_complete(
            self._arun(mobile_number, **kwargs)
        )

    async def _arun(self, mobile_number: str, **kwargs):
        return await generate_otp(mobile_number)
    

class VerifyOTPTool(BaseTool):
    name: str = "verify_otp"
    description: str = "Verify the OTP code for account creation"
    args_schema: Type[BaseModel] = VerifyOTPInput
    category: str = "banking"

    def _run(self, identifier: str, otp_code: str, **kwargs):
        return asyncio.get_event_loop().run_until_complete(
            self._arun(identifier, otp_code, **kwargs)
        )

    async def _arun(self, identifier: str, otp_code: str, **kwargs):
        return await verify_otp(identifier, otp_code)

class ConfirmPaymentInput(BaseModel):
    payment_reference: str = Field(..., description="Payment reference code to confirm")

class ConfirmPaymentTool(BaseTool):
    name: str = "confirm_payment"
    description: str = "Confirm a payment by reference"
    args_schema: Type[BaseModel] = ConfirmPaymentInput
    category: str = "banking"

    def _run(self, payment_reference: str, **kwargs):
        return asyncio.get_event_loop().run_until_complete(
            self._arun(payment_reference, **kwargs)
        )

    async def _arun(self, payment_reference: str, **kwargs):
        return await confirm_payment(payment_reference)

class GenerateSecurityLinkTool(BaseTool):
    name: str = "generate_security_verification_link"
    description: str = """
    Send a structured security verification message with CTA URL button and image header.
    Use this when you need to verify a customer's identity through their security question.
    The message includes a professional image header and a button that links to the verification page.
    """
    args_schema: Type[BaseModel] = GenerateSecurityLinkInput
    category: str = "security"

    def _run(self, customer_name: str, mobile_number: str, **kwargs):
        return asyncio.get_event_loop().run_until_complete(
            self._arun(customer_name, mobile_number, **kwargs)
        )

    async def _arun(self, customer_name: str, mobile_number: str, **kwargs):
        """
        Generate a secure verification link for security question authentication.
        Args:
            customer_name (str): Customer's full name
            mobile_number (str): Customer's mobile number with country code
        Returns:
            Dict: Result of the security link generation operation
        """
        return await generate_security_verification_link(customer_name, mobile_number)

class VerifySecurityAnswerTool(BaseTool):
    name: str = "verify_security_answer"
    description: str = """
    Verify a customer's answer to their security question.
    Use this to authenticate a customer's identity by checking their security question answer.
    """
    args_schema: Type[BaseModel] = VerifySecurityAnswerInput
    category: str = "security"

    def _run(self, mobile_number: str, security_answer: str, **kwargs):
        return asyncio.get_event_loop().run_until_complete(
            self._arun(mobile_number, security_answer, **kwargs)
        )

    async def _arun(self, mobile_number: str, security_answer: str, **kwargs):
        """
        Verify a customer's answer to their security question.
        Args:
            mobile_number (str): Customer's mobile number with country code
            security_answer (str): Customer's answer to their security question
        Returns:
            Dict: Result of the security verification with user details if successful
        """
        return await verify_security_answer(mobile_number, security_answer)

class GetSecurityQuestionTool(BaseTool):
    name: str = "get_user_security_question"
    description: str = """
    Get a customer's security question for verification.
    Use this to retrieve the security question for a specific customer before asking them to answer it.
    """
    args_schema: Type[BaseModel] = GetSecurityQuestionInput
    category: str = "security"

    def _run(self, mobile_number: str, **kwargs):
        return asyncio.get_event_loop().run_until_complete(
            self._arun(mobile_number, **kwargs)
        )

    async def _arun(self, mobile_number: str, **kwargs):
        """
        Get a customer's security question for verification.
        Args:
            mobile_number (str): Customer's mobile number with country code
        Returns:
            Dict: Customer's security question and user information
        """
        return await get_user_security_question(mobile_number)

class GeneratePaymentLinkInput(BaseModel):
    customer_name: str = Field(..., description="Customer's full name for the payment link")
    mobile_number: str = Field(..., description="Customer's mobile number with country code (e.g., 233558158591)")
    
    @validator("mobile_number")
    def validate_mobile(cls, v):
        if len(v) < 10:
            raise ValueError("Mobile number must be at least 10 characters")
        return v

class ActivateAccountInput(BaseModel):
    payment_reference: str = Field(..., description="Payment reference code to verify for account activation")
    
    @validator("payment_reference")
    def validate_payment_reference(cls, v):
        if not v or len(v.strip()) < 5:
            raise ValueError("Payment reference code must be at least 5 characters")
        return v.strip()

class GeneratePaymentLink(BaseTool):
    name: str = "generate_payment_link"
    description: str = """
    Send a structured payment link message with CTA URL button and image header.
    Use this when a customer needs to make a payment for a booking or service.
    The message includes a professional image header and a button that links to the payment page.
    """
    args_schema: Type[BaseModel] = GeneratePaymentLinkInput
    return_direct: bool = False
    backend_url: str = os.getenv("BACKEND_URL")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
   

    def __hash__(self):
        return hash((self.name,))

    def __eq__(self, other):
        if not isinstance(other, GeneratePaymentLink):
            return False
        return self.name == other.name

    def _run(self, customer_name: str, mobile_number: str, **kwargs):
        """Synchronous wrapper for the async method"""
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self._arun(customer_name, mobile_number, **kwargs))
    
    async def _arun(self, customer_name: str, mobile_number: str, **kwargs):
        """Async method to generate and send payment link"""
        from assistant.tools.tool_functions import generate_payment_link
        return await generate_payment_link(customer_name, mobile_number)

class ActivateAccountTool(BaseTool):
    name: str = "activate_user_account"
    description: str = """
    Activate a user account by verifying their payment reference code.
    Use this when a user has completed payment and needs their account activated.
    The tool verifies the payment reference exists in the database and activates the account.
    """
    args_schema: Type[BaseModel] = ActivateAccountInput
    category: str = "account"

    def _run(self, payment_reference: str, **kwargs):
        """Synchronous wrapper for the async method"""
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self._arun(payment_reference, **kwargs))
    
    async def _arun(self, payment_reference: str, **kwargs):
        """Async method to activate user account"""
        from assistant.tools.tool_functions import activate_user_account
        return await activate_user_account(payment_reference)
    
class GetUserDetailsByNameInput(BaseModel):
    name: str = Field(..., description="User's full name to look up in the simulated database")

class GetUserDetailsByNameTool(BaseTool):
    name: str = "get_user_details_by_name"
    description: str = "Retrieve user details by name from the user database "
    args_schema: Type[BaseModel] = GetUserDetailsByNameInput
    category: str = "user"

    def _run(self, name: str, **kwargs):
        return asyncio.get_event_loop().run_until_complete(self._arun(name, **kwargs))

    async def _arun(self, name: str, **kwargs):
        return await get_user_details_by_name(name)

class GetUserAccountNumberInput(BaseModel):
    name: str = Field(..., description="User's full name to look up account number in the database")

class GetUserAccountNumberTool(BaseTool):
    name: str = "get_user_account_number"
    description: str = "Retrieve the account number for a user by name from the user database "
    args_schema: Type[BaseModel] = GetUserAccountNumberInput
    category: str = "user"

    def _run(self, name: str, **kwargs):
        return asyncio.get_event_loop().run_until_complete(self._arun(name, **kwargs))

    async def _arun(self, name: str, **kwargs):
        return await get_user_account_number(name)

class CreateAccountConfirmationInput(BaseModel):
    name: str = Field(..., description="User's full name to confirm account creation")

class CreateAccountConfirmationTool(BaseTool):
    name: str = "create_account_"
    description: str = "account creation after user details and location are verified. ."
    args_schema: Type[BaseModel] = CreateAccountConfirmationInput
    category: str = "account"

    def _run(self, name: str, **kwargs):
        return asyncio.get_event_loop().run_until_complete(self._arun(name, **kwargs))

    async def _arun(self, name: str, **kwargs):
        return await create_account_confirmation(name)

class GetAlternativeSecurityQuestionTool(BaseTool):
    name: str = "get_alternative_security_questions"
    description: str = "Retrieve alternative security questions for a customer"
    args_schema: Type[BaseModel] = GetAlternativeSecurityQuestionInput
    category: str = "security"

    def _run(self, mobile_number: str, exclude_question: str, **kwargs):
        return asyncio.get_event_loop().run_until_complete(self._arun(mobile_number, exclude_question, **kwargs))

    async def _arun(self, mobile_number: str, exclude_question: str, **kwargs):
        """
        Retrieve alternative security questions for a customer.
        Args:
            mobile_number (str): Customer's mobile number with country code
            exclude_question (str): Question to exclude (1, 2, or 3)
        Returns:
            List[str]: List of alternative security questions
        """
        return await get_alternative_security_questions(mobile_number, exclude_question)

class VerifySecurityAnswerFlexibleTool(BaseTool):
    name: str = "verify_security_answer_flexible"
    description: str = "Verify a customer's answer to their security question"
    args_schema: Type[BaseModel] = VerifySecurityAnswerFlexibleInput
    category: str = "security"

    def _run(self, mobile_number: str, security_answer_1: str, security_answer_2: str, question_combination: str, **kwargs):
        return asyncio.get_event_loop().run_until_complete(self._arun(mobile_number, security_answer_1, security_answer_2, question_combination, **kwargs))

    async def _arun(self, mobile_number: str, security_answer_1: str, security_answer_2: str, question_combination: str, **kwargs):
        """
        Verify a customer's answer to their security question.
        Args:
            mobile_number (str): Customer's mobile number with country code
            security_answer_1 (str): Customer's answer to first security question
            security_answer_2 (str): Customer's answer to second security question
            question_combination (str): Which questions are being answered (e.g., '1,2', '1,3', '2,3')
        Returns:
            Dict: Result of the security verification with user details if successful
        """
        return await verify_security_answer_flexible(mobile_number, security_answer_1, security_answer_2, question_combination)

class SendEmailVerificationInput(BaseModel):
    email: EmailStr = Field(..., description="User's email address to send verification code to")

class VerifyEmailCodeInput(BaseModel):
    email: EmailStr = Field(..., description="User's email address to verify")
    code: str = Field(..., description="Verification code sent to the user's email")

class SendEmailVerificationTool(BaseTool):
    name: str = "send_email_verification_code"
    description: str = "Send a verification code to the user's email address."
    args_schema: Type[BaseModel] = SendEmailVerificationInput
    category: str = "email"

    def _run(self, email: str, **kwargs):
        return asyncio.get_event_loop().run_until_complete(self._arun(email, **kwargs))

    async def _arun(self, email: str, **kwargs):
        return await send_email_verification_code(email)

class VerifyEmailCodeTool(BaseTool):
    name: str = "verify_email_code"
    description: str = "Verify the code sent to the user's email address."
    args_schema: Type[BaseModel] = VerifyEmailCodeInput
    category: str = "email"

    def _run(self, email: str, code: str, **kwargs):
        return asyncio.get_event_loop().run_until_complete(self._arun(email, code, **kwargs))

    async def _arun(self, email: str, code: str, **kwargs):
        return await verify_email_code(email, code)

class GenerateSecurityPasswordPinLinkInput(BaseModel):
    user_phone_number: str = Field(..., description="Optional user phone number for personalized link")

class GenerateSecurityPasswordPinLinkTool(BaseTool):
    name: str = "generate_security_password_pin_link"
    description: str = "Generate a secure link for the user to set their security questions, password, and PIN."
    args_schema: Type[BaseModel] = GenerateSecurityPasswordPinLinkInput
    category: str = "security"

    def _run(self, user_phone_number: Optional[str] = None, **kwargs):
        return asyncio.get_event_loop().run_until_complete(self._arun(user_phone_number, **kwargs))

    async def _arun(self, user_phone_number: Optional[str] = None, **kwargs):
        return await generate_security_password_pin_link(user_phone_number)

class SaveOnboardingRecordTool(BaseTool):
    name: str = "save_onboarding_record"
    description: str = "Save all onboarding details to the database and generate an account number."
    args_schema: Type[BaseModel] = OnboardingRecordInput
    category: str = "account"

    def _run(self, **kwargs):
        return asyncio.get_event_loop().run_until_complete(self._arun(**kwargs))

    async def _arun(self, **kwargs):
        data = OnboardingRecordInput(**kwargs)
        return await save_onboarding_record(data)


# Loan-related input models and tools

class CreateLoanRequestInput(BaseModel):
    member_phone: str = Field(..., description="Member's phone number")
    loan_type: str = Field(..., description="Type of loan (personal, business, education, emergency, home_improvement, vehicle, agriculture, other)")
    loan_amount: float = Field(..., description="Requested loan amount")
    loan_purpose: str = Field(..., description="Purpose of the loan")
    loan_term_months: int = Field(..., description="Loan term in months")
    monthly_income: float = Field(..., description="Member's monthly income")
    collateral_type: Optional[str] = Field(None, description="Type of collateral (optional)")
    collateral_value: Optional[float] = Field(None, description="Value of collateral (optional)")
    collateral_description: Optional[str] = Field(None, description="Description of collateral (optional)")
    guarantor_name: Optional[str] = Field(None, description="Name of guarantor (optional)")
    guarantor_phone: Optional[str] = Field(None, description="Phone number of guarantor (optional)")
    guarantor_relationship: Optional[str] = Field(None, description="Relationship to guarantor (optional)")
    guarantor_income: Optional[float] = Field(None, description="Guarantor's monthly income (optional)")
    employment_duration_months: Optional[int] = Field(None, description="Duration of employment in months (optional)")
    employer_name: Optional[str] = Field(None, description="Name of employer (optional)")

    @validator("loan_type")
    def validate_loan_type(cls, v):
        valid_types = ["personal", "business", "education", "emergency", "home_improvement", "vehicle", "agriculture", "other"]
        if v.lower() not in valid_types:
            raise ValueError(f"Loan type must be one of: {', '.join(valid_types)}")
        return v.lower()

    @validator("loan_amount")
    def validate_loan_amount(cls, v):
        if v <= 0:
            raise ValueError("Loan amount must be greater than 0")
        return v

    @validator("loan_term_months")
    def validate_loan_term(cls, v):
        if v <= 0 or v > 120:  # Max 10 years
            raise ValueError("Loan term must be between 1 and 120 months")
        return v

    @validator("monthly_income")
    def validate_monthly_income(cls, v):
        if v <= 0:
            raise ValueError("Monthly income must be greater than 0")
        return v


class GetLoanStatusInput(BaseModel):
    loan_reference: Optional[str] = Field(None, description="Loan reference number (optional if member_phone provided)")
    member_phone: Optional[str] = Field(None, description="Member's phone number (optional if loan_reference provided)")

    @validator("loan_reference", "member_phone", pre=True, always=True)
    def validate_at_least_one_provided(cls, v, values):
        if not values.get("loan_reference") and not values.get("member_phone"):
            raise ValueError("Either loan_reference or member_phone must be provided")
        return v


class CreateLoanRequestTool(BaseTool):
    name: str = "create_loan_request"
    description: str = """
    Create a new loan request for a member.
    Use this when a member wants to apply for a loan.
    The tool will validate the member's eligibility and create a loan application.
    """
    args_schema: Type[BaseModel] = CreateLoanRequestInput
    category: str = "loan"

    def _run(self, **kwargs):
        return asyncio.get_event_loop().run_until_complete(self._arun(**kwargs))

    async def _arun(self, **kwargs):
        data = CreateLoanRequestInput(**kwargs)
        return await create_loan_request(
            member_phone=data.member_phone,
            loan_type=data.loan_type,
            loan_amount=data.loan_amount,
            loan_purpose=data.loan_purpose,
            loan_term_months=data.loan_term_months,
            monthly_income=data.monthly_income,
            collateral_type=data.collateral_type,
            collateral_value=data.collateral_value,
            collateral_description=data.collateral_description,
            guarantor_name=data.guarantor_name,
            guarantor_phone=data.guarantor_phone,
            guarantor_relationship=data.guarantor_relationship,
            guarantor_income=data.guarantor_income,
            employment_duration_months=data.employment_duration_months,
            employer_name=data.employer_name
        )


class GetLoanStatusTool(BaseTool):
    name: str = "get_loan_status"
    description: str = """
    Get loan status by loan reference or member phone number.
    Use this to check the status of a loan application or get all loans for a member.
    """
    args_schema: Type[BaseModel] = GetLoanStatusInput
    category: str = "loan"

    def _run(self, **kwargs):
        return asyncio.get_event_loop().run_until_complete(self._arun(**kwargs))

    async def _arun(self, **kwargs):
        data = GetLoanStatusInput(**kwargs)
        return await get_loan_status(
            loan_reference=data.loan_reference,
            member_phone=data.member_phone
        )


class GetLoanTypesTool(BaseTool):
    name: str = "get_loan_types"
    description: str = """
    Get available loan types and their basic information.
    Use this to show members what types of loans are available and their requirements.
    """
    category: str = "loan"

    def _run(self, **kwargs):
        return asyncio.get_event_loop().run_until_complete(self._arun(**kwargs))

    async def _arun(self, **kwargs):
        return await get_loan_types()

class GetLoanRepaymentProgressInput(BaseModel):
    member_phone: str = Field(..., description="Member's phone number")
    loan_reference: Optional[str] = Field(None, description="Specific loan reference (optional)")

class GetBorrowingCapacityInput(BaseModel):
    member_phone: str = Field(..., description="Member's phone number")

class GetLoanRepaymentProgressTool(BaseTool):
    name: str = "get_loan_repayment_progress"
    description: str = """
    Get detailed loan repayment progress for a member.
    Shows total paid, remaining balance, completion percentage, payment history, and next payment due dates.
    Use this when a member wants to check their loan repayment status and progress.
    """
    args_schema: Type[BaseModel] = GetLoanRepaymentProgressInput
    category: str = "loan"

    def _run(self, member_phone: str, loan_reference: Optional[str] = None, **kwargs):
        return asyncio.get_event_loop().run_until_complete(
            self._arun(member_phone, loan_reference, **kwargs)
        )

    async def _arun(self, member_phone: str, loan_reference: Optional[str] = None, **kwargs):
        return await get_loan_repayment_progress(member_phone, loan_reference)

class GetBorrowingCapacityTool(BaseTool):
    name: str = "get_borrowing_capacity"
    description: str = """
    Calculate member's borrowing capacity based on income, existing loans, and SACCO policies.
    Shows debt-to-income ratio, maximum loan amount, and loan type recommendations.
    Use this when a member wants to know how much they can borrow.
    """
    args_schema: Type[BaseModel] = GetBorrowingCapacityInput
    category: str = "loan"

    def _run(self, member_phone: str, **kwargs):
        return asyncio.get_event_loop().run_until_complete(
            self._arun(member_phone, **kwargs)
        )

    async def _arun(self, member_phone: str, **kwargs):
        return await get_borrowing_capacity(member_phone)

# Savings System Tools
class GetSavingsBalanceTool(BaseTool):
    name: str = "get_savings_balance"
    description: str = "Get savings balance for a member by phone number. Shows current balance, total deposits, withdrawals, and interest rate."
    args_schema: Type[BaseModel] = GetSavingsBalanceInput
    category: str = "savings"

    def _run(self, **kwargs):
        return asyncio.get_event_loop().run_until_complete(self._arun(**kwargs))

    async def _arun(self, **kwargs):
        data = GetSavingsBalanceInput(**kwargs)
        return await get_savings_balance(data.member_phone)

class AddSavingsTool(BaseTool):
    name: str = "add_savings"
    description: str = "Add money to member's savings account. Creates savings record if it doesn't exist."
    args_schema: Type[BaseModel] = AddSavingsInput
    category: str = "savings"

    def _run(self, **kwargs):
        return asyncio.get_event_loop().run_until_complete(self._arun(**kwargs))

    async def _arun(self, **kwargs):
        data = AddSavingsInput(**kwargs)
        return await add_savings(data.member_phone, data.amount, data.payment_method)

class RequestSavingsWithdrawalTool(BaseTool):
    name: str = "request_savings_withdrawal"
    description: str = "Request a withdrawal from member's savings account. Supports various withdrawal methods: bank_transfer, mobile_money, cash, check"
    args_schema: Type[BaseModel] = RequestSavingsWithdrawalInput
    category: str = "savings"

    def _run(self, **kwargs):
        return asyncio.get_event_loop().run_until_complete(self._arun(**kwargs))

    async def _arun(self, **kwargs):
        data = RequestSavingsWithdrawalInput(**kwargs)
        return await request_savings_withdrawal(
            data.member_phone,
            data.amount,
            data.withdrawal_reason,
            data.withdrawal_method
        )

class GetWithdrawalStatusTool(BaseTool):
    name: str = "get_withdrawal_status"
    description: str = "Get the status of a withdrawal request by withdrawal reference."
    args_schema: Type[BaseModel] = GetWithdrawalStatusInput
    category: str = "savings"

    def _run(self, **kwargs):
        return asyncio.get_event_loop().run_until_complete(self._arun(**kwargs))

    async def _arun(self, **kwargs):
        data = GetWithdrawalStatusInput(**kwargs)
        return await get_withdrawal_status(data.withdrawal_reference)

# Savings System Pydantic Models

# Initialize tools after all classes are defined
tools = BankingTools().create_tools()

# Legacy tools (commented out)
# def addition(a:int, b:int):
#     """ add 2 numbers together"""
#     return a + b

# def get_customer_name():
#     """ get the customer name"""
#     return "John Doe"

# def get_customer_phone_number():
#     """ get the customer phone number"""
#     return "1234567890"

# tools = [addition, get_customer_name, get_customer_phone_number]
