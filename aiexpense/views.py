from django.contrib.auth import logout as auth_logout

def logout_view(request):
    auth_logout(request)
    return redirect('dashboard')
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from .models import Expense
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
import re
from datetime import datetime
import cv2
import numpy as np
import os

# ✅ Set Tesseract environment
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
os.environ['TESSDATA_PREFIX'] = r"C:\Program Files\Tesseract-OCR\tessdata"

def preprocess_for_ocr(pil_image):
    """
    Preprocessing optimized for printed bills & receipts.
    Focus: bold totals, clean digits, stable contrast.
    """
    img = np.array(pil_image)

    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img

    # Resize FIRST (helps OCR read big totals)
    gray = cv2.resize(gray, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)

    # Remove noise
    gray = cv2.bilateralFilter(gray, 9, 75, 75)

    # Improve contrast
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)

    # Adaptive threshold (clean background)
    gray = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_MEAN_C,
        cv2.THRESH_BINARY,
        15, 4
    )

    # Strengthen text (esp. totals)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    gray = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)

    return Image.fromarray(gray)

def preprocess_upi_image(pil_image):
    """Preprocess UPI screenshot images for better OCR accuracy."""
    img = np.array(pil_image)

    # Convert to grayscale
    if len(img.shape) == 3 and img.shape[2] == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    else:
        gray = img if len(img.shape) == 2 else cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

    # ===== STEP 1: Denoise =====
    gray = cv2.fastNlMeansDenoising(gray, None, h=15, templateWindowSize=7, searchWindowSize=21)

    # ===== STEP 2: Enhance Contrast with CLAHE =====
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)

    # ===== STEP 3: Bilateral Filtering =====
    # Preserve edges while smoothing
    gray = cv2.bilateralFilter(gray, 9, 75, 75)

    # ===== STEP 4: Upscale Image =====
    # UPI text is smaller, so 3x upscale for better OCR
    gray = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)

    # ===== STEP 5: Thresholding =====
    # Otsu's thresholding for automatic optimal threshold
    _, gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # ===== STEP 6: Morphological Cleanup =====
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    gray = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel, iterations=1)

    return Image.fromarray(gray)

def detect_image_type(text):
    text = text.lower()

    upi_keywords = [
        "upi",
        "google pay",
        "g pay",
        "phonepe",
        "paytm",
        "transaction id",
        "utr",
        "to:",
        "from:"
    ]

    if any(k in text for k in upi_keywords):
        return "upi"

    return "bill"


from datetime import datetime

