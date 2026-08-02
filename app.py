from flask import Flask, render_template, request, jsonify
import pickle
import numpy as np
import json
import os
import json
import urllib.request
import re
from database import init_db, get_db
import sqlite3
from datetime import datetime
app = Flask(__name__)
DATABASE = "community.db"

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():

    conn = get_db()

    conn.execute("""
    CREATE TABLE IF NOT EXISTS posts(

        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        text TEXT NOT NULL,
        image TEXT,
        created_at TEXT

    )
    """)

    conn.commit()
    conn.close()


init_db()

# ─────────────────────────────────────────
# LOAD MODELS
# ─────────────────────────────────────────
crop_model = pickle.load(open("models/crop_model.pkl", "rb"))
production_model = pickle.load(open("models/production_model.pkl", "rb"))

le_state = pickle.load(open("models/le_state.pkl", "rb"))
le_district = pickle.load(open("models/le_district.pkl", "rb"))
le_season = pickle.load(open("models/le_season.pkl", "rb"))
le_crop = pickle.load(open("models/le_crop.pkl", "rb"))

# Dictionary
CHAT_KB = {
    # ───────────────────────────────
    # SMALL TALK / GREETINGS
    # ───────────────────────────────
    "hello|hi|hey|namaste|namaskar|good morning|good evening|good afternoon|yo|sup": {
        "response": "🌱 <b>Namaste!</b> I'm AgroBot, your farming assistant.<br><br>I can help you with:<br>• 🌾 Crop selection & cultivation<br>• 💧 Irrigation & water management<br>• 🌿 Fertilizers & soil health<br>• 💰 MSP prices & market info<br>• 🏛️ Government schemes & subsidies<br>• 🐛 Pest & disease control<br><br>What would you like to know?",
        "followups": ["Best crop for my region?", "Current MSP rates?", "Govt schemes for farmers?"]
    },
    "how are you|how r u|whats up|what's up|how is it going|how are things": {
        "response": "😊 I'm doing great, ready to talk farming! How's your field/season going?<br><br>Ask me anything about crops, water, fertilizer, schemes, or market prices.",
        "followups": ["Best crop for Kharif?", "MSP rates today?", "Fertilizer tips"]
    },
    "who are you|what are you|your name|about you|what can you do|help|menu|options|what do you know": {
        "response": "🤖 I'm <b>AgroBot</b> — a farming assistant built to help with crop planning.<br><br>📋 <b>Topics I know:</b><br>• Crop info (rice, wheat, cotton, maize, sugarcane, pulses, vegetables...)<br>• Irrigation & water needs<br>• Fertilizer guidance<br>• Soil types & testing<br>• Pest & disease control<br>• MSP & market prices<br>• Government schemes (PM-KISAN, KCC, PMFBY, PMKSY, e-NAM)<br>• Seasons (Kharif/Rabi/Zaid)<br>• Crop rotation & intercropping<br>• Storage & post-harvest<br><br>Just ask naturally, like you'd ask a friend!",
        "followups": ["Best crop for Kharif?", "MSP rates today?", "Govt schemes list"]
    },
    "bye|goodbye|see you|see ya|tata|alvida|exit|quit|close chat": {
        "response": "👋 Take care, and good luck with your harvest! Come back anytime you have farming questions.<br><br>🌾 <i>\"Jai Kisan!\"</i>",
        "followups": ["Ask about fertilizers", "Check MSP rates", "Irrigation methods"]
    },
    "thank|thanks|thank you|dhanyawad|धन्यवाद|shukriya|great|awesome|helpful|nice|good bot|well done": {
        "response": "🙏 Happy to help! Feel free to ask anything about farming anytime.<br><br>🌾 <i>\"Jai Kisan!\"</i>",
        "followups": ["Ask about fertilizers", "Check MSP rates", "Irrigation methods"]
    },
    "you are wrong|that's wrong|incorrect|not helpful|useless|bad answer|doesn't make sense": {
        "response": "😅 Sorry about that! I work off a fixed knowledge base so I can sometimes miss the mark. Try rephrasing your question, or ask about a specific crop, scheme, or practice and I'll do my best.",
        "followups": ["Best Kharif crops?", "Fertilizer for wheat?", "Govt schemes list"]
    },

    # ───────────────────────────────
    # WATER / IRRIGATION
    # ───────────────────────────────
    "water|irrigation|drip|sprinkler|moisture|watering|water requirement|how much water": {
        "response": "💧 <b>Water Requirements by Crop:</b><br>• Rice — Very High (flooding needed)<br>• Wheat — Medium (3-4 irrigations)<br>• Cotton — High (drip irrigation best)<br>• Maize — Medium (critical at flowering)<br>• Sugarcane — Very High (furrow/drip)<br>• Pulses (gram/moong/urad) — Low<br><br>💡 Tip: Drip irrigation saves 40-50% water vs flood irrigation.",
        "followups": ["Which crop needs least water?", "How does drip irrigation work?", "Best season for wheat?"]
    },
    "drip irrigation|how does drip|micro irrigation": {
        "response": "💧 <b>Drip Irrigation</b> delivers water directly to roots via pipes & emitters.<br><br>✅ Benefits:<br>• 40-50% water savings<br>• Fewer weeds<br>• Less disease<br>• Higher yield<br><br>🏛️ Govt subsidy available under PMKSY scheme — up to 55% for small farmers!",
        "followups": ["Tell me about PMKSY", "What crops suit drip irrigation?"]
    },
    "sprinkler|sprinkler irrigation": {
        "response": "💦 <b>Sprinkler Irrigation</b> mimics rainfall, spraying water over crops through pressurized nozzles.<br><br>✅ Best for: Wheat, groundnut, vegetables, and undulating land unsuitable for flood irrigation.<br>✅ Saves 30-35% water vs flood irrigation.<br><br>🏛️ Subsidy up to 55% under PMKSY for small/marginal farmers.",
        "followups": ["Drip vs sprinkler?", "PMKSY subsidy details"]
    },
    "drought|water scarcity|less rain|no rain|dry spell": {
        "response": "🏜️ <b>Managing Drought / Water Scarcity:</b><br>• Switch to drought-tolerant crops: Bajra, Jowar, Moong, Groundnut<br>• Use mulching to retain soil moisture<br>• Adopt drip irrigation to cut water use by 40-50%<br>• Practice deficit irrigation at non-critical growth stages<br><br>🛡️ Consider PMFBY crop insurance to cover drought-related losses.",
        "followups": ["Drought resistant crops?", "PMFBY details"]
    },

    # ───────────────────────────────
    # FERTILIZER
    # ───────────────────────────────
    "fertilizer|urea|npk|dap|potash|nutrient|manure|compost|fertilizer dose|how much fertilizer": {
        "response": "🌿 <b>Fertilizer Guide:</b><br>• <b>Urea (46-0-0)</b> — Nitrogen boost, supports leafy growth<br>• <b>DAP (18-46-0)</b> — Phosphorus, useful for root and seed development<br>• <b>MOP/Potash</b> — Improves crop strength, quality, and disease resistance<br>• <b>NPK 20-20-20</b> — Balanced fertilizer for general crop support<br><br>🧪 <b>Fertilizer Levels in this system:</b><br>• <b>Low</b> — lower nutrient demand<br>• <b>Medium</b> — moderate balanced demand<br>• <b>High</b> — higher nutrient requirement<br><br>💡 Soil test first. Exact fertilizer dosage depends on soil condition, crop stage, and local climate.",
        "followups": ["What is low fertilizer?", "What is medium fertilizer?", "What is high fertilizer?"]
    },
    "organic|compost|vermi|bio.fertilizer|natural fertilizer|organic farming": {
        "response": "🌱 <b>Organic Fertilizer Options:</b><br>• <b>Vermicompost</b> — Best all-rounder, 2-3 tons/acre<br>• <b>FYM (Farm Yard Manure)</b> — Apply 4-6 weeks before sowing<br>• <b>Green Manure</b> — Dhaincha/Sunhemp before Kharif<br>• <b>Biofertilizers</b> — Rhizobium for legumes, Azospirillum for cereals<br><br>✅ Organic farming gets 20-50% premium price in market!",
        "followups": ["How to make vermicompost?", "Which crops get organic premium?", "Organic certification process?"]
    },
    "organic certification|pgs.india|jaivik bharat": {
        "response": "📜 <b>Organic Certification in India:</b><br>• <b>PGS-India</b> — Peer-verified, low-cost, good for small farmers<br>• <b>NPOP (National Programme for Organic Production)</b> — Needed for export<br>• Conversion period: 2-3 years of organic practice before certification<br><br>💡 Certified organic produce can fetch 20-50% higher prices.",
        "followups": ["Organic fertilizer options?", "Which crops get organic premium?"]
    },
    "low fertilizer|what is low fertilizer|meaning of low fertilizer|fertilizer low": {
        "response": "🌿 <b>Low Fertilizer Requirement</b><br>This means the crop usually needs a smaller amount of nutrient input compared to heavy-feeding crops.<br><br>✅ Suitable when:<br>• Soil is already reasonably fertile<br>• Farmer wants lower input cost<br>• Low-maintenance crop planning is preferred<br><br>💡 In this system, low fertilizer crops are generally easier to manage and cheaper to cultivate.",
        "followups": ["What is medium fertilizer?", "Which crops need high fertilizer?"]
    },
    "medium fertilizer|what is medium fertilizer|meaning of medium fertilizer|fertilizer medium": {
        "response": "🌾 <b>Medium Fertilizer Requirement</b><br>This means the crop needs a balanced and moderate nutrient supply.<br><br>✅ Usually requires:<br>• Regular but controlled fertilizer use<br>• Basic nitrogen, phosphorus, and potassium management<br>• Monitoring during growth stages<br><br>💡 In this project, medium fertilizer crops are considered balanced in input cost and crop performance.",
        "followups": ["What is low fertilizer?", "What is high fertilizer?"]
    },
    "high fertilizer|what is high fertilizer|meaning of high fertilizer|fertilizer high": {
        "response": "⚠️ <b>High Fertilizer Requirement</b><br>This means the crop generally needs more nutrient support for better yield.<br><br>✅ Common in:<br>• High-yield crops<br>• Long-duration crops<br>• Commercial crops with greater nutrient demand<br><br>💡 These crops may give good output, but input cost is usually higher and nutrient management becomes more important.",
        "followups": ["Which crops need high fertilizer?", "How to reduce fertilizer cost?"]
    },
    "fertilizer level|fertilizer requirement level|what does fertilizer level mean": {
        "response": "🧪 <b>Fertilizer Level in this Project</b><br>The fertilizer label (Low / Medium / High) is used as an advisory indicator.<br><br>• <b>Low</b> → lower nutrient input needed<br>• <b>Medium</b> → balanced nutrient input needed<br>• <b>High</b> → greater nutrient input needed<br><br>💡 It helps farmers understand approximate crop input demand, but exact fertilizer dosage should still depend on soil testing and local conditions.",
        "followups": ["What is low fertilizer?", "What is medium fertilizer?", "What is high fertilizer?"]
    },

    # ───────────────────────────────
    # PROFIT / PRICE / MARKET
    # ───────────────────────────────
    "profit|income|earn|money|price|msp|market|sell|revenue|most profitable": {
        "response": "💰 <b>Most Profitable Crops (2025-26):</b><br>• <b>Cotton</b> — MSP ₹7,121/quintal, high demand<br>• <b>Wheat</b> — MSP ₹2,425/quintal, guaranteed purchase<br>• <b>Sugarcane</b> — FRP ₹340/quintal, stable income<br>• <b>Vegetables</b> — Tomato/Onion can give 3-5x returns<br><br>📈 Tip: Join FPOs (Farmer Producer Orgs) for 15-20% better prices!",
        "followups": ["What is MSP?", "How to join FPO?", "Best crop for small land?"]
    },
    "msp|minimum support price": {
        "response": "📊 <b>MSP 2025-26 Key Rates:</b><br>• Wheat — ₹2,425/quintal<br>• Rice (Common) — ₹2,300/quintal<br>• Cotton (Medium) — ₹7,121/quintal<br>• Maize — ₹2,225/quintal<br>• Soybean — ₹4,892/quintal<br>• Gram (Chana) — ₹5,650/quintal<br>• Mustard — ₹5,950/quintal<br><br>🏛️ MSP is declared by Cabinet Committee on Economic Affairs (CCEA). Sell at APMC mandi or e-NAM portal for best rates.",
        "followups": ["What is e-NAM?", "How to sell at mandi?"]
    },
    "e.nam|enam|online mandi|sell at mandi|apmc": {
        "response": "🖥️ <b>e-NAM (National Agriculture Market):</b><br>• Online trading platform linking 1,000+ mandis across India<br>• Farmers can get quotes from multiple buyers, not just local traders<br>• Registration free at nearest APMC or via enam.gov.in<br><br>💡 Typically gives 15-20% better price discovery than local-only sale.",
        "followups": ["What is MSP?", "How to join FPO?"]
    },
    "fpo|farmer producer organization|join fpo": {
        "response": "🤝 <b>FPO (Farmer Producer Organisation):</b><br>• Group of farmers pooling produce for better bargaining power<br>• Access to bulk input discounts, shared machinery, and better market prices<br>• Govt gives financial support up to ₹18 lakh per FPO under the 10,000 FPO scheme<br><br>📞 Contact your nearest NABARD office or Krishi Vigyan Kendra (KVK) to join or start one.",
        "followups": ["Most profitable crops?", "Govt schemes list"]
    },

    # ───────────────────────────────
    # RISK / INSURANCE
    # ───────────────────────────────
    "risk|insurance|loss|flood|disaster|fasal bima|pmfby|crop insurance": {
        "response": "⚠️ <b>Crop Risk Management:</b><br>• <b>Low Risk</b>: Rice, Wheat, Pulses<br>• <b>Medium Risk</b>: Maize, Sugarcane<br>• <b>High Risk</b>: Cotton, Vegetables<br><br>🛡️ <b>PMFBY (Pradhan Mantri Fasal Bima Yojana)</b>:<br>• Premium: only 2% for Kharif, 1.5% for Rabi<br>• Covers drought, flood, pest, post-harvest losses<br>• Enroll at nearest bank or CSC center before sowing!",
        "followups": ["How to claim PMFBY?", "Which crops are high risk?"]
    },
    "claim pmfby|how to claim insurance|crop damage claim": {
        "response": "📝 <b>Claiming PMFBY Insurance:</b><br>1. Report crop loss within 72 hours via app/helpline/bank<br>2. Local agriculture officer conducts loss assessment (CCE survey)<br>3. Claim amount credited directly to your bank account<br><br>📞 Toll-free: 14447, or use the 'Crop Insurance' app.",
        "followups": ["What does PMFBY cover?", "PMFBY premium rates?"]
    },

    # ───────────────────────────────
    # SEASON / TIMING
    # ───────────────────────────────
    "season|kharif|rabi|zaid|when to sow|sowing time|planting time|best time to plant": {
        "response": "📅 <b>Indian Crop Seasons:</b><br><br>🌧️ <b>Kharif (June–October)</b>:<br>Rice, Cotton, Maize, Bajra, Soybean, Groundnut<br><br>❄️ <b>Rabi (November–March)</b>:<br>Wheat, Mustard, Gram, Peas, Barley<br><br>☀️ <b>Zaid (March–June)</b>:<br>Watermelon, Cucumber, Moong, Vegetables<br><br>💡 Sow within first 2 weeks of season for best yield!",
        "followups": ["Best Kharif crop for Maharashtra?", "Rabi crop for UP?"]
    },
    "crop rotation|rotate crops|intercropping|mixed cropping": {
        "response": "🔄 <b>Crop Rotation & Intercropping:</b><br>• Rotate cereals with legumes (e.g., Rice → Gram) to restore soil nitrogen<br>• Avoid growing the same crop repeatedly — reduces pest/disease buildup<br>• Intercropping (e.g., Cotton + Moong) improves land-use efficiency and gives an extra harvest<br><br>💡 A good rule: 1 cereal season followed by 1 legume/pulse season.",
        "followups": ["Best combo crop for my crop?", "Benefits of pulses in rotation?"]
    },

    # ───────────────────────────────
    # SOIL
    # ───────────────────────────────
    "soil|ph|sandy|clay|loam|black soil|red soil|alluvial|soil test|soil health": {
        "response": "🪱 <b>Soil Types & Best Crops:</b><br>• <b>Black (Regur)</b> — Cotton, Soybean, Wheat (Maharashtra, MP)<br>• <b>Alluvial</b> — Rice, Wheat, Sugarcane (Punjab, UP, Bihar)<br>• <b>Red Laterite</b> — Groundnut, Millets (Tamil Nadu, Odisha)<br>• <b>Sandy Loam</b> — Vegetables, Potato, Carrot<br><br>🧪 Ideal pH: 6.0–7.5 for most crops. Free soil testing at KVK centers!",
        "followups": ["How to improve soil health?", "What is soil pH?", "Where to get soil tested?"]
    },
    "improve soil|soil health card|soil fertility": {
        "response": "🌍 <b>Improving Soil Health:</b><br>• Get a free <b>Soil Health Card</b> from your local agriculture office (shows N-P-K & pH)<br>• Add organic matter (FYM/compost) every season<br>• Rotate with legumes to fix nitrogen naturally<br>• Avoid over-tilling — it degrades soil structure<br><br>🏛️ Apply for Soil Health Card at soilhealth.dac.gov.in",
        "followups": ["Soil types & crops?", "Organic fertilizer options?"]
    },

    # ───────────────────────────────
    # PEST / DISEASE
    # ───────────────────────────────
    "pest|insect|disease|fungus|blight|wilt|aphid|whitefly|spray|pesticide|bollworm|stem borer": {
        "response": "🐛 <b>Common Pest Management:</b><br>• <b>Aphids/Whitefly</b> — Neem oil spray (5ml/L water)<br>• <b>Stem Borer (Rice)</b> — Cartap Hydrochloride 50SP<br>• <b>Bollworm (Cotton)</b> — Bt cotton + Spinosad spray<br>• <b>Leaf Blight (Wheat)</b> — Propiconazole fungicide<br><br>💡 IPM (Integrated Pest Management) reduces chemical use by 60% and saves cost!",
        "followups": ["Natural pest control methods?", "Neem spray preparation?", "What is IPM?"]
    },
    "ipm|integrated pest management|natural pest control|neem spray": {
        "response": "🌿 <b>IPM (Integrated Pest Management):</b><br>• Combines biological, cultural, and minimal chemical control<br>• Use pheromone traps, yellow sticky traps for early detection<br>• Neem oil spray: mix 5ml neem oil + 1L water + few drops soap, spray weekly<br>• Encourage natural predators (ladybugs for aphids)<br><br>✅ Cuts pesticide cost by up to 60% while protecting yield.",
        "followups": ["Common pests by crop?", "Pheromone trap details?"]
    },

    # ───────────────────────────────
    # GOVERNMENT SCHEMES
    # ───────────────────────────────
    "scheme|government|subsidy|pm.kisan|kisan|loan|credit|yojana|govt help": {
        "response": "🏛️ <b>Key Govt Schemes for Farmers:</b><br>• <b>PM-KISAN</b> — ₹6,000/year direct to bank (3 installments)<br>• <b>KCC (Kisan Credit Card)</b> — Crop loan at 4% interest<br>• <b>PMFBY</b> — Crop insurance at 1.5-2% premium<br>• <b>PMKSY</b> — Drip/sprinkler irrigation subsidy (55-75%)<br>• <b>e-NAM</b> — Online mandi for better crop prices<br><br>📱 Apply at pmkisan.gov.in or nearest CSC center.",
        "followups": ["How to apply for PM-KISAN?", "What is KCC loan?", "e-NAM registration?"]
    },
    "pm.kisan|pmkisan": {
        "response": "🏛️ <b>PM-KISAN Scheme:</b><br>• ₹6,000/year in 3 equal installments of ₹2,000<br>• Directly transferred to bank account<br>• All landholding farmers eligible<br><br>📋 <b>How to apply:</b><br>1. Visit pmkisan.gov.in<br>2. Click 'New Farmer Registration'<br>3. Enter Aadhaar + land details<br>4. Verify via OTP<br><br>✅ Check status at pmkisan.gov.in/beneficiarystatus",
        "followups": ["KCC loan details?", "Other farmer schemes?"]
    },
    "kcc|kisan credit card|crop loan": {
        "response": "💳 <b>Kisan Credit Card (KCC):</b><br>• Short-term crop loans at just 4% interest (with timely repayment subsidy)<br>• Loan limit based on land holding & crop type<br>• Can also cover post-harvest and farm asset needs<br><br>📋 Apply at any nationalised bank/RRB/cooperative bank with land records + Aadhaar.",
        "followups": ["PM-KISAN details?", "PMFBY insurance details?"]
    },

    # ───────────────────────────────
    # SPECIFIC CROPS
    # ───────────────────────────────
    "rice|paddy|dhan": {
        "response": "🌾 <b>Rice Cultivation Guide:</b><br>• <b>Season</b>: Kharif (June–Nov), also Rabi in South India<br>• <b>Water</b>: High — 1,200-2,000mm or flood irrigation<br>• <b>Fertilizer</b>: Urea 120kg + DAP 60kg + MOP 40kg per acre<br>• <b>Yield</b>: 20-35 quintals/acre<br>• <b>MSP 2025</b>: ₹2,300/quintal<br><br>💡 SRI (System of Rice Intensification) can boost yield by 20-50%!",
        "followups": ["Rice pest control?", "Best rice variety?", "SRI method details?"]
    },
    "wheat|gehu": {
        "response": "🌾 <b>Wheat Cultivation Guide:</b><br>• <b>Season</b>: Rabi — Sow Nov 1-25, Harvest Mar-Apr<br>• <b>Water</b>: 4-6 irrigations (critical: CRI, tillering, jointing stages)<br>• <b>Fertilizer</b>: NPK 120:60:40 kg/acre<br>• <b>Best varieties</b>: HD-3226, DBW-187, GW-496<br>• <b>MSP 2025</b>: ₹2,425/quintal<br><br>💡 Timely sowing (Nov 1-15) gives 10-15% higher yield vs late sowing!",
        "followups": ["Wheat disease management?", "Wheat storage tips?"]
    },
    "cotton|kapas": {
        "response": "🌿 <b>Cotton Cultivation Guide:</b><br>• <b>Season</b>: Kharif — Sow April-June, Harvest Oct-Feb<br>• <b>Water</b>: High — drip irrigation best (saves 30%)<br>• <b>Fertilizer</b>: DAP 50kg + Urea 100kg + MOP 50kg per acre<br>• <b>Yield</b>: 8-15 quintals/acre (Bt cotton)<br>• <b>MSP 2025</b>: ₹7,121/quintal<br><br>⚠️ Pink bollworm is major threat — use pheromone traps + Bt spray.",
        "followups": ["Cotton pest management?", "Best cotton variety?"]
    },
    "maize|corn|makka": {
        "response": "🌽 <b>Maize Cultivation Guide:</b><br>• <b>Season</b>: Kharif (June-July) & Rabi (Oct-Nov)<br>• <b>Water</b>: Medium — critical at tasseling/silking stage<br>• <b>Fertilizer</b>: NPK 120:60:40 kg/acre<br>• <b>Yield</b>: 25-30 quintals/acre<br>• <b>MSP 2025</b>: ₹2,225/quintal<br><br>💡 Maize is highly versatile — used for food, feed, and ethanol.",
        "followups": ["Maize pest control?", "Best maize hybrid?"]
    },
    "sugarcane|ganna": {
        "response": "🎋 <b>Sugarcane Cultivation Guide:</b><br>• <b>Season</b>: Year-round planting, 10-12 month crop<br>• <b>Water</b>: Very High — furrow or drip irrigation<br>• <b>Fertilizer</b>: NPK 250:115:115 kg/acre (split doses)<br>• <b>Yield</b>: 350-450 quintals/acre<br>• <b>FRP 2025</b>: ₹340/quintal<br><br>💡 Drip irrigation in sugarcane can boost yield by 20-30% while saving water.",
        "followups": ["Sugarcane pest control?", "Best sugarcane variety?"]
    },
    "soybean|soya": {
        "response": "🫘 <b>Soybean Cultivation Guide:</b><br>• <b>Season</b>: Kharif — Sow June-July<br>• <b>Water</b>: Medium — rainfed suitable, avoid waterlogging<br>• <b>Fertilizer</b>: DAP 40kg + MOP 20kg per acre (low nitrogen needed, fixes its own)<br>• <b>Yield</b>: 8-12 quintals/acre<br>• <b>MSP 2025</b>: ₹4,892/quintal<br><br>💡 Great rotation crop — improves soil nitrogen for the next crop.",
        "followups": ["Soybean pest control?", "Best soybean variety?"]
    },
    "groundnut|peanut|moongfali": {
        "response": "🥜 <b>Groundnut Cultivation Guide:</b><br>• <b>Season</b>: Kharif & summer (Zaid)<br>• <b>Water</b>: Low-Medium — drought tolerant<br>• <b>Fertilizer</b>: Gypsum at flowering is critical, low nitrogen needed<br>• <b>Yield</b>: 10-15 quintals/acre<br><br>💡 Suits sandy/red laterite soils well; good for dryland farming.",
        "followups": ["Best soil for groundnut?", "Groundnut pest control?"]
    },
    "gram|chana|chickpea": {
        "response": "🫛 <b>Gram (Chana) Cultivation Guide:</b><br>• <b>Season</b>: Rabi — Sow Oct-Nov<br>• <b>Water</b>: Low — 1-2 irrigations sufficient<br>• <b>Fertilizer</b>: Low nitrogen needed (nitrogen-fixing legume), DAP 25kg/acre<br>• <b>Yield</b>: 6-10 quintals/acre<br>• <b>MSP 2025</b>: ₹5,650/quintal<br><br>💡 Great for crop rotation after rice/maize — restores soil nitrogen.",
        "followups": ["Gram pest control?", "Best gram variety?"]
    },
    "mustard|sarson|rai": {
        "response": "🌼 <b>Mustard Cultivation Guide:</b><br>• <b>Season</b>: Rabi — Sow mid-Oct to mid-Nov<br>• <b>Water</b>: Low-Medium — 2-3 irrigations<br>• <b>Fertilizer</b>: NPK 80:40:40 kg/acre<br>• <b>Yield</b>: 6-8 quintals/acre<br>• <b>MSP 2025</b>: ₹5,950/quintal<br><br>💡 Good oilseed option for Rabi with relatively low water needs.",
        "followups": ["Mustard pest control?", "Best mustard variety?"]
    },
    "bajra|pearl millet": {
        "response": "🌾 <b>Bajra (Pearl Millet) Cultivation Guide:</b><br>• <b>Season</b>: Kharif — Sow June-July<br>• <b>Water</b>: Low — highly drought-tolerant<br>• <b>Fertilizer</b>: NPK 40:20:20 kg/acre<br>• <b>Yield</b>: 8-12 quintals/acre<br><br>💡 Excellent choice for dry, low-rainfall regions.",
        "followups": ["Drought resistant crops?", "Bajra pest control?"]
    },
    "jowar|sorghum": {
        "response": "🌾 <b>Jowar (Sorghum) Cultivation Guide:</b><br>• <b>Season</b>: Kharif & Rabi both possible<br>• <b>Water</b>: Low-Medium — drought tolerant<br>• <b>Fertilizer</b>: NPK 80:40:40 kg/acre<br>• <b>Yield</b>: 10-15 quintals/acre<br><br>💡 Dual purpose — grain for food, stalks for fodder.",
        "followups": ["Drought resistant crops?", "Jowar pest control?"]
    },
    "pulses|moong|urad|arhar|lentil|dal": {
        "response": "🫘 <b>Pulses (Moong/Urad/Arhar) Cultivation Guide:</b><br>• <b>Season</b>: Moong/Urad — Kharif & Zaid; Arhar — Kharif (long duration)<br>• <b>Water</b>: Low — mostly rainfed<br>• <b>Fertilizer</b>: Minimal nitrogen needed — legumes fix their own<br>• <b>Yield</b>: 4-8 quintals/acre<br><br>💡 Excellent for crop rotation and improving soil fertility.",
        "followups": ["Best rotation with pulses?", "Pulses MSP rates?"]
    },
    "onion|pyaz": {
        "response": "🧅 <b>Onion Cultivation Guide:</b><br>• <b>Season</b>: Kharif, late-Kharif, and Rabi (3 crops possible)<br>• <b>Water</b>: Medium — frequent light irrigation, avoid waterlogging<br>• <b>Fertilizer</b>: NPK 100:50:50 kg/acre<br>• <b>Yield</b>: 80-120 quintals/acre<br><br>💡 Prices are highly volatile — consider storage to sell at better rates.",
        "followups": ["Onion storage tips?", "Onion pest control?"]
    },
    "tomato|tamatar": {
        "response": "🍅 <b>Tomato Cultivation Guide:</b><br>• <b>Season</b>: Year-round in most regions, best in Rabi/Zaid<br>• <b>Water</b>: Medium-High — drip irrigation ideal<br>• <b>Fertilizer</b>: NPK 120:60:60 kg/acre<br>• <b>Yield</b>: 150-250 quintals/acre<br><br>💡 High risk-reward crop — prices can be 3-5x in good market conditions.",
        "followups": ["Tomato pest control?", "Best tomato variety?"]
    },
    "potato|aloo": {
        "response": "🥔 <b>Potato Cultivation Guide:</b><br>• <b>Season</b>: Rabi — Sow Oct-Nov<br>• <b>Water</b>: Medium — frequent light irrigation<br>• <b>Fertilizer</b>: NPK 150:80:100 kg/acre<br>• <b>Yield</b>: 100-150 quintals/acre<br><br>💡 Needs cold storage access for best price realization post-harvest.",
        "followups": ["Potato storage tips?", "Potato pest control?"]
    },
    "brinjal|eggplant|baingan": {
        "response": "🍆 <b>Brinjal Cultivation Guide:</b><br>• <b>Season</b>: Year-round, best in Kharif/Rabi<br>• <b>Water</b>: Medium — regular irrigation needed<br>• <b>Fertilizer</b>: NPK 100:50:50 kg/acre<br>• <b>Yield</b>: 150-200 quintals/acre<br><br>⚠️ Watch for fruit and shoot borer — use pheromone traps.",
        "followups": ["Brinjal pest control?", "Vegetable market tips?"]
    },

    # ───────────────────────────────
    # STORAGE / POST-HARVEST / MACHINERY / LABOUR
    # ───────────────────────────────
    "storage|store crop|warehouse|cold storage|godown": {
        "response": "🏬 <b>Post-Harvest Storage Tips:</b><br>• Grains: dry to 12-14% moisture before storage to prevent fungus<br>• Use hermetic bags/silos to cut pest losses by up to 90%<br>• Perishables (onion, potato, tomato): use ventilated/cold storage<br><br>🏛️ Subsidy available for building on-farm storage under Agriculture Infrastructure Fund.",
        "followups": ["Onion storage tips?", "Govt schemes for storage?"]
    },
    "machinery|tractor|equipment|harvester|farm machinery": {
        "response": "🚜 <b>Farm Machinery Support:</b><br>• <b>Custom Hiring Centers (CHC)</b> — rent tractors/harvesters at subsidized rates<br>• <b>SMAM Scheme</b> — up to 50% subsidy on farm equipment<br>• Consider shared/cooperative ownership via FPOs to cut costs<br><br>📞 Contact your nearest Krishi Vigyan Kendra (KVK) for CHC locations.",
        "followups": ["FPO details?", "Govt schemes list"]
    },
    "labour|labor cost|farm workers|hired labour": {
        "response": "👷 <b>Managing Farm Labour Costs:</b><br>• Peak labour demand is at sowing, weeding, and harvest — plan ahead<br>• Mechanization (e.g., seed drills, harvesters) can cut labour needs by 30-40%<br>• MGNREGA convergence schemes can support farm-pond and land-development labour<br><br>💡 Group hiring through FPOs often reduces per-acre labour cost.",
        "followups": ["Farm machinery support?", "Reduce input cost?"]
    },

    # ───────────────────────────────
    # WEATHER / CLIMATE
    # ───────────────────────────────
    "weather|rain|temperature|heat|cold|frost|climate|monsoon": {
        "response": "🌤️ <b>Weather & Farming Tips:</b><br>• <b>Heat stress (>35°C)</b>: Irrigate in evening, use mulching<br>• <b>Heavy rain</b>: Ensure drainage, apply fungicide preventively<br>• <b>Frost warning</b>: Smoke fields, irrigate lightly before frost<br>• <b>Drought</b>: Switch to millets/pulses — more drought tolerant<br><br>📱 Check IMD Meghdoot app for 5-day agro-weather forecast free!",
        "followups": ["Drought resistant crops?", "IMD weather app?"]
    },
    "climate change|erratic weather|changing rainfall": {
        "response": "🌍 <b>Adapting to Climate Change:</b><br>• Diversify crops instead of relying on a single one<br>• Shift toward drought/heat-tolerant varieties (millets, pulses)<br>• Invest in water harvesting (farm ponds) for buffer irrigation<br>• Use weather-based advisories (IMD Meghdoot) to time operations<br><br>🛡️ PMFBY insurance helps cushion climate-related crop losses.",
        "followups": ["Drought resistant crops?", "PMFBY insurance details?"]
    },

    # ───────────────────────────────
    # EXPORT / DIVERSIFICATION
    # ───────────────────────────────
    "export|international market|apeda": {
        "response": "🚢 <b>Exporting Agricultural Produce:</b><br>• Register with <b>APEDA</b> for export of processed foods, fruits, and vegetables<br>• Basmati rice, spices, and mangoes are top Indian agri-export earners<br>• Quality certification (GlobalGAP, organic NPOP) boosts export value<br><br>📞 Contact APEDA regional office or your state export promotion cell.",
        "followups": ["Organic certification process?", "Most profitable crops?"]
    },
}
#─────────────────────────────────
# CROP INFO
# ─────────────────────────────────────────
CROP_INFO = {
    "Rice": {"water": "High", "profit": "Medium", "risk": "Low", "fertilizer": "Urea + DAP", "months": "June–Nov"},
    "Wheat": {"water": "Medium", "profit": "High", "risk": "Low", "fertilizer": "NPK 20-20-0", "months": "Nov–Mar"},
    "Maize": {"water": "Medium", "profit": "Medium", "risk": "Medium", "fertilizer": "Urea + Potash", "months": "June–Sept"},
    "Cotton": {"water": "High", "profit": "High", "risk": "High", "fertilizer": "DAP + MOP", "months": "April–Oct"},
    "Sugarcane": {"water": "Very High", "profit": "High", "risk": "Medium", "fertilizer": "Urea + SSP", "months": "Year-round"}
}

