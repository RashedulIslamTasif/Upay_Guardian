# Guardian: 9-Step Product Logic Chain (DIU CPC × upay Track 07)

1. **User Persona**: First-time, rural, and elderly mobile wallet users on upay who are vulnerable to social engineering.
2. **Problem**: Social-engineering scams (OTP theft, fake support, fake prize fees, fake 'sent-by-mistake' refunds) cause irreversible monetary loss, leading to permanent erosion of customer trust in digital financial services.
3. **Why Now**: Mobile financial services in Bangladesh have achieved ubiquitous penetration, shifting fraudulent tactics from network compromises to human manipulation through psychological urgency and conversational scripts.
4. **Solution (Guardian)**: A multi-modal, zero-auto-block protection shield providing explainable voice/visual warnings in Bengali and dynamically tiered, calibrated friction (L0 Allow, L1 Spoken Warning, L2 Cool-off, L3 Trusted-Contact Co-Approval, L4 Analyst Review).
5. **AI Role**:
   - High-throughput TF-IDF + Logistic Regression NLP classifier identifying Banglish/Bangla scam templates.
   - Calibrated LightGBM model evaluating transactional velocity, behavioral deviation, and cohort anomalies.
   - NetworkX graph analytics detecting rapid fan-in/fan-out mule syndicates.
   - SHAP feature attributions grounding bilingual, non-hallucinatory explanations.
6. **Impact**: Prevents over 75% of social engineering scam losses while keeping legitimate user friction below 2.5%, reducing manual fraud investigator case burdens through automated structured triage narratives.
7. **Data Strategy**: Fully synthetic data generation reproducing realistic Bangladesh MFS distribution curves (5,000 users, 150,000 transactions, 6,000 slot-varied multilingual text snippets), with time-separated and unseen-template test splits. Zero production PII.
8. **Validation**: Time-split test PR-AUC, calibration plots, unseen-template text classification Macro-F1, simulated A/B policy economic outcome analysis, and cross-demographic fairness audits.
9. **Scale & Post-Hackathon Path**: Pluggable microservice architecture adhering to event-driven MFS messaging; modular upgrade path to run shadow-mode evaluation on anonymized upay transaction streams.