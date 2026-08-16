"""
SurakshaAI — Manual Dataset Templates
=======================================
Creates the three manually curated datasets:
  1. Banking Notifications (safe + fraud)
  2. Loan Advertisements   (safe + fraud)
  3. WhatsApp Financial Chats (safe + fraud)

Seed examples are based on:
  - Real Indian bank communication templates (RBI, SBI, HDFC, ICICI, Axis)
  - Known fraud patterns from RBI and cybercrime portal advisories
  - NPCI UPI fraud awareness materials

Generation strategy:
  - Start with 50-100 seed examples per category
  - Expand using structured variation:
      * Swap bank names
      * Swap amounts
      * Swap account number fragments
      * Swap URLs (safe: real bank domains, fraud: fake domains)
  - All records flagged is_manual=True

Usage:
    from src.data.manual_templates import ManualDatasetGenerator
    gen = ManualDatasetGenerator()
    gen.generate_all(output_dir="data/raw/")
"""

from __future__ import annotations

import itertools
import logging
import random
from pathlib import Path
from typing import List, Tuple

import pandas as pd

from src.config import settings

logger = logging.getLogger(__name__)

random.seed(settings.RANDOM_SEED)


# ══════════════════════════════════════════════════════════════════════════════
# SEED DATA
# ══════════════════════════════════════════════════════════════════════════════

REAL_BANKS = [
    "SBI", "HDFC Bank", "ICICI Bank", "Axis Bank",
    "Bank of Baroda", "PNB", "Kotak Mahindra Bank", "Yes Bank",
    "Canara Bank", "Union Bank of India",
]

FAKE_BANK_NAMES = [
    "SBI Secure", "HDFC-Online", "ICICI NetBank",
    "Axis Secure Bank", "India National Bank",
    "National Savings Bank", "RBI Certified Bank",
]

AMOUNTS = [
    "Rs.500", "Rs.1,000", "Rs.2,500", "Rs.5,000",
    "Rs.10,000", "Rs.25,000", "Rs.50,000", "Rs.1,00,000",
]

ACCOUNT_FRAGMENTS = [
    "XX1234", "XX5678", "XX9012", "XX3456",
    "XXXX7890", "XXXX2345", "XXXX6789",
]

REAL_DOMAINS = [
    "onlinesbi.sbi", "netbanking.hdfcbank.com",
    "icicibank.com", "axisbank.com",
    "bankofbaroda.in", "pnbibanking.com",
]

FAKE_DOMAINS = [
    "sbi-secure.xyz", "hdfc-login.net", "icici-verify.co",
    "axis-bank-update.com", "india-bank-kyc.xyz",
    "rbi-refund.net", "neft-refund.co.in",
    "sbi.update-kyc.com", "upi-support.xyz",
]

DATES = [
    "01-Jan-2025", "15-Feb-2025", "03-Mar-2025",
    "22-Apr-2025", "10-May-2025",
]

OTP_NUMBERS = ["123456", "654321", "987654", "246810", "135790"]


# ══════════════════════════════════════════════════════════════════════════════
# 1. BANKING NOTIFICATIONS
# ══════════════════════════════════════════════════════════════════════════════

BANKING_SAFE_SEEDS = [
    "{bank}: {amount} debited from A/c {acct} on {date}. Avl Bal: Rs.12,345.67. If not done by you, call 1800111222.",
    "Dear Customer, Your {bank} A/c {acct} is credited with {amount} on {date}. Updated balance: Rs.45,678. -{bank}",
    "{bank} OTP for login is {otp}. Valid for 10 mins. DO NOT share with anyone. {bank} never asks for OTP.",
    "Your KYC for {bank} A/c {acct} has been updated successfully. No action required. For queries call 1800XXXXXXX.",
    "{bank}: A/c {acct} — NEFT credit of {amount} received from RAJESH KUMAR on {date}. Ref No: NEFT24013001234.",
    "ATM transaction of {amount} at SBI ATM, MUMBAI on {date} from A/c {acct}. If not done by you, call 18004253800.",
    "Dear {bank} Customer, Your EMI of {amount} due on {date} has been auto-debited. Thank you for timely payment.",
    "{bank} UPI: {amount} paid to Amazon using UPI on {date}. Ref: UPI24013012345. A/c {acct}.",
    "Your {bank} credit card ending {acct} statement for Jan 2025: Total Due {amount}. Min Due Rs.500. Pay by 05-Feb-2025.",
    "Dear Customer, Your {bank} Fixed Deposit of {amount} has matured on {date}. Amount credited to A/c {acct}.",
    "Security alert: a login was made to your {bank} account. If this was not you, call the official bank helpline.",
    "Your service request with {bank} has been closed. No action is required from your side.",
    "Reminder: EMI of {amount} is due this week. Pay using official app, branch, or registered autopay.",
    "Dear customer, your monthly statement is attached. Please login through the official {bank} app or {safe_domain} for details.",
]

