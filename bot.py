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
    },
    "admin_state": {}  # Admin holatini saqlash
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

def set_admin_state(user_id, state, data=None):
    """Admin holatini saqlash"""
    data['admin_state'][str(user_id)] = {
        'state': state,
        'data': data if data else {},
        'timestamp': datetime.now().timestamp()
    }
    save_data(data)

def get_admin_state(user_id):
    """Admin holatini olish"""
    return data['admin_state'].get(str(user_id), {})

def clear_admin_state(user_id):
    """Admin holatini tozalash"""
    if str(user_id) in data['admin_state']:
        del data['admin_state'][str(user_id)]
        save_data(data)

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
            data['stats']['today_users'] += 1
            save_data(data)
            logger.info(f"Yangi foydalanuvchi qo'shildi: {user_id}")
        else:
            data['users'][str(user_id)]['last_active'] = datetime.now().timestamp()
            save_data(data)
        
        # Referal tizimi
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
        
        # ADMIN HANDLERLARI
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
        elif query.data == "admin_settings":
            await show_admin_settings(query)
        elif query.data == "admin_back":
            await show_admin_panel(query)
        
        # Ball boshqarish handlerlari
        elif query.data.startswith("admin_add_points_"):
            target_user_id = int(query.data.split("_")[3])
            set_admin_state(user_id, "add_points", {"target_user_id": target_user_id})
            await query.edit_message_text(
                f"💰 *Ball qo'shish*\n\n"
                f"Foydalanuvchi ID: {target_user_id}\n"
                f"Foydalanuvchi: {data['users'].get(str(target_user_id), {}).get('name', 'Noma lum')}\n\n"
                f"Qo'shmoqchi bo'lgan ball miqdorini yuboring:",
                parse_mode='Markdown'
            )
        elif query.data.startswith("admin_remove_points_"):
            target_user_id = int(query.data.split("_")[3])
            set_admin_state(user_id, "remove_points", {"target_user_id": target_user_id})
            await query.edit_message_text(
                f"💰 *Ball olib tashlash*\n\n"
                f"Foydalanuvchi ID: {target_user_id}\n"
                f"Foydalanuvchi: {data['users'].get(str(target_user_id), {}).get('name', 'Noma lum')}\n"
                f"Joriy ball: {get_user_points(target_user_id)}\n\n"
                f"Olib tashlamoqchi bo'lgan ball miqdorini yuboring:",
                parse_mode='Markdown'
            )
        elif query.data.startswith("admin_view_user_"):
            target_user_id = int(query.data.split("_")[3])
            await show_user_details(query, target_user_id)
        
        else:
            await query.message.reply_text("❌ Noma'lum buyruq!")
            
    except Exception as e:
        logger.error(f"Button handlerda xato: {e}")
        try:
            await query.message.reply_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")
        except:
            pass

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
        
        coupon_text += "🔑 *Kupon Kodlari:*\n"
        coupon_text += f"• 1xBet: `{today_coupons['coupon_codes'].get('1xbet', 'Kod mavjud emas')}`\n"
        coupon_text += f"• MelBet: `{today_coupons['coupon_codes'].get('melbet', 'Kod mavjud emas')}`\n"
        coupon_text += f"• DB Bet: `{today_coupons['coupon_codes'].get('dbbet', 'Kod mavjud emas')}`\n\n"
        
        coupon_text += "---\n\n"
        
        for i, match in enumerate(today_coupons['matches'], 1):
            coupon_text += f"*{i}. {match['time']} - {match['league']}*\n"
            coupon_text += f"🏆 `{match['teams']}`\n"
            coupon_text += f"🎯 **Bashorat:** `{match['prediction']}`\n"
            coupon_text += f"📊 **Koeffitsient:** `{match['odds']}`\n"
            coupon_text += f"💎 **Ishonch:** {match['confidence']}\n\n"
        
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
            await query.edit_message_text(
                f"❌ Ballaringiz yetarli emas!\n"
                f"💰 Sizda: {user_points} ball\n"
                f"💵 Kerak: {coupon_price} ball\n\n"
                f"📤 Ball to'plash uchun referal havolangizni tarqating yoki ball almashingiz!",
                parse_mode='Markdown'
            )
            return await show_coupon_selection(query, user_id)
        
        ball_coupons = data['coupons']['ball_coupons']['available']
        if not ball_coupons:
            await query.edit_message_text(
                "❌ Hozircha mavjud kuponlar yo'q. Tez orada yangilanadi! 🔄",
                parse_mode='Markdown'
            )
            return await show_coupon_selection(query, user_id)
        
        coupon = random.choice(ball_coupons)
        
        data['users'][str(user_id)]['points'] -= coupon_price
        data['stats']['total_coupons_sold'] += 1
        
        if 'purchased' not in data['coupons']['ball_coupons']:
            data['coupons']['ball_coupons']['purchased'] = {}
        
        if str(user_id) not in data['coupons']['ball_coupons']['purchased']:
            data['coupons']['ball_coupons']['purchased'][str(user_id)] = []
        
        data['coupons']['ball_coupons']['purchased'][str(user_id)].append({
            **coupon,
            'purchased_date': datetime.now().strftime("%Y-%m-%d %H:%M"),
            'price_paid': coupon_price
        })
        
        data['coupons']['ball_coupons']['available'].remove(coupon)
        save_data(data)
        
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

