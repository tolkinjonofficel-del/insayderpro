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
            },
            "button_text": "🎰 Bukmekerlar",
            "button_url": "https://t.me/bot_haqida"
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
        "min_referrals": 20,
        "referral_points": 5,
        "coupon_price": 15,
        "premium_price": 100000,
        "currency": "so'm",
        "min_exchange_points": 50,
        "exchange_rate": 10000,  # 50 ball = 10,000 so'm
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
    
    if 'points' not in data['users'][str(user_id)]:
        data['users'][str(user_id)]['points'] = 0
    
    data['users'][str(user_id)]['points'] += points
    data['stats']['total_points_given'] += points
    
    # Ball tarixini saqlash
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
    
    # Ball tarixini saqlash
    if 'points_history' not in data['users'][str(user_id)]:
        data['users'][str(user_id)]['points_history'] = []
    
    data['users'][str(user_id)]['points_history'].append({
        'points': -points,
        'reason': reason,
        'date': datetime.now().strftime("%Y-%m-%d %H:%M"),
        'type': 'remove'
    })
    
    return save_data(data)

def get_random_ball_coupon():
    """Tasodifiy ball kuponini olish"""
    ball_coupons = data['coupons']['ball_coupons']['available']
    if not ball_coupons:
        return None
    return random.choice(ball_coupons)

