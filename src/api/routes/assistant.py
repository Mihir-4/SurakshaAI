"""AI Safety Assistant route for general financial safety questions."""

from __future__ import annotations

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/assistant", tags=["assistant"])


class AssistantQueryRequest(BaseModel):
    question: str = Field(..., min_length=2)
    language: str = "en"


# Built-in multilingual safety knowledge base for instant answers
KNOWLEDGE_BASE = {
    "1930": {
        "en": "Call national Cybercell Helpline 1930 immediately if money was debited fraudulently. Reporting within 1 hour ('Golden Hour') allows police to lock the scammer's bank account before funds are withdrawn.",
        "hi": "धोखाधड़ी से पैसे कटने पर तुरंत राष्ट्रीय साइबर हेल्पलाइन 1930 पर कॉल करें। 1 घंटे ('गोल्डन ऑवर') के भीतर रिपोर्ट करने से पुलिस जालसाज का बैंक खाता ब्लॉक कर सकती है।",
        "mr": "फसवणुकीने पैसे कपात झाल्यास लगेचच राष्ट्रीय सायबर हेल्पलाइन 1930 वर कॉल करा. 1 तासाच्या आत तक्रार केल्यास पोलीस फसवणूक करणाऱ्याचे बँक खाते ब्लॉक करू शकतात.",
        "gu": "છેતરપિંડીથી પૈસા કપાય તો તુરંત જ સાઇબર હેલ્પલાઇન 1930 પર કોલ કરો. 1 કલાકની અંદર રિપોર્ટ કરવાથી પોલીસ ઠગનું એકાઉન્ટ સીલ કરી શકે છે.",
        "bn": "প্রতারণামূলকভাবে টাকা কাটা গেলে অবিলম্বে জাতীয় সাইবার হেল্পলাইন 1930-এ কল করুন। 1 ঘণ্টার মধ্যে রিপোর্ট করলে পুলিশ প্রতারকের অ্যাকাউন্ট ফ্রিজ করতে পারে।",
    },
    "anydesk": {
        "en": "Never install AnyDesk, TeamViewer, or QuickSupport on request of callers or WhatsApp agents. These remote screen sharing apps allow scammers to view your banking password, OTPs, and control your device.",
        "hi": "अनजान कॉलर या व्हाट्सएप एजेंट के कहने पर कभी भी AnyDesk, TeamViewer या QuickSupport इंस्टॉल न करें। ये ऐप आपकी स्क्रीन देखकर पासवर्ड और OTP चुराते हैं।",
        "mr": "अनोळखी कॉलरच्या सांगण्यावरून कधीही AnyDesk किंवा QuickSupport इन्स्टॉल करू नका. या ॲप्समुळे सायबर गुन्हेगार तुमचा पासवर्ड आणि OTP पाहू शकतात.",
        "gu": "અજાણ્યા કોલરના કહેવાથી ક્યારેય AnyDesk અથવા QuickSupport ઇન્સ્ટોલ કરશો નહીં. આ એપથી ગુનેગારો તમારો پاسવર્ડ અને OTP જોઈ શકે છે.",
        "bn": "অজানা কলারের কথায় কখনোই AnyDesk বা QuickSupport ইনস্টল করবেন না। এই অ্যাপগুলো দিয়ে তারা আপনার পাসওয়ার্ড এবং OTP দেখতে পায়।",
    },
    "upi_pin": {
        "en": "Remember: UPI PIN is ONLY required for sending (debiting) money from your account. You NEVER need to enter a UPI PIN to receive money, get cashbacks, or accept refunds.",
        "hi": "याद रखें: UPI PIN का उपयोग केवल पैसे भेजने (खाते से कटने) के लिए होता है। पैसे प्राप्त करने या रिफंड लेने के लिए PIN दर्ज करने की आवश्यकता कभी नहीं होती।",
        "mr": "लक्षात ठेवा: UPI PIN फक्त पैसे पाठवण्यासाठी असतो. पैसे मिळवण्यासाठी किंवा रिफंडसाठी PIN टाकण्याची अजिबात गरज नसते.",
        "gu": "યાદ રાખો: UPI PIN માત્ર પૈસા મોકલવા માટે હોય છે. પૈસા મેળવવા માટે ક્યારેય PIN નાખવાની જરૂર નથી.",
        "bn": "মনে রাখবেন: UPI PIN শুধুমাত্র টাকা পাঠানোর জন্য লাগে। টাকা পাওয়ার জন্য কখনো PIN দিতে হয় না।",
    },
    "otp": {
        "en": "Bank officials, RBI, and payment apps (GPay, PhonePe) NEVER ask for your OTP or PIN. Never share OTP even if the caller claims your account/SIM card is about to be blocked.",
        "hi": "बैंक कर्मचारी, RBI या GPay/PhonePe कभी भी आपका OTP नहीं मांगते। खाते या सिम कार्ड ब्लॉक होने की धमकी मिलने पर भी OTP कभी शेयर न करें।",
        "mr": "बँक अधिकारी किंवा GPay/PhonePe कधीही तुमचा OTP मागत नाहीत. खाते बंद पडण्याच्या भीतीपोटीही OTP शेअर करू नका.",
        "gu": "બૅન્ક અધિકારી કે GPay/PhonePe ક્યારેય તમારો OTP ન માંગે. ખાતું બંધ થવાની ધમકી મળે તો પણ OTP આપશો નહીં.",
        "bn": "ব্যাংক বা কোনো পেমেন্ট অ্যাপ কখনো OTP চায় না। অ্যাকাউন্ট বা সিম বন্ধের ভয় দেখালেও OTP শেয়ার করবেন না।",
    },
    "default": {
        "en": "For any financial cyber fraud in India: 1) Immediately call 1930 Cyber Helpline. 2) Lock your debit/credit card via mobile banking app. 3) Report online at cybercrime.gov.in. 4) Contact your official bank branch.",
        "hi": "भारत में वित्तीय साइबर धोखाधड़ी के लिए: 1) तुरंत 1930 साइबर हेल्पलाइन पर कॉल करें। 2) मोबाइल बैंकिंग ऐप से कार्ड ब्लॉक करें। 3) cybercrime.gov.in पर रिपोर्ट दर्ज करें।",
        "mr": "कोणत्याही सायबर फसवणुकीसाठी: 1) लगेच 1930 सायबर हेल्पलाइनवर कॉल करा. 2) मोबाईल बँकिंगद्वारे कार्ड ब्लॉक करा. 3) cybercrime.gov.in वर तक्रार नोंदवा.",
        "gu": "કોઈપણ સાઇબર છેતરપિંડી માટે: 1) તુરંત 1930 સાઇબર હેલ્પલાઇન પર કોલ કરો. 2) બૅન્ક ઍપથી કાર્ડ બ્લૉક કરો. 3) cybercrime.gov.in પર ફરિયાદ નોંધાવો.",
        "bn": "যেকোনো সাইবার প্রতারণার জন্য: 1) অবিলম্বে 1930-এ কল করুন। 2) মোবাইল ব্যাংকিং দিয়ে কার্ড ব্লক করুন। 3) cybercrime.gov.in-এ রিপোর্ট করুন।",
    }
}