# ─────────────────────────────────────────
# PLANTING GUIDE DATABASE (all 105 crops)
# ─────────────────────────────────────────
PLANTING_GUIDE = {
    "Rice": {
        "plants_per_ha": 333333, "spacing": "30cm × 10cm (transplanted)",
        "water_mm": "1200–2000 mm", "fertilizer": "NPK 120:60:40 kg/ha",
        "method": "Transplant 25-day seedlings or direct seed"
    },
    "Paddy": {
        "plants_per_ha": 333333, "spacing": "30cm × 10cm",
        "water_mm": "1200–2000 mm", "fertilizer": "NPK 120:60:40 kg/ha",
        "method": "Transplant or direct seeding in flooded fields"
    },
    "Wheat": {
        "plants_per_ha": 4000000, "spacing": "22cm rows, 5cm apart",
        "water_mm": "450–650 mm", "fertilizer": "NPK 120:60:40 kg/ha",
        "method": "Drill sowing, 100–125 kg seed/ha"
    },
    "Maize": {
        "plants_per_ha": 55556, "spacing": "60cm × 30cm",
        "water_mm": "500–800 mm", "fertilizer": "NPK 150:75:40 kg/ha",
        "method": "Sow 2 seeds/hole, thin to 1 plant"
    },
    "Banana": {
        "plants_per_ha": 3086, "spacing": "1.8m × 1.8m",
        "water_mm": "1800–2500 mm", "fertilizer": "NPK 200:60:200 kg/ha",
        "method": "Plant tissue-culture or sword suckers"
    },
    "Sugarcane": {
        "plants_per_ha": 40000, "spacing": "90cm × 30cm",
        "water_mm": "1500–2500 mm", "fertilizer": "NPK 250:60:120 kg/ha",
        "method": "Plant 3-eye setts, 35–40 quintals/ha"
    },
    "Cotton(lint)": {
        "plants_per_ha": 11111, "spacing": "90cm × 60cm (Bt cotton)",
        "water_mm": "700–1200 mm", "fertilizer": "NPK 120:60:60 kg/ha",
        "method": "Sow 2 seeds/hole at 3–4 cm depth, thin to 1"
    },
    "Kapas": {
        "plants_per_ha": 11111, "spacing": "90cm × 60cm",
        "water_mm": "700–1200 mm", "fertilizer": "NPK 120:60:60 kg/ha",
        "method": "Same as Cotton(lint) — desi variety"
    },
    "Groundnut": {
        "plants_per_ha": 100000, "spacing": "30cm × 10cm",
        "water_mm": "500–700 mm", "fertilizer": "NPK 20:60:40 kg/ha",
        "method": "Shell pods just before sowing, 80–100 kg pods/ha"
    },
    "Soyabean": {
        "plants_per_ha": 444444, "spacing": "45cm × 5cm",
        "water_mm": "450–700 mm", "fertilizer": "NPK 30:60:40 kg/ha",
        "method": "Treat seed with Rhizobium culture, 65–70 kg seed/ha"
    },
    "Sunflower": {
        "plants_per_ha": 55556, "spacing": "60cm × 30cm",
        "water_mm": "600–1000 mm", "fertilizer": "NPK 90:60:30 kg/ha",
        "method": "Sow 2 seeds/hole, thin to 1, 5 kg hybrid seed/ha"
    },
    "Coconut": {
        "plants_per_ha": 178, "spacing": "7.5m × 7.5m (triangular)",
        "water_mm": "1300–2300 mm", "fertilizer": "NPK 1000:500:1500 g/palm/yr",
        "method": "Plant 9-month nursery seedlings in pits 1m × 1m × 1m"
    },
    "Arecanut": {
        "plants_per_ha": 2500, "spacing": "2.7m × 2.7m",
        "water_mm": "1500–4500 mm", "fertilizer": "NPK 100:40:140 g/palm/yr",
        "method": "Plant rooted seedlings 2 years old in pits"
    },
    "Arcanut (Processed)": {
        "plants_per_ha": 2500, "spacing": "2.7m × 2.7m",
        "water_mm": "1500–4500 mm", "fertilizer": "NPK 100:40:140 g/palm/yr",
        "method": "Same as Arecanut — processed form"
    },
    "Atcanut (Raw)": {
        "plants_per_ha": 2500, "spacing": "2.7m × 2.7m",
        "water_mm": "1500–4500 mm", "fertilizer": "NPK 100:40:140 g/palm/yr",
        "method": "Same as Arecanut — raw form"
    },
    "Cashewnut": {
        "plants_per_ha": 400, "spacing": "5m × 5m",
        "water_mm": "1000–2000 mm", "fertilizer": "NPK 300:125:300 g/tree/yr",
        "method": "Plant softwood grafts or air-layers in pits"
    },
    "Cashewnut Processed": {
        "plants_per_ha": 400, "spacing": "5m × 5m",
        "water_mm": "1000–2000 mm", "fertilizer": "NPK 300:125:300 g/tree/yr",
        "method": "Same as Cashewnut — processed form"
    },
    "Cashewnut Raw": {
        "plants_per_ha": 400, "spacing": "5m × 5m",
        "water_mm": "1000–2000 mm", "fertilizer": "NPK 300:125:300 g/tree/yr",
        "method": "Same as Cashewnut — raw form"
    },
    "Jute": {
        "plants_per_ha": 5000000, "spacing": "30cm rows, broadcast",
        "water_mm": "1000–2000 mm", "fertilizer": "NPK 60:30:30 kg/ha",
        "method": "Broadcast or line sow, 6–7 kg seed/ha"
    },
    "Jute & mesta": {
        "plants_per_ha": 5000000, "spacing": "30cm rows",
        "water_mm": "1000–2000 mm", "fertilizer": "NPK 60:30:30 kg/ha",
        "method": "Broadcast sow 6–7 kg seed/ha"
    },
    "Gram": {
        "plants_per_ha": 333333, "spacing": "30cm × 10cm",
        "water_mm": "300–400 mm", "fertilizer": "NPK 20:40:20 kg/ha",
        "method": "Treat with Rhizobium, sow 80–90 kg/ha"
    },
    "Lentil": {
        "plants_per_ha": 1000000, "spacing": "22cm × 5cm",
        "water_mm": "250–400 mm", "fertilizer": "NPK 20:40:20 kg/ha",
        "method": "Sow 30–35 kg seed/ha in rows"
    },
    "Blackgram": {
        "plants_per_ha": 333333, "spacing": "30cm × 10cm",
        "water_mm": "300–500 mm", "fertilizer": "NPK 20:40:20 kg/ha",
        "method": "Sow 15–20 kg seed/ha with Rhizobium"
    },
    "Moong(Green Gram)": {
        "plants_per_ha": 333333, "spacing": "30cm × 10cm",
        "water_mm": "300–500 mm", "fertilizer": "NPK 20:40:20 kg/ha",
        "method": "Sow 15–20 kg seed/ha with Rhizobium"
    },
    "Arhar/Tur": {
        "plants_per_ha": 44444, "spacing": "75cm × 30cm",
        "water_mm": "600–1000 mm", "fertilizer": "NPK 20:50:20 kg/ha",
        "method": "Sow 12–15 kg seed/ha with Rhizobium"
    },
    "Urad": {
        "plants_per_ha": 333333, "spacing": "30cm × 10cm",
        "water_mm": "300–500 mm", "fertilizer": "NPK 20:40:20 kg/ha",
        "method": "Sow 15–20 kg seed/ha"
    },
    "Jowar": {
        "plants_per_ha": 180000, "spacing": "45cm × 12cm",
        "water_mm": "400–600 mm", "fertilizer": "NPK 80:40:40 kg/ha",
        "method": "Sow 10–12 kg seed/ha in rows"
    },
    "Bajra": {
        "plants_per_ha": 133333, "spacing": "50cm × 15cm",
        "water_mm": "300–500 mm", "fertilizer": "NPK 80:40:40 kg/ha",
        "method": "Sow 4–5 kg hybrid seed/ha"
    },
    "Ragi": {
        "plants_per_ha": 250000, "spacing": "30cm × 15cm (transplanted)",
        "water_mm": "500–900 mm", "fertilizer": "NPK 60:30:30 kg/ha",
        "method": "Transplant 25-day seedlings or direct sow"
    },
    "Barley": {
        "plants_per_ha": 5000000, "spacing": "22cm rows",
        "water_mm": "350–500 mm", "fertilizer": "NPK 60:30:20 kg/ha",
        "method": "Drill sow 75–80 kg seed/ha"
    },
    "Potato": {
        "plants_per_ha": 50000, "spacing": "60cm × 30cm",
        "water_mm": "500–700 mm", "fertilizer": "NPK 180:120:120 kg/ha",
        "method": "Plant certified seed tubers 40–50g, 2500 kg/ha"
    },
    "Onion": {
        "plants_per_ha": 100000, "spacing": "15cm × 10cm (transplanted)",
        "water_mm": "350–550 mm", "fertilizer": "NPK 100:50:50 kg/ha",
        "method": "Transplant 6-week seedlings from nursery"
    },
    "Tomato": {
        "plants_per_ha": 22222, "spacing": "75cm × 60cm",
        "water_mm": "400–600 mm", "fertilizer": "NPK 150:75:75 kg/ha",
        "method": "Transplant 4-week nursery seedlings"
    },
    "Brinjal": {
        "plants_per_ha": 22222, "spacing": "75cm × 60cm",
        "water_mm": "400–600 mm", "fertilizer": "NPK 100:50:50 kg/ha",
        "method": "Transplant 5-week seedlings, 500g seed/ha"
    },
    "Cabbage": {
        "plants_per_ha": 33333, "spacing": "60cm × 45cm",
        "water_mm": "380–500 mm", "fertilizer": "NPK 120:60:60 kg/ha",
        "method": "Transplant 4-week seedlings, 300g seed/ha"
    },
    "Cauliflower": {
        "plants_per_ha": 33333, "spacing": "60cm × 45cm",
        "water_mm": "380–500 mm", "fertilizer": "NPK 120:60:60 kg/ha",
        "method": "Transplant 4-week nursery seedlings"
    },
    "Carrot": {
        "plants_per_ha": 666667, "spacing": "30cm × 5cm",
        "water_mm": "400–600 mm", "fertilizer": "NPK 50:75:75 kg/ha",
        "method": "Direct sow 4–5 kg seed/ha in rows"
    },
    "Garlic": {
        "plants_per_ha": 500000, "spacing": "15cm × 10cm",
        "water_mm": "350–500 mm", "fertilizer": "NPK 100:50:50 kg/ha",
        "method": "Plant cloves 4–5 cm deep, 500 kg cloves/ha"
    },
    "Ginger": {
        "plants_per_ha": 133333, "spacing": "25cm × 30cm",
        "water_mm": "1500–3000 mm", "fertilizer": "NPK 75:50:75 kg/ha",
        "method": "Plant 20–25g rhizome pieces 4–5 cm deep"
    },
    "Turmeric": {
        "plants_per_ha": 100000, "spacing": "30cm × 25cm",
        "water_mm": "1500–2250 mm", "fertilizer": "NPK 60:50:120 kg/ha",
        "method": "Plant 40–50g mother/finger rhizomes"
    },
    "Dry ginger": {
        "plants_per_ha": 133333, "spacing": "25cm × 30cm",
        "water_mm": "1500–2500 mm", "fertilizer": "NPK 75:50:75 kg/ha",
        "method": "Same as Ginger — dried after harvest"
    },
    "Black pepper": {
        "plants_per_ha": 1111, "spacing": "3m × 3m",
        "water_mm": "1500–2500 mm", "fertilizer": "NPK 100:40:140 g/vine/yr",
        "method": "Plant rooted cuttings on live/dead standards"
    },
    "Cardamom": {
        "plants_per_ha": 1667, "spacing": "2.5m × 2.5m",
        "water_mm": "1500–4000 mm", "fertilizer": "NPK 75:75:150 kg/ha",
        "method": "Transplant 18-month seedlings under shade"
    },
    "Coffee": {
        "plants_per_ha": 1250, "spacing": "3m × 2.5m",
        "water_mm": "1000–2000 mm", "fertilizer": "NPK 100:25:75 g/plant/yr",
        "method": "Transplant grafted seedlings in pits under shade"
    },
    "Tea": {
        "plants_per_ha": 13889, "spacing": "120cm × 60cm",
        "water_mm": "1150–2500 mm", "fertilizer": "NPK 90:15:45 kg/ha",
        "method": "Plant rooted cuttings in rows, prune at 50cm"
    },
    "Rubber": {
        "plants_per_ha": 420, "spacing": "5m × 5m",
        "water_mm": "2000–4500 mm", "fertilizer": "NPK 100:60:100 g/tree/yr",
        "method": "Plant budded stumps or polybag plants"
    },
    "Tobacco": {
        "plants_per_ha": 20000, "spacing": "90cm × 55cm",
        "water_mm": "500–1000 mm", "fertilizer": "NPK 90:45:90 kg/ha",
        "method": "Transplant 6-week seedlings, 100g seed for nursery"
    },
    "Tapioca": {
        "plants_per_ha": 10000, "spacing": "100cm × 100cm",
        "water_mm": "1000–1500 mm", "fertilizer": "NPK 100:50:100 kg/ha",
        "method": "Plant 20cm stem cuttings at 45° angle"
    },
    "Sweet potato": {
        "plants_per_ha": 33333, "spacing": "60cm × 50cm",
        "water_mm": "750–1000 mm", "fertilizer": "NPK 60:80:100 kg/ha",
        "method": "Plant vine cuttings 30–40 cm long"
    },
    "Mango": {
        "plants_per_ha": 100, "spacing": "10m × 10m",
        "water_mm": "750–2500 mm", "fertilizer": "NPK 1000:500:1000 g/tree/yr",
        "method": "Plant grafted saplings in 1m pits with FYM"
    },
    "Grapes": {
        "plants_per_ha": 2500, "spacing": "2m × 2m",
        "water_mm": "700–1200 mm", "fertilizer": "NPK 300:200:400 kg/ha",
        "method": "Plant rooted cuttings on trellis, prune annually"
    },
    "Lemon": {
        "plants_per_ha": 400, "spacing": "5m × 5m",
        "water_mm": "750–1200 mm", "fertilizer": "NPK 300:200:300 g/tree/yr",
        "method": "Plant budded seedlings in 60cm³ pits"
    },
    "Orange": {
        "plants_per_ha": 278, "spacing": "6m × 6m",
        "water_mm": "1200–1800 mm", "fertilizer": "NPK 400:200:400 g/tree/yr",
        "method": "Plant budded seedlings, intercrop first 4 years"
    },
    "Pineapple": {
        "plants_per_ha": 53333, "spacing": "30cm × 30cm × 60cm (double row)",
        "water_mm": "1000–1500 mm", "fertilizer": "NPK 400:200:600 kg/ha",
        "method": "Plant crowns, slips or ratoons 5–8 cm deep"
    },
    "Papaya": {
        "plants_per_ha": 1600, "spacing": "2.5m × 2.5m",
        "water_mm": "1200–1700 mm", "fertilizer": "NPK 200:200:250 g/plant/yr",
        "method": "Sow 3 seeds/pit, thin to 1 female + 1 male"
    },
    "Jack Fruit": {
        "plants_per_ha": 156, "spacing": "8m × 8m",
        "water_mm": "1000–2400 mm", "fertilizer": "NPK 300:200:300 g/tree/yr",
        "method": "Plant grafted seedlings, mulch heavily"
    },
    "Sapota": {
        "plants_per_ha": 160, "spacing": "8m × 8m",
        "water_mm": "1000–2500 mm", "fertilizer": "NPK 500:250:500 g/tree/yr",
        "method": "Plant grafted or budded plants in 1m pits"
    },
    "Citrus Fruit": {
        "plants_per_ha": 400, "spacing": "5m × 5m",
        "water_mm": "750–1200 mm", "fertilizer": "NPK 300:200:300 g/tree/yr",
        "method": "Plant budded seedlings on appropriate rootstock"
    },
    "Pome Fruit": {
        "plants_per_ha": 250, "spacing": "6m × 6m",
        "water_mm": "700–1000 mm", "fertilizer": "NPK 400:200:400 g/tree/yr",
        "method": "Plant grafted apple/pear saplings in pits"
    },
    "Pome Granet": {
        "plants_per_ha": 500, "spacing": "5m × 4m",
        "water_mm": "500–800 mm", "fertilizer": "NPK 300:125:250 g/plant/yr",
        "method": "Plant hardwood cuttings or suckers in pits"
    },
    "Rapeseed &Mustard": {
        "plants_per_ha": 1666667, "spacing": "30cm × 10cm",
        "water_mm": "300–450 mm", "fertilizer": "NPK 80:40:40 kg/ha",
        "method": "Drill sow 4–5 kg seed/ha, thin to 10cm"
    },
    "Linseed": {
        "plants_per_ha": 2000000, "spacing": "25cm × 5cm",
        "water_mm": "300–450 mm", "fertilizer": "NPK 40:20:20 kg/ha",
        "method": "Drill sow 30–40 kg seed/ha in rows"
    },
    "Safflower": {
        "plants_per_ha": 133333, "spacing": "45cm × 15cm",
        "water_mm": "400–700 mm", "fertilizer": "NPK 60:30:20 kg/ha",
        "method": "Sow 10–12 kg seed/ha, thin to 15cm"
    },
    "Castor seed": {
        "plants_per_ha": 6667, "spacing": "150cm × 100cm",
        "water_mm": "500–750 mm", "fertilizer": "NPK 60:30:30 kg/ha",
        "method": "Sow 2 seeds/hole, thin to 1 plant"
    },
    "Sesamum": {
        "plants_per_ha": 500000, "spacing": "30cm × 10cm",
        "water_mm": "300–500 mm", "fertilizer": "NPK 40:20:20 kg/ha",
        "method": "Broadcast or line sow 3–5 kg seed/ha"
    },
    "Niger seed": {
        "plants_per_ha": 500000, "spacing": "30cm × 7cm",
        "water_mm": "250–400 mm", "fertilizer": "NPK 20:30:20 kg/ha",
        "method": "Broadcast 7–10 kg seed/ha, tolerates poor soil"
    },
    "Coriander": {
        "plants_per_ha": 500000, "spacing": "30cm × 7cm",
        "water_mm": "300–500 mm", "fertilizer": "NPK 40:30:20 kg/ha",
        "method": "Crush seeds before sowing, 15–20 kg/ha"
    },
    "Dry chillies": {
        "plants_per_ha": 22222, "spacing": "75cm × 60cm",
        "water_mm": "600–1250 mm", "fertilizer": "NPK 100:50:50 kg/ha",
        "method": "Transplant 5-week seedlings from nursery"
    },
    "Bhindi": {
        "plants_per_ha": 44444, "spacing": "45cm × 30cm (kharif)",
        "water_mm": "600–1000 mm", "fertilizer": "NPK 100:50:50 kg/ha",
        "method": "Sow 8–10 kg seed/ha direct, 2–3 seeds/hole"
    },
    "Bitter Gourd": {
        "plants_per_ha": 5556, "spacing": "3m × 60cm",
        "water_mm": "600–1000 mm", "fertilizer": "NPK 60:60:60 kg/ha",
        "method": "Sow 3–5 kg seed/ha on trellis or bower"
    },
    "Bottle Gourd": {
        "plants_per_ha": 5556, "spacing": "3m × 60cm",
        "water_mm": "600–1000 mm", "fertilizer": "NPK 60:60:60 kg/ha",
        "method": "Sow 2–3 seeds/pit on bower/trellis"
    },
    "Ash Gourd": {
        "plants_per_ha": 5556, "spacing": "3m × 60cm",
        "water_mm": "600–900 mm", "fertilizer": "NPK 60:40:40 kg/ha",
        "method": "Sow 3–4 kg seed/ha on trellis"
    },
    "Drum Stick": {
        "plants_per_ha": 1111, "spacing": "3m × 3m",
        "water_mm": "400–600 mm", "fertilizer": "NPK 60:60:60 g/tree/yr",
        "method": "Plant stem cuttings 1–1.5m long in pits"
    },
    "Bean": {
        "plants_per_ha": 133333, "spacing": "45cm × 15cm",
        "water_mm": "300–500 mm", "fertilizer": "NPK 20:60:40 kg/ha",
        "method": "Sow 30–40 kg seed/ha direct in rows"
    },
    "Beans & Mutter(Vegetable)": {
        "plants_per_ha": 133333, "spacing": "45cm × 15cm",
        "water_mm": "350–600 mm", "fertilizer": "NPK 30:60:40 kg/ha",
        "method": "Sow direct in rows, Rhizobium treatment recommended"
    },
    "Cowpea(Lobia)": {
        "plants_per_ha": 133333, "spacing": "45cm × 15cm",
        "water_mm": "300–500 mm", "fertilizer": "NPK 20:40:20 kg/ha",
        "method": "Sow 20–25 kg seed/ha with Rhizobium"
    },
    "Peas & beans (Pulses)": {
        "plants_per_ha": 333333, "spacing": "30cm × 10cm",
        "water_mm": "300–500 mm", "fertilizer": "NPK 20:60:30 kg/ha",
        "method": "Sow with Rhizobium, 80–100 kg seed/ha"
    },
    "Horse-gram": {
        "plants_per_ha": 500000, "spacing": "30cm × 7cm",
        "water_mm": "300–500 mm", "fertilizer": "NPK 20:40:20 kg/ha",
        "method": "Broadcast or line sow 30–40 kg/ha"
    },
    "Khesari": {
        "plants_per_ha": 1000000, "spacing": "22cm × 5cm",
        "water_mm": "250–400 mm", "fertilizer": "NPK 20:40:20 kg/ha",
        "method": "Sow 30–40 kg seed/ha in lines or broadcast"
    },
    "Masoor": {
        "plants_per_ha": 1000000, "spacing": "22cm × 5cm",
        "water_mm": "250–400 mm", "fertilizer": "NPK 20:40:20 kg/ha",
        "method": "Sow 30–35 kg seed/ha with Rhizobium"
    },
    "Guar seed": {
        "plants_per_ha": 166667, "spacing": "45cm × 10cm",
        "water_mm": "300–500 mm", "fertilizer": "NPK 20:40:20 kg/ha",
        "method": "Sow 20–25 kg seed/ha, drought tolerant"
    },
    "Rajmash Kholar": {
        "plants_per_ha": 133333, "spacing": "45cm × 15cm",
        "water_mm": "400–600 mm", "fertilizer": "NPK 20:60:40 kg/ha",
        "method": "Sow 80–100 kg seed/ha in hills"
    },
    "Moth": {
        "plants_per_ha": 333333, "spacing": "30cm × 10cm",
        "water_mm": "200–400 mm", "fertilizer": "NPK 20:40:20 kg/ha",
        "method": "Broadcast 20 kg/ha, very drought tolerant"
    },
    "Ricebean (nagadal)": {
        "plants_per_ha": 333333, "spacing": "30cm × 10cm",
        "water_mm": "500–700 mm", "fertilizer": "NPK 20:40:20 kg/ha",
        "method": "Sow 20–25 kg seed/ha in rows"
    },
    "Colocosia": {
        "plants_per_ha": 40000, "spacing": "50cm × 50cm",
        "water_mm": "1000–1500 mm", "fertilizer": "NPK 100:60:80 kg/ha",
        "method": "Plant corms or cormels 8–10 cm deep"
    },
    "Beet Root": {
        "plants_per_ha": 222222, "spacing": "30cm × 15cm",
        "water_mm": "400–600 mm", "fertilizer": "NPK 80:60:80 kg/ha",
        "method": "Sow seed clusters 2–3 cm deep, thin later"
    },
    "Redish": {
        "plants_per_ha": 666667, "spacing": "30cm × 5cm",
        "water_mm": "350–500 mm", "fertilizer": "NPK 60:40:40 kg/ha",
        "method": "Direct sow 8–10 kg seed/ha in rows"
    },
    "Turnip": {
        "plants_per_ha": 333333, "spacing": "30cm × 10cm",
        "water_mm": "350–500 mm", "fertilizer": "NPK 60:40:40 kg/ha",
        "method": "Broadcast or drill 3–4 kg seed/ha"
    },
    "Peas  (vegetable)": {
        "plants_per_ha": 666667, "spacing": "30cm × 5cm",
        "water_mm": "350–500 mm", "fertilizer": "NPK 20:60:40 kg/ha",
        "method": "Sow 80–100 kg seed/ha with Rhizobium"
    },
    "Other Vegetables": {
        "plants_per_ha": 44444, "spacing": "60cm × 30cm (typical)",
        "water_mm": "400–700 mm", "fertilizer": "NPK 80:60:60 kg/ha",
        "method": "Varies by vegetable type — consult local KVK"
    },
    "Other Fresh Fruits": {
        "plants_per_ha": 400, "spacing": "5m × 5m (typical)",
        "water_mm": "800–1500 mm", "fertilizer": "NPK 200:100:200 g/plant/yr",
        "method": "Plant grafted/budded saplings in prepared pits"
    },
    "Citrus Fruit": {
        "plants_per_ha": 400, "spacing": "5m × 5m",
        "water_mm": "750–1200 mm", "fertilizer": "NPK 300:200:300 g/tree/yr",
        "method": "Plant budded seedlings on appropriate rootstock"
    },
    "Other Citrus Fruit": {
        "plants_per_ha": 400, "spacing": "5m × 5m",
        "water_mm": "750–1200 mm", "fertilizer": "NPK 300:200:300 g/tree/yr",
        "method": "Plant budded seedlings, irrigate in dry months"
    },
    "Peach": {
        "plants_per_ha": 400, "spacing": "5m × 5m",
        "water_mm": "700–1000 mm", "fertilizer": "NPK 400:200:300 g/tree/yr",
        "method": "Plant budded saplings in well-drained soil"
    },
    "Pear": {
        "plants_per_ha": 250, "spacing": "6m × 6m",
        "water_mm": "600–1000 mm", "fertilizer": "NPK 400:200:400 g/tree/yr",
        "method": "Plant grafted saplings, needs chilling hours"
    },
    "Plums": {
        "plants_per_ha": 400, "spacing": "5m × 5m",
        "water_mm": "600–1000 mm", "fertilizer": "NPK 400:200:300 g/tree/yr",
        "method": "Plant budded or grafted saplings in pits"
    },
    "Litchi": {
        "plants_per_ha": 156, "spacing": "8m × 8m",
        "water_mm": "1200–1800 mm", "fertilizer": "NPK 600:400:600 g/tree/yr",
        "method": "Plant air-layered plants, avoid waterlogging"
    },
    "Ber": {
        "plants_per_ha": 156, "spacing": "8m × 8m",
        "water_mm": "400–700 mm", "fertilizer": "NPK 300:150:300 g/tree/yr",
        "method": "Plant budded saplings, drought tolerant once established"
    },
    "Cond-spcs other": {
        "plants_per_ha": 100000, "spacing": "30cm × 30cm (typical)",
        "water_mm": "600–1200 mm", "fertilizer": "NPK 50:40:40 kg/ha",
        "method": "Varies by spice — follow crop-specific guide"
    },
    "Rubber": {
        "plants_per_ha": 420, "spacing": "5m × 5m",
        "water_mm": "2000–4500 mm", "fertilizer": "NPK 100:60:100 g/tree/yr",
        "method": "Plant budded stumps or polybag plants"
    },
    "Mesta": {
        "plants_per_ha": 500000, "spacing": "30cm × 7cm",
        "water_mm": "800–1500 mm", "fertilizer": "NPK 60:30:30 kg/ha",
        "method": "Sow 8–10 kg seed/ha, intercrop with pulses"
    },
    "Sannhamp": {
        "plants_per_ha": 500000, "spacing": "30cm × 7cm",
        "water_mm": "600–1200 mm", "fertilizer": "NPK 40:20:20 kg/ha",
        "method": "Broadcast 20–25 kg seed/ha as green manure"
    },
    "Korra": {
        "plants_per_ha": 250000, "spacing": "25cm × 15cm",
        "water_mm": "300–500 mm", "fertilizer": "NPK 40:20:20 kg/ha",
        "method": "Sow 5–6 kg seed/ha broadcast"
    },
    "Varagu": {
        "plants_per_ha": 250000, "spacing": "25cm × 15cm",
        "water_mm": "300–500 mm", "fertilizer": "NPK 40:20:20 kg/ha",
        "method": "Sow 8–10 kg seed/ha broadcast or in rows"
    },
    "Samai": {
        "plants_per_ha": 333333, "spacing": "30cm × 10cm",
        "water_mm": "300–500 mm", "fertilizer": "NPK 40:20:20 kg/ha",
        "method": "Broadcast 8–10 kg seed/ha, drought tolerant"
    },
    "Perilla": {
        "plants_per_ha": 100000, "spacing": "30cm × 30cm",
        "water_mm": "600–1200 mm", "fertilizer": "NPK 60:40:40 kg/ha",
        "method": "Broadcast 2–3 kg seed/ha, thin to 30cm"
    },
    "Jobster": {
        "plants_per_ha": 50000, "spacing": "45cm × 45cm",
        "water_mm": "600–1000 mm", "fertilizer": "NPK 60:30:30 kg/ha",
        "method": "Sow 5 kg seed/ha, grown for grain and fodder"
    },
    "Small millets": {
        "plants_per_ha": 250000, "spacing": "25cm × 15cm",
        "water_mm": "300–500 mm", "fertilizer": "NPK 40:20:20 kg/ha",
        "method": "Broadcast 6–8 kg seed/ha, minimal inputs"
    },
    "Other Cereals & Millets": {
        "plants_per_ha": 200000, "spacing": "30cm × 15cm",
        "water_mm": "350–600 mm", "fertilizer": "NPK 50:25:25 kg/ha",
        "method": "Varies by cereal type — consult local KVK"
    },
    "Other Kharif pulses": {
        "plants_per_ha": 333333, "spacing": "30cm × 10cm",
        "water_mm": "300–500 mm", "fertilizer": "NPK 20:40:20 kg/ha",
        "method": "Sow with Rhizobium, 15–25 kg seed/ha"
    },
    "Other  Rabi pulses": {
        "plants_per_ha": 500000, "spacing": "22cm × 10cm",
        "water_mm": "250–400 mm", "fertilizer": "NPK 20:40:20 kg/ha",
        "method": "Sow 30–40 kg seed/ha with Rhizobium"
    },
    "other misc. pulses": {
        "plants_per_ha": 333333, "spacing": "30cm × 10cm",
        "water_mm": "300–500 mm", "fertilizer": "NPK 20:40:20 kg/ha",
        "method": "Follow crop-specific planting norms"
    },
    "other oilseeds": {
        "plants_per_ha": 133333, "spacing": "45cm × 15cm",
        "water_mm": "300–600 mm", "fertilizer": "NPK 40:30:20 kg/ha",
        "method": "Varies by oilseed — follow crop-specific guide"
    },
    "Oilseeds total": {
        "plants_per_ha": 133333, "spacing": "45cm × 15cm",
        "water_mm": "300–700 mm", "fertilizer": "NPK 50:30:20 kg/ha",
        "method": "Aggregate — sow specific oilseed per season"
    },
    "Pulses total": {
        "plants_per_ha": 333333, "spacing": "30cm × 10cm",
        "water_mm": "300–500 mm", "fertilizer": "NPK 20:40:20 kg/ha",
        "method": "Aggregate — sow specific pulse per season"
    },
    "Total foodgrain": {
        "plants_per_ha": 500000, "spacing": "Varies by crop",
        "water_mm": "300–1500 mm", "fertilizer": "NPK varies by crop",
        "method": "Aggregate — follow individual crop guidelines"
    },
    "Other Dry Fruit": {
        "plants_per_ha": 200, "spacing": "7m × 7m",
        "water_mm": "400–800 mm", "fertilizer": "NPK 200:100:200 g/tree/yr",
        "method": "Plant grafted saplings in well-drained soil"
    },
}

