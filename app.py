import os
import time
import requests
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

IBM_IAM_TOKEN_URL = os.getenv("IBM_IAM_TOKEN_URL", "https://iam.cloud.ibm.com/identity/token")
WATSONX_GENERATION_URL = os.getenv("WATSONX_GENERATION_URL")
MODEL_ID = os.getenv("MODEL_ID", "ibm/granite-4-h-small")
PROJECT_ID = os.getenv("PROJECT_ID")
IBM_API_KEY = os.getenv("IBM_API_KEY")

# Simple in-memory token cache to avoid re-fetching on every request
_token_cache = {"token": None, "expiry": 0}

# ---------------------------------------------------------------------------
# RAG Knowledge Base
# ---------------------------------------------------------------------------
KNOWLEDGE_BASE = [
    {
        "id": "pm_svanidhi",
        "tags": ["scheme", "loan", "government", "svanidhi", "credit", "pm"],
        "title": "PM SVANidhi Scheme",
        "content": (
            "PM Street Vendor's AtmaNirbhar Nidhi (PM SVANidhi) provides collateral-free working capital "
            "loans to street vendors. Initial loan: ₹10,000 with 1-year tenure. Enhanced credit: ₹20,000 "
            "then ₹50,000 on timely repayment. Subsidy: 7% interest subsidy credited directly to bank account. "
            "Eligibility: Vendors with Certificate of Vending or Letter of Recommendation from ULB. "
            "Apply at: pmSVANidhi.pib.gov.in or Common Service Centres (CSCs). "
            "Documents needed: Aadhar card, bank account, vending certificate."
        ),
    },
    {
        "id": "msme_mudra",
        "tags": ["scheme", "loan", "mudra", "msme", "finance", "shishu", "kishore", "tarun"],
        "title": "MSME Mudra Loan",
        "content": (
            "Mudra Yojana offers micro-enterprise loans under 3 tiers: "
            "Shishu (up to ₹50,000), Kishore (₹50,001–₹5 lakh), Tarun (₹5 lakh–₹10 lakh). "
            "No collateral needed for Shishu. Apply via any public/private sector bank, MFI, or NBFC. "
            "Repayment period: 3–5 years. Use for buying equipment, raw materials, or expanding inventory. "
            "Suitable for food stalls, mobile vendors, small retail shops."
        ),
    },
    {
        "id": "upi_setup",
        "tags": ["upi", "qr", "payment", "gpay", "phonepe", "paytm", "digital payment", "how to"],
        "title": "UPI QR Code Setup for Vendors",
        "content": (
            "Step 1: Download any UPI app — Google Pay, PhonePe, Paytm, or BHIM. "
            "Step 2: Register with your mobile number linked to your bank account. "
            "Step 3: Go to 'Merchant' or 'Accept Payment' section. "
            "Step 4: Generate your unique QR code (free). "
            "Step 5: Print the QR code (A4 laminated) and display it at your stall. "
            "Step 6: Customers scan and pay directly to your bank. No smartphone needed for receiving. "
            "Tip: Keep transaction history as digital proof for future loan applications."
        ),
    },
    {
        "id": "pricing_fruit",
        "tags": ["pricing", "fruit", "vegetables", "produce", "margin", "profit"],
        "title": "Fruit & Vegetable Pricing Strategy",
        "content": (
            "Buy from APMC wholesale market early morning (4–6 AM) for lowest prices. "
            "Standard mark-up: 30–40% on fruits, 20–30% on vegetables. "
            "Seasonal fruit (mango, strawberry): can charge 50% premium in peak season. "
            "Bundle deals attract families — e.g., ₹100 fruit basket. "
            "Reduce waste: sell bruised fruit as juice/smoothie ingredients at 50% price. "
            "Compare prices with nearby vendors weekly to stay competitive."
        ),
    },
    {
        "id": "pricing_street_food",
        "tags": ["pricing", "food", "snacks", "tiffin", "vada pav", "pani puri", "chaat"],
        "title": "Street Food Pricing & Profit Tips",
        "content": (
            "Calculate cost per serving (raw material + gas + packaging). "
            "Target 60–70% gross margin. Example: Vada Pav raw cost ₹4–₹5, sell at ₹12–₹15. "
            "Pani Puri: cost ₹1.50/plate, sell ₹20–₹30. "
            "Weekend premium: increase prices by 10–15% on Saturday/Sunday. "
            "Festival season (Ganesh Chaturthi, Navratri): prepare special limited items with higher margin. "
            "Offer loyalty — buy 10 get 1 free cards to retain regular customers."
        ),
    },
    {
        "id": "local_seo_pune",
        "tags": ["seo", "online", "google", "maps", "pune", "listing", "digital visibility"],
        "title": "Local SEO & Online Listing for Pune Vendors",
        "content": (
            "Register on Google Business Profile (free): maps.google.com/business. "
            "Add your stall name, address (e.g., 'Camp, Pune'), phone, and photos. "
            "Use Justdial and IndiaMART for free local listings. "
            "Join Zomato/Swiggy as a local partner if you do tiffin or packaged food. "
            "Post reels on Instagram with location tag 'Pune Camp' or 'FC Road Pune'. "
            "WhatsApp Business: set up a catalogue with your items and prices. "
            "Ask happy customers to leave Google reviews — boosts local search ranking."
        ),
    },
    {
        "id": "local_seo_mumbai",
        "tags": ["seo", "online", "google", "maps", "mumbai", "listing", "digital visibility"],
        "title": "Local SEO & Online Listing for Mumbai Vendors",
        "content": (
            "Target high-footfall areas: Dadar, Bandra, Kurla, Andheri. "
            "Google Business Profile listing with 'near CST' or 'near Dadar station' keywords. "
            "Join local Facebook groups: 'Mumbai Street Food', 'Mumbai Deals'. "
            "Offer 'takeaway combos' and promote on Instagram Stories with Mumbai hashtags. "
            "Partner with local housing societies for weekly sabzi or tiffin delivery."
        ),
    },
    {
        "id": "local_seo_delhi",
        "tags": ["seo", "online", "google", "maps", "delhi", "listing", "digital visibility"],
        "title": "Local SEO & Online Listing for Delhi Vendors",
        "content": (
            "Register on Google Maps near major landmarks: Connaught Place, Chandni Chowk, Saket. "
            "Use Delhi-specific hashtags on Instagram: #DelhiStreetFood #ChandniChowkFood. "
            "List on Magicpin for local discovery and cashback offers. "
            "WhatsApp broadcast list: send daily menu to loyal customers. "
            "NDMC and SDMC often have vendor facilitation desks for digital onboarding."
        ),
    },
    {
        "id": "customer_engagement",
        "tags": ["marketing", "customer", "loyalty", "engagement", "retention", "whatsapp"],
        "title": "Customer Engagement & Retention Tips",
        "content": (
            "Create a WhatsApp group for regular customers — share daily specials and offers. "
            "Offer a referral bonus: 'Bring a friend, get ₹10 off'. "
            "Seasonal greetings with special offers build loyalty. "
            "Maintain a simple notebook or Google Sheet ledger of top customers. "
            "QR code on packaging linking to your WhatsApp or Google listing. "
            "Respond quickly to messages — even a voice note builds trust. "
            "Simple loyalty card (stamp card) printed at ₹2/card works very well."
        ),
    },
    {
        "id": "digital_profile_tips",
        "tags": ["profile", "bio", "flyer", "digital card", "branding", "name"],
        "title": "Creating Your Digital Business Profile",
        "content": (
            "A great vendor profile includes: Shop Name, Owner Name, Location, Specialty items, "
            "UPI ID or QR code, WhatsApp number, and a short tagline. "
            "Tools: Canva (free) to design a digital flyer; share on WhatsApp, Facebook, Instagram. "
            "Photo tip: bright natural light, clean background, colourful produce/food in frame. "
            "Tagline formula: [Specialty] + [Location] + [USP] e.g., 'Fresh Alphonso Mangoes | Camp Pune | Farm-to-Street Daily'."
        ),
    },
]


