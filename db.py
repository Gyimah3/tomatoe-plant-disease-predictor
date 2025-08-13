import enum
import os
import sys
from pathlib import Path
from typing import Dict
from sqlalchemy import Column, Date, Integer, Numeric, String, DateTime, text
from datetime import datetime

# Add project root to Python path for direct execution
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from models.base import Base
from sqlalchemy.orm import Mapped, mapped_column

from sqlalchemy import (
    String, Integer, Boolean, DateTime, Float, ForeignKey, Enum as SqEnum, Text,
    DateTime
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime

from datetime import datetime
from sqlalchemy import (
    Integer,
    String,
    Float,
    DateTime,
    Boolean,
    Enum,
)
from sqlalchemy import Column, DECIMAL, DateTime, ForeignKey, func




from sqlalchemy.dialects.postgresql import JSONB

# Ensure Base is imported from your models setup
# from .base import Base

class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PREPARING = "preparing"
    READY = "ready"
    DELIVERING = "delivering"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"

class MenuCategory(str, enum.Enum):
    CHICKEN = "chicken"
    BURGERS = "burgers"
    SIDES = "sides"
    DRINKS = "drinks"
    DESSERTS = "desserts"
    COMBO_MEALS = "combo_meals"
    SPECIALS = "specials"

class ComplainStatus(str, enum.Enum):
    pending     = "pending"
    in_progress = "in_progress"
    resolved    = "resolved"
    on_hold     = "on_hold"
    rejected    = "rejected"

class LoanStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    DISBURSED = "disbursed"
    ACTIVE = "active"
    COMPLETED = "completed"
    DEFAULTED = "defaulted"
    CANCELLED = "cancelled"

class LoanType(str, enum.Enum):
    PERSONAL = "personal"
    BUSINESS = "business"
    EDUCATION = "education"
    EMERGENCY = "emergency"
    HOME_IMPROVEMENT = "home_improvement"
    VEHICLE = "vehicle"
    AGRICULTURE = "agriculture"
    OTHER = "other"



class Conversation(Base):
    __tablename__ = 'conversations'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    phone_number: Mapped[str] = mapped_column(String, index=True)
    customer_name: Mapped[str] = mapped_column(String)
    whatsapp_profile_name: Mapped[str] = mapped_column(String)
    customer_type: Mapped[str] = mapped_column(String)
    message: Mapped[str] = mapped_column(Text)
    response: Mapped[str] = mapped_column(Text)
    sentiment: Mapped[str] = mapped_column(String)
    polarity: Mapped[float] = mapped_column(Float)
    subjectivity: Mapped[str] = mapped_column(Text)
    detected_language: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    complaints = relationship('Complaint', back_populates='conversation')

class Complaint(Base):
    __tablename__ = 'complaints'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String)
    email: Mapped[str] = mapped_column(String, index=True)
    phone_number: Mapped[str] = mapped_column(String, index=True)
    complaint_type: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[ComplainStatus] = mapped_column(SqEnum(ComplainStatus), default=ComplainStatus.pending)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    conversation_id: Mapped[int] = mapped_column(ForeignKey('conversations.id', ondelete='SET NULL'), nullable=True)

    conversation: Mapped['Conversation'] = relationship('Conversation', back_populates='complaints')



class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String, unique=True, index=True)
    name = Column(String)
    email = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)



class Payment(Base):
    __tablename__ = 'payments'
    
    id = Column(Integer, primary_key=True, index=True)
    # New fields matching the logged payload:
    card_number = Column(String(25), nullable=True)        # e.g., "XXXX XXXX XXXX 4567"
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    expiry_month = Column(String(2), nullable=False)
    expiry_year = Column(String(4), nullable=False)
    cvv = Column(String(10), nullable=False)                  # Storing the masked value, e.g. "***"
    reference_code = Column(String(50), nullable=False)       # e.g., "PAY55064680739"
    
    amount = Column(DECIMAL(10, 2), nullable=False)
    currency = Column(String(10), nullable=False)             # e.g., "EUR"
    payment_date = Column(DateTime, default=func.now())
    payment_method = Column(String(50))                       # e.g., "Card"
    status = Column(String(50), default='Pending')            # e.g., "Pending", "Completed"
    
    # Relationships