def get_planting_guide(crop):
    guide = PLANTING_GUIDE.get(crop)
    if guide:
        return guide
    # smart fallback by category keywords
    cl = crop.lower()
    if any(x in cl for x in ["pulse","gram","bean","pea"]):
        return {"plants_per_ha": 333333, "spacing": "30cm × 10cm", "water_mm": "300–500 mm",
                "fertilizer": "NPK 20:40:20 kg/ha", "method": "Sow with Rhizobium, 20–30 kg seed/ha"}
    if any(x in cl for x in ["fruit","citrus","pome"]):
        return {"plants_per_ha": 400, "spacing": "5m × 5m", "water_mm": "800–1500 mm",
                "fertilizer": "NPK 200:100:200 g/tree/yr", "method": "Plant grafted/budded saplings in pits"}
    if any(x in cl for x in ["vegetable","gourd","greens"]):
        return {"plants_per_ha": 44444, "spacing": "60cm × 30cm", "water_mm": "400–700 mm",
                "fertilizer": "NPK 80:60:60 kg/ha", "method": "Transplant or direct sow per crop type"}
    if any(x in cl for x in ["millet","cereal","grain"]):
        return {"plants_per_ha": 250000, "spacing": "30cm × 15cm", "water_mm": "300–600 mm",
                "fertilizer": "NPK 60:30:30 kg/ha", "method": "Broadcast or drill sow per crop type"}
    if any(x in cl for x in ["oilseed","oil"]):
        return {"plants_per_ha": 133333, "spacing": "45cm × 15cm", "water_mm": "300–600 mm",
                "fertilizer": "NPK 40:30:20 kg/ha", "method": "Sow 5–10 kg seed/ha per crop type"}
    return {"plants_per_ha": 50000, "spacing": "Consult local KVK", "water_mm": "Varies",}
  