def _keyword_match_score(query: str, doc: dict) -> int:
    """Simple TF-style keyword scoring for RAG retrieval."""
    query_lower = query.lower()
    score = 0
    for tag in doc["tags"]:
        if tag in query_lower:
            score += 3
    words = query_lower.split()
    for word in words:
        if len(word) > 3 and word in doc["content"].lower():
            score += 1
    return score


def retrieve_context(query: str, top_k: int = 3) -> str:
    """Return concatenated content from top-k relevant KB documents."""
    scored = [(doc, _keyword_match_score(query, doc)) for doc in KNOWLEDGE_BASE]
    scored.sort(key=lambda x: x[1], reverse=True)
    top_docs = [doc for doc, score in scored[:top_k] if score > 0]
    if not top_docs:
        # Fallback: return first 2 generic docs
        top_docs = KNOWLEDGE_BASE[:2]
    return "\n\n---\n\n".join(
        f"### {doc['title']}\n{doc['content']}" for doc in top_docs
    )


# ---------------------------------------------------------------------------
# IBM IAM Authentication
# ---------------------------------------------------------------------------
def get_iam_token() -> str:
    """Exchange IBM_API_KEY for a bearer access token, with simple caching."""
    global _token_cache
    if _token_cache["token"] and time.time() < _token_cache["expiry"]:
        return _token_cache["token"]

    response = requests.post(
        IBM_IAM_TOKEN_URL,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
            "apikey": IBM_API_KEY,
        },
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()
    _token_cache["token"] = data["access_token"]
    # Cache for 10 minutes less than actual expiry to be safe
    _token_cache["expiry"] = time.time() + data.get("expires_in", 3600) - 600
    return _token_cache["token"]