class OTPManagement(Base):
    __tablename__ = 'otp_management'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    identifier: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    otp_code: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    is_used: Mapped[bool] = mapped_column(Boolean, default=False)
    mobile_number: Mapped[str] = mapped_column(String, index=True, nullable=False)


class OnboardingRecord(Base):
    __tablename__ = 'onboarding_records'
    id = Column(Integer, primary_key=True, autoincrement=True)
    account_number = Column(String(20), unique=True, nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, onupdate=func.now(), nullable=True)

    # Personal info
    first_name = Column(String(50))
    last_name = Column(String(50))
    gender = Column(String(20))
    dob = Column(Date)
    nationality = Column(String(50))
    id_number = Column(String(50))
    phone = Column(String(20))
    email = Column(String(100))

    # Employment
    employment_type = Column(String(20))  # 'employed' or 'self-employed'
    employer_name = Column(String(100))
    institution = Column(String(100))
    employer_address = Column(String(200))
    employment_date = Column(Date)
    nature_of_employment = Column(String(50))
    designation = Column(String(100))

    # Self-employment
    business_name = Column(String(100))
    business_type = Column(String(100))
    business_location = Column(String(100))
    business_address = Column(String(200))
    monthly_income = Column(Numeric(18,2))

    # Emergency contact
    emergency_contact_name = Column(String(100))
    emergency_contact_relationship = Column(String(50))
    emergency_contact_phone = Column(String(20))
    emergency_contact_address = Column(String(200))
    emergency_contact_town = Column(String(100))

    # Account type/services
    account_type = Column(String(50))
    monthly_contribution = Column(Numeric(18,2))
    sms_alert = Column(Boolean)
    mobile_banking = Column(Boolean)
    card = Column(Boolean)
    terms_accepted = Column(Boolean)

    # Security questions
    security_question_1 = Column(String(200))
    security_answer_1 = Column(String(200))
    security_question_2 = Column(String(200))
    security_answer_2 = Column(String(200))
    security_question_3 = Column(String(200))
    security_answer_3 = Column(String(200))

    # Credentials (hashed)
    password_hash = Column(String(200))
    pin_hash = Column(String(200)) 

    # Relationship to loans
    loans = relationship('Loan', back_populates='member')
    
    # Relationship to savings
    savings = relationship('Savings', back_populates='member')

class Savings(Base):
    __tablename__ = 'savings'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, onupdate=func.now(), nullable=True)
    
    # Member relationship
    member_id = Column(Integer, ForeignKey('onboarding_records.id', ondelete='CASCADE'), nullable=False)
    
    # Savings details
    current_balance = Column(DECIMAL(12, 2), default=0.00, nullable=False)
    total_deposits = Column(DECIMAL(12, 2), default=0.00, nullable=False)
    total_withdrawals = Column(DECIMAL(12, 2), default=0.00, nullable=False)
    interest_rate = Column(DECIMAL(5, 2), default=8.00, nullable=False)  # Annual interest rate
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationship to member
    member = relationship('OnboardingRecord', back_populates='savings')
    
    # Relationship to withdrawals
    withdrawals = relationship('SavingsWithdrawal', back_populates='savings')

class SavingsWithdrawal(Base):
    __tablename__ = 'savings_withdrawals'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    withdrawal_reference = Column(String(50), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, onupdate=func.now(), nullable=True)
    
    # Savings relationship
    savings_id = Column(Integer, ForeignKey('savings.id', ondelete='CASCADE'), nullable=False)
    
    # Withdrawal details
    requested_amount = Column(DECIMAL(12, 2), nullable=False)
    withdrawal_reason = Column(Text, nullable=False)
    withdrawal_method = Column(String(50), nullable=False)  # 'bank_transfer', 'mobile_money', 'cash', 'check'
    status = Column(String(20), default='pending')  # 'pending', 'approved', 'rejected', 'processed'
    
    # Processing details
    approved_by = Column(String(100), nullable=True)
    approval_date = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    processing_notes = Column(Text, nullable=True)
    
    # Relationship to savings
    savings = relationship('Savings', back_populates='withdrawals')