def extract_date(text):

    patterns = [
        r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        r'(\d{4}[/-]\d{1,2}[/-]\d{1,2})',
        r'(\d{1,2}\s*[A-Za-z]{3,9}\s*\d{4})',
        r'([A-Za-z]{3,9}\s*\d{1,2}[,]?\s*\d{4})',
        r'(\d{2}/\d{2})', # MM/YY or DD/MM
        r'(\d{2}-\d{2})', # MM-YY or DD-MM
        r'BATCH:\s*[A-Za-z0-9]+:\s*(\d{2}[/-]\d{2})', # Batch date
    ]
    from datetime import datetime
    import re
    from datetime import datetime
    sep = r"[\/\-\.:]"
    patterns = [
        rf"(\d{{1,2}}{sep}\d{{1,2}}{sep}\d{{2,4}})",
        rf"(\d{{4}}{sep}\d{{1,2}}{sep}\d{{1,2}})",
        r"(\d{1,2}\s*[A-Za-z]{3,9}\s*\d{4})",
        r"([A-Za-z]{3,9}\s*\d{1,2}[,]?\s*\d{4})",
        rf"(\d{{2}}{sep}\d{{2}})",
    ]
    payment_keywords = ["total", "amount paid", "payment", "paid", "mode", "date", "bill", "invoice"]
    exclude_keywords = ["batch", "expiry", "exp", "mfg", "manufacture"]
    lines = text.splitlines()
    def clean_date_str(s):
        s = s.replace('O', '0').replace('o', '0').replace('l', '1').replace('I', '1')
        s = s.replace('S', '5').replace('B', '8')
        s = re.sub(r'\s+', ' ', s)
        return s.strip()
    # 1. Context-aware scan
    date_candidates = []
    for idx, line in enumerate(lines):
        line_lower = line.lower()
        if any(ex_kw in line_lower for ex_kw in exclude_keywords):
            continue
        if any(pk in line_lower for pk in payment_keywords) or idx >= len(lines) - 5:
            for pattern in patterns:
                matches = re.findall(pattern, line)
                for date_str in matches:
                    date_candidates.append(clean_date_str(date_str))
    # 2. Try parsing context candidates
    plausible_dates = []
    for date_str in date_candidates:
        for fmt in [
            "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d:%m:%Y",
            "%Y/%m/%d", "%Y-%m-%d", "%Y.%m.%d", "%Y:%m:%d",
            "%d %b %Y", "%d %B %Y", "%b %d %Y", "%B %d %Y",
            "%d/%m/%y", "%d-%m-%y", "%d.%m.%y", "%d:%m:%y",
            "%m/%y", "%m-%y", "%m.%y", "%m:%y",
            "%d/%m", "%d-%m", "%d.%m", "%d:%m"
        ]:
            try:
                dt = datetime.strptime(date_str, fmt)
                if 2000 <= dt.year <= datetime.now().year + 1:
                    plausible_dates.append(dt)
            except Exception:
                continue
    if plausible_dates:
        return max(plausible_dates)
    # 3. Fallback: scan all lines for any plausible date
    for line in lines:
        if any(ex_kw in line.lower() for ex_kw in exclude_keywords):
            continue
        for pattern in patterns:
            matches = re.findall(pattern, line)
            for date_str in matches:
                date_str = clean_date_str(date_str)
                for fmt in [
                    "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d:%m:%Y",
                    "%Y/%m/%d", "%Y-%m-%d", "%Y.%m.%d", "%Y:%m:%d",
                    "%d %b %Y", "%d %B %Y", "%b %d %Y", "%B %d %Y",
                    "%d/%m/%y", "%d-%m-%y", "%d.%m.%y", "%d:%m:%y",
                    "%m/%y", "%m-%y", "%m.%y", "%m:%y",
                    "%d/%m", "%d-%m", "%d.%m", "%d:%m"
                ]:
                    try:
                        dt = datetime.strptime(date_str, fmt)
                        if 2000 <= dt.year <= datetime.now().year + 1:
                            plausible_dates.append(dt)
                    except Exception:
                        continue
    if plausible_dates:
        return max(plausible_dates)
    # 4. Last fallback: search for year in all lines
    for line in lines:
        year_match = re.search(r"(20\d{2})", line)
        if year_match:
            try:
                return datetime.strptime(year_match.group(1), "%Y")
            except Exception:
                continue
    return None

def index(request):
    return render(request, "index.html")   # public home page

def signup_view(request):
    if request.method == "POST":
        name = request.POST["name"]
        email = request.POST["email"].lower().strip()
        password = request.POST["password"]
        confirm_password = request.POST["confirm_password"]

        # Password check
        if password != confirm_password:
            return render(request, "signup.html", {
                "error": "Passwords do not match"
            })

        # Email already exists?
        if User.objects.filter(email=email).exists():
            return render(request, "signup.html", {
                "error": "Email already in use"
            })

        # 🔥 IMPORTANT: username = email (for email login)
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password
        )
        user.first_name = name
        user.save()

        return redirect("login")

    return render(request, "signup.html")


def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email").lower().strip()
        password = request.POST.get("password")

        # Authenticate using email as username
        user = authenticate(
            request,
            username=email,
            password=password
        )

        if user is not None:
            login(request, user)
            messages.success(request, "Logged in successfully!")
            return redirect("dashboard")
        else:
            messages.error(request, "Invalid email or password!")

        print(User.objects.filter(username=email))

    return render(request, "login.html")