# FOYDALANUVCHI HISOBINI KO'RSATISH
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

# REFERAL TIZIMI
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

# YORDAM BO'LIMI
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

# ADMIN PANELI
async def show_admin_panel(query):
    """Admin panelini ko'rsatish"""
    try:
        stats = get_user_statistics()
        total_points = sum(user.get('points', 0) for user in data['users'].values())
        
        text = f"""
👑 *ADMIN PANELI*

📊 **Bot Statistikasi:**
👥 Jami foydalanuvchilar: {stats['total_users']} ta
💰 Jami ballar: {total_points} ball
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
            [InlineKeyboardButton("💰 Ball Boshqarish", callback_data="admin_manage_points")],
            [InlineKeyboardButton("🎯 Kupon Qo'shish", callback_data="admin_add_coupon")],
            [InlineKeyboardButton("⚙️ Sozlamalar", callback_data="admin_settings")],
            [InlineKeyboardButton("🗑️ Kuponlarni Tozalash", callback_data="admin_clear_coupons")],
            [InlineKeyboardButton("📢 Reklama Yuborish", callback_data="admin_broadcast")],
            [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"show_admin_panel da xato: {e}")
        await query.message.reply_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

async def show_admin_stats(query):
    """Batafsil statistika"""
    try:
        stats = get_user_statistics()
        total_points = sum(user.get('points', 0) for user in data['users'].values())
        total_referrals = sum(user.get('referrals', 0) for user in data['users'].values())
        
        text = f"""
📊 *BATAFSIL STATISTIKA*

👥 **Foydalanuvchilar:**
• Jami: {stats['total_users']} ta
• Bugungi yangi: {stats['today_users']} ta
• Aktiv (7 kun): {stats['active_users']} ta

💰 **Ball Tizimi:**
• Jami berilgan: {data['stats']['total_points_given']} ball
• Foydalanuvchilarda: {total_points} ball
• Sotilgan kuponlar: {data['stats']['total_coupons_sold']} ta

📈 **Referallar:**
• Jami referallar: {total_referrals} ta
• Bugungi referallar: {stats['today_referrals']} ta

⚽ **Kuponlar:**
• Bepul kuponlar: {len(data['coupons']['today']['matches'])} ta
• Ball kuponlar: {len(data['coupons']['ball_coupons']['available'])} ta