BANKING_FRAUD_SEEDS = [
    "URGENT: Your {fake_bank} A/c {acct} will be BLOCKED today. Complete KYC at {fake_domain} and enter OTP {otp}.",
    "Dear Customer, {amount} will be deducted from your account. To stop, share your OTP {otp} with our agent. -{fake_bank}",
    "Congratulations! You have won {amount} cashback from {fake_bank}. Click {fake_domain} to claim. Offer expires today!",
    "Your {fake_bank} net banking is SUSPENDED. Verify immediately: {fake_domain}. Enter card details.",
    "ALERT: Suspicious login detected on your account. Share OTP {otp} with helpdesk to secure: {fake_domain}",
    "RBI has approved a refund of {amount} to your account. Provide your card number and CVV at: {fake_domain}",
    "Dear Customer, KYC expired. Your {fake_bank} account will be deactivated in 24hrs. Update: {fake_domain}",
    "{fake_bank}: Your account shows {amount} pending reversal. Approve on UPI. Send {otp} to confirm.",
    "NOTICE from {fake_bank}: Your account {acct} flagged for suspicious activity. Verify identity: {fake_domain} using PIN.",
    "LAST WARNING: Your {fake_bank} A/c will be permanently closed. To keep active, pay processing fee Rs.499 at {fake_domain}",
    "Fraud detected in your account. Share OTP {otp} with helpdesk immediately to stop debit of {amount}.",
    "Your refund is pending. Tell us the OTP just received and your money will be credited in 2 minutes.",
    "To reverse wrong UPI transfer of {amount}, share UPI PIN and OTP with customer care.",
    "Bank verification call: provide card CVV and OTP {otp} to secure account.",
]


def _expand_banking(
    templates: List[str],
    label: str,
    n_per_template: int = 5,
) -> List[dict]:
    records = []
    for tmpl in templates:
        for _ in range(n_per_template):
            text = tmpl.format(
                bank=random.choice(REAL_BANKS),
                fake_bank=random.choice(FAKE_BANK_NAMES),
                amount=random.choice(AMOUNTS),
                acct=random.choice(ACCOUNT_FRAGMENTS),
                date=random.choice(DATES),
                otp=random.choice(OTP_NUMBERS),
                safe_domain=random.choice(REAL_DOMAINS),
                fake_domain=random.choice(FAKE_DOMAINS),
            )
            records.append({
                "text": text,
                "label": label,
                "channel": "banking_notification",
                "is_manual": True,
                "source": "manual_banking",
            })
    return records


# ══════════════════════════════════════════════════════════════════════════════
# 2. LOAN ADVERTISEMENTS
# ══════════════════════════════════════════════════════════════════════════════

LOAN_SAFE_SEEDS = [
    "SBI Personal Loan: Borrow up to Rs.20 lakh at 10.40% p.a. No hidden charges. Apply at onlinesbi.sbi or nearest branch.",
    "HDFC Bank Home Loan: Interest rates starting 8.75% p.a. EMI as low as Rs.769/lakh. Apply online: hdfcbank.com/homeloan",
    "Axis Bank instant personal loan up to Rs.15 lakh. Paperless process. Check eligibility: axisbank.com/personal-loan",
    "Bajaj Finserv Personal Loan: Rs.25 lakh in 24 hours. Minimal documentation. Apply: bajajfinserv.in",
    "ICICI Bank Car Loan at 9.00% p.a. Zero processing fee for salaried customers. Visit nearest branch or call 1800200XXXX.",
    "Bank of Baroda Education Loan for studies abroad. Up to Rs.80 lakh. Competitive interest. Apply: bankofbaroda.in",
    "SBI MUDRA Loan for small businesses. Up to Rs.10 lakh. No collateral. Apply at any SBI branch.",
    "PNB Home Loan: Up to 90% of property value. Processing fee: 0.35% + GST. Apply: pnbhousing.com",
]