@login_required
def dashboard(request):
    """
    Dashboard view - displays user's expenses and expense entry forms.
    Focuses on: quick overview, expense entry, and recent expenses list.
    Charts and analytics have been moved to /analytics/ page.
    """
    # Fetch user's expenses ordered by most recent first
    expenses = Expense.objects.filter(user=request.user).order_by("-date")

    # Calculate total expenses
    total_expense = Expense.objects.filter(
        user=request.user
    ).aggregate(total=Sum("amount"))["total"] or 0

    # Get scanned data from session (populated by scan_receipt_view)
    context = {
        "expenses": expenses,
        "total_expense": total_expense,
        "ocr_text": request.session.pop("raw_text", None),
        "merchant_name": request.session.pop("scanned_title", None),
        "detected_amount": request.session.pop("scanned_amount", None),
        "detected_category": request.session.pop("scanned_category", None),
        "detected_date": request.session.pop("scanned_date", None),
    }

    return render(request, "dashboard.html", context)

from datetime import date
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from .models import Expense


@login_required
def add_expense_view(request):
    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        amount = request.POST.get("amount")
        category = request.POST.get("category", "").strip()
        expense_date = request.POST.get("date")

        # 🔹 Validation
        if not title:
            messages.error(request, "Title cannot be empty.")
            return redirect("/dashboard/")

        if not category:
            messages.error(request, "Category cannot be empty.")
            return redirect("/dashboard/")

        try:
            amount = float(amount)
            if amount <= 0:
                messages.error(request, "Amount must be greater than 0.")
                return redirect("/dashboard/")
        except:
            messages.error(request, "Invalid amount.")
            return redirect("/dashboard/")

        if not expense_date:
            messages.error(request, "Date is required.")
            return redirect("/dashboard/")

        if expense_date > str(date.today()):
            messages.error(request, "Date cannot be in the future.")
            return redirect("/dashboard/")

        # 🔹 Save expense
        Expense.objects.create(
            user=request.user,
            title=title,
            amount=amount,
            category=category,
            date=expense_date
        )

        messages.success(request, "Expense added successfully!")
        return redirect("/dashboard/")

    return redirect("/dashboard/")

from django.shortcuts import get_object_or_404

@login_required
def delete_expense_view(request, id):
    expense = get_object_or_404(Expense, id=id)

    # Security check: only owner can delete
    if expense.user != request.user:
        messages.error(request, "You are not allowed to delete this expense.")
        return redirect("/dashboard/")

    expense.delete()
    messages.success(request, "Expense deleted successfully.")
    return redirect("/dashboard/")

def extract_total_amount(text):
    import re
    import unicodedata

    # ---------- Normalize OCR text ----------
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[^\x20-\x7E₹\n]", " ", text)
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    def is_valid_amount(val):
        try:
            amt = float(val)
            return 1 <= amt <= 100000
        except:
            return False

    # ---------- 1️⃣ PRINTED BILL / RECEIPT KEYWORDS ----------
    BILL_KEYWORDS = [
        "amount paid",
        "total amount",
        "grand total",
        "net amount",
        "total payable",
        "final amount",
        "subtotal",
        "total:"
    ]

    for line in lines:
        low = line.lower()
        if any(k in low for k in BILL_KEYWORDS):
            m = re.search(r"(₹|rs\.?|inr)?\s*([0-9]{1,6}(?:\.[0-9]{1,2})?)", line, re.I)
            if m and is_valid_amount(m.group(2)):
                return float(m.group(2))

    # ---------- 2️⃣ UPI EXPLICIT KEYWORDS ----------
    UPI_KEYWORDS = [
        "paid",
        "debited",
        "sent",
        "credited"
    ]

    for line in lines:
        low = line.lower()
        if any(k in low for k in UPI_KEYWORDS):
            m = re.search(r"(₹|rs\.?|inr)?\s*([0-9]{1,6}(?:\.[0-9]{1,2})?)", line, re.I)
            if m and is_valid_amount(m.group(2)):
                return float(m.group(2))

    # ---------- 3️⃣ UPI X-AMOUNT FORMAT (X145) ----------
    for line in lines:
        m = re.search(r"\b[xX]\s*([0-9]{1,6}(?:\.[0-9]{1,2})?)\b", line)
        if m and is_valid_amount(m.group(1)):
            return float(m.group(1))

    # ---------- 4️⃣ ₹ / INR ANYWHERE ----------
    m = re.search(r"(₹|rs\.?|inr)\s*([0-9]{1,6}(?:\.[0-9]{1,2})?)", text, re.I)
    if m and is_valid_amount(m.group(2)):
        return float(m.group(2))

    # ---------- 5️⃣ SAFE FALLBACK: LARGEST REASONABLE NUMBER ----------
    candidates = []
    for m in re.finditer(r"\b([0-9]{1,6}(?:\.[0-9]{1,2})?)\b", text):
        if is_valid_amount(m.group(1)):
            candidates.append(float(m.group(1)))

    return max(candidates) if candidates else None