def get_crop_info(crop):
    return CROP_INFO.get(crop, {
        "water": "Moderate",
        "profit": "Moderate",
        "risk": "Moderate",
        "fertilizer": "Balanced NPK",
        "months": "Seasonal"
    })

def level_score(value):
    scores = {
        "Low": 1,
        "Medium": 2,
        "Moderate": 2,
        "High": 3,
        "Very High": 4
    }
    return scores.get(value, 2)


def get_alternative_crops(top3):
    best_crop = top3[0]["crop"]
    best_info = get_crop_info(best_crop)

    alternatives = []

    for item in top3[1:]:
        crop_name = item["crop"]
        info = get_crop_info(crop_name)

        reasons = []

        if level_score(info["risk"]) < level_score(best_info["risk"]):
            reasons.append("lower risk")

        if level_score(info["water"]) < level_score(best_info["water"]):
            reasons.append("lower water requirement")

        if level_score(info["profit"]) >= level_score(best_info["profit"]):
            reasons.append("good profit potential")

        if not reasons:
            reasons.append("balanced alternative based on model ranking")

        alternatives.append({
            "crop": crop_name,
            "confidence": item["confidence"],
            "reason": ", ".join(reasons)
        })

    return alternatives

def get_combo_crop(best_crop):
    crop = best_crop.lower()

    # 🌾 cereals → mix with pulses
    if any(x in crop for x in ["rice", "paddy", "wheat", "maize", "jowar", "bajra"]):
        return {
            "main_crop": best_crop,
            "partner_crop": "Pulses",
            "mix": f"70% {best_crop} + 30% Pulses",
            "reason": "Improves soil fertility (nitrogen fixation) and reduces risk."
        }

    # 🌱 pulses → mix with cereals
    if any(x in crop for x in ["gram", "moong", "urad", "arhar", "lentil"]):
        return {
            "main_crop": best_crop,
            "partner_crop": "Cereal Crop",
            "mix": f"70% {best_crop} + 30% Cereal",
            "reason": "Balances yield and improves land productivity."
        }

    # 🌿 cash crops → mix with pulses
    if any(x in crop for x in ["cotton", "sugarcane", "tobacco"]):
        return {
            "main_crop": best_crop,
            "partner_crop": "Pulses",
            "mix": f"70% {best_crop} + 30% Pulses",
            "reason": "Reduces financial risk and improves soil nutrients."
        }

    # 🥬 vegetables / fruits → mix with legumes
    if any(x in crop for x in ["vegetable", "onion", "tomato", "potato", "brinjal"]):
        return {
            "main_crop": best_crop,
            "partner_crop": "Legumes",
            "mix": f"70% {best_crop} + 30% Legumes",
            "reason": "Helps maintain soil health and improves yield balance."
        }

    # default fallback
    return {
            "main_crop": best_crop,
            "partner_crop": "Optional",
            "mix": f"{best_crop} can be grown independently",
    "       reason": "This crop is typically cultivated as a standalone crop, but diversification can be considered based on local practices."
        }       
