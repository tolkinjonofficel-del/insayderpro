import os
import json
import logging
import random
import string
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from datetime import datetime, timedelta

# Bot tokeni
TOKEN = "8114630640:AAHSCef-rcKE0E5Hz0501Lvvl0AltMh0-Jk"

# Admin ID
ADMIN_ID = 7081746531

# Ma'lumotlarni saqlash fayli
DATA_FILE = "data.json"

# Bukmekerlar havolalari
BUKMAKER_LINKS = {
    "1xbet": "https://reffpa.com/L?tag=d_4147173m_1599c_&site=4147173&ad=1599&r=registration",
    "melbet": "https://refpa42380.com/L?tag=s_4856673m_57037c_&site=4856673&ad=57037", 
    "dbbet": "https://refpa96317.com/L?tag=d_4585917m_11213c_&site=4585917&ad=11213"
}

# Loggerni sozlash
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Boshlang'ich ma'lumotlar
default_data = {
    "users": {},
    "coupons": {
        "today": {
            "date": "",
            "matches": [],
            "description": "🎯 Bugungi Bepul Kuponlar",
            "active": True,
            "coupon_codes": {
                "1xbet": "",
                "melbet": "",
                "dbbet": ""
            }
        },
        "premium": {
            "date": "",
            "matches": [],
            "description": "💎 VIP Premium Kuponlar",
            "active": True,
            "coupon_codes": {
                "1xbet": "",
                "melbet": "",
                "dbbet": ""
            }
        },
        "ball_coupons": {
            "available": [],
            "purchased": {},
            "price": 15,
            "last_update": ""
        }
    },
    "settings": {
        "min_referrals": 20,  # VIP uchun 20 ta referal
        "referral_points": 5,  # Har bir referal uchun 5 ball
        "coupon_price": 15,    # 1 kupon narxi
        "premium_price": 100000,
        "currency": "so'm",
        "payment_details": "💳 *To'lov qilish uchun:*\n\n🏦 **HUMO:** `9860356622837710`\n📱 **Payme:** `mavjud emas`\n💳 **Uzumbank visa:** `4916990318695001`\n\n✅ To'lov qilgach, chek skrinshotini @baxtga_olga ga yuboring."
    },
    "stats": {
        "total_users": 0,
        "premium_users": 0,
        "today_users": 0,
        "today_referrals": 0,
        "total_points_given": 0,
        "total_coupons_sold": 0
    }
}

def load_data():
    """Ma'lumotlarni yuklash"""
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(default_data, f, ensure_ascii=False, indent=2)
        return default_data

def save_data(data):
    """Ma'lumotlarni saqlash"""
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Saqlash xatosi: {e}")
        return False

# Ma'lumotlarni yuklash
data = load_data()

def is_admin(user_id):
    return user_id == ADMIN_ID

def is_premium(user_id):
    user_data = data['users'].get(str(user_id), {})
    return user_data.get('premium', False)

def get_user_points(user_id):
    user_data = data['users'].get(str(user_id), {})
    return user_data.get('points', 0)

def get_user_referrals(user_id):
    user_data = data['users'].get(str(user_id), {})
    return user_data.get('referrals', 0)

def add_user_points(user_id, points, reason=""):
    """Foydalanuvchiga ball qo'shish"""
    if str(user_id) not in data['users']:
        return False
    
    data['users'][str(user_id)]['points'] = data['users'][str(user_id)].get('points', 0) + points
    data['stats']['total_points_given'] += points
    
    # Ball tarixini saqlash
    if 'points_history' not in data['users'][str(user_id)]:
        data['users'][str(user_id)]['points_history'] = []
    
    data['users'][str(user_id)]['points_history'].append({
        'points': points,
        'reason': reason,
        'date': datetime.now().strftime("%Y-%m-%d %H:%M")
    })
    
    save_data(data)
    return True