@login_required
def edit_expense_view(request, id):
    expense = get_object_or_404(Expense, id=id)

    # Security check
    if expense.user != request.user:
        messages.error(request, "You are not allowed to edit this expense.")
        return redirect("/dashboard/")

    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        amount = request.POST.get("amount")
        category = request.POST.get("category", "").strip()
        expense_date = request.POST.get("date")

        # 🔹 Validation
        if not title:
            messages.error(request, "Title cannot be empty.")
            return redirect(f"/edit-expense/{id}/")

        if not category:
            messages.error(request, "Category cannot be empty.")
            return redirect(f"/edit-expense/{id}/")

        try:
            amount = float(amount)
            if amount <= 0:
                messages.error(request, "Amount must be greater than 0.")
                return redirect(f"/edit-expense/{id}/")
        except:
            messages.error(request, "Invalid amount.")
            return redirect(f"/edit-expense/{id}/")

        if not expense_date:
            messages.error(request, "Date is required.")
            return redirect(f"/edit-expense/{id}/")

        if expense_date > str(date.today()):
            messages.error(request, "Date cannot be in the future.")
            return redirect(f"/edit-expense/{id}/")

        # 🔹 Update expense
        expense.title = title
        expense.amount = amount
        expense.category = category
        expense.date = expense_date
        expense.save()

        messages.success(request, "Expense updated successfully.")
        return redirect("/dashboard/")

    return render(request, "edit_expense.html", {"expense": expense})


def run_ocr(image):
    gray = image.convert("L")
    gray = ImageEnhance.Contrast(gray).enhance(3)

    text = pytesseract.image_to_string(
        gray,
        config="--oem 3 --psm 6"
    )

    return text


def detect_image_type(text):
    """
    Detect whether the uploaded image is:
    - UPI payment screenshot
    - Printed bill / receipt
    """

    text = text.lower()

    upi_keywords = [
        "upi", "txn id", "transaction id",
        "paid to", "google pay", "phonepe",
        "paytm", "successful", "debited from"
    ]

    bill_keywords = [
        "invoice", "bill", "cash memo",
        "total", "subtotal", "grand total",
        "amount payable", "gst", "tax"
    ]

    if any(word in text for word in upi_keywords):
        return "upi"

    if any(word in text for word in bill_keywords):
        return "bill"

    return "unknown"


def extract_title(text):
    """Extract merchant/shop name from receipt or UPI transaction."""
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    text_lower = text.lower()

    # ===== UPI TRANSACTIONS: Look for recipient/payer name =====
    for line in lines:
        line_clean = line.strip()
        if line_clean.lower().startswith("to:"):
            recipient = line_clean.replace("To:", "").replace("to:", "").strip()
            if recipient and len(recipient) > 2:
                print(f"[DEBUG] UPI recipient found: {recipient}")
                return recipient
        elif line_clean.lower().startswith("from:"):
            payer = line_clean.replace("From:", "").replace("from:", "").strip()
            if payer and len(payer) > 2:
                print(f"[DEBUG] UPI payer found: {payer}")
                return f"Payment to {payer}"

    # ===== BILL/RECEIPT: Look for merchant/shop name =====
    metadata_keywords = [
        "gst", "phone", "email", "invoice", "bill no", "bill number",
        "date", "time", "tax", "total", "amount", "transaction",
        "utr", "ref", "reference", "status", "success", "order",
        "payment", "received", "thank you", "gstin", "pan",
        "sub total", "discount", "balance", "payable", "due", "cash"
    ]

    candidates = []
    
    for idx, line in enumerate(lines):
        line_clean = line.strip()
        line_lower = line_clean.lower()
        
        # Skip too short
        if len(line_clean) < 3:
            continue
        
        # Skip pure numbers (bill numbers)
        if re.match(r'^\d+$', line_clean):
            continue
        
        # Skip lines with too many digits (likely invoice/bill numbers)
        digit_count = len(re.findall(r'\d', line_clean))
        if digit_count > len(line_clean) * 0.6:
            continue
        
        # Skip metadata lines
        if any(keyword in line_lower for keyword in metadata_keywords):
            continue
        
        # Skip lines without letters
        if len(re.findall(r'[a-zA-Z]', line_clean)) < 2:
            continue
        
        # Score candidate lines
        score = 0
        
        # Prefer lines appearing earlier
        score += (len(lines) - idx) * 10
        
        # Prefer reasonable length merchant names
        if 3 <= len(line_clean) <= 50:
            score += 50
        
        # Prefer mixed case
        if re.search(r'[A-Z]', line_clean):
            score += 20
        
        # Penalize lines with numbers
        if digit_count > 0:
            score -= digit_count * 5
        
        if score > 0:
            candidates.append((line_clean, score))
    
    if candidates:
        candidates.sort(key=lambda x: x[1], reverse=True)
        best_merchant = candidates[0][0]
        print(f"[DEBUG] Selected merchant: {best_merchant}")
        return best_merchant

    print(f"[DEBUG] No merchant name found, returning 'Expense'")
    return "Expense"

