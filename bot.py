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

def find_user_by_id_or_username(search_term):
    """Foydalanuvchini ID yoki username orqali qidirish"""
    results = []
    search_term = str(search_term).lower().strip()
    
    for user_id, user_data in data['users'].items():
        # ID bo'yicha qidirish
        if search_term == user_id:
            results.append((user_id, user_data))
            continue
        
        # Username bo'yicha qidirish
        username = user_data.get('username', '').lower()
        if username and search_term in username:
            results.append((user_id, user_data))
            continue
        
        # Ism bo'yicha qidirish
        name = user_data.get('name', '').lower()
        if name and search_term in name:
            results.append((user_id, user_data))
    
    return results

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
        elif query.data == "admin_find_user":
            await admin_find_user(query, context)
        
        else:
            await query.message.reply_text("❌ Noma'lum buyruq!")
            
    except Exception as e:
        logger.error(f"Button handlerda xato: {e}")
        try:
            await update.callback_query.message.reply_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")
        except:
            pass

# YANGI ADMIN FUNKSIYALARI
async def show_admin_manage_points(query):
    """Ball boshqarish sahifasi"""
    try:
        text = """
💰 *BALL BOSHQARISH*

Foydalanuvchi ballarini boshqarish uchun quyidagi imkoniyatlar mavjud:

🔍 *Foydalanuvchi qidirish usullari:*
• **ID orqali** - Foydalanuvchi ID raqamini kiriting
• **Username orqali** - @username formatida
• **Ism orqali** - Foydalanuvchi ismini kiriting

🎯 *Ball operatsiyalari:*
• Ball qo'shish
• Ball olib tashlash
• Ballar tarixini ko'rish
"""

        keyboard = [
            [InlineKeyboardButton("🔍 Foydalanuvchi Qidirish", callback_data="admin_find_user")],
            [InlineKeyboardButton("📊 Foydalanuvchilar Ro'yxati", callback_data="admin_users")],
            [InlineKeyboardButton("👑 Admin Panel", callback_data="admin")],
            [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"show_admin_manage_points da xato: {e}")
        await query.message.reply_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

async def admin_find_user(query, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchi qidirishni boshlash"""
    try:
        context.user_data['searching_user'] = True
        
        text = """
🔍 *FOYDALANUVCHI QIDIRISH*

Foydalanuvchini qidirish uchun quyidagilardan birini kiriting:

• **ID raqami** (masalan: 123456789)
• **Username** (masalan: @username yoki username)
• **Ism** (masalan: Ali)

Qidiruv natijasida topilgan foydalanuvchilarni tanlang va ballarini boshqaring.
"""

        keyboard = [
            [InlineKeyboardButton("👑 Admin Panel", callback_data="admin")],
            [InlineKeyboardButton("🔙 Orqaga", callback_data="admin_manage_points")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"admin_find_user da xato: {e}")

async def show_user_search_results(query, search_term, results):
    """Foydalanuvchi qidirish natijalarini ko'rsatish"""
    try:
        if not results:
            text = f"""
🔍 *QIDIRUV NATIJALARI*

❌ *"{search_term}" bo'yicha foydalanuvchi topilmadi!*

Qaytadan urinib ko'ring yoki boshqa kalit so'z kiriting.
"""
            
            keyboard = [
                [InlineKeyboardButton("🔄 Qayta Qidirish", callback_data="admin_find_user")],
                [InlineKeyboardButton("👑 Admin Panel", callback_data="admin")],
                [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
            ]
        else:
            text = f"""
🔍 *QIDIRUV NATIJALARI*

✅ *"{search_term}" bo'yicha {len(results)} ta foydalanuvchi topildi:*

"""
            
            for i, (user_id, user_data) in enumerate(results, 1):
                name = user_data.get('name', 'Noma\'lum')
                username = f"@{user_data.get('username')}" if user_data.get('username') else "Yo'q"
                points = user_data.get('points', 0)
                referrals = user_data.get('referrals', 0)
                
                text += f"{i}. **{name}**\n"
                text += f"   👤 {username} | 🆔 {user_id}\n"
                text += f"   💰 {points} ball | 👥 {referrals} referal\n\n"
            
            keyboard = []
            
            for user_id, user_data in results:
                name = user_data.get('name', 'Noma\'lum')[:20]
                keyboard.append([
                    InlineKeyboardButton(f"➕ {name}", callback_data=f"admin_add_points_{user_id}"),
                    InlineKeyboardButton(f"➖ {name}", callback_data=f"admin_remove_points_{user_id}")
                ])
            
            keyboard.extend([
                [InlineKeyboardButton("📋 Ball Tarixi", callback_data=f"admin_points_history_{results[0][0]}")],
                [InlineKeyboardButton("🔄 Boshqa Qidirish", callback_data="admin_find_user")],
                [InlineKeyboardButton("👑 Admin Panel", callback_data="admin")],
                [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"show_user_search_results da xato: {e}")

async def show_user_points_history(query, user_id):
    """Foydalanuvchi ball tarixini ko'rsatish"""
    try:
        user_data = data['users'].get(str(user_id), {})
        name = user_data.get('name', 'Noma\'lum')
        username = f"@{user_data.get('username')}" if user_data.get('username') else "Yo'q"
        current_points = user_data.get('points', 0)
        points_history = user_data.get('points_history', [])
        
        text = f"""
📋 *BALL TARIXI*

👤 **Foydalanuvchi:** {name}
📱 **Username:** {username}
🆔 **ID:** {user_id}
💰 **Joriy ball:** {current_points}

"""
        
        if points_history:
            text += "📅 **Ball operatsiyalari:**\n\n"
            for history in points_history[-10:]:  # Oxirgi 10 ta operatsiya
                sign = "+" if history['points'] > 0 else ""
                emoji = "🟢" if history['points'] > 0 else "🔴"
                text += f"{emoji} {sign}{history['points']} ball\n"
                text += f"   📝 {history['reason']}\n"
                text += f"   ⏰ {history['date']}\n\n"
        else:
            text += "📭 Ball operatsiyalari mavjud emas.\n\n"
        
        keyboard = [
            [
                InlineKeyboardButton("➕ Ball Qo'shish", callback_data=f"admin_add_points_{user_id}"),
                InlineKeyboardButton("➖ Ball Olib Tashlash", callback_data=f"admin_remove_points_{user_id}")
            ],
            [InlineKeyboardButton("🔍 Boshqa Foydalanuvchi", callback_data="admin_find_user")],
            [InlineKeyboardButton("👑 Admin Panel", callback_data="admin")],
            [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"show_user_points_history da xato: {e}")

# ADMIN PANELNI YANGILAYMIZ
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
            [InlineKeyboardButton("🔍 Ball Boshqarish", callback_data="admin_manage_points")],
            [InlineKeyboardButton("👥 Foydalanuvchilar", callback_data="admin_users")],
            [InlineKeyboardButton("🎯 Kupon Qo'shish", callback_data="admin_add_coupon")],
            [InlineKeyboardButton("🗑️ Kuponlarni Tozalash", callback_data="admin_clear_coupons")],
            [InlineKeyboardButton("📢 Reklama Yuborish", callback_data="admin_broadcast")],
            [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"show_admin_panel da xato: {e}")
        await query.message.reply_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

# BUTTON HANDLERGA YANGI HANDLERLARNI QO'SHAMIZ
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
        elif query.data == "admin_find_user":
            await admin_find_user(query, context)
        
        # BALL QO'SHISH/OLISH HANDLERLARI
        elif query.data.startswith("admin_add_points_"):
            user_id_to_edit = query.data.replace("admin_add_points_", "")
            context.user_data['editing_user'] = user_id_to_edit
            context.user_data['action'] = 'add_points'
            user_data = data['users'].get(user_id_to_edit, {})
            user_name = user_data.get('name', 'Noma\'lum')
            current_points = user_data.get('points', 0)
            
            await query.message.reply_text(
                f"👤 *Foydalanuvchi:* {user_name}\n"
                f"🆔 *ID:* {user_id_to_edit}\n"
                f"💰 *Joriy ball:* {current_points} ball\n"
                f"💳 *Qancha ball qo'shmoqchisiz?*\n\n"
                f"Raqam kiriting:",
                parse_mode='Markdown'
            )
            
        elif query.data.startswith("admin_remove_points_"):
            user_id_to_edit = query.data.replace("admin_remove_points_", "")
            context.user_data['editing_user'] = user_id_to_edit
            context.user_data['action'] = 'remove_points'
            user_data = data['users'].get(user_id_to_edit, {})
            user_name = user_data.get('name', 'Noma\'lum')
            current_points = user_data.get('points', 0)
            
            await query.message.reply_text(
                f"👤 *Foydalanuvchi:* {user_name}\n"
                f"🆔 *ID:* {user_id_to_edit}\n"
                f"💰 *Joriy ball:* {current_points} ball\n"
                f"💳 *Qancha ball olib tashlamoqchisiz?*\n\n"
                f"Raqam kiriting:",
                parse_mode='Markdown'
            )
        
        # BALL TARIXI HANDLERI
        elif query.data.startswith("admin_points_history_"):
            user_id_to_view = query.data.replace("admin_points_history_", "")
            await show_user_points_history(query, user_id_to_view)
        
        else:
            await query.message.reply_text("❌ Noma'lum buyruq!")
            
    except Exception as e:
        logger.error(f"Button handlerda xato: {e}")
        try:
            await update.callback_query.message.reply_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")
        except:
            pass

# ADMIN XABARLARINI QAYTA ISHLASHNI YANGILAYMIZ
async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin xabarlarini qayta ishlash"""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return
    
    try:
        message = update.message
        
        # Foydalanuvchi qidirish rejimi
        if context.user_data.get('searching_user'):
            search_term = message.text
            results = find_user_by_id_or_username(search_term)
            
            await show_user_search_results(update.callback_query, search_term, results)
            context.user_data.pop('searching_user', None)
            return
        
        # Ball qo'shish/olish rejimi
        if context.user_data.get('editing_user'):
            user_id_to_edit = context.user_data['editing_user']
            action = context.user_data.get('action')
            
            try:
                points = int(message.text)
                user_data = data['users'].get(user_id_to_edit, {})
                user_name = user_data.get('name', 'Noma\'lum')
                current_points = user_data.get('points', 0)
                
                if action == 'add_points':
                    add_user_points(int(user_id_to_edit), points, f"Admin tomonidan qo'shildi")
                    await message.reply_text(
                        f"✅ *Ball qo'shildi!*\n\n"
                        f"👤 Foydalanuvchi: {user_name}\n"
                        f"🆔 ID: {user_id_to_edit}\n"
                        f"💰 Qo'shildi: {points} ball\n"
                        f"📊 Avval: {current_points} ball\n"
                        f"🎯 Keyin: {get_user_points(int(user_id_to_edit))} ball",
                        parse_mode='Markdown'
                    )
                    
                elif action == 'remove_points':
                    if remove_user_points(int(user_id_to_edit), points, f"Admin tomonidan olindi"):
                        await message.reply_text(
                            f"✅ *Ball olindi!*\n\n"
                            f"👤 Foydalanuvchi: {user_name}\n"
                            f"🆔 ID: {user_id_to_edit}\n"
                            f"💰 Olindi: {points} ball\n"
                            f"📊 Avval: {current_points} ball\n"
                            f"🎯 Keyin: {get_user_points(int(user_id_to_edit))} ball",
                            parse_mode='Markdown'
                        )
                    else:
                        await message.reply_text(
                            f"❌ *Ball olib bo'lmadi!*\n\n"
                            f"👤 Foydalanuvchi: {user_name}\n"
                            f"💰 So'ralgan: {points} ball\n"
                            f"🎯 Mavjud: {current_points} ball\n\n"
                            f"Ball yetarli emas!",
                            parse_mode='Markdown'
                        )
                
                context.user_data.pop('editing_user', None)
                context.user_data.pop('action', None)
                return
                
            except ValueError:
                await message.reply_text("❌ Iltimos, faqat raqam kiriting!")
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

# QOLGAN FUNKSIYALAR (avvalgi kabi)
# ... (qolgan funksiyalar o'zgarmagan)

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
        print("🎯 YANGI ADMIN PANELI:")
        print("   • 🔍 Foydalanuvchi qidirish (ID, username, ism)")
        print("   • 💰 Ball boshqarish")
        print("   • 📋 Ball tarixini ko'rish")
        print("   • 👑 Mukammal boshqaruv")
        
        application.run_polling()
        
    except Exception as e:
        logger.error(f"Main da xato: {e}")
        print(f"❌ Xato: {e}")

if __name__ == "__main__":
    main()
