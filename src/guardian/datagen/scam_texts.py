import numpy as np
import pandas as pd
from typing import Tuple

# Families of templates separated strictly to prevent train-test contamination
TEMPLATES = {
    "otp_pin_request": {
        "train": [
            "জরুরি: আপনার {wallet} অ্যাকাউন্ট সাময়িক বন্ধ করা হয়েছে। অবিলম্বে পিন এবং পাঠানো {code} ওটিপি দিয়ে অ্যাকাউন্ট চালু করুন।",
            "Customer care theke bolchi, apnar account verify korte {code} number ta bolun.",
            "Alert! Your {wallet} wallet is suspended. Send verification PIN and code {code} to reactivate immediately.",
            "আপনার একাউন্ট থেকে ৳{amount} কাটার অনুরোধ পেয়েছি। বাতিল করতে ওটিপি কোডটি জানান।"
        ],
        "test": [
            "জরুরি নিরাপত্তা সতর্কবার্তা: সার্ভিস চালু রাখতে মেসেজের {code} কোডটি কারো সাথে শেয়ার করবেন না না বলে আমাদের জানান।",
            "Apnar {wallet} account theke taka kete jabe, thamate ekhoni incoming OTP {code} share korun.",
            "Important advisory: Reply with secret PIN to confirm you authorized transaction TXN{code}."
        ]
    },
    "fake_agent_support": {
        "train": [
            "আমরা {wallet} প্রধান কার্যালয় থেকে বলছি। আপনার KYC আপডেট না থাকায় অ্যাকাউন্ট বন্ধ হচ্ছে। যোগাযোগ করুন {phone} নম্বরে।",
            "Apnar upaye technical error hoyeche, thik korte helpline {phone} e kotha bolun ekhoni.",
            "Official Head Office Alert: Send ৳{amount} security deposit to agent number {phone} to unlock your balance."
        ],
        "test": [
            "সার্ভিস সেন্টার বার্তা: কারিগরি ত্রুটির কারণে আপনার ওয়ালেট ব্লক হয়েছে। রিকভারি করতে অবিলম্বে {phone} এজেন্টে কল করুন।",
            "System issue detect kora hoyeche, agent {phone} er shathe jogajog kore verify korun."
        ]
    },
    "sent_by_mistake": {
        "train": [
            "ভাই ভুল করে আপনার নম্বরে ৳{amount} চলে গেছে। দয়া করে এই নম্বরে {phone} টাকাটা ফেরত পাঠিয়ে দিন, খুব বিপদে আছি।",
            "Bhai bhul kore ৳{amount} send money hoye geche apnar account e. Please eita {phone} e refund kore den.",
            "Mistakenly transferred ৳{amount} to your wallet. Please return the funds urgently to {phone}."
        ],
        "test": [
            "ছোট বোনের চিকিৎসার ৳{amount} ভুল করে আপনার অ্যাকাউন্টে গেছে ভাই। মানবিক কারণে {phone} নম্বরে ব্যাক দিন।",
            "Emergency refund appeal: ৳{amount} went to your number by mistake, please send it back immediately to {phone}."
        ]
    },
    "fake_prize": {
        "train": [
            "অভিনন্দন! আপনি জিতেছেন ৳{amount} ক্যাশ প্রাইজ! পুরস্কারের অর্থ পেতে রেজিস্ট্রেশন ফি বাবদ ৳{fee} পাঠান।",
            "Congratulations! Apni ৳{amount} lottery jitechen. Claim korte registration fee ৳{fee} pathan {phone} e.",
            "Exclusive Winner! You won a brand new motorcycle. Deposit processing charge ৳{fee} to claim."
        ],
        "test": [
            "বিশেষ অফার: লাকি ড্রতে আপনার নাম নির্বাচিত হয়েছে ৳{amount} টাকার জন্য। ডেলিভারি চার্জ বাবদ ৳{fee} প্রদান করুন।",
            "Promo winner notice: Transfer fee of ৳{fee} required to disburse your winning sum of ৳{amount}."
        ]
    },
    "urgency_threat": {
        "train": [
            "আইনি নোটিশ: আগামী ৩০ মিনিটের মধ্যে ৳{amount} জরিমানা প্রদান না করলে আপনার এনআইডি ও অ্যাকাউন্ট বাজেয়াপ্ত হবে।",
            "Police complaint registered against your SIM. Clear fine ৳{amount} immediately to avoid arrest.",
            "জরুরি ওয়ার্নিং: ২০ মিনিটের মধ্যে বকেয়া পরিশোধ না করলে আপনার বিরুদ্ধে মামলা দায়ের করা হবে।"
        ],
        "test": [
            "জরুরি আদালত নির্দেশিকা: ট্রানজেকশন পেন্ডেন্সি দূর করতে ৩০ মিনিটের মধ্যে উল্লেখিত ফি পরিশোধ করুন।",
            "Legal action pending on your mobile number. Remit fine ৳{amount} right now to avoid police inquiry."
        ]
    },
    "benign": {
        "train": [
            "মা, তোমার ওষুধের জন্য ৳{amount} পাঠালাম। ডাক্তার কী বলেছেন আমাকে জানিও।",
            "Mama baper bari jaoar bhara ৳{amount} pathiyechi, peye phone diyo.",
            "Dear customer, your utility bill payment of ৳{amount} has been processed successfully.",
            "ভাই রাতের খাবারের বিলের তোমার অংশের ৳{amount} পাঠিয়ে দিও যখন ফ্রি হও।",
            "Remember that your OTP is private. upay never calls you asking for any PIN or OTP."
        ],
        "test": [
            "বাবা, টিউশন ফি বাবদ ৳{amount} লাগবে। আর্জেন্ট না, কাল দিলেও হবে।",
            "Bhai dokan theke ৳{amount} taka nish, ami pore hishab bujhe nebo.",
            "Salary of ৳{amount} for the month has been credited to your digital wallet."
        ]
    }
}