def suggest_category(text):
    """Suggest category based on receipt/UPI text with enhanced keywords."""
    text_lower = text.lower()

    # Track match count for each category (for better accuracy)
    matches = {}

    # ========== FOOD & DINING (HIGHEST KEYWORD MATCH) ==========
    food_keywords = [
        "food", "drink", "restaurant", "cafe", "coffee", "starbucks",
        "ice cream", "icecream", "beverage", "meal", "lunch", "dinner",
        "breakfast", "bakery", "pizza", "burger", "fast food", "snack",
        "tea", "juice", "hotel", "dhaba", "chinese", "biryani",
        "pizza hut", "dominos", "kfc", "mcdonalds", "subway",
        "swiggy", "zomato", "food delivery", "restaurant delivery",
        "pastry", "cake", "donut", "fries", "sandwich", "wrap",
        "noodles", "pasta", "ramen", "sushi", "rolls", "chicken",
        "cafe coffee", "barista", "costa", "cafe cafe", "indian food",
        "south indian", "north indian", "dosa", "idli", "panipuri", "chat",
        "momos", "samosa", "vada", "grill", "shawarma", "kebab"
    ]
    if any(word in text_lower for word in food_keywords):
        matches['Food'] = matches.get('Food', 0) + sum(1 for word in food_keywords if word in text_lower)

    # ========== TRAVEL & TRANSPORT ==========
    travel_keywords = [
        "uber", "ola", "taxi", "bus", "train", "metro", "railway",
        "flight", "airbnb", "travel", "transport", "cab", "autorickshaw",
        "petrol", "fuel", "parking", "tolls", "auto", "rickshaw",
        "booking.com", "makemytrip", "goibibo", "cleartrip", "yatra",
        "flight ticket", "train ticket", "bus ticket", "bus service",
        "railway station", "airport", "metro card", "toll", "highway",
        "vehicle", "transport service", "ride", "booking", "hotel"
    ]
    if any(word in text_lower for word in travel_keywords):
        matches['Travel'] = matches.get('Travel', 0) + sum(1 for word in travel_keywords if word in text_lower)

    # ========== SHOPPING & RETAIL ==========
    shopping_keywords = [
        "amazon", "flipkart", "mall", "shopping", "store", "retail",
        "apparel", "clothing", "shoes", "electronics", "gadgets",
        "clothes", "dress", "shirt", "pant", "trouser", "jacket",
        "myntra", "ajio", "uniqlo", "h&m", "zara", "forever 21",
        "shopee", "daraz", "alibaba", "ebay", "snapdeal",
        "decathlon", "nike", "adidas", "puma", "new balance",
        "apple store", "microsoft store", "samsung", "iphone", "laptop",
        "mobile", "phone", "watch", "headphone", "charger", "cable",
        "cloths", "footwear", "shoes store", "apparel store", "boutique"
    ]
    if any(word in text_lower for word in shopping_keywords):
        matches['Shopping'] = matches.get('Shopping', 0) + sum(1 for word in shopping_keywords if word in text_lower)

    # ========== ENTERTAINMENT & MEDIA ==========
    entertainment_keywords = [
        "movie", "cinema", "theatre", "theater", "concert", "tickets",
        "show", "entertainment", "gaming", "sports", "spotify", "netflix",
        "amazon prime", "hotstar", "zee5", "youtube premium", "music",
        "game", "playstation", "xbox", "pc game", "steam",
        "bookmyshow", "paf", "uci cinema", "imax", "pvr",
        "inox", "cineplex", "comedy club", "theater tickets",
        "event", "festival", "match", "sports ticket"
    ]
    if any(word in text_lower for word in entertainment_keywords):
        matches['Entertainment'] = matches.get('Entertainment', 0) + sum(1 for word in entertainment_keywords if word in text_lower)

    # ========== HEALTHCARE & MEDICINE ==========
    healthcare_keywords = [
        "hospital", "clinic", "pharmacy", "doctor", "medicine",
        "medical", "medicals", "lab", "diagnostic", "health",
        "treatment", "surgeon", "dental", "ayurveda", "homeopathy",
        "chemist", "apothecary", "cure", "disease", "test",
        "x-ray", "ultrasound", "ct scan", "pathology", "blood test",
        "vaccine", "vaccination", "medical store", "health center",
        "eye care", "ophthalmology", "dental clinic", "surgery",
        "physiotherapy", "gym", "fitness", "wellness", "spa",
        "beauty", "salon", "haircut", "grooming"
    ]
    if any(word in text_lower for word in healthcare_keywords):
        matches['Medicine'] = matches.get('Medicine', 0) + sum(1 for word in healthcare_keywords if word in text_lower)

    # ========== GROCERIES & ESSENTIALS ==========
    grocery_keywords = [
        "vegetable", "grocery", "supermarket", "mart", "market",
        "counter", "dmart", "more", "bisleri", "big basket",
        "spice", "rice", "flour", "atta", "oil", "milk",
        "dairy", "eggs", "bread", "butter", "yogurt", "cheese",
        "jaggery", "sugar", "salt", "masala", "herbs", "dried goods",
        "fresh produce", "fruits", "vegetables market", "local market",
        "weekly bazaar", "organic store", "health store",
        "blinkit", "zepto", "grofers", "amazon fresh", "dunzo",
        "instamart", "milk man", "pharmacy grocery"
    ]
    if any(word in text_lower for word in grocery_keywords):
        matches['Groceries'] = matches.get('Groceries', 0) + sum(1 for word in grocery_keywords if word in text_lower)

    # ========== UTILITIES & BILLS ==========
    utilities_keywords = [
        "electricity", "water", "bill", "mobile", "internet",
        "phone", "broadband", "utility", "meter", "power",
        "electric", "water supply", "telephone", "sim", "recharge",
        "airtel", "jio", "vodafone", "idea", "bsnl",
        "dth", "cable", "broadband plan", "wifi", "isp",
        "electricity board", "water authority", "municipal", "tax"
    ]
    if any(word in text_lower for word in utilities_keywords):
        matches['Utilities'] = matches.get('Utilities', 0) + sum(1 for word in utilities_keywords if word in text_lower)

    # ========== Return category with highest match count ==========
    if matches:
        best_category = max(matches, key=matches.get)
        print(f"[DEBUG] Category matches: {matches}")
        print(f"[DEBUG] Selected category: {best_category}")
        return best_category

    print(f"[DEBUG] No category matches found, returning 'Other'")
    return "Other"