def get_worst_case_scenario(crop):
    info = get_crop_info(crop)

    water = info.get("water", "Medium")
    risk = info.get("risk", "Medium")
    profit = info.get("profit", "Medium")

    # High-risk crops
    if risk == "High":
        return {
            "level": "High",
            "title": "High Risk Scenario",
            "message": f"{crop} may face higher production uncertainty due to market, pest, or seasonal variability.",
            "advice": "Consider alternative crops or diversification to reduce loss."
        }

    # High water need crops
    if water in ["High", "Very High"]:
        return {
            "level": "Medium",
            "title": "Water Stress Warning",
            "message": f"{crop} may underperform if rainfall or irrigation supply is insufficient.",
            "advice": "Ensure proper irrigation planning or consider lower-water alternatives."
        }

    # Low profit crops
    if profit == "Low":
        return {
            "level": "Medium",
            "title": "Profitability Warning",
            "message": f"{crop} may give stable production but lower profit margins under current conditions.",
            "advice": "Compare with alternative crops for better financial return."
        }

    # Default safe case
    return {
        "level": "Low",
        "title": "Stable Scenario",
        "message": f"{crop} appears relatively stable under the selected conditions.",
        "advice": "Continue with good irrigation, nutrient, and pest management practices."
    }

def generate_advisory(crop, production, area, area_acres):

    info = get_crop_info(crop)
    guide = get_planting_guide(crop)
    plants = int(guide["plants_per_ha"] * area)

    return [

        {
            "icon": "🌱",
            "label": "Recommended Crop",
            "value": crop
        },

        {
            "icon": "📈",
            "label": "Expected Production",
            "value": f"{round(production,2)} tonnes"
        },

        {
            "icon": "💧",
            "label": "Water Requirement",
            "value": info["water"]
        },

        {
            "icon": "💰",
            "label": "Profit Potential",
            "value": info["profit"]
        },

        {
            "icon": "⚠️",
            "label": "Risk Level",
            "value": info["risk"]
        },

        {
            "icon": "📅",
            "label": "Growing Season",
            "value": info["months"]
        },

        {
            "icon": "🌿",
            "label": "Planting Guide",
            "sub": [
                f"Plants for {round(area_acres, 2)} acres: {plants:,}",
                f"Spacing: {guide['spacing']}",
                f"Water: {guide['water_mm']}",
                f"Fertilizer: {guide['fertilizer']}",
                f"Method: {guide['method']}"
            ]
        }

    ]