def _get_fallback_answer(q: str, lang: str) -> str:
    ql = q.lower()
    l = lang if lang in ["en", "hi", "mr", "gu", "bn"] else "en"
    if "1930" in ql or "helpline" in ql or "debit" in ql or "lost money" in ql or "पैसे" in ql:
        return KNOWLEDGE_BASE["1930"][l]
    elif "anydesk" in ql or "teamviewer" in ql or "app" in ql or "screen" in ql or "सॉफ़्टवेयर" in ql:
        return KNOWLEDGE_BASE["anydesk"][l]
    elif "pin" in ql or "upi" in ql or "collect" in ql or "refund" in ql or "रिसीव" in ql:
        return KNOWLEDGE_BASE["upi_pin"][l]
    elif "otp" in ql or "code" in ql or "password" in ql or "पासवर्ड" in ql:
        return KNOWLEDGE_BASE["otp"][l]
    return KNOWLEDGE_BASE["default"][l]


@router.post("/chat")
def answer_safety_query(payload: AssistantQueryRequest) -> dict:
    lang = payload.language or "en"
    q = payload.question.strip()

    if not q:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    # Try Mistral API first if available
    if settings.MISTRAL_API_KEY:
        try:
            from mistralai import Mistral
            client = Mistral(api_key=settings.MISTRAL_API_KEY)
            prompt = (
                f"You are SurakshaAI Cyber Safety Assistant for rural and digital banking users in India.\n"
                f"Answer the user's question concisely in maximum 3-4 bullet points in {lang} language.\n"
                f"Always emphasize calling Cybercell Helpline 1930 if money was lost.\n\n"
                f"User Question: {q}"
            )
            response = client.chat.complete(
                model=settings.MISTRAL_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=300,
            )
            answer_text = response.choices[0].message.content.strip()
            return {
                "question": q,
                "answer": answer_text,
                "helpline": "1930",
                "portal": "cybercrime.gov.in",
                "source": "mistral_ai",
            }
        except Exception as exc:
            logger.warning("Mistral assistant call failed: %s", exc)

    # Built-in intelligent safety knowledge base fallback
    answer_text = _get_fallback_answer(q, lang)
    return {
        "question": q,
        "answer": answer_text,
        "helpline": "1930",
        "portal": "cybercrime.gov.in",
        "source": "knowledge_base",
    }