def generate_coupon_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    # Yangi foydalanuvchi
    if str(user_id) not in data['users']:
        data['users'][str(user_id)] = {
            'name': user.first_name,
            'username': user.username,
            'referrals': 0,
            'points': 0,
            'premium': False,
            'joined_date': datetime.now().strftime("%Y-%m-%d"),
            'last_active': datetime.now().timestamp(),
            'points_history': []
        }
        data['stats']['total_users'] += 1
        save_data(data)
    else:
        # Faollikni yangilash
        data['users'][str(user_id)]['last_active'] = datetime.now().timestamp()
        save_data(data)
    
    # Referal tekshirish
    if context.args:
        ref_id = context.args[0]
        if ref_id.startswith('ref'):
            try:
                referrer_id = int(ref_id[3:])
                if str(referrer_id) in data['users'] and referrer_id != user_id:
                    # Referal sonini oshirish
                    data['users'][str(referrer_id)]['referrals'] += 1
                    data['stats']['today_referrals'] += 1
                    
                    # Ball qo'shish
                    points_to_add = data['settings']['referral_points']
                    add_user_points(referrer_id, points_to_add, f"Referal: {user.first_name}")
                    
                    save_data(data)
                    
                    # Referal egasiga xabar berish
                    try:
                        await context.bot.send_message(
                            chat_id=referrer_id,
                            text=f"🎉 *Tabriklaymiz!*\n\n"
                                 f"📤 Sizning referal havolangiz orqali yangi foydalanuvchi qo'shildi!\n"
                                 f"👤 Yangi foydalanuvchi: {user.first_name}\n"
                                 f"💰 Sizga {points_to_add} ball qo'shildi!\n"
                                 f"🎯 Jami ball: {get_user_points(referrer_id)}",
                            parse_mode='Markdown'
                        )
                    except:
                        pass
            except Exception as e:
                logger.error(f"Referal qayd etishda xato: {e}")

    # Yangi interfeys tugmalari
    keyboard = [
        # 1-qator: Asosiy kuponlar
        [
            InlineKeyboardButton("🎯 Bepul Kuponlar", callback_data="today_coupons"),
            InlineKeyboardButton("💎 VIP Kuponlar", callback_data="premium_coupons")
        ],
        # 2-qator: Ball va kuponlar
        [
            InlineKeyboardButton("💰 Ball Kuponlar", callback_data="ball_coupons"),
            InlineKeyboardButton("🏆 Mening Ballim", callback_data="my_points")
        ],
        # 3-qator: Referal va ulashish
        [
            InlineKeyboardButton("📤 Referal Havola", callback_data="get_referral_link"),
            InlineKeyboardButton("🔗 Ulashish", callback_data="share_referral")
        ],
        # 4-qator: Yordam va to'lov
        [
            InlineKeyboardButton("💳 VIP Sotib Olish", callback_data="buy_premium"),
            InlineKeyboardButton("ℹ️ Yordam", callback_data="help")
        ]
    ]
    
    if is_admin(user_id):
        keyboard.append([InlineKeyboardButton("👑 Admin Panel", callback_data="admin")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Yangilangan start xabari
    welcome_text = f"""
🎉 *Salom {user.first_name}!* 👋

⚽ *Futbol Kuponlari Botiga Xush Kelibsiz!*

💰 *YANGI BALL TIZIMI:*
• 📤 Har bir referal = *{data['settings']['referral_points']} ball*
• 🎯 {data['settings']['coupon_price']} ball = *1 ta ekskluziv kupon*
• 💎 {data['settings']['min_referrals']} ta referal = *Bepul VIP*

📊 *Sizning holatingiz:*
👥 Referallar: {get_user_referrals(user_id)}/{data['settings']['min_referrals']} ta
💰 Ballar: {get_user_points(user_id)} ball

🎯 *Kupon turlari:*
• 🎯 **Kunlik bepul** - Har kuni yangilanadi
• 💎 **VIP kuponlar** - Ekskluziv bashoratlar  
• 💰 **Ball kuponlar** - Ballaringiz evaziga

*Ball to'plang va qimmat kuponlarga ega bo'ling!* 🚀
"""
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if query.data == "today_coupons":
        await send_today_coupons(query)
    elif query.data == "premium_coupons":
        await handle_premium_coupons(query, user_id)
    elif query.data == "ball_coupons":
        await show_ball_coupons(query, user_id)
    elif query.data == "my_points":
        await show_my_points(query, user_id)
    elif query.data == "get_referral_link":
        await show_referral_link(query, user_id)
    elif query.data == "share_referral":
        await share_referral_link(query, user_id)
    elif query.data == "buy_premium":
        await show_premium_payment(query, user_id)
    elif query.data == "help":
        await show_help(query)
    elif query.data == "back":
        await back_to_main(query)
    elif query.data == "back_to_coupons":
        await back_to_coupons(query)
    elif query.data.startswith("buy_coupon_"):
        coupon_index = int(query.data.replace("buy_coupon_", ""))
        await buy_coupon_with_points(query, user_id, coupon_index)
    elif query.data == "admin":
        if is_admin(user_id):
            await show_admin_panel(query)
        else:
            await query.message.reply_text("❌ Siz admin emassiz!")
    elif query.data == "admin_add_coupon":
        await show_coupon_type_selection(query)
    elif query.data == "admin_add_ball_coupon":
        await start_adding_ball_coupon(query, context)
    elif query.data == "admin_view_ball_coupons":
        await show_ball_coupons_admin(query)
    # ... boshqa handlerlar

# YANGI BALL KUPONLARI FUNKSIYALARI
async def show_ball_coupons(query, user_id):
    """Ball evaziga kuponlar sahifasi"""
    ball_coupons = data['coupons']['ball_coupons']
    user_points = get_user_points(user_id)
    coupon_price = data['settings']['coupon_price']
    
    text = f"""
💰 *BALL EVAZIGA KUPONLAR*

🎯 **Sizning balansingiz:** {user_points} ball
💵 **1 kupon narxi:** {coupon_price} ball

📊 **Mavjud kuponlar:** {len(ball_coupons['available'])} ta
"""

    if ball_coupons['available']:
        text += "\n🎟️ *Kuponlar ro'yxati:*\n\n"
        for i, coupon in enumerate(ball_coupons['available']):
            text += f"{i+1}. 🏆 {coupon['teams']}\n"
            text += f"   ⏰ {coupon['time']} | {coupon['league']}\n"
            text += f"   🎯 {coupon['prediction']} | 📊 {coupon['odds']}\n"
            text += f"   💰 {coupon_price} ball\n\n"
    else:
        text += "\n📭 Hozircha mavjud kuponlar yo'q. Tez orada yangilanadi! 🔄\n"

    keyboard = []
    
    if ball_coupons['available']:
        for i in range(len(ball_coupons['available'])):
            if i % 2 == 0:
                row = []
            row.append(InlineKeyboardButton(f"🎟️ {i+1} kupon", callback_data=f"buy_coupon_{i}"))
            if i % 2 == 1 or i == len(ball_coupons['available']) - 1:
                keyboard.append(row)
    
    keyboard.extend([
        [InlineKeyboardButton("🔄 Yangilash", callback_data="ball_coupons")],
        [InlineKeyboardButton("📤 Referal Topish", callback_data="get_referral_link")],
        [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def buy_coupon_with_points(query, user_id, coupon_index):
    """Ball evaziga kupon sotib olish"""
    ball_coupons = data['coupons']['ball_coupons']
    user_points = get_user_points(user_id)
    coupon_price = data['settings']['coupon_price']
    
    if coupon_index >= len(ball_coupons['available']):
        await query.message.reply_text("❌ Bu kupon mavjud emas!")
        return
    
    if user_points < coupon_price:
        await query.message.reply_text(
            f"❌ Ballaringiz yetarli emas!\n"
            f"💰 Sizda: {user_points} ball\n"
            f"💵 Kerak: {coupon_price} ball\n\n"
            f"📤 Ko'proq referal taklif qiling va ball to'plang!"
        )
        return
    
    # Kuponni olish
    coupon = ball_coupons['available'].pop(coupon_index)
    
    # Ballarni hisobdan olib tashlash
    data['users'][str(user_id)]['points'] -= coupon_price
    data['stats']['total_coupons_sold'] += 1
    
    # Kuponni foydalanuvchiga berish
    if 'purchased' not in ball_coupons:
        ball_coupons['purchased'] = {}
    
    if str(user_id) not in ball_coupons['purchased']:
        ball_coupons['purchased'][str(user_id)] = []
    
    ball_coupons['purchased'][str(user_id)].append({
        **coupon,
        'purchased_date': datetime.now().strftime("%Y-%m-%d %H:%M"),
        'price_paid': coupon_price
    })
    
    save_data(data)
    
    # Kupon ma'lumotlarini yuborish
    coupon_text = f"""
🎉 *TABRIKLAYMIZ!*

✅ Siz {coupon_price} ball evaziga kupon sotib oldingiz!

🎟️ *Kupon ma'lumotlari:*
🏆 **O'yin:** {coupon['teams']}
⏰ **Vaqt:** {coupon['time']}
🌍 **Liga:** {coupon['league']}
🎯 **Bashorat:** {coupon['prediction']}
📊 **Koeffitsient:** {coupon['odds']}
💎 **Ishonch:** {coupon['confidence']}

🔑 *Kupon kodlari:*
• 1xBet: `{coupon['codes']['1xbet']}`
• MelBet: `{coupon['codes']['melbet']}`
• DB Bet: `{coupon['codes']['dbbet']}`

💰 **Qolgan ball:** {get_user_points(user_id)}
"""
    
    keyboard = [
        [
            InlineKeyboardButton("🎰 1xBet", url=BUKMAKER_LINKS['1xbet']),
            InlineKeyboardButton("🎯 MelBet", url=BUKMAKER_LINKS['melbet']),
            InlineKeyboardButton("💰 DB Bet", url=BUKMAKER_LINKS['dbbet'])
        ],
        [InlineKeyboardButton("💰 Boshqa Kuponlar", callback_data="ball_coupons")],
        [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(coupon_text, reply_markup=reply_markup, parse_mode='Markdown')

async def show_my_points(query, user_id):
    """Foydalanuvchi ballari va statistikasi"""
    user_data = data['users'].get(str(user_id), {})
    points = user_data.get('points', 0)
    referrals = user_data.get('referrals', 0)
    required_refs = data['settings']['min_referrals']
    points_per_ref = data['settings']['referral_points']
    coupon_price = data['settings']['coupon_price']
    
    text = f"""
🏆 *MENING HISOBIM*

💰 **Ballar:** {points} ball
👥 **Referallar:** {referrals} ta
🎯 **VIP uchun:** {referrals}/{required_refs} ta

📊 **Statistika:**
• 1 referal = {points_per_ref} ball
• 1 kupon = {coupon_price} ball
• VIP uchun = {required_refs} referal

💡 **Ball to'plash usullari:**
1. 📤 Do'stlarni taklif qiling ({points_per_ref} ball/referal)
2. 📈 Ko'proq referal = Tezroq VIP
3. 🎯 Ballarni kuponlarga almashtiring

🎯 **Sotib olishingiz mumkin:** {points // coupon_price} ta kupon
"""
    
    # Ball tarixi
    points_history = user_data.get('points_history', [])
    if points_history:
        text += "\n📅 **So'nggi operatsiyalar:**\n"
        for history in points_history[-5:]:  # Oxirgi 5 tasi
            sign = "+" if history['points'] > 0 else ""
            text += f"• {sign}{history['points']} ball - {history['reason']} ({history['date']})\n"
    
    keyboard = [
        [InlineKeyboardButton("💰 Kuponlar Sotib Olish", callback_data="ball_coupons")],
        [InlineKeyboardButton("📤 Referal Havola", callback_data="get_referral_link")],
        [InlineKeyboardButton("💎 VIP Olish", callback_data="premium_coupons")],
        [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

# YANGI ADMIN FUNKSIYALARI
async def show_admin_panel(query):
    stats = get_user_statistics()
    today_status = "🟢 Faol" if data['coupons']['today']['active'] else "🔴 Nofaol"
    premium_status = "🟢 Faol" if data['coupons']['premium']['active'] else "🔴 Nofaol"
    ball_coupons_count = len(data['coupons']['ball_coupons']['available'])
    
    text = f"""
👑 *ADMIN PANELI*

📊 **Bot Statistikasi:**
👥 Jami foydalanuvchilar: {stats['total_users']} ta
💎 VIP foydalanuvchilar: {stats['premium_users']} ta
💰 Berilgan ballar: {data['stats']['total_points_given']} ball
🎟️ Sotilgan kuponlar: {data['stats']['total_coupons_sold']} ta

⚽ **Kuponlar Holati:**
🎯 Kunlik kuponlar: {today_status}
💎 VIP kuponlar: {premium_status}
💰 Ball kuponlar: {ball_coupons_count} ta

🎯 **Admin Imkoniyatlari:**
"""
    
    keyboard = [
        [InlineKeyboardButton("🎯 Kunlik Kupon Qo'shish", callback_data="admin_add_coupon")],
        [InlineKeyboardButton("💰 Ball Kupon Qo'shish", callback_data="admin_add_ball_coupon")],
        [InlineKeyboardButton("📊 Ball Kuponlarni Ko'rish", callback_data="admin_view_ball_coupons")],
        [InlineKeyboardButton("📊 Statistika", callback_data="admin_stats")],
        [InlineKeyboardButton("📢 Xabar Yuborish", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def start_adding_ball_coupon(query, context: ContextTypes.DEFAULT_TYPE):
    """Ball kupon qo'shishni boshlash"""
    context.user_data['adding_ball_coupon'] = True
    
    await query.edit_message_text(
        "💰 *BALL KUPON QO'SHISH*\n\n"
        "Quyidagi formatda ma'lumot yuboring:\n\n"
        "`vaqt|liga|jamoalar|bashorat|koeffitsient|ishonch|1xbet_kodi|melbet_kodi|dbbet_kodi`\n\n"
        "*Misol:*\n"
        "`20:00|Premier League|Man City vs Arsenal|1X|1.50|85%|1XBET123|MELBET456|DBBET789`\n\n"
        "📝 *Eslatma:* Bir nechta kupon qo'shish uchun har birini alohida yuboring.",
        parse_mode='Markdown'
    )

async def show_ball_coupons_admin(query):
    """Admin uchun ball kuponlarini ko'rsatish"""
    ball_coupons = data['coupons']['ball_coupons']
    
    text = f"""
💰 *BALL KUPONLARI - ADMIN*

🎯 **Narxi:** {data['settings']['coupon_price']} ball
📊 **Mavjud kuponlar:** {len(ball_coupons['available'])} ta
📈 **Sotilgan kuponlar:** {data['stats']['total_coupons_sold']} ta

"""
    
    if ball_coupons['available']:
        text += "📋 **Mavjud kuponlar:**\n\n"
        for i, coupon in enumerate(ball_coupons['available']):
            text += f"{i+1}. 🏆 {coupon['teams']}\n"
            text += f"   ⏰ {coupon['time']} | {coupon['league']}\n"
            text += f"   🎯 {coupon['prediction']} | 📊 {coupon['odds']}\n\n"
    else:
        text += "📭 Hozircha mavjud kuponlar yo'q.\n"
    
    keyboard = [
        [InlineKeyboardButton("➕ Kupon Qo'shish", callback_data="admin_add_ball_coupon")],
        [InlineKeyboardButton("🗑️ Kuponlarni Tozalash", callback_data="admin_clear_ball_coupons")],
        [InlineKeyboardButton("👑 Admin Panel", callback_data="admin")],
        [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return
    
    # Ball kupon qo'shish rejimi
    if context.user_data.get('adding_ball_coupon'):
        await process_ball_coupon_addition(update, context)
        return
    
    # ... boshqa admin rejimlari

async def process_ball_coupon_addition(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ball kupon qo'shish"""
    try:
        message_text = update.message.text
        parts = message_text.split('|')
        
        if len(parts) < 8:
            await update.message.reply_text("❌ Noto'g'ri format! 8 ta parametr kerak.")
            return
        
        time, league, teams, prediction, odds, confidence, code_1xbet, code_melbet, code_dbbet = parts[:9]
        
        new_coupon = {
            'time': time.strip(),
            'league': league.strip(),
            'teams': teams.strip(),
            'prediction': prediction.strip(),
            'odds': odds.strip(),
            'confidence': confidence.strip(),
            'codes': {
                '1xbet': code_1xbet.strip(),
                'melbet': code_melbet.strip(),
                'dbbet': code_dbbet.strip()
            },
            'added_date': datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        
        data['coupons']['ball_coupons']['available'].append(new_coupon)
        data['coupons']['ball_coupons']['last_update'] = datetime.now().strftime("%Y-%m-%d %H:%M")
        save_data(data)
        
        await update.message.reply_text(
            f"✅ *Ball kupon qo'shildi!*\n\n"
            f"🏆 **O'yin:** {teams.strip()}\n"
            f"⏰ **Vaqt:** {time.strip()}\n"
            f"🎯 **Bashorat:** {prediction.strip()}\n"
            f"💰 **Narxi:** {data['settings']['coupon_price']} ball\n\n"
            f"📊 Jami mavjud kuponlar: {len(data['coupons']['ball_coupons']['available'])} ta",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        await update.message.reply_text(f"❌ Xato: {e}")
    
    context.user_data.pop('adding_ball_coupon', None)

# YANGILANGAN PREMIUM FUNKSIYALARI
async def show_premium_offer(query, user_id):
    referrals_count = get_user_referrals(user_id)
    required_refs = data['settings']['min_referrals']
    user_points = get_user_points(user_id)
    
    text = f"""
💎 *VIP KUPONLARGA KIRISH*

📊 **Sizning holatingiz:**
👥 Referallar: {referrals_count}/{required_refs} ta
💰 Ballar: {user_points} ball
💵 To'lov: {data['settings']['premium_price']} {data['settings']['currency']}

🎯 *VIP afzalliklari:*
• ✅ Yuqori daromadli kuponlar
• ✅ Ekskluziv bashoratlar  
• ✅ 90-95% ishonchlilik
• ✅ Statistik tahlillar
• ✅ Shaxsiy qo'llab-quvvatlash

💡 *VIP olish usullari:*
"""
    
    keyboard = []
    
    if referrals_count >= required_refs:
        keyboard.append([InlineKeyboardButton("🎁 BEPUL VIP OCHISH", callback_data="get_free_premium")])
        text += f"1. 🎁 **{required_refs} ta referal** - Bepul VIP!\n"
    else:
        text += f"1. 👥 **{required_refs} ta referal** to'plang\n"
    
    text += f"2. 💳 **{data['settings']['premium_price']} {data['settings']['currency']}** to'lov qiling\n\n"
    text += "💎 VIP orqali yuqori daromadli kuponlarga ega bo'ling!"
    
    keyboard.extend([
        [InlineKeyboardButton("👥 Referal Orqali", callback_data="get_referral_link")],
        [InlineKeyboardButton("💳 To'lov Orqali", callback_data="buy_premium")],
        [InlineKeyboardButton("💰 Ball Kuponlar", callback_data="ball_coupons")],
        [InlineKeyboardButton("🔙 Orqaga", callback_data="back")]
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

# YANGILANGAN REFERAL FUNKSIYALARI
async def show_referral_link(query, user_id):
    bot_username = (await query.message._bot.get_me()).username
    ref_link = f"https://t.me/{bot_username}?start=ref{user_id}"
    referrals_count = get_user_referrals(user_id)
    required_refs = data['settings']['min_referrals']
    points_per_ref = data['settings']['referral_points']
    user_points = get_user_points(user_id)
    
    text = f"""
📤 *REFERAL HAVOLANGIZ*

`{ref_link}`

📊 **Sizning statistikangiz:**
👥 Referallar: {referrals_count}/{required_refs} ta
💰 Ballar: {user_points} ball
🎯 Maqsad: {required_refs} ta (Bepul VIP)

💡 **Qanday ishlatish:**
1. Havolani nusxalang
2. Do'stlaringizga yuboring
3. Har bir yangi foydalanuvchi = +{points_per_ref} ball
4. {required_refs} ta referal = Bepul VIP!

💰 **Hisob-kitob:**
• {points_per_ref} ball × {referrals_count} referal = {points_per_ref * referrals_count} ball
• {required_refs - referrals_count} ta qolgan = {(required_refs - referrals_count) * points_per_ref} ball

🔗 Havolani ko'proq odamga yuboring, tezroq VIPga ega bo'ling!
"""
    
    keyboard = [
        [InlineKeyboardButton("🔗 TELEGRAMDA ULASHISH", callback_data="share_referral")],
        [InlineKeyboardButton("💰 Ball Kuponlar", callback_data="ball_coupons")],
        [InlineKeyboardButton("💎 VIP Olish", callback_data="premium_coupons")],
        [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

# ... qolgan funksiyalar (send_today_coupons, handle_premium_coupons, va boshqalar)

def get_user_statistics():
    """Foydalanuvchi statistikasini hisoblash"""
    total_users = len(data['users'])
    premium_users = sum(1 for user in data['users'].values() if user.get('premium', False))
    
    # Bugungi yangi foydalanuvchilar
    today = datetime.now().strftime("%Y-%m-%d")
    today_users = sum(1 for user in data['users'].values() if user.get('joined_date') == today)
    
    # Bugungi referallar
    today_referrals = sum(user.get('referrals', 0) for user in data['users'].values() if user.get('joined_date') == today)
    
    # Aktiv foydalanuvchilar (oxirgi 7 kun)
    active_users = 0
    week_ago = datetime.now().timestamp() - 7 * 24 * 60 * 60
    for user_id, user_data in data['users'].items():
        last_active = user_data.get('last_active', 0)
        if last_active > week_ago:
            active_users += 1
    
    return {
        'total_users': total_users,
        'premium_users': premium_users,
        'today_users': today_users,
        'today_referrals': today_referrals,
        'active_users': active_users
    }

async def back_to_main(query):
    user = query.from_user
    user_id = user.id
    
    # Yangi interfeys tugmalari
    keyboard = [
        [
            InlineKeyboardButton("🎯 Bepul Kuponlar", callback_data="today_coupons"),
            InlineKeyboardButton("💎 VIP Kuponlar", callback_data="premium_coupons")
        ],
        [
            InlineKeyboardButton("💰 Ball Kuponlar", callback_data="ball_coupons"),
            InlineKeyboardButton("🏆 Mening Ballim", callback_data="my_points")
        ],
        [
            InlineKeyboardButton("📤 Referal Havola", callback_data="get_referral_link"),
            InlineKeyboardButton("🔗 Ulashish", callback_data="share_referral")
        ],
        [
            InlineKeyboardButton("💳 VIP Sotib Olish", callback_data="buy_premium"),
            InlineKeyboardButton("ℹ️ Yordam", callback_data="help")
        ]
    ]
    
    if is_admin(user_id):
        keyboard.append([InlineKeyboardButton("👑 Admin Panel", callback_data="admin")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🎯 *Asosiy Menyu*\n\n"
        "Ball to'plang, kuponlar sotib oling va yutuqlarga erishing! 🚀",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

def main():
    try:
        app = Application.builder().token(TOKEN).build()
        
        # Handlerlar
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CallbackQueryHandler(button_handler))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_message))
        
        print("✅ Bot muvaffaqiyatli ishga tushdi!")
        print("🤖 Bot ishlayapti...")
        print(f"👑 Admin ID: {ADMIN_ID}")
        print("💰 YANGI BALL TIZIMI QO'SHILDI!")
        print("🎯 Har referal = 5 ball")
        print("💎 VIP uchun 20 ta referal talab qilinadi")
        print("🎟️ 15 ball = 1 ta kupon")
        print("📊 Real-time ball hisobi")
        
        app.run_polling()
        
    except Exception as e:
        print(f"❌ Xato: {e}")

if __name__ == "__main__":
    main()