# ─────────────────────────────────────────
# PAGE ROUTES
# ─────────────────────────────────────────
@app.route("/")
def index():
    states    = sorted(list(le_state.classes_))
    districts = sorted(list(le_district.classes_))
    seasons   = sorted(list(le_season.classes_))
    crops     = sorted(list(le_crop.classes_))
    return render_template("index.html",states=states,districts=districts,seasons=seasons,crops=crops)

@app.route("/analytics")
def analytics():
    return render_template("analytics.html")

@app.route("/community")
def community():
    return render_template("community.html")
# ─────────────────────────────────────────
# PREDICTION API
# ─────────────────────────────────────────
@app.route("/predict", methods=["POST"])
def predict():
    data = request.json

    # ✅ INPUT VALIDATION
    required_fields = ["state", "district", "season", "area"]

    for field in required_fields:
        if field not in data or str(data[field]).strip() == "":
            return jsonify({"error": f"Missing or empty field: {field}"})

    try:
        state = le_state.transform([data["state"]])[0]
        district = le_district.transform([data["district"]])[0]
        season = le_season.transform([data["season"]])[0]

        # ✅ Acres → hectares
        area_acres = float(data["area"])
        area = area_acres * 0.404686

    except Exception as e:
        return jsonify({"error": f"Invalid input: {str(e)}"})

    probs = crop_model.predict_proba([[state, district, season, area]])[0]
    top3_idx = np.argsort(probs)[::-1][:3]

    top3 = []
    for i in top3_idx:
        top3.append({
            "crop": le_crop.classes_[i],
            "confidence": round(probs[i] * 100, 1)
        })

    best_crop = top3[0]["crop"]
    crop_encoded = le_crop.transform([best_crop])[0]

    production = production_model.predict(
        [[state, district, season, crop_encoded, area]]
    )[0]

    advisory = generate_advisory(best_crop, production, area, area_acres)
    alternatives = get_alternative_crops(top3)
    combo_crop = get_combo_crop(best_crop)
    worst_case = get_worst_case_scenario(best_crop)

    comparison = {
        c["crop"]: get_crop_info(c["crop"]) for c in top3
    }

    return jsonify({
    "crop": best_crop,
    "production": round(float(production), 2),
    "top3": top3,
    "advisory": advisory,
    "alternatives": alternatives,
    "combo_crop": combo_crop,
    "comparison": comparison,
    "worst_case": worst_case
})