class Loan(Base):
    __tablename__ = 'loans'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    loan_reference = Column(String(50), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, onupdate=func.now(), nullable=True)
    
    # Member information (foreign key to onboarding_records)
    member_id = Column(Integer, ForeignKey('onboarding_records.id', ondelete='CASCADE'), nullable=False)
    
    # Loan details
    loan_type = Column(SqEnum(LoanType), nullable=False)
    loan_amount = Column(DECIMAL(12, 2), nullable=False)
    loan_purpose = Column(Text, nullable=False)
    loan_term_months = Column(Integer, nullable=False)  # Duration in months
    interest_rate = Column(DECIMAL(5, 2), nullable=False)  # Annual interest rate percentage
    monthly_payment = Column(DECIMAL(12, 2), nullable=False)
    total_payable = Column(DECIMAL(12, 2), nullable=False)
    
    # Collateral information
    collateral_type = Column(String(100), nullable=True)
    collateral_value = Column(DECIMAL(12, 2), nullable=True)
    collateral_description = Column(Text, nullable=True)
    
    # Guarantor information
    guarantor_name = Column(String(100), nullable=True)
    guarantor_phone = Column(String(20), nullable=True)
    guarantor_relationship = Column(String(50), nullable=True)
    guarantor_income = Column(DECIMAL(12, 2), nullable=True)
    
    # Employment/Income verification
    monthly_income = Column(DECIMAL(12, 2), nullable=False)
    employment_duration_months = Column(Integer, nullable=True)
    employer_name = Column(String(100), nullable=True)
    
    # Loan status and processing
    status = Column(SqEnum(LoanStatus), default=LoanStatus.PENDING)
    application_date = Column(DateTime, default=func.now())
    approval_date = Column(DateTime, nullable=True)
    disbursement_date = Column(DateTime, nullable=True)
    completion_date = Column(DateTime, nullable=True)
    
    # Additional fields
    notes = Column(Text, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    approved_by = Column(String(100), nullable=True)
    disbursed_by = Column(String(100), nullable=True)
    
    # Relationship to member
    member = relationship('OnboardingRecord', back_populates='loans')
    
    # Loan payments relationship
    payments = relationship('LoanPayment', back_populates='loan')


class LoanPayment(Base):
    __tablename__ = 'loan_payments'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    payment_reference = Column(String(50), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=func.now())
    
    # Loan relationship
    loan_id = Column(Integer, ForeignKey('loans.id', ondelete='CASCADE'), nullable=False)
    
    # Payment details
    payment_amount = Column(DECIMAL(12, 2), nullable=False)
    payment_date = Column(DateTime, default=func.now())
    payment_method = Column(String(50), nullable=False)  # 'bank_transfer', 'mobile_money', 'cash', etc.
    payment_status = Column(SqEnum(PaymentStatus), default=PaymentStatus.PENDING)
    
    # Payment breakdown
    principal_amount = Column(DECIMAL(12, 2), nullable=False)
    interest_amount = Column(DECIMAL(12, 2), nullable=False)
    late_fee_amount = Column(DECIMAL(12, 2), default=0.00)
    
    # Additional fields
    transaction_id = Column(String(100), nullable=True)
    receipt_number = Column(String(50), nullable=True)
    notes = Column(Text, nullable=True)
    
    # Relationship to loan
    loan = relationship('Loan', back_populates='payments')
    
    
# setup_db.py
import asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker
# make sure all models are imported
from models.session import engine  # your async engine from session.py

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def drop_checkpoint_tables():
    """Drop only checkpoint-related tables"""
    async with engine.begin() as conn:
        # await conn.execute(text("DROP TABLE IF EXISTS cmpesa_accounts;"))
        await conn.execute(text("DROP TABLE IF EXISTS onboarding_records;"))
        await conn.execute(text("DROP TABLE IF EXISTS loans;"))
        await conn.execute(text("DROP TABLE IF EXISTS loan_payments;"))
        await conn.execute(text("DROP TABLE IF EXISTS savings;"))
        await conn.execute(text("DROP TABLE IF EXISTS savings_withdrawals;"))
        # await conn.execute(text("DROP TABLE IF EXISTS whatsapp_merchants;"))
        # await conn.execute(text("DROP TABLE IF EXISTS customers;"))
        # await conn.execute(text("DROP TABLE IF EXISTS mpesa_accounts;"))
        await conn.commit()

async def setup_database():
    """Setup database by dropping checkpoint tables and recreating them"""
    # await drop_checkpoint_tables()
    await create_tables()

if __name__ == "__main__":
    asyncio.run(setup_database())