LOAN_FRAUD_SEEDS = [
    "INSTANT LOAN Rs.5 lakh! No CIBIL check! No documents! Approved in 5 minutes! Call 9999888877 NOW. Limited offer!",
    "Get loan Rs.50,000 to Rs.5,00,000 WITHOUT salary slip. Pay Rs.999 registration fee to get approved instantly. WhatsApp: 8888777766",
    "GUARANTEED loan approval for all! Bad CIBIL? No problem! Just pay Rs.2,500 processing fee upfront. Call 7777666655.",
    "RBI Approved Easy Loan Scheme! Get {amount} at 2% interest. Advance fee of Rs.500 required. Apply: {fake_domain}",
    "Work from home + Easy Loan! Earn while borrowing! Zero interest for first 3 months! Pay Rs.1,999 to activate. Limited slots! Call 9876543210",
    "Aadhar Card Loan! Only Aadhar needed. Get {amount} in 1 hour. Rs.499 insurance fee required. Contact: 9988776655",
    "PM Loan Yojana 2025: Government approved {amount} for all citizens. No repayment for 5 years! Processing fee Rs.750. Apply: {fake_domain}",
    "URGENT: Your pre-approved loan of {amount} will EXPIRE today. Pay Rs.599 activation fee at {fake_domain} to claim.",
]


def _expand_loan(
    templates: List[str],
    label: str,
    n_per_template: int = 6,
) -> List[dict]:
    records = []
    for tmpl in templates:
        for _ in range(n_per_template):
            text = tmpl.format(
                bank=random.choice(REAL_BANKS),
                fake_bank=random.choice(FAKE_BANK_NAMES),
                amount=random.choice(AMOUNTS),
                acct=random.choice(ACCOUNT_FRAGMENTS),
                date=random.choice(DATES),
                fake_domain=random.choice(FAKE_DOMAINS),
            )
            records.append({
                "text": text,
                "label": label,
                "channel": "loan_ad",
                "is_manual": True,
                "source": "manual_loan",
            })
    return records


# ══════════════════════════════════════════════════════════════════════════════
# 3. WHATSAPP FINANCIAL CHATS
# ══════════════════════════════════════════════════════════════════════════════

WHATSAPP_SAFE_SEEDS = [
    "Hi! I'm from {bank} customer support. Your account statement for last month is ready. Please visit our official app to download.",
    "Hello, this is a reminder that your {bank} credit card payment of {amount} is due on {date}. Pay via the {bank} app to avoid late charges.",
    "{bank}: As part of our security upgrade, we have sent you an OTP to register your device. Please enter it in the app only. We will NEVER ask for OTP over WhatsApp.",
    "Dear customer, your loan EMI of {amount} is due this week. Please ensure sufficient balance in your {bank} account. Auto-debit is enabled.",
    "Hello! Your {bank} account {acct} had a transaction of {amount} on {date}. Please check your passbook or app for details.",
]

WHATSAPP_FRAUD_SEEDS = [
    "Hello sir/madam, I am calling from {fake_bank} fraud department. Your account is under attack. Please share your OTP {otp} immediately to secure your account. This is urgent!",
    "Hi! I am {fake_bank} helpdesk agent Rahul. We are upgrading UPI. Please install this app: {fake_domain} and enter your PIN to complete upgrade.",
    "CONGRATULATIONS! You have been selected for {fake_bank} lucky draw winner {amount}! Send Rs.500 registration fee to claim prize: {fake_domain}",
    "Sir your UPI payment of {amount} is stuck. To reverse, you need to SEND Rs.1 to verify account. UPI ID: refund@{fake_bank}. Do it urgently!",
    "Hello, this is RBI helpline. Your bank account shows suspicious transactions. Share your card number and CVV to block them now.",
    "Hello sir I am from {bank} support. Install AnyDesk and share the code to update KYC.",
    "Madam your account is under cyber attack. Send card number, CVV and OTP now.",
    "Your UPI is blocked. I am customer care executive. Share screen and enter PIN for verification.",
    "Your UPI refund of {amount} is waiting. Open collect request and enter PIN to receive money.",
    "Cashback from PhonePe pending. Pay Rs.1 verification to refund@upi and claim reward.",
    "Payment failed but amount stuck. Approve UPI request from support@upi to reverse transaction.",
    "RBI refund department: accept UPI collect request urgently to receive {amount}.",
    "Part time job offer from {fake_bank}. Work from home. Earn {amount} per day. Registration fee Rs.999. WhatsApp: 9999888877",
    "Hi! Your account has {amount} pending refund from last transaction. To receive, share OTP we just sent to your number. Refund will credit in 2 minutes.",
]


