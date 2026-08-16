/**
 * SurakshaAI — Internationalization (i18n) Translation Dictionary
 * Supported languages: English (en), Hindi (hi), Marathi (mr), Gujarati (gu), Bengali (bn)
 */

const I18N = {
  en: {
    // Meta
    lang_name: "English",
    lang_flag: "🇮🇳",

    // Header
    app_name: "SurakshaAI",
    app_tagline: "AI-Powered Fraud Detection",
    api_status_ok: "API Online",
    api_status_err: "API Offline",

    // Nav Tabs
    tab_studio: "Detection Studio",
    tab_history: "History",
    tab_analytics: "Analytics",
    tab_assistant: "AI Safety Assistant",
    assistant_title: "AI Safety Advisor",
    assistant_subtitle: "Ask any cybersecurity or financial safety question in your preferred language",
    ask_placeholder: "Type your safety question here (e.g., What to do if money was debited?)...",
    btn_ask: "Ask Assistant",

    // Input Mode Tabs
    mode_sms: "Text / SMS / Chat",
    mode_image: "Screenshot",

    // Studio
    studio_title: "Analyze Communication",
    studio_subtitle: "Paste suspicious text or upload a screenshot for AI fraud detection",
    placeholder_sms: "Paste SMS, WhatsApp message, or email body here...",
    label_image_upload: "Upload Screenshot",
    image_drop_text: "Drag & drop image here or click to browse",
    image_formats: "Supports PNG, JPG, WebP — Max 10MB",
    btn_analyze: "Analyze Communication",
    btn_analyze_image: "Analyze Screenshot",
    btn_clear: "Clear",
    analyzing: "Analyzing...",

    // Risk Levels
    risk_critical: "CRITICAL THREAT",
    risk_very_high: "VERY HIGH RISK",
    risk_high: "HIGH RISK",
    risk_medium: "MEDIUM RISK",
    risk_low: "LOW RISK",
    risk_safe: "SAFE",

    // Result Labels
    result_score: "Risk Score",
    result_category: "Category",
    result_channel: "Channel",
    result_do_not: "DO NOT",
    result_actions: "SAFE ALTERNATIVE",
    result_immediate: "Immediate Actions",
    result_report: "Report Guidance",
    result_evidence: "Evidence Found",
    result_ocr: "Extracted Text from Screenshot",
    result_flags: "Rule Flags",

    // History
    history_title: "Analysis History",
    history_empty: "No analysis history yet. Start by analyzing a message.",
    history_clear: "Clear History",

    // Analytics
    analytics_title: "Fraud Analytics Dashboard",
    analytics_total: "Total Analyses",
    analytics_fraud: "Fraud Detected",
    analytics_safe: "Safe Messages",
    analytics_avg_score: "Avg Risk Score",

    // Emergency
    emergency_title: "Emergency Contacts",
    cybercrime_helpline: "Cybercrime Helpline",
    cybercrime_portal: "cybercrime.gov.in",
    lang_select: "Select Language",
  },

  hi: {
    lang_name: "हिंदी",
    lang_flag: "🇮🇳",
    app_name: "सुरक्षाAI",
    app_tagline: "AI-संचालित धोखाधड़ी पहचान",
    api_status_ok: "API ऑनलाइन",
    api_status_err: "API ऑफलाइन",
    tab_studio: "पहचान केंद्र",
    tab_history: "इतिहास",
    tab_analytics: "विश्लेषण",
    mode_sms: "टेक्स्ट / SMS / चैट",
    mode_image: "स्क्रीनशॉट",
    studio_title: "संदेश विश्लेषण करें",
    studio_subtitle: "संदिग्ध संदेश चिपकाएँ या धोखाधड़ी जाँच के लिए स्क्रीनशॉट अपलोड करें",
    placeholder_sms: "संदिग्ध SMS, WhatsApp संदेश यहाँ चिपकाएँ...",
    label_image_upload: "स्क्रीनशॉट अपलोड करें",
    image_drop_text: "यहाँ इमेज खींचें या क्लिक करें",
    image_formats: "PNG, JPG, WebP — अधिकतम 10MB",
    btn_analyze: "विश्लेषण करें",
    btn_analyze_image: "स्क्रीनशॉट विश्लेषण करें",
    btn_clear: "साफ करें",
    analyzing: "विश्लेषण हो रहा है...",
    risk_critical: "अत्यंत खतरनाक",
    risk_very_high: "बहुत अधिक जोखिम",
    risk_high: "उच्च जोखिम",
    risk_medium: "मध्यम जोखिम",
    risk_low: "कम जोखिम",
    risk_safe: "सुरक्षित",
    result_score: "जोखिम स्कोर",
    result_category: "श्रेणी",
    result_channel: "चैनल",
    result_do_not: "बिल्कुल न करें",
    result_actions: "सुरक्षित विकल्प",
    result_immediate: "तत्काल कार्रवाई",
    result_report: "रिपोर्ट करें",
    result_evidence: "मिले प्रमाण",
    result_ocr: "स्क्रीनशॉट से निकाला गया टेक्स्ट",
    result_flags: "नियम संकेत",
    history_title: "विश्लेषण इतिहास",
    history_empty: "अभी तक कोई इतिहास नहीं। एक संदेश का विश्लेषण शुरू करें।",
    history_clear: "इतिहास साफ करें",
    analytics_title: "धोखाधड़ी विश्लेषण डैशबोर्ड",
    analytics_total: "कुल विश्लेषण",
    analytics_fraud: "धोखाधड़ी पकड़ी",
    analytics_safe: "सुरक्षित संदेश",
    analytics_avg_score: "औसत जोखिम",
    emergency_title: "आपातकालीन संपर्क",
    cybercrime_helpline: "साइबर अपराध हेल्पलाइन",
    cybercrime_portal: "ऑनलाइन रिपोर्ट करें",
    lang_select: "भाषा चुनें",
  },

  mr: {
    lang_name: "मराठी",
    lang_flag: "🇮🇳",
    app_name: "सुरक्षाAI",
    app_tagline: "AI-चलित फसवणूक शोध",
    api_status_ok: "API ऑनलाइन",
    api_status_err: "API ऑफलाइन",
    tab_studio: "शोध केंद्र",
    tab_history: "इतिहास",
    tab_analytics: "विश्लेषण",
    mode_sms: "मजकूर / SMS / चॅट",
    mode_image: "स्क्रीनशॉट",
    studio_title: "संदेश तपासा",
    studio_subtitle: "संशयास्पद संदेश पेस्ट करा किंवा स्क्रीनशॉट अपलोड करा",
    placeholder_sms: "संशयास्पद SMS, WhatsApp संदेश येथे पेस्ट करा...",
    label_image_upload: "स्क्रीनशॉट अपलोड करा",
    image_drop_text: "येथे इमेज ड्रॅग करा किंवा क्लिक करा",
    image_formats: "PNG, JPG, WebP — कमाल 10MB",
    btn_analyze: "तपासा",
    btn_analyze_image: "स्क्रीनशॉट तपासा",
    btn_clear: "साफ करा",
    analyzing: "तपासत आहे...",
    risk_critical: "अत्यंत धोकादायक",
    risk_very_high: "खूप जास्त धोका",
    risk_high: "उच्च धोका",
    risk_medium: "मध्यम धोका",
    risk_low: "कमी धोका",
    risk_safe: "सुरक्षित",
    result_score: "धोका गुण",
    result_category: "वर्ग",
    result_channel: "माध्यम",
    result_do_not: "हे करू नका",
    result_actions: "सुरक्षित पर्याय",
    result_immediate: "तातडीची कारवाई",
    result_report: "तक्रार नोंदवा",
    result_evidence: "आढळलेले पुरावे",
    result_ocr: "स्क्रीनशॉटमधील मजकूर",
    result_flags: "नियम संकेत",
    history_title: "विश्लेषण इतिहास",
    history_empty: "अद्याप कोणताही इतिहास नाही.",
    history_clear: "इतिहास साफ करा",
    analytics_title: "फसवणूक विश्लेषण डॅशबोर्ड",
    analytics_total: "एकूण विश्लेषण",
    analytics_fraud: "फसवणूक आढळली",
    analytics_safe: "सुरक्षित संदेश",
    analytics_avg_score: "सरासरी धोका",
    emergency_title: "आपत्कालीन संपर्क",
    cybercrime_helpline: "सायबर गुन्हे हेल्पलाइन",
    cybercrime_portal: "ऑनलाइन तक्रार",
    lang_select: "भाषा निवडा",
  },

  gu: {
    lang_name: "ગુજરાતી",
    lang_flag: "🇮🇳",
    app_name: "સુરક્ષાAI",
    app_tagline: "AI-સંચાલિત છેતરપિંડી શોધ",
    api_status_ok: "API ઓનલાઇન",
    api_status_err: "API ઓફલાઇન",
    tab_studio: "શોધ કેન્દ્ર",
    tab_history: "ઇતિહાસ",
    tab_analytics: "વિશ્લેષણ",
    mode_sms: "ટેક્સ્ટ / SMS / ચૅટ",
    mode_image: "સ્ક્રીનશૉટ",
    studio_title: "સંદેશ ચકાસો",
    studio_subtitle: "શંકાસ્પદ સંદેશ પેસ્ટ કરો અથવા સ્ક્રીનશૉટ અપલોડ કરો",
    placeholder_sms: "શંકાસ્પદ SMS, WhatsApp સંદેશ અહીં પેસ્ટ કરો...",
    label_image_upload: "સ્ક્રીનશૉટ અપલોડ કરો",
    image_drop_text: "અહીં ઈમેજ ખેંચો અથવા ક્લિક કરો",
    image_formats: "PNG, JPG, WebP — મહત્તમ 10MB",
    btn_analyze: "ચકાસો",
    btn_analyze_image: "સ્ક્રીનશૉટ ચકાસો",
    btn_clear: "સાફ કરો",
    analyzing: "ચકાસી રહ્યા છીએ...",
    risk_critical: "અત્યંત જોખમ",
    risk_very_high: "ખૂબ વધુ જોખમ",
    risk_high: "ઉચ્ચ જોખમ",
    risk_medium: "મધ્યમ જોખમ",
    risk_low: "ઓછું જોખમ",
    risk_safe: "સુરક્ષિત",
    result_score: "જોખમ સ્કોર",
    result_category: "શ્રેણી",
    result_channel: "માધ્યમ",
    result_do_not: "આ ન કરો",
    result_actions: "સુરક્ષિત વિકલ્પ",
    result_immediate: "તાત્કાલિક પગલા",
    result_report: "ફરિયાદ",
    result_evidence: "મળેલ પુરાવા",
    result_ocr: "સ્ક્રીનશૉટ માંથી ટેક્સ્ટ",
    result_flags: "નિયમ સંકેત",
    history_title: "વિશ્લેષણ ઇતિહાસ",
    history_empty: "હજી સુધી કોઈ ઇતિહાસ નથી.",
    history_clear: "ઇતિહાસ સાફ કરો",
    analytics_title: "છેતરપિંડી વિશ્લેષણ ડૅશબોર્ડ",
    analytics_total: "કુલ વિશ્લેષણ",
    analytics_fraud: "છેતરપિંડી મળ્યો",
    analytics_safe: "સુરક્ષિત સંદેશ",
    analytics_avg_score: "સરેરાશ જોખમ",
    emergency_title: "આકસ્મિક સંપર્ક",
    cybercrime_helpline: "સાઇબર ક્રાઇમ હેલ્પલાઇન",
    cybercrime_portal: "ઓનલાઇન ફરિયાદ",
    lang_select: "ભાષા પસંદ કરો",
  },

  bn: {
    lang_name: "বাংলা",
    lang_flag: "🇧🇩",
    app_name: "সুরক্ষাAI",
    app_tagline: "AI-চালিত প্রতারণা শনাক্তকরণ",
    api_status_ok: "API অনলাইন",
    api_status_err: "API অফলাইন",
    tab_studio: "শনাক্ত কেন্দ্র",
    tab_history: "ইতিহাস",
    tab_analytics: "বিশ্লেষণ",
    mode_sms: "পাঠ্য / SMS / চ্যাট",
    mode_image: "স্ক্রিনশট",
    studio_title: "বার্তা বিশ্লেষণ",
    studio_subtitle: "সন্দেহজনক বার্তা পেস্ট করুন বা স্ক্রিনশট আপলোড করুন",
    placeholder_sms: "সন্দেহজনক SMS, WhatsApp বার্তা এখানে পেস্ট করুন...",
    label_image_upload: "স্ক্রিনশট আপলোড করুন",
    image_drop_text: "এখানে ইমেজ টেনে আনুন বা ক্লিক করুন",
    image_formats: "PNG, JPG, WebP — সর্বোচ্চ 10MB",
    btn_analyze: "বিশ্লেষণ করুন",
    btn_analyze_image: "স্ক্রিনশট বিশ্লেষণ",
    btn_clear: "পরিষ্কার করুন",
    analyzing: "বিশ্লেষণ হচ্ছে...",
    risk_critical: "অত্যন্ত বিপজ্জনক",
    risk_very_high: "অত্যধিক ঝুঁকি",
    risk_high: "উচ্চ ঝুঁকি",
    risk_medium: "মধ্যম ঝুঁকি",
    risk_low: "কম ঝুঁকি",
    risk_safe: "নিরাপদ",
    result_score: "ঝুঁকি স্কোর",
    result_category: "বিভাগ",
    result_channel: "চ্যানেল",
    result_do_not: "এটি করবেন না",
    result_actions: "নিরাপদ বিকল্প",
    result_immediate: "তাৎক্ষণিক পদক্ষেপ",
    result_report: "রিপোর্ট করুন",
    result_evidence: "প্রমাণ",
    result_ocr: "স্ক্রিনশট থেকে পাঠ্য",
    result_flags: "নিয়ম সংকেত",
    history_title: "বিশ্লেষণ ইতিহাস",
    history_empty: "এখনও কোনো ইতিহাস নেই।",
    history_clear: "ইতিহাস মুছুন",
    analytics_title: "প্রতারণা বিশ্লেষণ ড্যাশবোর্ড",
    analytics_total: "মোট বিশ্লেষণ",
    analytics_fraud: "প্রতারণা শনাক্ত",
    analytics_safe: "নিরাপদ বার্তা",
    analytics_avg_score: "গড় ঝুঁকি",
    emergency_title: "জরুরি যোগাযোগ",
    cybercrime_helpline: "সাইবার ক্রাইম হেল্পলাইন",
    cybercrime_portal: "অনলাইনে রিপোর্ট",
    lang_select: "ভাষা নির্বাচন করুন",
  },
};

// Active language code
let currentLang = localStorage.getItem("surakshaai_lang") || "en";

/**
 * Get translation string for a key in the current active language.
 * Falls back to English if key not found.
 */
function t(key) {
  const langDict = I18N[currentLang] || I18N["en"];
  return langDict[key] || I18N["en"][key] || key;
}

/**
 * Set active language and persist to localStorage.
 */
function setLanguage(lang) {
  if (!I18N[lang]) return;
  currentLang = lang;
  localStorage.setItem("surakshaai_lang", lang);
  applyTranslations();
}

/**
 * Apply translations to all elements with data-i18n attribute.
 */
function applyTranslations() {
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const key = el.getAttribute("data-i18n");
    if (el.tagName === "INPUT" || el.tagName === "TEXTAREA") {
      el.placeholder = t(key);
    } else {
      el.textContent = t(key);
    }
  });
  document.querySelectorAll("[data-i18n-title]").forEach((el) => {
    el.title = t(el.getAttribute("data-i18n-title"));
  });
}

// Export to global scope
window.I18N = I18N;
window.t = t;
window.setLanguage = setLanguage;
window.applyTranslations = applyTranslations;
window.getLang = function() { return currentLang; };
