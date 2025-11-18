import os
import json
import logging
import random
import string
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from datetime import datetime, timedelta

# Bot tokeni
TOKEN = "8114630640:AAGoBCnsw22xIHIzRK5Mt0N1f1gtodKLl40"

# Admin ID
ADMIN_ID = 7081746531

# Ma'lumotlarni saqlash fayli
DATA_FILE = "apple_fortune_data.json"

# Loggerni sozlash
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Boshlang'ich ma'lumotlar
default_data = {
    "users": {},
    "signals": {
        "available": [],
        "sent": {},
        "price": 15,
        "last_update": ""
    },
    "settings": {
        "referral_points": 5,
        "new_user_points": 15,
        "signal_price": 15,
        "min_exchange_points": 50,
        "exchange_rate": 10000,
        "currency": "so'm",
        "payment_details": "💳 *To'lov qilish uchun:*\n\n🏦 **HUMO:** `9860356622837710`\n📱 **Payme:** `mavjud emas`\n💳 **Uzumbank visa:** `4916990318695001`\n\n✅ To'lov qilgach, chek skrinshotini @baxtga_olga ga yuboring."
    },
    "stats": {
        "total_users": 0,
        "today_users": 0,
        "today_referrals": 0,
        "total_points_given": 0,
        "total_signals_sold": 0,
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
        
        is_new_user = False
        if str(user_id) not in data['users']:
            data['users'][str(user_id)] = {
                'name': user.first_name,
                'username': user.username,
                'referrals': 0,
                'points': 0,
                'joined_date': datetime.now().strftime("%Y-%m-%d"),
                'last_active': datetime.now().timestamp(),
                'points_history': []
            }
            data['stats']['total_users'] += 1
            data['stats']['today_users'] += 1
            is_new_user = True
            
        data['users'][str(user_id)]['last_active'] = datetime.now().timestamp()
        
        # Referal tizimi
        if context.args:
            ref_id = context.args[0]
            logger.info(f"Referal argument: {ref_id}")
            if ref_id.startswith('ref'):
                try:
                    referrer_id = int(ref_id[3:])
                    if str(referrer_id) in data['users'] and referrer_id != user_id:
                        # Taklif qilgan odamga 5 ball
                        data['users'][str(referrer_id)]['referrals'] += 1
                        add_user_points(referrer_id, data['settings']['referral_points'], 
                                      f"Referal taklif: {user.first_name}")
                        
                        # Yangi odamga 15 ball (faqat yangi foydalanuvchilar uchun)
                        if is_new_user:
                            add_user_points(user_id, data['settings']['new_user_points'], 
                                          "Yangi foydalanuvchi bonusi")
                        
                        data['stats']['today_referrals'] += 1
                        save_data(data)
                        
                        try:
                            await context.bot.send_message(
                                chat_id=referrer_id,
                                text=f"🎉 *Tabriklaymiz!*\n\n"
                                     f"📤 Sizning referal havolangiz orqali yangi foydalanuvchi qo'shildi!\n"
                                     f"👤 Yangi foydalanuvchi: {user.first_name}\n"
                                     f"💰 Sizga {data['settings']['referral_points']} ball qo'shildi!\n"
                                     f"🎯 Jami ball: {get_user_points(referrer_id)}",
                                parse_mode='Markdown'
                            )
                        except Exception as e:
                            logger.error(f"Referal bildirishnoma yuborishda xato: {e}")
                except Exception as e:
                    logger.error(f"Referal qayd etishda xato: {e}")
        
        save_data(data)

        welcome_text = f"""
🍎 *APPLE OF FORTUNE SIGNAL BOTIGA XUSH KELIBSIZ!* 🎰

💰 *APPLE OF FORTUNE EXCLUSIVE SIGNALLAR!*
• 🎯 Har bir signal - 15 ball
• 📊 Professional tahlillar
• 💰 Yuqori daromad imkoniyati

🏆 *BALL TIZIMI:*
• 📤 1 do'st taklif = *5 ball*
• 🎁 Yangi foydalanuvchi = *15 ball*
• 💰 50 ball = *10,000 so'm*

📊 *SIZNING HOLATINGIZ:*
👥 Referallar: {get_user_referrals(user_id)} ta
💰 Balans: {get_user_points(user_id)} ball

🚀 *HOZIRROQ BOSHLANG!*
Ball to'plang, signallar oling va yutuqlarga erishing!
"""

        keyboard = [
            [
                InlineKeyboardButton("🎯 SIGNAL OLISH", callback_data="get_signals"),
                InlineKeyboardButton("💰 PUL ISHLASH", callback_data="exchange_points")
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
        
        if query.data == "get_signals":
            await show_signal_selection(query, user_id)
        elif query.data == "buy_signal":
            await buy_signal(query, user_id)
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
        
        # ADMIN HANDLERLARI
        elif query.data == "admin":
            if is_admin(user_id):
                await show_admin_panel(query)
        elif query.data == "admin_stats":
            await show_admin_stats(query)
        elif query.data == "admin_users":
            await show_admin_users(query)
        elif query.data == "admin_add_signal":
            await show_admin_add_signal(query)
        elif query.data == "admin_manage_points":
            await show_admin_manage_points(query)
        elif query.data == "admin_broadcast":
            await show_admin_broadcast(query)
        elif query.data == "admin_clear_signals":
            await admin_clear_signals(query)
        
        # BALL BOSHQARISH
        elif query.data.startswith("admin_add_points_"):
            user_id_to_edit = query.data.replace("admin_add_points_", "")
            context.user_data['editing_user'] = user_id_to_edit
            context.user_data['action'] = 'add_points'
            user_data = data['users'].get(user_id_to_edit, {})
            user_name = user_data.get('name', 'Noma\'lum')
            current_points = user_data.get('points', 0)
            
            await query.message.reply_text(
                f"👤 *Foydalanuvchi:* {user_name}\n"
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
                f"💰 *Joriy ball:* {current_points} ball\n"
                f"💳 *Qancha ball olib tashlamoqchisiz?*\n\n"
                f"Raqam kiriting:",
                parse_mode='Markdown'
            )
        
        else:
            await query.message.reply_text("❌ Noma'lum buyruq!")
            
    except Exception as e:
        logger.error(f"Button handlerda xato: {e}")

# SIGNAL OLISH TIZIMI
async def show_signal_selection(query, user_id):
    """Signal olish sahifasi"""
    try:
        user_points = get_user_points(user_id)
        signal_price = data['settings']['signal_price']
        available_signals = len(data['signals']['available'])
        
        text = f"""
🎯 *APPLE OF FORTUNE SIGNALLARI*

💰 **Sizning balansingiz:** {user_points} ball
🎰 **Signal narxi:** {signal_price} ball
📊 **Mavjud signallar:** {available_signals} ta

💎 *Professional Apple of Fortune signallari:*
• Yuqori aniqlikdagi tahlillar
• Optimal stavka strategiyalari
• Maximum daromad imkoniyati
"""

        keyboard = []
        
        if available_signals > 0:
            if user_points >= signal_price:
                keyboard.append([InlineKeyboardButton(f"🎯 SIGNAL OLISH ({signal_price} ball)", callback_data="buy_signal")])
                text += f"\n✅ *Siz signal olishingiz mumkin!*"
            else:
                text += f"\n❌ *Ball yetarli emas!* {signal_price - user_points} ball yetishmayapti."
                keyboard.append([InlineKeyboardButton("📤 Ball To'plash", callback_data="get_referral_link")])
        else:
            text += f"\n📭 *Hozircha signallar mavjud emas.* Tez orada yangilanadi!"
        
        keyboard.extend([
            [InlineKeyboardButton("💰 PUL ISHLASH", callback_data="exchange_points")],
            [InlineKeyboardButton("📤 Ball To'plash", callback_data="get_referral_link")],
            [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"show_signal_selection da xato: {e}")

async def buy_signal(query, user_id):
    """Signal sotib olish"""
    try:
        user_points = get_user_points(user_id)
        signal_price = data['settings']['signal_price']
        
        if user_points < signal_price:
            await query.message.reply_text(
                f"❌ Ballaringiz yetarli emas!\n"
                f"💰 Sizda: {user_points} ball\n"
                f"💵 Kerak: {signal_price} ball\n\n"
                f"📤 Ball to'plash uchun referal havolangizni tarqating!",
                parse_mode='Markdown'
            )
            return await show_signal_selection(query, user_id)
        
        available_signals = data['signals']['available']
        if not available_signals:
            await query.message.reply_text(
                "❌ Hozircha mavjud signallar yo'q. Tez orada yangilanadi! 🔄",
                parse_mode='Markdown'
            )
            return await show_signal_selection(query, user_id)
        
        signal = available_signals[0]  # Birinchi signalni olamiz
        
        # Ball olib tashlash
        data['users'][str(user_id)]['points'] -= signal_price
        data['stats']['total_signals_sold'] += 1
        
        # Signalni yuborish
        signal_text = f"""
🍎 *APPLE OF FORTUNE SIGNAL* 🎰

⏰ **Vaqt:** {signal['time']}
💰 **Stavka:** {signal['bet_amount']}
🎯 **Strategiya:** {signal['strategy']}
📊 **Bashorat:** {signal['prediction']}
💎 **Ishonch darajasi:** {signal['confidence']}

📝 **Tavsiya:**
{signal['recommendation']}

⚠️ **Eslatma:** 
- Stavkalarni ehtiyotkorlik bilan qo'ying
- Bankrot bo'lmaslik uchun mablag'ingizni boshqaring
- Signal faqat 1 soat davomida amal qiladi
"""

        keyboard = [
            [InlineKeyboardButton("🔄 Yana Signal Olish", callback_data="get_signals")],
            [InlineKeyboardButton("💰 Mening Ballim", callback_data="my_points")],
            [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(signal_text, reply_markup=reply_markup, parse_mode='Markdown')
        
        # Signalni available ro'yxatdan olib tashlash
        data['signals']['available'].pop(0)
        
        # Sent signals ga qo'shish
        if 'sent' not in data['signals']:
            data['signals']['sent'] = {}
        
        if str(user_id) not in data['signals']['sent']:
            data['signals']['sent'][str(user_id)] = []
        
        data['signals']['sent'][str(user_id)].append({
            **signal,
            'purchased_date': datetime.now().strftime("%Y-%m-%d %H:%M"),
            'price_paid': signal_price
        })
        
        save_data(data)
        
    except Exception as e:
        logger.error(f"buy_signal da xato: {e}")

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

💡 *Ballni pulga almashish uchun @baxtga_olga ga murojaat qiling!*
"""

        keyboard = []
        
        if user_points >= min_points:
            keyboard.append([InlineKeyboardButton("📨 SO'ROV YUBORISH", url="https://t.me/baxtga_olga")])
        else:
            text += f"\n❌ *Ball yetarli emas!* {min_points - user_points} ball yetishmayapti."
            keyboard.append([InlineKeyboardButton("📤 Ball To'plash", callback_data="get_referral_link")])
        
        keyboard.extend([
            [InlineKeyboardButton("🎯 Signal Olish", callback_data="get_signals")],
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
🎁 *BONUS TIZIMI*

🏆 *Ball to'plashning tez yo'llari:*

📤 **Referal tizimi:**
• Har bir do'st taklif = *5 ball*
• Yangi foydalanuvchi = *15 ball*
• Cheksiz do'st taklif qiling!

💰 **Ball almashish:**
• 50 ball = 10,000 so'm
• 100 ball = 20,000 so'm
• 500 ball = 100,000 so'm

🎯 **Signallar:**
• Har bir signal = 15 ball
• Professional tahlillar
• Yuqori daromad imkoniyati

🚀 *Ko'proq do'st taklif qiling, tezroq ball to'plang!*
"""

        keyboard = [
            [InlineKeyboardButton("📤 Referal Havola", callback_data="get_referral_link")],
            [InlineKeyboardButton("🎯 Signal Olish", callback_data="get_signals")],
            [InlineKeyboardButton("💰 PUL ISHLASH", callback_data="exchange_points")],
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

💰 **Balans:** {points} ball
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
            [InlineKeyboardButton("💰 PUL ISHLASH", callback_data="exchange_points")],
            [InlineKeyboardButton("🎯 Signal Olish", callback_data="get_signals")],
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
        new_user_points = data['settings']['new_user_points']
        user_points = get_user_points(user_id)
        
        text = f"""
📤 *BALL TO'PLASH USULI*

🔗 **Sizning referal havolangiz:**
`{ref_link}`

💰 **Ball to'plash formulasi:**
• Har bir do'st taklif = {points_per_ref} ball
• Yangi foydalanuvchi = {new_user_points} ball (bepul)
• Ko'proq do'st = Ko'proq ball

📊 **Sizning holatingiz:**
• Do'stlar: {referrals_count} ta
• Balans: {user_points} ball
• Jami olingan ball: {referrals_count * points_per_ref} ball

💡 **Qanday ball to'plasaniz:**
1. Havolani nusxalang
2. Do'stlaringizga yuboring  
3. Har bir yangi do'st = {points_per_ref} ball
4. Do'stingiz {new_user_points} ball bilan boshlaydi
5. Ballarni signallarga aylantiring!

🚀 *Ko'proq do'st taklif qiling, tezroq ball to'plang!*
"""

        keyboard = [
            [InlineKeyboardButton("🔗 TELEGRAMDA ULASHISH", callback_data="share_referral")],
            [InlineKeyboardButton("🎯 Signal Olish", callback_data="get_signals")],
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
        
        share_text = f"""🍎 *Apple of Fortune Signal Boti*

🎰 Exclusive Apple of Fortune signallari
💰 Har bir signal - professional tahlillar
🎁 Yangi foydalanuvchilar uchun 15 ball bepul!

📤 Do'stlaringizni taklif qiling va ball to'plang:
• Har bir do'st = 5 ball
• Do'stingiz = 15 ball bepul

Botga kirib, daromad olishni boshlang:
{ref_link}"""

        keyboard = [
            [InlineKeyboardButton("📤 TELEGRAMDA ULASHISH", url=f"https://t.me/share/url?url={ref_link}&text={share_text}")],
            [InlineKeyboardButton("💰 Mening Ballim", callback_data="my_points")],
            [InlineKeyboardButton("🎯 Signal Olish", callback_data="get_signals")],
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

🍎 *Apple of Fortune Signallari:*
• **Har bir signal** - 15 ball
• **Professional tahlillar**
• **Yuqori daromad imkoniyati**

💰 *Ball Tizimi:*
• **1 do'st taklif = 5 ball**
• **Yangi foydalanuvchi = 15 ball** (bepul)
• **50 ball = 10,000 so'm** almashish
• **15 ball = 1 ta signal**

🎯 *Qanday boshlash kerak:*
1. 📤 Do'stlaringizni taklif qiling
2. 💰 Ball to'plang (har bir do'st = 5 ball)
3. 🎯 Signallar oling (har biri 15 ball)
4. 💸 Ballarni pulga aylantiring

📞 *Qo'llab-quvvatlash:*
@baxtga_olga

🚀 *Professional signallar bilan yutuqqa intiling!*
"""
        
        keyboard = [
            [InlineKeyboardButton("🎯 Signal Olish", callback_data="get_signals")],
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
🎟️ Sotilgan signallar: {data['stats']['total_signals_sold']} ta
🔄 Almashish so'rovlari: {data['stats']['total_exchanges']} ta

🎰 **Signallar:**
📊 Mavjud signallar: {len(data['signals']['available'])} ta

🎯 **Admin Imkoniyatlari:**
"""
        
        keyboard = [
            [InlineKeyboardButton("📊 Statistika", callback_data="admin_stats")],
            [InlineKeyboardButton("👥 Foydalanuvchilar", callback_data="admin_users")],
            [InlineKeyboardButton("💰 Ball Boshqarish", callback_data="admin_manage_points")],
            [InlineKeyboardButton("🎯 Signal Qo'shish", callback_data="admin_add_signal")],
            [InlineKeyboardButton("🗑️ Signallarni Tozalash", callback_data="admin_clear_signals")],
            [InlineKeyboardButton("📢 Reklama Yuborish", callback_data="admin_broadcast")],
            [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"show_admin_panel da xato: {e}")

# QOLGAN ADMIN FUNKSIYALARI (qisqartirilgan versiya)
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

💰 **Ball Tizimi:**
• Jami berilgan: {data['stats']['total_points_given']} ball
• Foydalanuvchilarda: {total_points} ball
• Sotilgan signallar: {data['stats']['total_signals_sold']} ta

📈 **Referallar:**
• Jami referallar: {total_referrals} ta
• Bugungi referallar: {stats['today_referrals']} ta

🎰 **Signallar:**
• Mavjud signallar: {len(data['signals']['available'])} ta

⏰ Yangilangan: {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""
        
        keyboard = [
            [InlineKeyboardButton("💰 Ball Boshqarish", callback_data="admin_manage_points")],
            [InlineKeyboardButton("🔄 Yangilash", callback_data="admin_stats")],
            [InlineKeyboardButton("👑 Admin Panel", callback_data="admin")],
            [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"show_admin_stats da xato: {e}")

async def show_admin_add_signal(query):
    """Signal qo'shish sahifasi"""
    try:
        text = """
🎯 *SIGNAL QO'SHISH*

Quyidagi formatda signal qo'shing:

`vaqt|stavka_miqdori|strategiya|bashorat|ishonch_darajasi|tavsiya`

📝 *Misol:*
`14:30|5000 so'm|3x Martingale|Qizil|85%|Avval kichik stavka qilib ko'ring`

💡 *Eslatma:* Signal qo'shilgach, foydalanuvchilar 15 ball evaziga sotib olishlari mumkin.
"""
        
        keyboard = [
            [InlineKeyboardButton("👑 Admin Panel", callback_data="admin")],
            [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"show_admin_add_signal da xato: {e}")

async def admin_clear_signals(query):
    """Signallarni tozalash"""
    try:
        data['signals']['available'] = []
        save_data(data)
        
        await query.message.reply_text(
            "✅ *Barcha signallar tozalandi!*\n\n"
            "Endi yangi signallar qo'shishingiz mumkin.",
            parse_mode='Markdown'
        )
        await show_admin_panel(query)
        
    except Exception as e:
        logger.error(f"admin_clear_signals da xato: {e}")

# YORDAMCHI FUNKSIYALAR
async def back_to_main(query):
    """Asosiy menyuga qaytish"""
    try:
        user = query.from_user
        user_id = user.id
        
        keyboard = [
            [
                InlineKeyboardButton("🎯 SIGNAL OLISH", callback_data="get_signals"),
                InlineKeyboardButton("💰 PUL ISHLASH", callback_data="exchange_points")
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
            "🍎 *Apple of Fortune - Asosiy Menyu*\n\n"
            "Ball to'plang, signallar oling va yutuqlarga erishing! 🚀",
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
    
    today_referrals = data['stats']['today_referrals']
    
    return {
        'total_users': total_users,
        'today_users': today_users,
        'today_referrals': today_referrals
    }

# ADMIN XABARLARINI QAYTA ISHLASH
async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin xabarlarini qayta ishlash"""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return
    
    try:
        message = update.message
        message_text = message.text.strip()
        
        # Signal qo'shish
        if '|' in message.text:
            parts = message.text.split('|')
            
            if len(parts) == 6:  # Signal format
                time, bet_amount, strategy, prediction, confidence, recommendation = parts
                
                new_signal = {
                    'time': time.strip(),
                    'bet_amount': bet_amount.strip(),
                    'strategy': strategy.strip(),
                    'prediction': prediction.strip(),
                    'confidence': confidence.strip(),
                    'recommendation': recommendation.strip(),
                    'added_date': datetime.now().strftime("%Y-%m-%d %H:%M")
                }
                
                data['signals']['available'].append(new_signal)
                data['signals']['last_update'] = datetime.now().strftime("%Y-%m-%d %H:%M")
                save_data(data)
                
                await message.reply_text(
                    f"✅ *Signal qo'shildi!*\n\n"
                    f"⏰ Vaqt: {time.strip()}\n"
                    f"💰 Stavka: {bet_amount.strip()}\n"
                    f"🎯 Strategiya: {strategy.strip()}\n"
                    f"📊 Bashorat: {prediction.strip()}\n"
                    f"💎 Ishonch: {confidence.strip()}\n\n"
                    f"📊 Jami signallar: {len(data['signals']['available'])} ta",
                    parse_mode='Markdown'
                )
        
        # Ball qo'shish/olish
        elif context.user_data.get('editing_user'):
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

# QOLGAN ADMIN FUNKSIYALARI (qisqartirilgan)
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
            username = user_data.get('username', '')
            points = user_data.get('points', 0)
            referrals = user_data.get('referrals', 0)
            
            username_display = f"(@{username})" if username else ""
            
            text += f"{i}. {name} {username_display}\n"
            text += f"   🆔: `{user_id}`\n"
            text += f"   💰: {points} ball | 👥: {referrals} ta\n\n"
        
        keyboard = [
            [InlineKeyboardButton("💰 Ball Boshqarish", callback_data="admin_manage_points")],
            [InlineKeyboardButton("🔄 Yangilash", callback_data="admin_users")],
            [InlineKeyboardButton("👑 Admin Panel", callback_data="admin")],
            [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"show_admin_users da xato: {e}")

async def show_admin_manage_points(query):
    """Ball boshqarish sahifasi"""
    try:
        text = """
💰 *BALL BOSHQARISH*

Foydalanuvchi ID sini va ball miqdorini yuboring:

`user_id ball_miqdori`

📝 *Misol:*
`123456789 50` - 123456789 ID li foydalanuvchiga 50 ball qo'shadi

Yoki foydalanuvchini tanlang:
"""
        
        users = data['users']
        sorted_users = sorted(users.items(), key=lambda x: x[1].get('points', 0), reverse=True)[:8]
        
        keyboard = []
        
        for user_id, user_data in sorted_users:
            name = user_data.get('name', 'Noma\'lum')[:12]
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

async def show_admin_broadcast(query):
    """Reklama yuborish sahifasi"""
    try:
        text = f"""
📢 *REKLAMA YUBORISH*

Barcha {len(data['users'])} ta foydalanuvchilarga xabar yuborish uchun xabar yuboring.

Xabar barcha foydalanuvchilarga yuboriladi.
"""
        
        keyboard = [
            [InlineKeyboardButton("👑 Admin Panel", callback_data="admin")],
            [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"show_admin_broadcast da xato: {e}")

# ASOSIY DASTUR
def main():
    """Asosiy dastur"""
    try:
        application = Application.builder().token(TOKEN).build()
        
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CallbackQueryHandler(button_handler))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_message))
        
        logger.info("Apple of Fortune Bot ishga tushmoqda...")
        print("✅ Bot muvaffaqiyatli ishga tushdi!")
        print("🍎 Apple of Fortune Signal Boti")
        print(f"👑 Admin ID: {ADMIN_ID}")
        print("🎯 BARCHA FUNKSIYALAR ISHLAYDI:")
        print("   • 🎯 Signal olish tizimi (15 ball)")
        print("   • 📤 Referal tizimi (5 ball + 15 ball yangi foydalanuvchi)")
        print("   • 💰 Ball almashish")
        print("   • 👑 Admin paneli")
        
        application.run_polling()
        
    except Exception as e:
        logger.error(f"Main da xato: {e}")
        print(f"❌ Xato: {e}")

if __name__ == "__main__":
    main()