⏰ Yangilangan: {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""
        
        keyboard = [
            [InlineKeyboardButton("💰 Ball Boshqarish", callback_data="admin_manage_points")],
            [InlineKeyboardButton("🔄 Yangilash", callback_data="admin_stats")],
            [InlineKeyboardButton("👑 Admin Panel", callback_data="admin_back")],
            [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"show_admin_stats da xato: {e}")
        await query.message.reply_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

async def show_admin_users(query):
    """Foydalanuvchilar ro'yxati"""
    try:
        users = data['users']
        users_list = list(users.items())[:10]
        
        text = f"""
👥 *FOYDALANUVCHILAR RO'YXATI*

Jami: {len(users)} ta foydalanuvchi

"""
        
        for i, (user_id, user_data) in enumerate(users_list, 1):
            name = user_data.get('name', 'Noma\'lum')
            points = user_data.get('points', 0)
            referrals = user_data.get('referrals', 0)
            joined_date = user_data.get('joined_date', 'Noma\'lum')
            
            text += f"{i}. {name}\n"
            text += f"   🆔: {user_id}\n"
            text += f"   💰: {points} ball | 👥: {referrals} ta\n"
            text += f"   📅: {joined_date}\n\n"
        
        keyboard = [
            [InlineKeyboardButton("💰 Ball Boshqarish", callback_data="admin_manage_points")],
            [InlineKeyboardButton("🔄 Yangilash", callback_data="admin_users")],
            [InlineKeyboardButton("👑 Admin Panel", callback_data="admin_back")],
            [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"show_admin_users da xato: {e}")
        await query.message.reply_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

async def show_admin_manage_points(query):
    """Ball boshqarish sahifasi"""
    try:
        users = data['users']
        users_list = list(users.items())[:5]
        
        text = """
💰 *BALL BOSHQARISH*

Quyidagi foydalanuvchilarga ball operatsiyalarini amalga oshirishingiz mumkin:

"""
        
        for i, (user_id, user_data) in enumerate(users_list, 1):
            name = user_data.get('name', 'Noma\'lum')
            points = user_data.get('points', 0)
            referrals = user_data.get('referrals', 0)
            
            text += f"{i}. {name}\n"
            text += f"   🆔: {user_id}\n"
            text += f"   💰: {points} ball | 👥: {referrals} ta\n\n"
        
        keyboard = []
        
        for user_id, user_data in users_list:
            name = user_data.get('name', 'Noma\'lum')[:15]
            keyboard.append([
                InlineKeyboardButton(f"➕ {name}", callback_data=f"admin_add_points_{user_id}"),
                InlineKeyboardButton(f"➖ {name}", callback_data=f"admin_remove_points_{user_id}"),
                InlineKeyboardButton(f"👁️ {name}", callback_data=f"admin_view_user_{user_id}")
            ])
        
        keyboard.extend([
            [InlineKeyboardButton("👥 Barcha Foydalanuvchilar", callback_data="admin_users")],
            [InlineKeyboardButton("👑 Admin Panel", callback_data="admin_back")],
            [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"show_admin_manage_points da xato: {e}")
        await query.message.reply_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

async def show_user_details(query, user_id):
    """Foydalanuvchi tafsilotlari"""
    try:
        user_data = data['users'].get(str(user_id), {})
        
        text = f"""
👤 *FOYDALANUVCHI TAFSILOTLARI*

🏷️ **Ism:** {user_data.get('name', 'Noma lum')}
🆔 **ID:** {user_id}
📅 **Qo'shilgan sana:** {user_data.get('joined_date', 'Noma lum')}
💰 **Ballar:** {user_data.get('points', 0)} ball
👥 **Referallar:** {user_data.get('referrals', 0)} ta
👑 **Premium:** {'✅' if user_data.get('premium', False) else '❌'}

📊 **Ball tarixi:**
"""
        
        points_history = user_data.get('points_history', [])
        if points_history:
            for history in points_history[-10:]:
                sign = "+" if history['points'] > 0 else ""
                text += f"• {sign}{history['points']} ball - {history['reason']} ({history['date']})\n"
        else:
            text += "• Tarix mavjud emas\n"
        
        keyboard = [
            [
                InlineKeyboardButton("➕ Ball Qo'shish", callback_data=f"admin_add_points_{user_id}"),
                InlineKeyboardButton("➖ Ball Olib Tashlash", callback_data=f"admin_remove_points_{user_id}")
            ],
            [InlineKeyboardButton("👥 Foydalanuvchilar", callback_data="admin_users")],
            [InlineKeyboardButton("👑 Admin Panel", callback_data="admin_back")],
            [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"show_user_details da xato: {e}")
        await query.message.reply_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

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
            [InlineKeyboardButton("👑 Admin Panel", callback_data="admin_back")],
            [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"show_admin_add_coupon da xato: {e}")
        await query.message.reply_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

async def show_admin_broadcast(query):
    """Reklama yuborish sahifasi"""
    try:
        text = f"""
📢 *REKLAMA YUBORISH*

Barcha {len(data['users'])} ta foydalanuvchilarga xabar yuborish uchun quyidagi formatda xabar yuboring:

📨 *Matn xabar:* Oddiy matn
🖼️ *Rasm xabar:* Rasm + taglavha
📎 *Fayl xabar:* Har qanday fayl

Xabar barcha foydalanuvchilarga yuboriladi.
"""
        
        keyboard = [
            [InlineKeyboardButton("👑 Admin Panel", callback_data="admin_back")],
            [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"show_admin_broadcast da xato: {e}")
        await query.message.reply_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

async def show_admin_settings(query):
    """Sozlamalar sahifasi"""
    try:
        settings = data['settings']
        
        text = f"""
⚙️ *SOZLAMALAR*

💰 **Ball tizimi sozlamalari:**
• Referal ball: {settings['referral_points']} ball
• Kupon narxi: {settings['coupon_price']} ball
• Minimal almashish: {settings['min_exchange_points']} ball
• Almashish kursi: {settings['exchange_rate']} {settings['currency']}

👥 **Referal sozlamalari:**
• Minimal referal: {settings['min_referrals']} ta

💎 **Premium sozlamalari:**
• Premium narxi: {settings['premium_price']} {settings['currency']}

📝 Sozlamalarni o'zgartirish uchun @baxtga_olga ga murojaat qiling.
"""
        
        keyboard = [
            [InlineKeyboardButton("👑 Admin Panel", callback_data="admin_back")],
            [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"show_admin_settings da xato: {e}")
        await query.message.reply_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

async def admin_clear_coupons(query):
    """Kuponlarni tozalash"""
    try:
        data['coupons']['ball_coupons']['available'] = []
        save_data(data)
        
        await query.edit_message_text(
            "✅ *Barcha ball kuponlar tozalandi!*\n\n"
            "Endi yangi kuponlar qo'shishingiz mumkin.",
            parse_mode='Markdown'
        )
        await show_admin_panel(query)
        
    except Exception as e:
        logger.error(f"admin_clear_coupons da xato: {e}")

# YORDAMCHI FUNKSIYALAR
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
        admin_state = get_admin_state(user_id)
        
        # Ball qo'shish/olib tashlash holati
        if admin_state.get('state') in ['add_points', 'remove_points']:
            try:
                points = int(message.text)
                target_user_id = admin_state['data']['target_user_id']
                
                if admin_state['state'] == 'add_points':
                    if add_user_points(target_user_id, points, f"Admin tomonidan qo'shildi"):
                        await message.reply_text(
                            f"✅ *Ball qo'shildi!*\n\n"
                            f"👤 Foydalanuvchi: {data['users'].get(str(target_user_id), {}).get('name', 'Noma lum')}\n"
                            f"🆔 ID: {target_user_id}\n"
                            f"💰 Qo'shildi: {points} ball\n"
                            f"🎯 Jami ball: {get_user_points(target_user_id)}",
                            parse_mode='Markdown'
                        )
                    else:
                        await message.reply_text("❌ Ball qo'shishda xatolik!")
                
                elif admin_state['state'] == 'remove_points':
                    if remove_user_points(target_user_id, points, f"Admin tomonidan olib tashlandi"):
                        await message.reply_text(
                            f"✅ *Ball olib tashlandi!*\n\n"
                            f"👤 Foydalanuvchi: {data['users'].get(str(target_user_id), {}).get('name', 'Noma lum')}\n"
                            f"🆔 ID: {target_user_id}\n"
                            f"💰 Olib tashlandi: {points} ball\n"
                            f"🎯 Qolgan ball: {get_user_points(target_user_id)}",
                            parse_mode='Markdown'
                        )
                    else:
                        await message.reply_text("❌ Ball olib tashlashda xatolik! Ball yetarli emas.")
                
                clear_admin_state(user_id)
                return
                
            except ValueError:
                await message.reply_text("❌ Iltimos, faqat raqam yuboring!")
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
            
            progress_msg = await message.reply_text(f"📤 Xabar yuborilmoqda... 0/{total_users}")
            
            for i, user_id_str in enumerate(data['users']):
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
                    
                    if i % 10 == 0:
                        await progress_msg.edit_text(f"📤 Xabar yuborilmoqda... {i}/{total_users}")
                        
                except Exception as e:
                    logger.error(f"Foydalanuvchiga xabar yuborishda xato {user_id_str}: {e}")
                    continue
            
            await progress_msg.edit_text(
                f"📊 *Reklama yuborildi!*\n\n"
                f"👥 Jami foydalanuvchi: {total_users} ta\n"
                f"✅ Muvaffaqiyatli: {successful} ta\n"
                f"❌ Xatolik: {total_users - successful} ta\n"
                f"📈 Muvaffaqiyat darajasi: {(successful/total_users*100):.1f}%",
                parse_mode='Markdown'
            )
            
    except Exception as e:
        logger.error(f"handle_admin_message da xato: {e}")
        await update.message.reply_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

# ASOSIY DASTUR
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
        print("🎯 BARCHA TUGMALAR ISHLAYDI:")
        print("   • 🎯 Kupon olish tizimi")
        print("   • 💰 Ball almashish") 
        print("   • 🎁 Bonuslar")
        print("   • 📊 Mening ballim")
        print("   • 📤 Referal tizimi")
        print("   • 👑 Admin paneli")
        print("   • 📊 Statistika")
        print("   • ⚙️ Sozlamalar")
        
        application.run_polling()
        
    except Exception as e:
        logger.error(f"Main da xato: {e}")
        print(f"❌ Xato: {e}")

if __name__ == "__main__":
    main()
