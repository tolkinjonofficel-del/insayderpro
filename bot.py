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
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
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
        "ball_coupons": {
            "available": [],
            "purchased": {},
            "price": 15,
            "last_update": ""
        }
    },
    "settings": {
        "min_referrals": 20,
        "referral_points": 5,
        "coupon_price": 15,
        "premium_price": 100000,
        "currency": "so'm",
        "min_exchange_points": 50,
        "exchange_rate": 10000,
        "payment_details": "💳 *To'lov qilish uchun:*\n\n🏦 **HUMO:** `9860356622837710`\n📱 **Payme:** `mavjud emas`\n💳 **Uzumbank visa:** `4916990318695001`\n\n✅ To'lov qilgach, chek skrinshotini @baxtga_olga ga yuboring."
    },
    "stats": {
        "total_users": 0,
        "premium_users": 0,
        "today_users": 0,
        "today_referrals": 0,
        "total_points_given": 0,
        "total_coupons_sold": 0,
        "total_exchanges": 0
    }
}

def load_data():
    """Ma'lumotlarni yuklash"""
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Ma'lumotlarni yuklashda xato: {e}")
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(default_data, f, ensure_ascii=False, indent=2)
        return default_data.copy()

def save_data(data):
    """Ma'lumotlarni saqlash"""
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Saqlash xatosi: {e}")
        return False

# Global data o'zgaruvchisini ishga tushirish
data = load_data()

def is_admin(user_id):
    return user_id == ADMIN_ID

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
    
    if 'points' not in data['users'][str(user_id)]:
        data['users'][str(user_id)]['points'] = 0
    
    data['users'][str(user_id)]['points'] += points
    data['stats']['total_points_given'] += points
    
    if 'points_history' not in data['users'][str(user_id)]:
        data['users'][str(user_id)]['points_history'] = []
    
    data['users'][str(user_id)]['points_history'].append({
        'points': points,
        'reason': reason,
        'date': datetime.now().strftime("%Y-%m-%d %H:%M"),
        'type': 'add'
    })
    
    return save_data(data)

