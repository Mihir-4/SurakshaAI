# SurakshaAI Dataset Quality Audit

Audit date: 2026-08-09

## Verdict

The downloaded datasets are usable for SurakshaAI, but the current processed text corpus is not yet perfectly aligned with the project goal.

It is strong for:
- General phishing and spam detection
- Email phishing language
- SMS smishing patterns
- Binary safe/fraud classification
- URL malicious/benign classification

It is weak for:
- Indian banking notification coverage
- UPI scam text coverage
- Loan scam coverage
- WhatsApp conversational scam coverage
- Regional Indian language coverage

## Raw Dataset Audit

| Dataset group | Rows | Label status | Fit for project |
|---|---:|---|---|
| financial_scams | 523 | scam/ham | Very relevant but small |
| sms_phishing | 5,971 | ham/spam/smishing | Highly relevant |
| sms_spam | 5,572 | ham/spam | Useful baseline, not finance-specific |
| phishing_email | 164,972 total | 0/1 labels | Useful but too dominant if not capped |
| indian_banking_sms | 100,243 | no label | Useful for unlabeled EDA/context, not supervised training |
| manual_banking | 1,000 | safe/fraud | Highly relevant but synthetic |
| manual_loan | 960 | safe/fraud | Highly relevant but many duplicates after cleaning |
| manual_whatsapp | 780 | safe/fraud | Relevant but still small after dedup |
| urls | 651,191 | benign/defacement/phishing/malware | Good for URL model |
| upi | 5,000 | synthetic | Pipeline sanity check, too easy for final claims |

## Processed Text Split Audit

Total processed text rows: 19,392

Label balance:
- Safe: 57.39%
- Fraud: 42.61%

Source balance:
- phishing_email: 60.01%
- sms_phishing: 29.62%
- sms_spam: 3.74%
- manual_banking: 2.94%
- financial_scams: 2.68%
- manual_whatsapp: 0.91%
- manual_loan: 0.11%

Channel balance:
- Email: 60.01%
- SMS-like/banking/WhatsApp/loan: 39.99%

Manual data share:
- 3.96% of processed corpus

## Main Issue

The raw manual datasets were expanded to thousands of rows, but the processed split keeps far fewer manual records because many generated variants become identical after cleaning/tokenization.

Example: amounts, URLs, OTPs, and account fragments are replaced with standard tokens. This is good for privacy and generalization, but it also collapses many template variants into duplicate cleaned text.

Because deduplication removes duplicate cleaned messages, `manual_loan` becomes only 0.11% of the final processed corpus. That is too low for a project where loan scams are a target use case.

## Does It Satisfy The Project Need?

Partially.

For a first working model, yes. The corpus is large enough, labels are binary, splits exist, and classical ML results are strong.

For a final capstone-quality SurakshaAI model, not fully. The model may over-learn email phishing and under-learn Indian rural financial scam patterns unless the manual and India-specific datasets are strengthened.

## Recommended Fixes Before Final Kaggle DL Training

1. Reduce email dominance further.
   Suggested cap: 8,000 to 10,000 email rows.

2. Add more unique manual templates, not just more variable substitutions.
   More template sentences matter more than more fake amounts/URLs, because those values are tokenized.

3. Keep manual data train-only.
   Manual synthetic records are useful for teaching patterns, but validation/test should ideally stay closer to public/original records.

4. Create a separate gold benchmark.
   Use 200 to 500 carefully written Indian banking, UPI, loan, WhatsApp, and safe notification examples. Do not train on it.

5. Treat UPI model metrics carefully.
   Current UPI result is 1.0 because the synthetic data is too separable. It proves the pipeline works, not real-world robustness.

## Best Current Use

Use the current processed text dataset for:
- Classical ML baseline
- DistilBERT/mBERT/IndicBERT first training
- Pipeline demonstration

Before final report claims, improve:
- manual loan examples
- manual WhatsApp examples
- Indian banking safe examples
- multilingual/regional examples
- gold benchmark evaluation