# make sure these exist in your file
# extract_total_amount(text)
# extract_date(text)
# extract_merchant(text)
# suggest_category(text)



@login_required
def analytics_dashboard(request):
    """
    Analytics and machine learning dashboard
    Shows: predictions, insights, anomalies, and visualizations
    """
    from .analytics import get_analytics_dashboard
    
    try:
        analytics_data = get_analytics_dashboard(request.user)
        
        context = {
            'analytics': analytics_data,
            'page_title': 'Analytics & Predictions'
        }
        
        return render(request, 'analytics_dashboard.html', context)
        
    except Exception as e:
        print(f"ERROR in analytics_dashboard: {e}")
        import traceback
        traceback.print_exc()
        
        messages.error(request, f"Failed to load analytics: {str(e)}")
        return redirect("dashboard")


@login_required
def scan_receipt_view(request):

    if request.method == "POST" and request.FILES.get("receipt"):

        try:
            uploaded_file = request.FILES["receipt"]

            # ✅ Convert to PIL Image
            image = Image.open(uploaded_file)
            
            print(f"\n[INFO] Image loaded: {uploaded_file.name}")

            # ✅ First pass: basic OCR to detect image type (simple config)
            try:
                gray = image.convert("L")
                text = pytesseract.image_to_string(gray, config="--oem 3 --psm 6")
                
                print("\n" + "="*60)
                print("OCR TEXT (First pass - detection):")
                print(text[:500] if text else "[NO TEXT DETECTED]")
                print("="*60)
            except Exception as ocr_error:
                print(f"[WARNING] First pass OCR failed: {ocr_error}")
                text = ""

            # ✅ Detect image type and reprocess
            image_type = detect_image_type(text)
            print(f"\n[TYPE DETECTED] {image_type.upper()}")
            
            if image_type == "upi":
                preprocessed = preprocess_upi_image(image)
                # UPI: Enhanced config for better text recognition
                ocr_config = "--oem 3 --psm 4 -c preserve_interword_spaces=1"
            else:
                preprocessed = preprocess_for_ocr(image)
                # Bills: Enhanced config for structured text
                ocr_config = "--oem 3 --psm 4 -c preserve_interword_spaces=1"
            
            # ✅ Second pass: OCR with optimized preprocessing
            try:
                text = pytesseract.image_to_string(
                    preprocessed,
                    config=ocr_config
                )
                print("\n" + "="*60)
                print("OCR TEXT (Preprocessed - final):")
                print(text if text else "[NO TEXT DETECTED]")
                print("="*60)
            except Exception as ocr_error:
                print(f"[ERROR] Second pass OCR failed: {ocr_error}")
                import traceback
                traceback.print_exc()
                messages.error(request, f"OCR Error: Failed to read receipt. {str(ocr_error)}")
                return redirect("dashboard")
            # 🔁 SECOND OCR PASS: focus on bottom area (totals usually there)
            width, height = preprocessed.size

