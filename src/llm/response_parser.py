"""Parse LLM JSON responses with a safe fallback."""

from __future__ import annotations

import json


DEFAULT_CONTACTS = {"cybercrime_helpline": "1930", "cybercrime_portal": "cybercrime.gov.in"}

# Multilingual UI strings for AI advisory output
LANG_STRINGS = {
    "en": {
        "warning": "Suraksha AI Warning",
        "advisory": "Suraksha AI Advisory",
        "verified": "Suraksha AI Safety Verified",
        "evaluation": "Suraksha AI Evaluation",
        "remote_summary": "This communication attempts to trick you into installing remote desktop software. Cybercriminals use AnyDesk or QuickSupport to view your screen and steal banking passwords or OTPs.",
        "otp_summary": "This message requests your secret OTP, PIN, or card credentials. Bank employees will NEVER ask for your OTP or PIN over chat or call.",
        "upi_summary": "This interaction involves a UPI transaction lure. Remember: Entering your UPI PIN always DEBITS money from your account — PIN is never required to receive money or refunds.",
        "loan_summary": "This loan offer demands an advance processing or activation fee. Legitimate bank loans never ask borrowers to deposit money upfront via personal UPI.",
        "safe_summary": "This message contains standard bank notification language or verified official bank web domains. No credential theft or urgent blocking pressure was detected.",
        "generic_summary": "Our hybrid security engine evaluated this message context against known fraud indicators.",
        "verify": "Verify details through official channels only.",
        "report": "If suspicious, call Cybercell Helpline 1930.",
        "lost_money": "If money was fraudulently debited, call 1930 within 1 hour to lock the transaction.",
    },
    "hi": {
        "warning": "सुरक्षा AI चेतावनी",
        "advisory": "सुरक्षा AI सलाह",
        "verified": "सुरक्षा AI सत्यापित",
        "evaluation": "सुरक्षा AI मूल्यांकन",
        "remote_summary": "यह संदेश आपको रिमोट डेस्कटॉप सॉफ़्टवेयर इंस्टॉल करने का प्रयास कर रहा है। साइबर अपराधी AnyDesk का उपयोग करके आपकी बैंकिंग पासवर्ड और OTP चुरा सकते हैं।",
        "otp_summary": "यह संदेश आपका OTP, PIN या कार्ड की जानकारी मांग रहा है। बैंक कर्मचारी कभी भी OTP या PIN नहीं मांगते।",
        "upi_summary": "यह UPI लेनदेन का एक जाल है। याद रखें: UPI PIN दर्ज करने से हमेशा पैसे कटते हैं — पैसे प्राप्त करने के लिए PIN की जरूरत नहीं होती।",
        "loan_summary": "यह ऋण ऑफर अग्रिम प्रसंस्करण शुल्क मांग रहा है। असली बैंक ऋण में कभी भी UPI पर पैसे जमा करने की आवश्यकता नहीं होती।",
        "safe_summary": "यह संदेश एक सामान्य बैंक अधिसूचना है। कोई संदिग्ध गतिविधि नहीं पाई गई।",
        "generic_summary": "हमारे सुरक्षा इंजन ने इस संदेश का विश्लेषण किया है।",
        "verify": "केवल आधिकारिक चैनलों से जानकारी सत्यापित करें।",
        "report": "संदिग्ध होने पर साइबर हेल्पलाइन 1930 पर कॉल करें।",
        "lost_money": "यदि पैसे धोखाधड़ी से निकाले गए हों, तो 1 घंटे के अंदर 1930 पर कॉल करें।",
    },
    "mr": {
        "warning": "सुरक्षाAI इशारा",
        "advisory": "सुरक्षाAI सल्ला",
        "verified": "सुरक्षाAI सत्यापित",
        "evaluation": "सुरक्षाAI मूल्यमापन",
        "remote_summary": "हा संदेश तुम्हाला रिमोट सॉफ्टवेअर स्थापित करण्यासाठी फसवण्याचा प्रयत्न करतो. AnyDesk वापरून सायबर गुन्हेगार तुमचा OTP चोरू शकतात.",
        "otp_summary": "हा संदेश तुमचा OTP, PIN किंवा कार्ड माहिती मागत आहे. बँक कर्मचारी कधीही OTP मागत नाहीत.",
        "upi_summary": "UPI PIN टाकल्याने नेहमी पैसे कपात होतात — पैसे मिळवण्यासाठी PIN लागत नाही.",
        "loan_summary": "हा कर्ज ऑफर अग्रिम शुल्क मागत आहे. खऱ्या बँका UPI वर पैसे जमा करायला सांगत नाहीत.",
        "safe_summary": "हा संदेश एक सामान्य बँक अधिसूचना आहे. कोणतीही संशयास्पद गोष्ट आढळली नाही.",
        "generic_summary": "आमच्या सुरक्षा इंजिनने या संदेशाचे विश्लेषण केले आहे.",
        "verify": "केवळ अधिकृत माध्यमांद्वारे माहिती तपासा.",
        "report": "संशयास्पद असल्यास सायबर हेल्पलाइन 1930 वर कॉल करा.",
        "lost_money": "पैसे फसवणुकीने काढले असल्यास 1 तासात 1930 वर कॉल करा.",
    },
    "gu": {
        "warning": "સુરક્ષા AI ચેતવણી",
        "advisory": "સુરક્ષા AI સલાહ",
        "verified": "સુરક્ષા AI ચકાસેલ",
        "evaluation": "સુરક્ષા AI મૂલ્યાંકન",
        "remote_summary": "આ સંદેશ તમને રિમોટ ડેસ્કટોપ સૉફ્ટવેર ઇન્સ્ટૉલ કરાવવા માટે છેતરી રહ્યો છે. AnyDesk દ્વારા સાઇબર ગુનેગારો OTP ચોરી શકે છે.",
        "otp_summary": "આ સંદેશ તમારો OTP, PIN અથવા કાર્ડ નંબર માંગે છે. બૅન્ક ક્યારેય OTP ન માંગે.",
        "upi_summary": "UPI PIN ભરવાથી હંમેશા પૈસા કપાય છે — પૈસા મેળવવા PIN ની જરૂર નથી.",
        "loan_summary": "આ લોન ઑફર અગ્રિમ ચાર્જ માંગે છે. સાચી બૅન્ક ક્યારેય UPI પર પૈસા જમા કરાવવા ન કહે.",
        "safe_summary": "આ સંદેશ એક સામાન્ય બૅન્ક સૂચના છે. કોઈ શંકાસ્પદ ગતિવિધિ મળી નથી.",
        "generic_summary": "અમારા સુરક્ષા એન્જિને આ સંદેશનું વિશ્લેષણ કર્યું છે.",
        "verify": "ફક્ત સત્તાવાર માધ્યમ દ્વારા માહિતી ચકાસો.",
        "report": "શંકા હોય તો સાઇબર હેલ્પલાઇન 1930 પર ફોન કરો.",
        "lost_money": "જો પૈસા ઉઠાવ્યા હોય, તો 1 કલાકમાં 1930 પર ફોન કરો.",
    },
    "bn": {
        "warning": "সুরক্ষা AI সতর্কতা",
        "advisory": "সুরক্ষা AI পরামর্শ",
        "verified": "সুরক্ষা AI যাচাইকৃত",
        "evaluation": "সুরক্ষা AI মূল্যায়ন",
        "remote_summary": "এই বার্তাটি আপনাকে রিমোট ডেস্কটপ সফটওয়্যার ইনস্টল করতে প্রতারণা করছে। AnyDesk ব্যবহার করে সাইবার অপরাধীরা OTP চুরি করতে পারে।",
        "otp_summary": "এই বার্তা আপনার OTP, PIN বা কার্ড তথ্য চাইছে। ব্যাংক কর্মচারীরা কখনো OTP চান না।",
        "upi_summary": "UPI PIN দিলে সবসময় টাকা কাটে — টাকা পেতে PIN লাগে না।",
        "loan_summary": "এই ঋণ অফার অগ্রিম ফি চাইছে। সত্যিকার ব্যাংক কখনো UPI-তে টাকা জমা দিতে বলে না।",
        "safe_summary": "এই বার্তাটি একটি স্বাভাবিক ব্যাংক বিজ্ঞপ্তি। কোনো সন্দেহজনক কার্যকলাপ পাওয়া যায়নি।",
        "generic_summary": "আমাদের নিরাপত্তা ইঞ্জিন এই বার্তাটি বিশ্লেষণ করেছে।",
        "verify": "শুধুমাত্র অফিসিয়াল চ্যানেলের মাধ্যমে তথ্য যাচাই করুন।",
        "report": "সন্দেহ হলে সাইবার হেল্পলাইন 1930-এ কল করুন।",
        "lost_money": "প্রতারণামূলকভাবে টাকা তোলা হলে 1 ঘণ্টার মধ্যে 1930-এ কল করুন।",
    },
}