def remove_user_points(user_id, points, reason=""):
    """Foydalanuvchidan ball olib tashlash"""
    if str(user_id) not in data['users']:
        return False
    
    if data['users'][str(user_id)].get('points', 0) < points:
        return False
    
    data['users'][str(user_id)]['points'] -= points
    
    if 'points_history' not in data['users'][str(user_id)]:
        data['users'][str(user_id)]['points_history'] = []
    
    data['users'][str(user_id)]['points_history'].append({
        'points': -points,
        'reason': reason,
        'date': datetime.now().strftime("%Y-%m-%d %H:%M"),
        'type': 'remove'
    })
    
    return save_data(data)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        user_id = user.id
        
        logger.info(f"Start command from user {user_id} ({user.first_name})")
        
        global data
        data = load_data()
        
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
            logger.info(f"Yangi foydalanuvchi qo'shildi: {user_id}")
        else:
            data['users'][str(user_id)]['last_active'] = datetime.now().timestamp()
            save_data(data)
        
        if context.args:
            ref_id = context.args[0]
            logger.info(f"Referal argument: {ref_id}")
            if ref_id.startswith('ref'):
                try:
                    referrer_id = int(ref_id[3:])
                    if str(referrer_id) in data['users'] and referrer_id != user_id:
                        data['users'][str(referrer_id)]['referrals'] += 1
                        data['stats']['today_referrals'] += 1
                        
                        points_to_add = data['settings']['referral_points']
                        add_user_points(referrer_id, points_to_add, f"Referal taklif: {user.first_name}")
                        
                        save_data(data)
                        
                        try:
                            await context.bot.send_message(
                                chat_id=referrer_id,
                                text=f"🎉 *Tabriklaymiz!*\n\n"
                                     f"📤 Sizning referal havolangiz orqali yangi foydalanuvchi qo'shildi!\n"
                                     f"👤 Yangi foydalanuvchi: {user.first_name}\n"
                                     f"💰 Sizga {points_to_add} ball qo'shildi! (1 referal = 5 ball)\n"
                                     f"🎯 Jami ball: {get_user_points(referrer_id)}",
                                parse_mode='Markdown'
                            )
                        except Exception as e:
                            logger.error(f"Referal bildirishnoma yuborishda xato: {e}")
                except Exception as e:
                    logger.error(f"Referal qayd etishda xato: {e}")

        # Yangi chiroyli start xabari
        welcome_text = f"""
🎉 *SALOM {user.first_name}!* 🏆

⚽ *FUTBOL BAHOLARI BOTIGA XUSH KELIBSIZ!*

💰 *HAR KUNI YANGI KUPONLAR!*
• 🎯 *Kunlik bepul kuponlar* - Har kuni yangilanadi!
• 💰 *Ball evaziga kuponlar* - 15 ball = 1 ta ekskluziv kupon
• 🎁 *Bonuslar* - Bukmeker kontorlarida ro'yxatdan o'ting

🏆 *BALL TIZIMI:*
• 📤 1 do'st taklif = *5 ball*
• 💰 50 ball = *10,000 so'm*
• 🎯 15 ball = *1 ta maxsus kupon*

📊 *SIZNING HOLATINGIZ:*
👥 Referallar: {get_user_referrals(user_id)} ta
💰 Ballar: {get_user_points(user_id)} ball

🚀 *HOZIRROQ BOSHLANG!*
Ball to'plang, kuponlar oling va yutuqlarga erishing!
"""

        keyboard = [
            [
                InlineKeyboardButton("🎯 KUPONLAR OLISH", callback_data="get_coupons"),
                InlineKeyboardButton("💰 BALL ALMASHISH", callback_data="exchange_points")
            ],
            [
                InlineKeyboardButton("🎁 BONUSLAR", callback_data="bonuses"),
                InlineKeyboardButton("📊 MENING BALLIM", callback_data="my_points")
            ],
            [
                InlineKeyboardButton("📤 REFERAL HAVOLA", callback_data="get_referral_link"),
                InlineKeyboardButton("ℹ️ YORDAM", callback_data="help")
            ]
        ]
        
        if is_admin(user_id):
            keyboard.append([InlineKeyboardButton("👑 ADMIN PANEL", callback_data="admin")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Start commandda xato: {e}")
        await update.message.reply_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        logger.info(f"Button handler: {query.data} from user {user_id}")
        
        global data
        data = load_data()
        
        if query.data == "get_coupons":
            await show_coupon_selection(query, user_id)
        elif query.data == "get_free_coupon":
            await send_today_coupons(query)
        elif query.data == "get_ball_coupon":
            await get_ball_coupon(query, user_id)
        elif query.data == "exchange_points":
            await show_exchange_points(query, user_id)
        elif query.data == "request_exchange":
            await request_exchange(query, user_id)
        elif query.data == "bonuses":
            await show_bonuses(query)
        elif query.data == "my_points":
            await show_my_points(query, user_id)
        elif query.data == "get_referral_link":
            await show_referral_link(query, user_id)
        elif query.data == "share_referral":
            await share_referral_link(query, user_id)
        elif query.data == "help":
            await show_help(query)
        elif query.data == "back":
            await back_to_main(query)
        elif query.data == "back_to_coupons":
            await back_to_coupon_selection(query)
        
        # Admin handlerlari
        elif query.data == "admin":
            if is_admin(user_id):
                await show_admin_panel(query)
            else:
                await query.message.reply_text("❌ Siz admin emassiz!")
        elif query.data == "admin_stats":
            await show_admin_stats(query)
        elif query.data == "admin_users":
            await show_admin_users(query)
        elif query.data == "admin_add_coupon":
            await show_admin_add_coupon(query)
        elif query.data == "admin_manage_points":
            await show_admin_manage_points(query)
        elif query.data == "admin_broadcast":
            await show_admin_broadcast(query)
        elif query.data == "admin_clear_coupons":
            await admin_clear_coupons(query)
        elif query.data.startswith("admin_add_points_"):
            user_id_to_edit = query.data.replace("admin_add_points_", "")
            context.user_data['editing_user'] = user_id_to_edit
            context.user_data['action'] = 'add_points'
            await query.message.reply_text(f"👤 Foydalanuvchi: {user_id_to_edit}\n💳 Qancha ball qo'shmoqchisiz?")
        elif query.data.startswith("admin_remove_points_"):
            user_id_to_edit = query.data.replace("admin_remove_points_", "")
            context.user_data['editing_user'] = user_id_to_edit
            context.user_data['action'] = 'remove_points'
            await query.message.reply_text(f"👤 Foydalanuvchi: {user_id_to_edit}\n💳 Qancha ball olib tashlamoqchisiz?")
        
        else:
            await query.message.reply_text("❌ Noma'lum buyruq!")
            
    except Exception as e:
        logger.error(f"Button handlerda xato: {e}")

# KUPON OLISH TIZIMI
async def show_coupon_selection(query, user_id):
    """Kupon olish sahifasi"""
    try:
        user_points = get_user_points(user_id)
        coupon_price = data['settings']['coupon_price']
        
        text = f"""
🎯 *KUPON OLISH*

💰 **Sizning balansingiz:** {user_points} ball

💎 *Quyidagi kuponlardan birini tanlang:*
"""

        keyboard = [
            [InlineKeyboardButton("🎯 BEPUL KUPON OLISH", callback_data="get_free_coupon")],
        ]
        
        # Ball kuponlar mavjudligini tekshirish
        ball_coupons_count = len(data['coupons']['ball_coupons']['available'])
        
        if ball_coupons_count > 0:
            if user_points >= coupon_price:
                keyboard.append([InlineKeyboardButton(f"💰 BALL EVAZIGA KUPON OLISH ({coupon_price} ball)", callback_data="get_ball_coupon")])
                text += f"\n✅ *{ball_coupons_count} ta ball kupon mavjud!*"
            else:
                text += f"\n❌ *Ball yetarli emas!* {coupon_price - user_points} ball yetishmayapti."
        else:
            text += f"\n📭 *Hozircha ball kuponlar mavjud emas.*"
        
        keyboard.extend([
            [InlineKeyboardButton("💰 Ball Almashish", callback_data="exchange_points")],
            [InlineKeyboardButton("📤 Bal To'plash", callback_data="get_referral_link")],
            [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"show_coupon_selection da xato: {e}")
        await query.message.reply_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

async def send_today_coupons(query):
    """Bepul kuponlarni yuborish"""
    try:
        today_coupons = data['coupons']['today']
        
        if not today_coupons['active'] or not today_coupons['matches']:
            await query.edit_message_text(
                "📭 *Hozircha bepul kuponlar mavjud emas*\n\n"
                "Kuponlar tez orada yangilanadi. Iltimos, keyinroq tekshiring! 🔄",
                parse_mode='Markdown'
            )
            return
        
        coupon_text = f"🎯 *{today_coupons['description']}*\n\n"
        coupon_text += f"📅 **Sana:** {today_coupons['date']}\n\n"
        
        # Har bir bukmeker uchun kodlar
        coupon_text += "🔑 *Kupon Kodlari:*\n"
        coupon_text += f"• 1xBet: `{today_coupons['coupon_codes'].get('1xbet', 'Kod mavjud emas')}`\n"
        coupon_text += f"• MelBet: `{today_coupons['coupon_codes'].get('melbet', 'Kod mavjud emas')}`\n"
        coupon_text += f"• DB Bet: `{today_coupons['coupon_codes'].get('dbbet', 'Kod mavjud emas')}`\n\n"
        
        coupon_text += "---\n\n"
        
        # Har bir o'yin uchun alohida koeffitsient
        for i, match in enumerate(today_coupons['matches'], 1):
            coupon_text += f"*{i}. {match['time']} - {match['league']}*\n"
            coupon_text += f"🏆 `{match['teams']}`\n"
            coupon_text += f"🎯 **Bashorat:** `{match['prediction']}`\n"
            coupon_text += f"📊 **Koeffitsient:** `{match['odds']}`\n"
            coupon_text += f"💎 **Ishonch:** {match['confidence']}\n\n"
        
        # Umumiy koeffitsientni hisoblash
        total_odds = 1.0
        for match in today_coupons['matches']:
            try:
                total_odds *= float(match['odds'])
            except:
                pass
        
        coupon_text += "---\n\n"
        coupon_text += f"💰 *Umumiy Koeffitsient:* `{total_odds:.2f}` 🚀\n\n"
        coupon_text += "⏰ *Eslatma:* Stavkalarni o'yin boshlanishidan oldin qo'ying!\n"
        
        keyboard = [
            [
                InlineKeyboardButton("🎰 1xBet", url=BUKMAKER_LINKS['1xbet']),
                InlineKeyboardButton("🎯 MelBet", url=BUKMAKER_LINKS['melbet']),
                InlineKeyboardButton("💰 DB Bet", url=BUKMAKER_LINKS['dbbet'])
            ],
            [InlineKeyboardButton("💰 Yana Kupon Olish", callback_data="get_coupons")],
            [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(coupon_text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"send_today_coupons da xato: {e}")
        await query.message.reply_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

async def get_ball_coupon(query, user_id):
    """Ball evaziga kupon olish"""
    try:
        user_points = get_user_points(user_id)
        coupon_price = data['settings']['coupon_price']
        
        if user_points < coupon_price:
            await query.message.reply_text(
                f"❌ Ballaringiz yetarli emas!\n"
                f"💰 Sizda: {user_points} ball\n"
                f"💵 Kerak: {coupon_price} ball\n\n"
                f"📤 Ball to'plash uchun referal havolangizni tarqating yoki ball almashingiz!",
                parse_mode='Markdown'
            )
            return await show_coupon_selection(query, user_id)
        
        # Tasodifiy ball kuponini olish
        ball_coupons = data['coupons']['ball_coupons']['available']
        if not ball_coupons:
            await query.message.reply_text(
                "❌ Hozircha mavjud kuponlar yo'q. Tez orada yangilanadi! 🔄",
                parse_mode='Markdown'
            )
            return await show_coupon_selection(query, user_id)
        
        coupon = random.choice(ball_coupons)
        
        # Ballarni hisobdan olib tashlash
        data['users'][str(user_id)]['points'] -= coupon_price
        data['stats']['total_coupons_sold'] += 1
        
        # Kuponni foydalanuvchiga berish
        if 'purchased' not in data['coupons']['ball_coupons']:
            data['coupons']['ball_coupons']['purchased'] = {}
        
        if str(user_id) not in data['coupons']['ball_coupons']['purchased']:
            data['coupons']['ball_coupons']['purchased'][str(user_id)] = []
        
        data['coupons']['ball_coupons']['purchased'][str(user_id)].append({
            **coupon,
            'purchased_date': datetime.now().strftime("%Y-%m-%d %H:%M"),
            'price_paid': coupon_price
        })
        
        # Kuponni ro'yxatdan olib tashlash
        data['coupons']['ball_coupons']['available'].remove(coupon)
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
            [InlineKeyboardButton("🔄 Yana Kupon Olish", callback_data="get_coupons")],
            [InlineKeyboardButton("💰 Mening Ballim", callback_data="my_points")],
            [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(coupon_text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"get_ball_coupon da xato: {e}")
        await query.message.reply_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

# BALL ALMASHISH TIZIMI
async def show_exchange_points(query, user_id):
    """Ball almashish sahifasi"""
    try:
        user_points = get_user_points(user_id)
        min_points = data['settings']['min_exchange_points']
        exchange_rate = data['settings']['exchange_rate']
        
        text = f"""
💰 *BALL ALMASHISH*

🎯 **Sizning ballaringiz:** {user_points} ball
💵 **Minimal almashish:** {min_points} ball
💰 **Almashish kursi:** {min_points} ball = {exchange_rate} {data['settings']['currency']}

📊 **Hisob-kitob:**
• {min_points} ball = {exchange_rate} {data['settings']['currency']}
• {min_points * 2} ball = {exchange_rate * 2} {data['settings']['currency']}
• {min_points * 5} ball = {exchange_rate * 5} {data['settings']['currency']}

💡 *Ball almashish uchun @baxtga_olga ga murojaat qiling!*
"""

        keyboard = []
        
        if user_points >= min_points:
            keyboard.append([InlineKeyboardButton("📨 SO'ROV YUBORISH", url="https://t.me/baxtga_olga")])
        else:
            text += f"\n❌ *Ball yetarli emas!* {min_points - user_points} ball yetishmayapti."
            keyboard.append([InlineKeyboardButton("📤 Bal To'plash", callback_data="get_referral_link")])
        
        keyboard.extend([
            [InlineKeyboardButton("🎯 Kupon Olish", callback_data="get_coupons")],
            [InlineKeyboardButton("💰 Mening Ballim", callback_data="my_points")],
            [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"show_exchange_points da xato: {e}")

# BONUSLAR BO'LIMI
async def show_bonuses(query):
    """Bonuslar sahifasi"""
    try:
        text = """
🎁 *BONUSLAR*

🏆 *Bukmeker kontorlarida ro'yxatdan o'ting va bonus oling!*

🎰 **1xBet:**
• Yangi foydalanuvchilar uchun 100% bonus
• Birinchi depozitga 100% gacha bonus
• Har qanday yo'qotish uchun 100% cashback

🎯 **MelBet:**
• Ro'yxatdan o'ting va bonus oling
• Birinchi stavkangiz uchun maxsus taklif
• Kunlik bonuslar va aksiyalar

📱 *APK fayllarni yuklab oling va mobil ilovadan foydalaning!*
"""

        keyboard = [
            [
                InlineKeyboardButton("🎰 1xBet Ro'yxatdan o'tish", url=BUKMAKER_LINKS['1xbet']),
                InlineKeyboardButton("🎯 MelBet Ro'yxatdan o'tish", url=BUKMAKER_LINKS['melbet'])
            ],
            [
                InlineKeyboardButton("📱 1xBet APK Yuklash", url="https://t.me/bonusliapkbot"),
                InlineKeyboardButton("📱 MelBet APK Yuklash", url="https://t.me/bonusliapkbot")
            ],
            [
                InlineKeyboardButton("🎯 Kupon Olish", callback_data="get_coupons"),
                InlineKeyboardButton("💰 Ball Almashish", callback_data="exchange_points")
            ],
            [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"show_bonuses da xato: {e}")

# ADMIN PANELI - MUKAMMAL VERSIYA
async def show_admin_panel(query):
    """Admin panelini ko'rsatish"""
    try:
        stats = get_user_statistics()
        
        text = f"""
👑 *ADMIN PANELI*

📊 **Bot Statistikasi:**
👥 Jami foydalanuvchilar: {stats['total_users']} ta
💰 Berilgan ballar: {data['stats']['total_points_given']} ball
🎟️ Sotilgan kuponlar: {data['stats']['total_coupons_sold']} ta
🔄 Almashish so'rovlari: {data['stats']['total_exchanges']} ta

⚽ **Kuponlar:**
🎯 Bepul kuponlar: {len(data['coupons']['today']['matches'])} ta
💰 Ball kuponlar: {len(data['coupons']['ball_coupons']['available'])} ta

🎯 **Admin Imkoniyatlari:**
"""
        
        keyboard = [
            [InlineKeyboardButton("📊 Statistika", callback_data="admin_stats")],
            [InlineKeyboardButton("👥 Foydalanuvchilar", callback_data="admin_users")],
            [InlineKeyboardButton("🎯 Kupon Qo'shish", callback_data="admin_add_coupon")],
            [InlineKeyboardButton("🗑️ Kuponlarni Tozalash", callback_data="admin_clear_coupons")],
            [InlineKeyboardButton("💰 Ball Boshqarish", callback_data="admin_manage_points")],
            [InlineKeyboardButton("📢 Reklama Yuborish", callback_data="admin_broadcast")],
            [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"show_admin_panel da xato: {e}")

async def show_admin_add_coupon(query):
    """Kupon qo'shish sahifasi"""
    try:
        text = """
🎯 *KUPON QO'SHISH*

Quyidagi formatlardan birida kupon qo'shing:

📅 *Bepul kupon format:*
`sana|vaqt|liga|jamoalar|bashorat|koeffitsient|ishonch|1xbet_kodi|melbet_kodi|dbbet_kodi`

💰 *Ball kupon format:*
`vaqt|liga|jamoalar|bashorat|koeffitsient|ishonch|1xbet_kodi|melbet_kodi|dbbet_kodi`

📝 *Misol (Bepul kupon):*
`2024-01-20|20:00|Premier League|Man City vs Arsenal|1X|1.50|85%|CODE123|CODE456|CODE789`

📝 *Misol (Ball kupon):*
`20:00|Premier League|Man City vs Arsenal|1X|1.50|85%|CODE123|CODE456|CODE789`

Yuborilgan xabar avtomatik tarzda qayta ishlanadi.
"""
        
        keyboard = [
            [InlineKeyboardButton("👑 Admin Panel", callback_data="admin")],
            [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"show_admin_add_coupon da xato: {e}")

async def admin_clear_coupons(query):
    """Kuponlarni tozalash"""
    try:
        # Ball kuponlarni tozalash
        data['coupons']['ball_coupons']['available'] = []
        save_data(data)
        
        await query.message.reply_text(
            "✅ *Barcha ball kuponlar tozalandi!*\n\n"
            "Endi yangi kuponlar qo'shishingiz mumkin.",
            parse_mode='Markdown'
        )
        await show_admin_panel(query)
        
    except Exception as e:
        logger.error(f"admin_clear_coupons da xato: {e}")

# QOLGAN FUNKSIYALAR
async def show_my_points(query, user_id):
    """Foydalanuvchi ballari va statistikasi"""
    try:
        user_data = data['users'].get(str(user_id), {})
        points = user_data.get('points', 0)
        referrals = user_data.get('referrals', 0)
        min_points = data['settings']['min_exchange_points']
        exchange_rate = data['settings']['exchange_rate']
        
        text = f"""
🏆 *MENING HISOBIM*

💰 **Ballar:** {points} ball
👥 **Referallar:** {referrals} ta
💵 **1 referal:** {data['settings']['referral_points']} ball

📊 **Almashish imkoniyatlari:**
• {min_points} ball = {exchange_rate} {data['settings']['currency']}
• {min_points * 2} ball = {exchange_rate * 2} {data['settings']['currency']}
• {min_points * 5} ball = {exchange_rate * 5} {data['settings']['currency']}

"""
        
        if points >= min_points:
            text += f"✅ **Almashish mumkin:** {points // min_points} marta\n\n"
        else:
            text += f"❌ **Almashish uchun:** {min_points - points} ball yetishmayapti\n\n"
        
        # Ball tarixi
        points_history = user_data.get('points_history', [])
        if points_history:
            text += "📅 **So'nggi operatsiyalar:**\n"
            for history in points_history[-5:]:
                sign = "+" if history['points'] > 0 else ""
                text += f"• {sign}{history['points']} ball - {history['reason']}\n"
        
        keyboard = [
            [InlineKeyboardButton("💰 Ball Almashish", callback_data="exchange_points")],
            [InlineKeyboardButton("🎯 Kupon Olish", callback_data="get_coupons")],
            [InlineKeyboardButton("📤 Referal Havola", callback_data="get_referral_link")],
            [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"show_my_points da xato: {e}")

async def show_referral_link(query, user_id):
    """Referal havolasini ko'rsatish"""
    try:
        bot_username = (await query.message._bot.get_me()).username
        ref_link = f"https://t.me/{bot_username}?start=ref{user_id}"
        referrals_count = get_user_referrals(user_id)
        points_per_ref = data['settings']['referral_points']
        user_points = get_user_points(user_id)
        
        text = f"""
📤 *BAL TO'PLASH USULI*

🔗 **Sizning referal havolangiz:**
`{ref_link}`

💰 **Ball to'plash formulasi:**
• Har bir do'st = {points_per_ref} ball
• Ko'proq do'st = Ko'proq ball

📊 **Sizning holatingiz:**
• Do'stlar: {referrals_count} ta
• Ballar: {user_points} ball
• Jami olingan ball: {referrals_count * points_per_ref} ball

💡 **Qanday ball to'plasaniz:**
1. Havolani nusxalang
2. Do'stlaringizga yuboring  
3. Har bir yangi do'st = {points_per_ref} ball
4. Ballarni kuponlarga aylantiring!

🚀 *Ko'proq do'st taklif qiling, tezroq ball to'plang!*
"""

        keyboard = [
            [InlineKeyboardButton("🔗 TELEGRAMDA ULASHISH", callback_data="share_referral")],
            [InlineKeyboardButton("🎯 Kupon Olish", callback_data="get_coupons")],
            [InlineKeyboardButton("💰 Mening Ballim", callback_data="my_points")],
            [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"show_referral_link da xato: {e}")

async def share_referral_link(query, user_id):
    """Havolani ulashish"""
    try:
        bot_username = (await query.message._bot.get_me()).username
        ref_link = f"https://t.me/{bot_username}?start=ref{user_id}"
        
        share_text = f"""🎯 *Futbol Kuponlari Boti*

⚽ Kunlik bepul kuponlar
💰 Ball evaziga ekskluziv kuponlar
💎 Har bir do'st uchun 5 ball

🎁 Do'stlaringizni taklif qiling va bepul kuponlar oling!

Botga kirib, daromad olishni boshlang:
{ref_link}"""

        keyboard = [
            [InlineKeyboardButton("📤 TELEGRAMDA ULASHISH", url=f"https://t.me/share/url?url={ref_link}&text={share_text}")],
            [InlineKeyboardButton("💰 Mening Ballim", callback_data="my_points")],
            [InlineKeyboardButton("🎯 Kupon Olish", callback_data="get_coupons")],
            [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🔗 *Havolani quyidagi tugma orqali osongina ulashing:*\n\n"
            "Tugmani bosing va do'stlaringizga yuboring!",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"share_referral_link da xato: {e}")

async def show_help(query):
    """Yordam sahifasi"""
    try:
        text = """
ℹ️ *BOTDAN FOYDALANISH QO'LLANMASI*

⚽ *Kuponlar:*
• **Bepul kuponlar** - Har kuni yangilanaveradi!
• **Ball kuponlar** - 15 ball = 1 ta ekskluziv kupon

💰 *Ball Tizimi:*
• **1 do'st taklif = 5 ball**
• **50 ball = 10,000 so'm** almashish
• **15 ball = 1 ta maxsus kupon**

🎯 *Qanday boshlash kerak:*
1. 📤 Do'stlaringizni taklif qiling
2. 💰 Ball to'plang
3. 🎯 Kuponlar oling
4. 💸 Ballarni pulga aylantiring

📞 *Qo'llab-quvvatlash:*
@baxtga_olga

🚀 *Har kuni yangi kuponlar bilan yutuqqa intiling!*
"""
        
        keyboard = [
            [InlineKeyboardButton("🎯 Kupon Olish", callback_data="get_coupons")],
            [InlineKeyboardButton("📤 Referal Havola", callback_data="get_referral_link")],
            [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"show_help da xato: {e}")

async def back_to_coupon_selection(query):
    """Kupon tanlash sahifasiga qaytish"""
    user_id = query.from_user.id
    await show_coupon_selection(query, user_id)

async def back_to_main(query):
    """Asosiy menyuga qaytish"""
    try:
        user = query.from_user
        user_id = user.id
        
        keyboard = [
            [
                InlineKeyboardButton("🎯 KUPONLAR OLISH", callback_data="get_coupons"),
                InlineKeyboardButton("💰 BALL ALMASHISH", callback_data="exchange_points")
            ],
            [
                InlineKeyboardButton("🎁 BONUSLAR", callback_data="bonuses"),
                InlineKeyboardButton("📊 MENING BALLIM", callback_data="my_points")
            ],
            [
                InlineKeyboardButton("📤 REFERAL HAVOLA", callback_data="get_referral_link"),
                InlineKeyboardButton("ℹ️ YORDAM", callback_data="help")
            ]
        ]
        
        if is_admin(user_id):
            keyboard.append([InlineKeyboardButton("👑 ADMIN PANEL", callback_data="admin")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🎯 *Asosiy Menyu*\n\n"
            "Ball to'plang, kuponlar oling va yutuqlarga erishing! 🚀",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"back_to_main da xato: {e}")

# YORDAMCHI FUNKSIYALAR
def get_user_statistics():
    """Foydalanuvchi statistikasini hisoblash"""
    total_users = len(data['users'])
    
    today = datetime.now().strftime("%Y-%m-%d")
    today_users = sum(1 for user in data['users'].values() if user.get('joined_date') == today)
    
    today_referrals = sum(user.get('referrals', 0) for user in data['users'].values() if user.get('joined_date') == today)
    
    active_users = 0
    week_ago = datetime.now().timestamp() - 7 * 24 * 60 * 60
    for user_id, user_data in data['users'].items():
        last_active = user_data.get('last_active', 0)
        if last_active > week_ago:
            active_users += 1
    
    return {
        'total_users': total_users,
        'today_users': today_users,
        'today_referrals': today_referrals,
        'active_users': active_users
    }

# ADMIN XABARLARINI QAYTA ISHLASH
async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin xabarlarini qayta ishlash"""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return
    
    try:
        message = update.message
        
        # Ball qo'shish/olish rejimi
        if context.user_data.get('editing_user'):
            user_id_to_edit = context.user_data['editing_user']
            action = context.user_data.get('action')
            
            try:
                points = int(message.text)
                user_name = data['users'].get(user_id_to_edit, {}).get('name', 'Noma\'lum')
                
                if action == 'add_points':
                    add_user_points(int(user_id_to_edit), points, f"Admin tomonidan qo'shildi")
                    await message.reply_text(
                        f"✅ *Ball qo'shildi!*\n\n"
                        f"👤 Foydalanuvchi: {user_name}\n"
                        f"💰 Qo'shildi: {points} ball\n"
                        f"🎯 Jami ball: {get_user_points(int(user_id_to_edit))}",
                        parse_mode='Markdown'
                    )
                elif action == 'remove_points':
                    if remove_user_points(int(user_id_to_edit), points, f"Admin tomonidan olindi"):
                        await message.reply_text(
                            f"✅ *Ball olindi!*\n\n"
                            f"👤 Foydalanuvchi: {user_name}\n"
                            f"💰 Olindi: {points} ball\n"
                            f"🎯 Jami ball: {get_user_points(int(user_id_to_edit))}",
                            parse_mode='Markdown'
                        )
                    else:
                        await message.reply_text("❌ Ball yetarli emas!")
                
                context.user_data.pop('editing_user', None)
                context.user_data.pop('action', None)
                return
                
            except ValueError:
                await message.reply_text("❌ Iltimos, raqam kiriting!")
                return
        
        # Kupon qo'shish
        if '|' in message.text:
            parts = message.text.split('|')
            
            if len(parts) == 10:  # Bepul kupon
                date, time, league, teams, prediction, odds, confidence, code_1xbet, code_melbet, code_dbbet = parts
                
                new_match = {
                    'time': time.strip(),
                    'league': league.strip(),
                    'teams': teams.strip(),
                    'prediction': prediction.strip(),
                    'odds': odds.strip(),
                    'confidence': confidence.strip()
                }
                
                data['coupons']['today']['matches'].append(new_match)
                data['coupons']['today']['date'] = date.strip()
                data['coupons']['today']['coupon_codes'] = {
                    "1xbet": code_1xbet.strip(),
                    "melbet": code_melbet.strip(),
                    "dbbet": code_dbbet.strip()
                }
                save_data(data)
                
                await message.reply_text(
                    f"✅ *Bepul kupon qo'shildi!*\n\n"
                    f"🏆 {teams.strip()}\n"
                    f"⏰ {time.strip()} | {league.strip()}\n"
                    f"🎯 {prediction.strip()} | 📊 {odds.strip()}\n\n"
                    f"📊 Jami bepul kuponlar: {len(data['coupons']['today']['matches'])} ta",
                    parse_mode='Markdown'
                )
                
            elif len(parts) == 9:  # Ball kupon
                time, league, teams, prediction, odds, confidence, code_1xbet, code_melbet, code_dbbet = parts
                
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
                
                await message.reply_text(
                    f"✅ *Ball kupon qo'shildi!*\n\n"
                    f"🏆 {teams.strip()}\n"
                    f"⏰ {time.strip()} | {league.strip()}\n"
                    f"🎯 {prediction.strip()} | 📊 {odds.strip()}\n"
                    f"💰 Narxi: {data['settings']['coupon_price']} ball\n\n"
                    f"📊 Jami ball kuponlar: {len(data['coupons']['ball_coupons']['available'])} ta",
                    parse_mode='Markdown'
                )
        
        # Reklama yuborish
        else:
            total_users = len(data['users'])
            successful = 0
            
            for user_id_str in data['users']:
                try:
                    if message.text:
                        await context.bot.send_message(
                            chat_id=int(user_id_str),
                            text=message.text,
                            parse_mode='Markdown'
                        )
                    elif message.photo:
                        await context.bot.send_photo(
                            chat_id=int(user_id_str),
                            photo=message.photo[-1].file_id,
                            caption=message.caption,
                            parse_mode='Markdown'
                        )
                    successful += 1
                except:
                    continue
            
            await message.reply_text(
                f"📊 *Reklama yuborildi!*\n\n"
                f"👥 Jami: {total_users} ta\n"
                f"✅ Muvaffaqiyatli: {successful} ta\n"
                f"❌ Xatolik: {total_users - successful} ta",
                parse_mode='Markdown'
            )
            
    except Exception as e:
        logger.error(f"handle_admin_message da xato: {e}")
        await update.message.reply_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

def main():
    """Asosiy dastur"""
    try:
        application = Application.builder().token(TOKEN).build()
        
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CallbackQueryHandler(button_handler))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_message))
        application.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, handle_admin_message))
        
        logger.info("Bot ishga tushmoqda...")
        print("✅ Bot muvaffaqiyatli ishga tushdi!")
        print("🤖 Bot ishlayapti...")
        print(f"👑 Admin ID: {ADMIN_ID}")
        print("🎯 YANGI TIZIM:")
        print("   • 🎯 Kupon olish tizimi to'g'irlandi")
        print("   • 💰 Ball almashish @baxtga_olga ga yo'naltirildi")
        print("   • 👑 Mukammal admin paneli")
        print("   • 🚀 Chiroyli start xabari")
        
        application.run_polling()
        
    except Exception as e:
        logger.error(f"Main da xato: {e}")
        print(f"❌ Xato: {e}")

if __name__ == "__main__":
    main()