# Crop bottom 40% of the receipt
            bottom_crop = preprocessed.crop((
                0,
                int(height * 0.6),
                width,
                height
            ))

            bottom_text = pytesseract.image_to_string(
                bottom_crop,
                config="--oem 3 --psm 6"
            )

# Merge bottom OCR text with main text
            text += "\n" + bottom_text          

            print("\n[DEBUG] OCR TEXT (Bottom Crop):")
            print(bottom_text if bottom_text else "[NO TEXT DETECTED]")         
            # Extract data
            amount = extract_total_amount(text)
            detected_date = extract_date(text)
            title = extract_title(text)
            category = suggest_category(text)

            # Debug: print extracted values
            print(f"\n{'='*60}")
            print(f"EXTRACTION RESULTS")
            print(f"{'='*60}")
            print(f"Amount: ₹{amount}")
            print(f"Date: {detected_date}")
            print(f"Title: {title}")
            print(f"Category: {category}")
            print(f"{'='*60}\n")

            # Validate extracted data
            if not amount:
                messages.warning(request, "⚠️ Scan complete but amount not found. Please enter it manually.")
            if not category or category == "Other":
                messages.warning(request, "⚠️ Category not detected. Please select it manually.")

            # Store in session (convert amount to string)
            request.session["scanned_title"] = title or ""
            request.session["scanned_amount"] = str(amount) if amount else ""
            request.session["scanned_category"] = category or ""
            request.session["scanned_date"] = detected_date.strftime("%Y-%m-%d") if detected_date and isinstance(detected_date, datetime) else (detected_date or "")
            request.session["raw_text"] = text or ""

            messages.success(request, "✅ Scan successful! Review the auto-detected values.")

            return redirect("dashboard")

        except Exception as e:

            print(f"\n[CRITICAL ERROR] Scan failed: {e}")
            import traceback
            traceback.print_exc()

            messages.error(request, f"Scan failed: {str(e)}")
            return redirect("dashboard")

    return redirect("dashboard")