def fallback_response(analysis: dict, language: str = "en") -> dict:
    raw_score = float(analysis.get("risk_score", 0.0))
    score_100 = int(round(raw_score * 100))
    level = str(analysis.get("risk_level", "low_risk")).replace("_", " ").title()
    text = str(analysis.get("original_text", "")).lower()
    flags = analysis.get("rule_flags", [])

    # Pick language strings, fallback to English
    L = LANG_STRINGS.get(language, LANG_STRINGS["en"])

    # Contextual dynamic summary construction
    if "remote_access_app" in flags or "anydesk" in text or "teamviewer" in text or "screen share" in text:
        summary = f"{L['warning']} (Score: {score_100}/100 — {level}): {L['remote_summary']}"
        do_nots = [
            "Do NOT install AnyDesk, TeamViewer, or QuickSupport on your device.",
            "Do NOT share any 9-digit remote control code with callers or chat agents.",
            "Do NOT enter your netbanking password or UPI PIN while screen sharing."
        ]
        alternatives = [
            "Disconnect the call or block the WhatsApp contact immediately.",
            "Contact your official bank helpline directly to report impersonation."
        ]
    elif "otp_or_pin_request" in flags or "otp" in text or "pin" in text or "cvv" in text:
        summary = f"{L['warning']} (Score: {score_100}/100 — {level}): {L['otp_summary']}"
        do_nots = [
            "Do NOT share your 6-digit OTP, UPI PIN, or card CVV with anyone.",
            "Do NOT enter your PIN on unverified websites or refund claim links.",
            "Do NOT approve payment collect requests sent by unknown parties."
        ]
        alternatives = [
            "Login only through your bank's official mobile application.",
            "If an unauthorized transaction occurred, block your card via official netbanking."
        ]
    elif "upi_collect_scam" in flags or "upi" in text or "collect request" in text:
        summary = f"{L['advisory']} (Score: {score_100}/100 — {level}): {L['upi_summary']}"
        do_nots = [
            "Do NOT enter your UPI PIN expecting to receive money or cashbacks.",
            "Do NOT accept unknown UPI collect requests on GPay, PhonePe, or Paytm.",
            "Do NOT send Rs.1 to 'verify' or 'unlock' pending refunds."
        ]
        alternatives = [
            "Check incoming credits directly on your bank statement.",
            "Decline suspicious collect requests immediately."
        ]
    elif "upfront_fee" in flags or "loan" in text or "cibil" in text:
        summary = f"{L['advisory']} (Score: {score_100}/100 — {level}): {L['loan_summary']}"
        do_nots = [
            "Do NOT pay advance processing fees, registration fees, or insurance deposits.",
            "Do NOT send scanned copies of Aadhar or PAN to unverified WhatsApp numbers."
        ]
        alternatives = [
            "Apply for loans directly through registered bank branches or official portals."
        ]
    elif "official_bank_domain" in flags or "statement" in text or "credited" in text:
        summary = f"{L['verified']} (Score: {score_100}/100 — {level}): {L['safe_summary']}"
        do_nots = [
            "Do NOT forward OTPs even if a message seems legitimate."
        ]
        alternatives = [
            "Access statement details inside your official mobile banking app."
        ]
    else:
        summary = f"{L['evaluation']} (Score: {score_100}/100 — {level}): {L['generic_summary']}"
        do_nots = [
            "Do NOT share personal or financial information with unverified sources.",
            "Do NOT click unverified links received via SMS or WhatsApp."
        ]
        alternatives = [
            "Verify any urgent claims directly with your official bank branch."
        ]

    return {
        "risk_summary": summary,
        "evidence": analysis.get("rule_evidence", []),
        "immediate_actions": [L["verify"], L["report"]],
        "do_not": do_nots,
        "safe_alternatives": alternatives,
        "report_guidance": L["lost_money"],
        "emergency_contacts": DEFAULT_CONTACTS,
    }


class LLMResponseParser:
    def parse(self, content: str, analysis: dict, language: str = "en") -> dict:
        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict):
                parsed.setdefault("emergency_contacts", DEFAULT_CONTACTS)
                return parsed
        except Exception:
            pass
        return fallback_response(analysis, language=language)