SLOTS = {
    "wallet": ["upay", "ইউপে", "Wallet Service", "MFS"],
    "phone": ["01711002233", "01999887766", "01855443322", "01300998877", "01522334455"],
    "code": ["482910", "938102", "110482", "572914", "882015"],
    "amount": ["15000", "25000", "50000", "100000", "2500", "7500"],
    "fee": ["500", "1000", "1500", "2000"]
}

def _fill_template(tmpl: str, rng: np.random.Generator) -> str:
    res = tmpl
    for slot, choices in SLOTS.items():
        placeholder = "{" + slot + "}"
        while placeholder in res:
            res = res.replace(placeholder, str(rng.choice(choices)), 1)
    return res

def generate_scam_corpus(n_samples: int = 6000, seed: int = 42) -> Tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    train_records = []
    test_records = []
    
    categories = list(TEMPLATES.keys())
    per_cat = n_samples // len(categories)
    
    msg_id = 1
    for cat in categories:
        train_tmpls = TEMPLATES[cat]["train"]
        test_tmpls = TEMPLATES[cat]["test"]
        
        # 80% train, 20% test by volume allocation across distinct template families
        n_train = int(per_cat * 0.8)
        n_test = per_cat - n_train
        
        for _ in range(n_train):
            chosen_tmpl = rng.choice(train_tmpls)
            filled = _fill_template(chosen_tmpl, rng)
            train_records.append({
                "msg_id": f"MSG_{msg_id:06d}",
                "text": filled,
                "label": 0 if cat == "benign" else 1,
                "category": cat,
                "template_split": "train_family"
            })
            msg_id += 1
            
        for _ in range(n_test):
            chosen_tmpl = rng.choice(test_tmpls)
            filled = _fill_template(chosen_tmpl, rng)
            test_records.append({
                "msg_id": f"MSG_{msg_id:06d}",
                "text": filled,
                "label": 0 if cat == "benign" else 1,
                "category": cat,
                "template_split": "unseen_test_family"
            })
            msg_id += 1
            
    df_train = pd.DataFrame(train_records).sample(frac=1.0, random_state=seed).reset_index(drop=True)
    df_test = pd.DataFrame(test_records).sample(frac=1.0, random_state=seed).reset_index(drop=True)
    return df_train, df_test