def _expand_whatsapp(
    templates: List[str],
    label: str,
    n_per_template: int = 6,
) -> List[dict]:
    records = []
    for tmpl in templates:
        for _ in range(n_per_template):
            text = tmpl.format(
                bank=random.choice(REAL_BANKS),
                fake_bank=random.choice(FAKE_BANK_NAMES),
                amount=random.choice(AMOUNTS),
                acct=random.choice(ACCOUNT_FRAGMENTS),
                date=random.choice(DATES),
                otp=random.choice(OTP_NUMBERS),
                fake_domain=random.choice(FAKE_DOMAINS),
            )
            records.append({
                "text": text,
                "label": label,
                "channel": "whatsapp",
                "is_manual": True,
                "source": "manual_whatsapp",
            })
    return records


# ══════════════════════════════════════════════════════════════════════════════
# GENERATOR CLASS
# ══════════════════════════════════════════════════════════════════════════════

class ManualDatasetGenerator:
    """Generates all three manual datasets and saves them as CSVs."""

    def __init__(self) -> None:
        self.raw_dir = settings.raw_data_dir

    def generate_banking_notifications(self, n_per_template: int = 50) -> pd.DataFrame:
        safe_records = _expand_banking(BANKING_SAFE_SEEDS, "safe", n_per_template)
        fraud_records = _expand_banking(BANKING_FRAUD_SEEDS, "fraud", n_per_template)
        df = pd.DataFrame(safe_records + fraud_records)
        df = df.sample(frac=1, random_state=settings.RANDOM_SEED).reset_index(drop=True)
        logger.info("Banking notifications: %d records (%d safe, %d fraud)", len(df), len(safe_records), len(fraud_records))
        return df

    def generate_loan_advertisements(self, n_per_template: int = 60) -> pd.DataFrame:
        safe_records = _expand_loan(LOAN_SAFE_SEEDS, "safe", n_per_template)
        fraud_records = _expand_loan(LOAN_FRAUD_SEEDS, "fraud", n_per_template)
        df = pd.DataFrame(safe_records + fraud_records)
        df = df.sample(frac=1, random_state=settings.RANDOM_SEED).reset_index(drop=True)
        logger.info("Loan advertisements: %d records (%d safe, %d fraud)", len(df), len(safe_records), len(fraud_records))
        return df

    def generate_whatsapp_chats(self, n_per_template: int = 60) -> pd.DataFrame:
        safe_records = _expand_whatsapp(WHATSAPP_SAFE_SEEDS, "safe", n_per_template)
        fraud_records = _expand_whatsapp(WHATSAPP_FRAUD_SEEDS, "fraud", n_per_template)
        df = pd.DataFrame(safe_records + fraud_records)
        df = df.sample(frac=1, random_state=settings.RANDOM_SEED).reset_index(drop=True)
        logger.info("WhatsApp chats: %d records (%d safe, %d fraud)", len(df), len(safe_records), len(fraud_records))
        return df

    def generate_all(self) -> dict:
        results = {}
        out_dir = self.raw_dir / "manual_banking"
        out_dir.mkdir(parents=True, exist_ok=True)
        df_banking = self.generate_banking_notifications()
        out_path = out_dir / "banking_notifications.csv"
        df_banking.to_csv(out_path, index=False, encoding="utf-8")
        results["manual_banking"] = df_banking

        out_dir = self.raw_dir / "manual_loan"
        out_dir.mkdir(parents=True, exist_ok=True)
        df_loan = self.generate_loan_advertisements()
        out_path = out_dir / "loan_advertisements.csv"
        df_loan.to_csv(out_path, index=False, encoding="utf-8")
        results["manual_loan"] = df_loan

        out_dir = self.raw_dir / "manual_whatsapp"
        out_dir.mkdir(parents=True, exist_ok=True)
        df_whatsapp = self.generate_whatsapp_chats()
        out_path = out_dir / "whatsapp_chats.csv"
        df_whatsapp.to_csv(out_path, index=False, encoding="utf-8")
        results["manual_whatsapp"] = df_whatsapp

        print("\n Manual Dataset Generation Complete")
        print("=" * 45)
        for name, df in results.items():
            fraud = (df["label"] == "fraud").sum()
            safe = (df["label"] == "safe").sum()
            print(f"  {name:<20} {len(df):>5} rows  (safe={safe}, fraud={fraud})")
        print("=" * 45 + "\n")
        return results