# ─────────────────────────────────────────
# CHATBOT API
# ─────────────────────────────────────────
def get_chat_reply(msg):
    msg_lower = msg.lower().strip()

    # Try each pattern (longest/most specific first)
    best_match = None
    best_score = 0

    for pattern, data in CHAT_KB.items():
        keywords = pattern.split("|")
        score = 0
        for kw in keywords:
            # Use regex word boundary matching
            if re.search(r'\b' + kw.replace(".", r"\s*") + r'\b', msg_lower):
                score += len(kw)  # longer keyword = more specific match
        if score > best_score:
            best_score = score
            best_match = data

    if best_match:
        reply = best_match["response"]
        if best_match.get("followups"):
            fu = best_match["followups"]
            reply += "<br><br>🔍 <i>You might also ask:</i><br>" + "".join(
                f'<span class="chat-suggest" onclick="askSuggestion(\'{q}\')">{q}</span> '
                for q in fu
            )
        return reply

    # Fallback with smart suggestions based on keywords detected
    detected = []
    if any(w in msg_lower for w in ["crop","grow","plant","farm","cultivat"]):
        detected.append("crop selection")
    if any(w in msg_lower for w in ["state","district","region","area","maharashtra","punjab","up","bihar"]):
        detected.append("region-specific advice")

    if detected:
        return f"🤔 I can help with {', '.join(detected)}! Could you be more specific? Try asking about a particular crop, season, or practice.<br><br>🔍 <i>Popular questions:</i><br>" + \
               '<span class="chat-suggest" onclick="askSuggestion(\'Best Kharif crops?\')">Best Kharif crops?</span> ' + \
               '<span class="chat-suggest" onclick="askSuggestion(\'Current MSP rates?\')">Current MSP rates?</span> ' + \
               '<span class="chat-suggest" onclick="askSuggestion(\'Fertilizer for wheat?\')">Fertilizer for wheat?</span>'

    return "🌾 I'm here to help with farming questions!<br><br>Try asking about:<br>• Specific crops (rice, wheat, cotton)<br>• Water & irrigation<br>• Fertilizers & soil<br>• Government schemes<br>• MSP prices & markets<br>• Pest control"

# ─────────────────────────────────────────
# ALL CROPS
# ─────────────────────────────────────────
@app.route("/all_crops")
def all_crops():
    crops = list(le_crop.classes_)

    data = []
    for crop in crops:
        info = get_crop_info(crop)
        data.append({
            "name": crop,
            "water": info["water"],
            "profit": info["profit"],
            "risk": info["risk"],
            "fertilizer": info["fertilizer"],
            "months": info["months"]
        })

    return jsonify(data)