# ---------------------------------------------------------------------------
# watsonx Generation
# ---------------------------------------------------------------------------
def generate_text(prompt: str, max_tokens: int = 800) -> str:
    """Call IBM watsonx text generation endpoint."""
    token = get_iam_token()
    payload = {
        "model_id": MODEL_ID,
        "input": prompt,
        "parameters": {
            "decoding_method": "greedy",
            "max_new_tokens": max_tokens,
            "min_new_tokens": 30,
            "stop_sequences": [],
            "repetition_penalty": 1.1,
        },
        "project_id": PROJECT_ID,
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    response = requests.post(
        WATSONX_GENERATION_URL,
        headers=headers,
        json=payload,
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    return data["results"][0]["generated_text"].strip()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    """
    Accepts vendor input, retrieves RAG context, calls IBM Granite,
    returns personalised advice.
    """
    body = request.get_json(force=True)
    user_message = (body.get("message") or "").strip()
    language = (body.get("language") or "english").lower()

    if not user_message:
        return jsonify({"error": "message is required"}), 400

    context = retrieve_context(user_message)

    lang_instruction = ""
    if language == "hindi":
        lang_instruction = "Respond in simple Hindi (Devanagari script). "
    elif language == "marathi":
        lang_instruction = "Respond in simple Marathi (Devanagari script). "
    else:
        lang_instruction = "Respond in simple, clear English. "

    prompt = f"""You are a helpful digital business advisor for street vendors, hawkers, and micro-entrepreneurs in India. {lang_instruction}

Use the following knowledge base context to give accurate, actionable advice:

{context}

Vendor's question or situation:
{user_message}

Provide a friendly, practical response with:
1. Direct answer to their question
2. Step-by-step actions they can take today
3. Relevant government schemes or digital tools if applicable
4. One motivational tip

Response:"""

    try:
        reply = generate_text(prompt, max_tokens=600)
        return jsonify({"reply": reply})
    except requests.HTTPError as e:
        return jsonify({"error": f"watsonx API error: {e.response.status_code}"}), 502
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/generate-profile", methods=["POST"])
def generate_profile():
    """
    Accepts vendor details and generates a digital flyer bio using IBM Granite.
    """
    body = request.get_json(force=True)
    business_name = (body.get("business_name") or "").strip()
    location = (body.get("location") or "").strip()
    item_type = (body.get("item_type") or "").strip()
    owner_name = (body.get("owner_name") or "").strip()
    upi_id = (body.get("upi_id") or "").strip()
    language = (body.get("language") or "english").lower()

    if not business_name or not location or not item_type:
        return jsonify({"error": "business_name, location, and item_type are required"}), 400

    lang_instruction = ""
    if language == "hindi":
        lang_instruction = "Write the profile in simple Hindi. "
    elif language == "marathi":
        lang_instruction = "Write the profile in simple Marathi. "
    else:
        lang_instruction = "Write the profile in English. "

    upi_line = f"UPI ID: {upi_id}" if upi_id else "UPI payments accepted (QR available at stall)"
    owner_line = f"Owner: {owner_name}" if owner_name else ""

    prompt = f"""You are a professional digital marketing copywriter helping Indian street vendors create their business profile. {lang_instruction}

Create a complete digital business profile / flyer text for this vendor:

Business Name: {business_name}
{owner_line}
Location: {location}
Products/Services: {item_type}
Payment: {upi_line}

Generate the following sections:
1. 📛 Business Name & Tagline (catchy, memorable)
2. 📍 Location & Timings (suggest typical timings if not provided)
3. 🛒 Specialty Products (expand on what they sell with descriptions)
4. 💳 How to Pay & Order (digital payment instructions)
5. ⭐ Why Choose Us (3 unique selling points)
6. 📢 WhatsApp/Social Media Bio (2-line bio for WhatsApp Business or Instagram)
7. 🎯 SEO Keywords (5 search keywords locals can use to find them)

Make it warm, professional, and suitable for printing as a flyer or sharing on WhatsApp.

Profile:"""

    try:
        profile_text = generate_text(prompt, max_tokens=800)
        return jsonify({"profile": profile_text})
    except requests.HTTPError as e:
        return jsonify({"error": f"watsonx API error: {e.response.status_code}"}), 502
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