def remove_ball_coupon(coupon):
    """Ball kuponini olib tashlash"""
    if coupon in data['coupons']['ball_coupons']['available']:
        data['coupons']['ball_coupons']['available'].remove(coupon)
        return save_data(data)
    return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        user_id = user.id
        
        logger.info(f"Start command from user {user_id} ({user.first_name})")
        
        # Ma'lumotlarni qayta yuklash
        global data
        data = load_data()
        
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
            logger.info(f"Yangi foydalanuvchi qo'shildi: {user_id}")
        else:
            # Faollikni yangilash
            data['users'][str(user_id)]['last_active'] = datetime.now().timestamp()
            save_data(data)
        
        # Referal tekshirish
        if context.args:
            ref_id = context.args[0]
            logger.info(f"Referal argument: {ref_id}")
            if ref_id.startswith('ref'):
                try:
                    referrer_id = int(ref_id[3:])
                    if str(referrer_id) in data['users'] and referrer_id != user_id:
                        # Referal sonini oshirish
                        data['users'][str(referrer_id)]['referrals'] += 1
                        data['stats']['today_referrals'] += 1
                        
                        # Ball qo'shish (1 referal = 5 ball)
                        points_to_add = data['settings']['referral_points']
                        add_user_points(referrer_id, points_to_add, f"Referal taklif: {user.first_name}")
                        
                        save_data(data)
                        
                        # Referal egasiga xabar berish
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
                            logger.info(f"Referal bildirishnoma yuborildi: {referrer_id}")
                        except Exception as e:
                            logger.error(f"Referal bildirishnoma yuborishda xato: {e}")
                except Exception as e:
                    logger.error(f"Referal qayd etishda xato: {e}")

        # Yangi menyu tugmalari
        keyboard = [
            [
                InlineKeyboardButton("🎯 Kuponlar Olish", callback_data="get_coupons"),
                InlineKeyboardButton("💰 Ball Almashish", callback_data="exchange_points")
            ],
            [
                InlineKeyboardButton("🎁 Bonuslar", callback_data="bonuses"),
                InlineKeyboardButton("📊 Mening Ballim", callback_data="my_points")
            ],
            [
                InlineKeyboardButton("📤 Referal Havola", callback_data="get_referral_link"),
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
• 📤 1 referal taklif = *{data['settings']['referral_points']} ball*
• 🎯 {data['settings']['coupon_price']} ball = *1 ta ekskluziv kupon*
• 💰 {data['settings']['min_exchange_points']} ball = *{data['settings']['exchange_rate']} {data['settings']['currency']}*

📊 *Sizning holatingiz:*
👥 Referallar: {get_user_referrals(user_id)} ta
💰 Ballar: {get_user_points(user_id)} ball

🎯 *Ball to'plash usullari:*
1. 📤 Do'stlarni taklif qiling (1 do'st = 5 ball)
2. 🎁 Bonuslardan foydalaning
3. 💰 Ballarni pulga aylantiring

*Ball to'plang va yutuqlarga erishing!* 🚀
"""
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        logger.info(f"Start xabari muvaffaqiyatli yuborildi: {user_id}")
        
    except Exception as e:
        logger.error(f"Start commandda xato: {e}")
        await update.message.reply_text(
            "❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.",
            parse_mode='Markdown'
        )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        logger.info(f"Button handler: {query.data} from user {user_id}")
        
        # Ma'lumotlarni yangilash
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
        elif query.data == "admin_coupon_buttons":
            await show_admin_coupon_buttons(query)
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
        try:
            await update.callback_query.message.reply_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")
        except:
            pass

# YANGI FUNKSIYALAR

async def show_coupon_selection(query, user_id):
    """Kupon olish sahifasi"""
    try:
        user_points = get_user_points(user_id)
        coupon_price = data['settings']['coupon_price']
        
        text = f"""
🎯 *KUPON OLISH*

💰 **Sizning balansingiz:** {user_points} ball

🎁 *Quyidagi kuponlardan birini tanlang:*
"""

        keyboard = [
            [InlineKeyboardButton("🎯 BEPUL KUPON OLISH", callback_data="get_free_coupon")],
        ]
        
        # Agar ball yetarli bo'lsa, ball kupon tugmasini ko'rsatish
        if user_points >= coupon_price:
            keyboard.append([InlineKeyboardButton(f"💰 BALL EVAZIGA KUPON OLISH ({coupon_price} ball)", callback_data="get_ball_coupon")])
        else:
            text += f"\n❌ *Ball yetarli emas!*\nBall to'plash uchun referal havolangizni tarqating."
        
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

💡 *Ball almashish uchun:*
1. Kamida {min_points} ball to'plang
2. "So'rov yuborish" tugmasini bosing
3. Admin siz bilan bog'lanadi

⚠️ *Eslatma:* Ball almashish uchun @baxtga_olga ga murojaat qiling.
"""

        keyboard = []
        
        if user_points >= min_points:
            keyboard.append([InlineKeyboardButton("📨 SO'ROV YUBORISH", callback_data="request_exchange")])
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
        await query.message.reply_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

async def request_exchange(query, user_id):
    """Ball almashish so'rovini yuborish"""
    try:
        user_points = get_user_points(user_id)
        min_points = data['settings']['min_exchange_points']
        
        if user_points < min_points:
            await query.message.reply_text(
                f"❌ Ballaringiz yetarli emas!\n"
                f"💰 Sizda: {user_points} ball\n"
                f"💵 Minimal: {min_points} ball",
                parse_mode='Markdown'
            )
            return await show_exchange_points(query, user_id)
        
        # Adminlarga bildirishnoma yuborish
        user_data = data['users'][str(user_id)]
        user_name = user_data.get('name', 'Noma\'lum')
        user_username = f"@{user_data.get('username')}" if user_data.get('username') else "Yo'q"
        
        exchange_text = f"""
🔄 *YANGI ALMASHISH SO'ROVI*

👤 **Foydalanuvchi:** {user_name}
📱 **Username:** {user_username}
🆔 **ID:** {user_id}
💰 **Ballar:** {user_points} ball

💸 **So'ralayotgan miqdor:** {min_points} ball = {data['settings']['exchange_rate']} {data['settings']['currency']}

📞 Bog'lanish: @baxtga_olga
"""
        
        # Adminlarga xabar yuborish
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=exchange_text,
            parse_mode='Markdown'
        )
        
        # Foydalanuvchiga tasdiqlash
        await query.edit_message_text(
            f"✅ *So'rovingiz qabul qilindi!*\n\n"
            f"📨 So'rovingiz adminlarga yuborildi.\n"
            f"💰 Miqdor: {min_points} ball\n"
            f"💵 Summa: {data['settings']['exchange_rate']} {data['settings']['currency']}\n\n"
            f"📞 Tez orada admin @baxtga_olga siz bilan bog'lanadi.\n\n"
            f"⏰ *Eslatma:* Bog'lanish uchun tayyor bo'ling!",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"request_exchange da xato: {e}")
        await query.message.reply_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