# ─────────────────────────────────────────
# FIXED DISTRICT API ✅
# ─────────────────────────────────────────
@app.route("/get_districts/<state>")
def get_districts(state):
    import pandas as pd

    try:
        df = pd.read_csv("data/crop_production_clean.csv")

        # 🔥 USE EXACT COLUMN NAMES
        df["State_Name"] = df["State_Name"].astype(str).str.strip().str.lower()
        df["District_Name"] = df["District_Name"].astype(str).str.strip()

        state = state.strip().lower()

        print("STATE FROM UI:", state)
        print("AVAILABLE STATES:", df["State_Name"].unique()[:10])

        # 🔥 EXACT MATCH (NOW WILL WORK)
        filtered = df[df["State_Name"] == state]

        print("MATCH COUNT:", len(filtered))

        districts = filtered["District_Name"].dropna().unique()

        return jsonify(sorted(districts.tolist()))

    except Exception as e:
        print("ERROR:", e)
        return jsonify([])
# ─────────────────────────────────────────
# ANALYTICS API ✅ WITH LEVELS (FINAL)
# ─────────────────────────────────────────
@app.route("/get_analytics")
def get_analytics():
    import pandas as pd

    try:
        df = pd.read_csv("data/crop_production_clean.csv")
        df = df.fillna(0)
        df.columns = df.columns.str.strip()

        # Clean columns
        df["Crop"] = df["Crop"].astype(str).str.strip()
        df["Area"] = pd.to_numeric(df["Area"], errors="coerce")
        df["Production"] = pd.to_numeric(df["Production"], errors="coerce")

        df = df.dropna(subset=["Crop", "Area", "Production"])

        # 🌿 Crop knowledge
        crop_info = {
            "Rice": {"fertilizer": "High", "season": "Kharif"},
            "Wheat": {"fertilizer": "Medium", "season": "Rabi"},
            "Cotton": {"fertilizer": "High", "season": "Kharif"},
            "Sugarcane": {"fertilizer": "High", "season": "Annual"},
            "Maize": {"fertilizer": "Medium", "season": "Kharif"},
            "Banana": {"fertilizer": "High", "season": "Annual"},
            "Groundnut": {"fertilizer": "Low", "season": "Kharif"},
            "Arecanut": {"fertilizer": "Medium", "season": "Annual"},
            "Cashewnut": {"fertilizer": "Low", "season": "Annual"}
        }

        # 🔥 LEVEL FUNCTION
        def get_level(value):
            if value < 33:
                return "Low"
            elif value < 66:
                return "Medium"
            else:
                return "High"

        result = []

        for crop in df["Crop"].unique():
            temp = df[df["Crop"] == crop]

            avg_area = temp["Area"].mean()
            avg_prod = temp["Production"].mean()

            # 📊 Metrics
            water = (avg_area / avg_prod) if avg_prod else 0
            profit = (avg_prod / avg_area) if avg_area else 0
            risk = temp["Production"].std()

            # Handle NaN
            if pd.isna(risk):
                risk = 0

            # 🔥 Normalize (0–100 scale)
            water = min(water * 100, 100)
            profit = min(profit * 10, 100)
            risk = min(risk / 1000, 100)

            # 🌿 Crop info
            info = crop_info.get(crop, {"fertilizer": "Medium", "season": "Kharif"})

            # 🔥 Levels
            water_level = get_level(water)
            profit_level = get_level(profit)
            risk_level = get_level(risk)

            result.append({
                "crop": crop,

                # numeric (charts)
                "water": round(water, 2),
                "profit": round(profit, 2),
                "risk": round(risk, 2),

                # levels (UI)
                "water_level": water_level,
                "profit_level": profit_level,
                "risk_level": risk_level,

                "fertilizer": info["fertilizer"],
                "season": info["season"]
            })

        result = sorted(result, key=lambda x: x["crop"].lower())
        return jsonify(result)

    except Exception as e:
        print("ERROR:", e)
        return jsonify([])

# app.py  (add this route)
@app.route("/get_analytics_map")
def get_analytics_map():
    import pandas as pd
    # Approximate state centroids for map visualization
    state_coords = {
        "andhra pradesh": {"lat": 15.9129, "lon": 79.7400},
        "arunachal pradesh": {"lat": 28.2180, "lon": 94.7278},
        "assam": {"lat": 26.2006, "lon": 92.9376},
        "bihar": {"lat": 25.0961, "lon": 85.3131},
        "chhattisgarh": {"lat": 21.2787, "lon": 81.8661},
        "goa": {"lat": 15.2993, "lon": 74.1240},
        "gujarat": {"lat": 22.2587, "lon": 71.1924},
        "haryana": {"lat": 29.0588, "lon": 76.0856},
        "himachal pradesh": {"lat": 31.1048, "lon": 77.1734},
        "jharkhand": {"lat": 23.6102, "lon": 85.2799},
        "karnataka": {"lat": 15.3173, "lon": 75.7139},
        "kerala": {"lat": 10.8505, "lon": 76.2711},
        "madhya pradesh": {"lat": 22.9734, "lon": 78.6569},
        "maharashtra": {"lat": 19.7515, "lon": 75.7139},
        "manipur": {"lat": 24.6637, "lon": 93.9063},
        "meghalaya": {"lat": 25.4670, "lon": 91.3662},
        "mizoram": {"lat": 23.1645, "lon": 92.9376},
        "nagaland": {"lat": 26.1584, "lon": 94.5624},
        "odisha": {"lat": 20.9517, "lon": 85.0985},
        "punjab": {"lat": 31.1471, "lon": 75.3412},
        "rajasthan": {"lat": 27.0238, "lon": 74.2179},
        "sikkim": {"lat": 27.5330, "lon": 88.5122},
        "tamil nadu": {"lat": 11.1271, "lon": 78.6569},
        "telangana": {"lat": 18.1124, "lon": 79.0193},
        "tripura": {"lat": 23.9408, "lon": 91.9882},
        "uttar pradesh": {"lat": 26.8467, "lon": 80.9462},
        "uttarakhand": {"lat": 30.0668, "lon": 79.0193},
        "west bengal": {"lat": 22.9868, "lon": 87.8550},
        "jammu and kashmir": {"lat": 34.0837, "lon": 74.7973},
        "ladakh": {"lat": 34.1526, "lon": 77.5770},
        "delhi": {"lat": 28.7041, "lon": 77.1025}
    }
    try:
        df = pd.read_csv("data/crop_production_clean.csv")
        df.columns = df.columns.str.strip()
        df["Crop"] = df["Crop"].astype(str).str.strip()
        df["State_Name"] = df["State_Name"].astype(str).str.strip()
        df["Area"] = pd.to_numeric(df["Area"], errors="coerce")
        df["Production"] = pd.to_numeric(df["Production"], errors="coerce")
        df = df.dropna(subset=["Crop", "State_Name", "Area", "Production"])
        payload = []
        grouped = df.groupby("State_Name")
        for state_name, state_df in grouped:
            key = state_name.lower()
            if key not in state_coords:
                continue
            area_sum = float(state_df["Area"].sum())
            production_sum = float(state_df["Production"].sum())
            water_raw = (area_sum / production_sum) if production_sum else 0.0
            profit_raw = (production_sum / area_sum) if area_sum else 0.0
            risk_raw = float(state_df["Production"].std())
            if pd.isna(risk_raw):
                risk_raw = 0.0
            top_crop_row = (
                state_df.groupby("Crop", as_index=False)["Production"]
                .sum()
                .sort_values("Production", ascending=False)
                .head(1)
            )
            top_crop = top_crop_row.iloc[0]["Crop"] if not top_crop_row.empty else "N/A"
            payload.append({
                "state": state_name,
                "lat": state_coords[key]["lat"],
                "lon": state_coords[key]["lon"],
                "water_raw": water_raw,
                "profit": min(profit_raw * 10, 100),
                "top_crop": top_crop
            })
        if payload:
            water_values = [x["water_raw"] for x in payload]
            w_min = min(water_values)
            w_max = max(water_values)
            w_span = (w_max - w_min) if w_max != w_min else 1.0
            for item in payload:
                item["water"] = round(((item["water_raw"] - w_min) / w_span) * 100, 2)
                item["profit"] = round(item["profit"], 2)
                del item["water_raw"]
        return jsonify(payload)
    except Exception as e:
        print("ERROR:", e)
        return jsonify([])

# chatbot api
@app.route("/chat", methods=["POST"])
def chat():
    msg = request.json.get("message", "").strip()
    if not msg:
        return jsonify({"reply": "Please type a message!"})
    return jsonify({"reply": get_chat_reply(msg)})

# Weather api
# ─────────────────────────────────────────
# WEATHER PROXY  (Open-Meteo — free, no key)
# ─────────────────────────────────────────
@app.route("/weather")
def weather():
    lat = request.args.get("lat", "19.076")   # Mumbai fallback
    lon = request.args.get("lon", "72.877")

    # Reverse-geocode city name via Open-Meteo geocoding
    city = "Your Location"
    try:
        geo_url = (
            f"https://nominatim.openstreetmap.org/reverse"
            f"?lat={lat}&lon={lon}&format=json"
        )
        req = urllib.request.Request(geo_url, headers={"User-Agent": "AgroMind/1.0"})
        with urllib.request.urlopen(req, timeout=4) as r:
            geo = json.loads(r.read())
        addr = geo.get("address", {})
        city = (addr.get("city") or addr.get("town") or
                addr.get("village") or addr.get("state", "Your Location"))
    except Exception:
        pass

    # Weather from Open-Meteo
    try:
        wx_url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            f"&current=temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation_probability"
            f"&daily=precipitation_probability_max"
            f"&timezone=auto&forecast_days=2"
        )
        with urllib.request.urlopen(wx_url, timeout=5) as r:
            wx = json.loads(r.read())

        cur  = wx["current"]
        temp = round(cur["temperature_2m"])
        hum  = cur["relative_humidity_2m"]
        wind = round(cur["wind_speed_10m"])
        rain_today    = cur["precipitation_probability"]
        rain_tomorrow = wx["daily"]["precipitation_probability_max"][1] if len(wx["daily"]["precipitation_probability_max"]) > 1 else rain_today

        rain_label = "Today" if rain_today > 50 else ("Tomorrow" if rain_tomorrow > 50 else "Low chance")

        return jsonify({
            "city":  city,
            "temp":  temp,
            "hum":   hum,
            "wind":  wind,
            "rain":  rain_label,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/posts", methods=["GET", "POST"])
def posts():

    conn = get_db()

    if request.method == "POST":

        data = request.json

        name = data.get("name")
        text = data.get("text")
        image = data.get("image", "")

        created_at = datetime.now().strftime("%d %b %Y • %I:%M %p")

        conn.execute(
            """
            INSERT INTO posts
            (name,text,image,created_at)

            VALUES (?,?,?,?)
            """,
            (name, text, image, created_at)
        )

        conn.commit()
        conn.close()

        return jsonify({
            "success": True
        })

    posts = conn.execute("""
        SELECT *
        FROM posts
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    return jsonify([dict(i) for i in posts])

# ─────────────────────────────────────────
# RUN APP
# ─────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    app.run(debug=True)