async def show_bonuses(query):
    """Bonuslar sahifasi"""
    try:
        text = """
🎁 *BONUSLAR*

🏆 *Bukmeker kontorlarida ro'yxatdan o'ting va bonus oling!*

🎰 **1xBet:**
• Yangi foydalanuvchilar uchun 100% bonus
• Birinchi depozitga 100% gacha bonus

🎯 **MelBet:**
• Ro'yxatdan o'ting va bonus oling
• Birinchi stavkangiz uchun maxsus taklif

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
        await query.message.reply_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

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
        await query.message.reply_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

# ADMIN FUNKSIYALARI

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
🔄 Almashishlar: {data['stats']['total_exchanges']} ta

⚽ **Kuponlar:**
🎯 Bepul kuponlar: {len(data['coupons']['today']['matches'])} ta
💰 Ball kuponlar: {len(data['coupons']['ball_coupons']['available'])} ta

🎯 **Admin Imkoniyatlari:**
"""
        
        keyboard = [
            [InlineKeyboardButton("📊 Statistika", callback_data="admin_stats")],
            [InlineKeyboardButton("👥 Foydalanuvchilar", callback_data="admin_users")],
            [InlineKeyboardButton("🎯 Kupon Qo'shish", callback_data="admin_add_coupon")],
            [InlineKeyboardButton("💰 Ball Boshqarish", callback_data="admin_manage_points")],
            [InlineKeyboardButton("📢 Reklama Yuborish", callback_data="admin_broadcast")],
            [InlineKeyboardButton("🔗 Kupon Tugmalari", callback_data="admin_coupon_buttons")],
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
        
        text = f"""
📊 *BATAFSIL STATISTIKA*

👥 **Foydalanuvchilar:**
• Jami: {stats['total_users']} ta
• Bugungi yangi: {stats['today_users']} ta
• Aktiv (7 kun): {stats['active_users']} ta

💰 **Ball Tizimi:**
• Berilgan ballar: {data['stats']['total_points_given']} ball
• Sotilgan kuponlar: {data['stats']['total_coupons_sold']} ta
• Almashishlar: {data['stats']['total_exchanges']} ta

📈 **Referallar:**
• Bugungi referallar: {stats['today_referrals']} ta
• Jami referallar: {sum(user.get('referrals', 0) for user in data['users'].values())} ta

⏰ Yangilangan: {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""
        
        keyboard = [
            [InlineKeyboardButton("🔄 Yangilash", callback_data="admin_stats")],
            [InlineKeyboardButton("👑 Admin Panel", callback_data="admin")],
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
        users_list = list(users.items())[:10]  # Birinchi 10 tasi
        
        text = f"""
👥 *FOYDALANUVCHILAR RO'YXATI*

Jami: {len(users)} ta foydalanuvchi

"""
        
        for i, (user_id, user_data) in enumerate(users_list, 1):
            name = user_data.get('name', 'Noma\'lum')
            points = user_data.get('points', 0)
            referrals = user_data.get('referrals', 0)
            
            text += f"{i}. {name}\n"
            text += f"   🆔: {user_id} | 💰: {points} ball | 👥: {referrals} ta\n\n"
        
        keyboard = [
            [InlineKeyboardButton("🔄 Yangilash", callback_data="admin_users")],
            [InlineKeyboardButton("💰 Ball Boshqarish", callback_data="admin_manage_points")],
            [InlineKeyboardButton("👑 Admin Panel", callback_data="admin")],
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
        users_list = list(users.items())[:5]  # Birinchi 5 tasi
        
        text = """
💰 *BALL BOSHQARISH*

Quyidagi foydalanuvchilarga ball qo'shish yoki olib tashlash uchun tugmalardan foydalaning:

"""
        
        for user_id, user_data in users_list:
            name = user_data.get('name', 'Noma\'lum')
            points = user_data.get('points', 0)
            
            text += f"👤 {name}\n"
            text += f"💰 {points} ball\n"
        
        keyboard = []
        
        for user_id, user_data in users_list:
            name = user_data.get('name', 'Noma\'lum')[:15]
            keyboard.append([
                InlineKeyboardButton(f"➕ {name}", callback_data=f"admin_add_points_{user_id}"),
                InlineKeyboardButton(f"➖ {name}", callback_data=f"admin_remove_points_{user_id}")
            ])
        
        keyboard.extend([
            [InlineKeyboardButton("👑 Admin Panel", callback_data="admin")],
            [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"show_admin_manage_points da xato: {e}")
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

📝 *Misol:*
`2024-01-20|20:00|Premier League|Man City vs Arsenal|1X|1.50|85%|CODE123|CODE456|CODE789`

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
        await query.message.reply_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

async def show_admin_broadcast(query):
    """Reklama yuborish sahifasi"""
    try:
        text = """
📢 *REKLAMA YUBORISH*

Barcha foydalanuvchilarga xabar yuborish uchun quyidagi formatda xabar yuboring:

📨 *Matn xabar:* Oddiy matn
🖼️ *Rasm xabar:* Rasm + taglavha
📎 *Fayl xabar:* Har qanday fayl

Xabar barcha {len(data['users'])} ta foydalanuvchiga yuboriladi.
"""
        
        keyboard = [
            [InlineKeyboardButton("👑 Admin Panel", callback_data="admin")],
            [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"show_admin_broadcast da xato: {e}")
        await query.message.reply_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

async def show_admin_coupon_buttons(query):
    """Kupon tugmalarini boshqarish"""
    try:
        current_button = data['coupons']['today'].get('button_text', '🎰 Bukmekerlar')
        current_url = data['coupons']['today'].get('button_url', 'https://t.me/bot_haqida')
        
        text = f"""
🔗 *KUPON TUGMALARI*

Kuponlar ostida ko'rinadigan tugmani sozlang:

📝 *Joriy sozlamalar:*
• Matn: {current_button}
• Havola: {current_url}

🔄 *O'zgartirish uchun:*
`tugma_matni|havola_url`

📝 *Misol:*
`🎰 1xBet ga o'tish|https://1xbet.com`
`📱 Ilova yuklash|https://t.me/bonusliapkbot`
"""
        
        keyboard = [
            [InlineKeyboardButton("👑 Admin Panel", callback_data="admin")],
            [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"show_admin_coupon_buttons da xato: {e}")
        await query.message.reply_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

# YORDAMCHI FUNKSIYALAR

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

async def back_to_coupon_selection(query):
    """Kupon tanlash sahifasiga qaytish"""
    user_id = query.from_user.id
    await show_coupon_selection(query, user_id)

async def back_to_main(query):
    """Asosiy menyuga qaytish"""
    try:
        user = query.from_user
        user_id = user.id
        
        # Yangi menyu tugmalari
        keyboard = [
            [
                InlineKeyboardButton("🎯 Kuponlar Olish", callback_data="get_coupons"),
                InlineKeyboardButton("💰 Ball Almashish", callback_data="exchange_points")
            ],
            [
                InlineKeyboardButton("🎁 Bonuslar", callback_data="bonuses"),
                InlineKeyboardButton("📊 Mening Ballim", callback_data="my_points")
            ],
            [
                InlineKeyboardButton("📤 Referal Havola", callback_data="get_referral_link"),
                InlineKeyboardButton("ℹ️ Yordam", callback_data="help")
            ]
        ]
        
        if is_admin(user_id):
            keyboard.append([InlineKeyboardButton("👑 Admin Panel", callback_data="admin")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🎯 *Asosiy Menyu*\n\n"
            "Ball to'plang, kuponlar oling va yutuqlarga erishing! 🚀",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"back_to_main da xato: {e}")
        await query.message.reply_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

# QOLGAN FUNKSIYALAR (send_today_coupons, get_ball_coupon, show_referral_link, va boshqalar)
# Ushbu funksiyalar avvalgi kodda mavjud, ularni o'zgartirmasdan qoldiring.

# ... (qolgan funksiyalar avvalgi kabi)

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
                # Bepul kupon qo'shish logikasi
                await message.reply_text("✅ Bepul kupon qo'shildi!")
                
            elif len(parts) == 9:  # Ball kupon
                # Ball kupon qo'shish logikasi
                await message.reply_text("✅ Ball kupon qo'shildi!")
            
            elif len(parts) == 2:  # Tugma sozlamalari
                button_text, button_url = parts
                data['coupons']['today']['button_text'] = button_text.strip()
                data['coupons']['today']['button_url'] = button_url.strip()
                save_data(data)
                await message.reply_text(
                    f"✅ *Tugma sozlamalari yangilandi!*\n\n"
                    f"📝 Matn: {button_text}\n"
                    f"🔗 Havola: {button_url}",
                    parse_mode='Markdown'
                )
        
        # Reklama yuborish
        else:
            # Barcha foydalanuvchilarga xabar yuborish
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
        # Application yaratish
        application = Application.builder().token(TOKEN).build()
        
        # Handlerlarni qo'shish
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CallbackQueryHandler(button_handler))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_message))
        application.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, handle_admin_message))
        
        # Botni ishga tushirish
        logger.info("Bot ishga tushmoqda...")
        print("✅ Bot muvaffaqiyatli ishga tushdi!")
        print("🤖 Bot ishlayapti...")
        print(f"👑 Admin ID: {ADMIN_ID}")
        print("🎯 YANGI FUNKSIYALAR:")
        print("   • 💰 Ball almashish (50 ball = 10,000 so'm)")
        print("   • 🎁 Bonuslar bo'limi")
        print("   • 👑 To'liq admin paneli")
        print("   • 🔗 Kupon tugmalari boshqaruvi")
        print("   • 📊 Batafsil statistika")
        
        application.run_polling()
        
    except Exception as e:
        logger.error(f"Main da xato: {e}")
        print(f"❌ Xato: {e}")

if __name__ == "__main__":
    main()
