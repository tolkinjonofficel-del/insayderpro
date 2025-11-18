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
    "settings": {
        "referral_points": 5,
        "new_user_points": 40,
        "regular_signal_price": 20,
        "vip_signal_price": 50,
        "signal_url": "https://www.signal7.digital/"
    },
    "stats": {
        "total_users": 0,
        "today_users": 0,
        "today_referrals": 0,
        "total_points_given": 0,
        "total_signals_used": 0,
        "total_vip_signals_used": 0
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
                'points': data['settings']['new_user_points'],
                'joined_date': datetime.now().strftime("%Y-%m-%d"),
                'last_active': datetime.now().timestamp(),
                'points_history': []
            }
            data['stats']['total_users'] += 1
            data['stats']['today_users'] += 1
            is_new_user = True
            
            # Yangi foydalanuvchi uchun ball qo'shish
            add_user_points(user_id, data['settings']['new_user_points'], "Yangi foydalanuvchi bonusi")
            
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
                        
                        data['stats']['today_referrals'] += 1
                        save_data(data)
                        
                        try:
                            await context.bot.send_message(
                                chat_id=referrer_id,
                                text=f"🎉 *Tabriklaymiz!*\n\n"
                                     f"📤 Sizning referal havolangiz orqali yangi foydalanuvchi qo'shildi!\n"
                                     f"👤 Yangi foydalanuvchi: {user.first_name}\n"
                                     f"💰 Sizga {data['settings']['referral_points']} ball qo'shildi!\n"
                                     f"🎯 Jami ball: {get_user_points(referrer_id)}\n\n"
                                     f"📊 Jami referallar: {get_user_referrals(referrer_id)} ta",
                                parse_mode='Markdown'
                            )
                        except Exception as e:
                            logger.error(f"Referal bildirishnoma yuborishda xato: {e}")
                except Exception as e:
                    logger.error(f"Referal qayd etishda xato: {e}")
        
        save_data(data)

        welcome_text = f"""
🍎 *APPLE OF FORTUNE SIGNAL BOTIGA XUSH KELIBSIZ!* 🎰

✨ *Exclusive Signallar - Faqat Bizda!*
• 🎯 Oddiy Signal - 20 ball
• 💎 VIP Signal (100%) - 50 ball
• 📊 Professional tahlillar
• 💰 Yuqori daromad kafolati

🎁 *BONUS: Yangi foydalanuvchilar uchun 40 ball BEPUL!*

🏆 *BALL TIZIMI:*
• 📤 1 do'st taklif = *5 ball*
• 🎁 Har bir yangi do'st = *40 ball* (bepul start)
• 💰 Tez va oson ball to'plash

📊 *SIZNING HOLATINGIZ:*
💰 Balans: *{get_user_points(user_id)} ball*
👥 Referallar: *{get_user_referrals(user_id)} ta*

🚀 *HOZIRROQ BOSHLANG!*
Ball to'plang, signallar oling va yutuqqa erishing!
"""

        keyboard = [
            [
                InlineKeyboardButton("🎯 SIGNAL OLISH", callback_data="get_signals"),
                InlineKeyboardButton("📊 MENING BALLIM", callback_data="my_points")
            ],
            [
                InlineKeyboardButton("📤 REFERAL HAVOLA", callback_data="get_referral_link"),
                InlineKeyboardButton("🎁 BONUSLAR", callback_data="bonuses")
            ],
            [
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
        elif query.data == "get_regular_signal":
            await get_regular_signal(query, user_id)
        elif query.data == "get_vip_signal":
            await get_vip_signal(query, user_id)
        elif query.data == "my_points":
            await show_my_points(query, user_id)
        elif query.data == "get_referral_link":
            await show_referral_link(query, user_id)
        elif query.data == "share_referral":
            await share_referral_link(query, user_id)
        elif query.data == "bonuses":
            await show_bonuses(query)
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
        elif query.data == "admin_broadcast":
            await show_admin_broadcast(query)
        
        else:
            await query.message.reply_text("❌ Noma'lum buyruq!")
            
    except Exception as e:
        logger.error(f"Button handlerda xato: {e}")

# SIGNAL OLISH TIZIMI
async def show_signal_selection(query, user_id):
    """Signal olish sahifasi"""
    try:
        user_points = get_user_points(user_id)
        regular_price = data['settings']['regular_signal_price']
        vip_price = data['settings']['vip_signal_price']
        
        text = f"""
🎰 *APPLE OF FORTUNE SIGNALLARI*

💰 **Sizning balansingiz:** {user_points} ball

💎 *Signallar:*

🎯 **ODDIY SIGNAL** - {regular_price} ball
• Professional tahlillar
• O'rtacha daromad
• Doimiy yangilanadi

💎 **VIP SIGNAL (100%)** - {vip_price} ball  
• Premium tahlillar
• Maximum daromad
• 100% ishonch
• Cheklangan soni

🔗 *Signal olish uchun ball to'lang va havolani oling!*
"""

        keyboard = []
        
        # Oddiy signal tugmasi
        if user_points >= regular_price:
            keyboard.append([InlineKeyboardButton(f"🎯 ODDIY SIGNAL OLISH ({regular_price} ball)", callback_data="get_regular_signal")])
        else:
            keyboard.append([InlineKeyboardButton(f"❌ ODDIY SIGNAL ({regular_price} ball)", callback_data="get_regular_signal")])
        
        # VIP signal tugmasi
        if user_points >= vip_price:
            keyboard.append([InlineKeyboardButton(f"💎 VIP SIGNAL OLISH ({vip_price} ball)", callback_data="get_vip_signal")])
        else:
            keyboard.append([InlineKeyboardButton(f"❌ VIP SIGNAL ({vip_price} ball)", callback_data="get_vip_signal")])
        
        keyboard.extend([
            [InlineKeyboardButton("📤 Ball To'plash", callback_data="get_referral_link")],
            [InlineKeyboardButton("💰 Mening Ballim", callback_data="my_points")],
            [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"show_signal_selection da xato: {e}")

async def get_regular_signal(query, user_id):
    """Oddiy signal olish"""
    try:
        user_points = get_user_points(user_id)
        signal_price = data['settings']['regular_signal_price']
        
        if user_points < signal_price:
            await query.answer(f"❌ Ball yetarli emas! {signal_price - user_points} ball yetishmayapti", show_alert=True)
            return await show_signal_selection(query, user_id)
        
        # Ball olib tashlash
        if not remove_user_points(user_id, signal_price, "Oddiy signal uchun to'lov"):
            await query.answer("❌ Xatolik yuz berdi!", show_alert=True)
            return
        
        data['stats']['total_signals_used'] += 1
        save_data(data)
        
        signal_url = data['settings']['signal_url']
        
        text = f"""
✅ *ODDIY SIGNAL MUVAFFAQIYATLI SOTIB OLINDI!*

💰 **Sarflangan ball:** {signal_price} ball
💰 **Qolgan ball:** {get_user_points(user_id)} ball
🎯 **Signal turi:** Oddiy Signal
⏰ **Amal qilish muddati:** 1 soat

🔗 **Signal havolasi:**
{signal_url}

📝 *Ko'rsatma:*
1. Havolani bosing
2. Signalni oling
3️. O'yinda foydalaning
4️. Daromadingizni oling!

🎉 *Omad tilaymiz!*
"""
        
        keyboard = [
            [InlineKeyboardButton("🔗 SIGNALNI OLISH", url=signal_url)],
            [InlineKeyboardButton("🔄 Yana Signal Olish", callback_data="get_signals")],
            [InlineKeyboardButton("💰 Mening Ballim", callback_data="my_points")],
            [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"get_regular_signal da xato: {e}")

async def get_vip_signal(query, user_id):
    """VIP signal olish"""
    try:
        user_points = get_user_points(user_id)
        signal_price = data['settings']['vip_signal_price']
        
        if user_points < signal_price:
            await query.answer(f"❌ Ball yetarli emas! {signal_price - user_points} ball yetishmayapti", show_alert=True)
            return await show_signal_selection(query, user_id)
        
        # Ball olib tashlash
        if not remove_user_points(user_id, signal_price, "VIP signal uchun to'lov"):
            await query.answer("❌ Xatolik yuz berdi!", show_alert=True)
            return
        
        data['stats']['total_vip_signals_used'] += 1
        save_data(data)
        
        signal_url = data['settings']['signal_url']
        
        text = f"""
💎 *VIP SIGNAL MUVAFFAQIYATLI SOTIB OLINDI!*

💰 **Sarflangan ball:** {signal_price} ball
💰 **Qolgan ball:** {get_user_points(user_id)} ball
🎯 **Signal turi:** VIP Signal (100%)
⏰ **Amal qilish muddati:** 30 daqiqa
⭐ **Ishonch darajasi:** 100%

🔗 **Signal havolasi:**
{signal_url}

📝 *Ko'rsatma:*
1. Havolani bosing
2. VIP signalni oling
3️. Darhol o'yinda foydalaning
4️️. Maximum daromad oling!

⚡ *VIP signal - Maximum yutuq kafolati!*
"""
        
        keyboard = [
            [InlineKeyboardButton("🔗 VIP SIGNALNI OLISH", url=signal_url)],
            [InlineKeyboardButton("🔄 Yana Signal Olish", callback_data="get_signals")],
            [InlineKeyboardButton("💰 Mening Ballim", callback_data="my_points")],
            [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"get_vip_signal da xato: {e}")

# BONUSLAR BO'LIMI
async def show_bonuses(query):
    """Bonuslar sahifasi"""
    try:
        text = f"""
🎁 *BONUS TIZIMI*

✨ *Ball to'plashning tez yo'llari:*

🎁 **Yangi foydalanuvchi bonusi:**
• Ro'yxatdan o'ting = *{data['settings']['new_user_points']} ball* BEPUL!

📤 **Referal tizimi:**
• Har bir do'st taklif = *{data['settings']['referral_points']} ball*
• Do'stingiz = *{data['settings']['new_user_points']} ball* BEPUL!
• Cheksiz do'st taklif qiling!

🎯 **Signallar:**
• Oddiy signal = {data['settings']['regular_signal_price']} ball
• VIP signal = {data['settings']['vip_signal_price']} ball

💡 *Qanday tez ball to'plasaniz:*
1. Do'stlaringizni taklif qiling (har biri 5 ball)
2. Har bir yangi do'st 40 ball bilan boshlaydi
3. Ko'proq do'st = Ko'proq ball
4. Signallar oling va yutuqqa erishing!

🚀 *Jamoangizni yig'ing va birgalikda boyiging!*
"""
        
        keyboard = [
            [InlineKeyboardButton("📤 Referal Havola", callback_data="get_referral_link")],
            [InlineKeyboardButton("🎯 Signal Olish", callback_data="get_signals")],
            [InlineKeyboardButton("💰 Mening Ballim", callback_data="my_points")],
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
        regular_price = data['settings']['regular_signal_price']
        vip_price = data['settings']['vip_signal_price']
        
        text = f"""
🏆 *MENING HISOBIM*

💰 **Balans:** {points} ball
👥 **Referallar:** {referrals} ta
💵 **1 referal:** {data['settings']['referral_points']} ball

🎯 **Signallar xarid qilish:**
• Oddiy signal: {regular_price} ball
• VIP signal: {vip_price} ball

📊 **Xarid qilish imkoniyatlari:**
"""
        
        if points >= regular_price:
            text += f"✅ Oddiy signal: {points // regular_price} ta\n"
        else:
            text += f"❌ Oddiy signal: {regular_price - points} ball yetishmayapti\n"
            
        if points >= vip_price:
            text += f"💎 VIP signal: {points // vip_price} ta\n"
        else:
            text += f"❌ VIP signal: {vip_price - points} ball yetishmayapti\n"
        
        points_history = user_data.get('points_history', [])
        if points_history:
            text += "\n📅 **So'nggi operatsiyalar:**\n"
            for history in points_history[-5:]:
                sign = "+" if history['points'] > 0 else "-"
                text += f"• {sign}{abs(history['points'])} ball - {history['reason']}\n"
        
        keyboard = [
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
• Har bir do'st taklif = *{points_per_ref} ball*
• Yangi foydalanuvchi = *{new_user_points} ball* (bepul)
• Cheksiz taklif qilish mumkin

📊 **Sizning holatingiz:**
• Do'stlar: {referrals_count} ta
• Balans: {user_points} ball
• Jami olingan ball: {referrals_count * points_per_ref} ball

💡 **Qanday tez ball to'plasaniz:**
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
💰 Professional tahlillar va strategiyalar
🎁 Yangi foydalanuvchilar uchun 40 ball BEPUL!

📤 Do'stlaringizni taklif qiling va ball to'plang:
• Har bir do'st = 5 ball
• Do'stingiz = 40 ball bepul

🔗 Signallar olish uchun ball to'plang va yutuqqa erishing!

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
            "Tugmani bosing va do'stlaringizga yuboring!\n\n"
            f"📊 Sizda hozir: {get_user_points(user_id)} ball\n"
            f"👥 Jami referallar: {get_user_referrals(user_id)} ta",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"share_referral_link da xato: {e}")

# YORDAM BO'LIMI
async def show_help(query):
    """Yordam sahifasi"""
    try:
        text = f"""
ℹ️ *BOTDAN FOYDALANISH QO'LLANMASI*

🍎 *Apple of Fortune Signallari:*
• **Oddiy Signal** - {data['settings']['regular_signal_price']} ball
• **VIP Signal (100%)** - {data['settings']['vip_signal_price']} ball
• **Professional tahlillar**
• **Yuqori daromad imkoniyati**

💰 *Ball Tizimi:*
• **Yangi foydalanuvchi** = {data['settings']['new_user_points']} ball (bepul)
• **1 do'st taklif** = {data['settings']['referral_points']} ball
• **Cheksiz taklif** qilish mumkin

🎯 *Qanday boshlash kerak:*
1. 📤 Do'stlaringizni taklif qiling (har biri 5 ball)
2. 💰 Ball to'plang (do'stlar = ball)
3. 🎯 Signallar oling (oddiy 20 ball, VIP 50 ball)
4. 💸 Daromad oling va yana taklif qiling

📞 *Qo'llab-quvvatlash:*
Agar savollaringiz bo'lsa, @baxtga_olga ga murojaat qiling

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
🎯 Oddiy signallar: {data['stats']['total_signals_used']} ta
💎 VIP signallar: {data['stats']['total_vip_signals_used']} ta
📈 Bugungi yangi: {stats['today_users']} ta
📤 Bugungi referallar: {stats['today_referrals']} ta

⚙️ **Sozlamalar:**
• Yangi foydalanuvchi: {data['settings']['new_user_points']} ball
• Referal ball: {data['settings']['referral_points']} ball
• Oddiy signal: {data['settings']['regular_signal_price']} ball  
• VIP signal: {data['settings']['vip_signal_price']} ball
"""

        keyboard = [
            [InlineKeyboardButton("📊 Batafsil Statistika", callback_data="admin_stats")],
            [InlineKeyboardButton("📢 Reklama Yuborish", callback_data="admin_broadcast")],
            [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"show_admin_panel da xato: {e}")

async def show_admin_stats(query):
    """Batafsil statistika"""
    try:
        stats = get_user_statistics()
        total_points = sum(user.get('points', 0) for user in data['users'].values())
        total_referrals = sum(user.get('referrals', 0) for user in data['users'].values())
        
        # Eng ko'p balli foydalanuvchilar
        top_users = sorted(data['users'].items(), key=lambda x: x[1].get('points', 0), reverse=True)[:5]
        
        text = f"""
📊 *BATAFSIL STATISTIKA*

👥 **Foydalanuvchilar:**
• Jami: {stats['total_users']} ta
• Bugungi yangi: {stats['today_users']} ta
• Aktiv (7 kun): {stats['active_users']} ta

💰 **Ball Tizimi:**
• Jami berilgan: {data['stats']['total_points_given']} ball
• Foydalanuvchilarda: {total_points} ball
• Oddiy signallar: {data['stats']['total_signals_used']} ta
• VIP signallar: {data['stats']['total_vip_signals_used']} ta

📈 **Referallar:**
• Jami referallar: {total_referrals} ta
• Bugungi referallar: {stats['today_referrals']} ta

🏆 **TOP 5 Foydalanuvchi:**
"""
        
        for i, (user_id, user_data) in enumerate(top_users, 1):
            name = user_data.get('name', 'Noma\'lum')
            points = user_data.get('points', 0)
            referrals = user_data.get('referrals', 0)
            text += f"{i}. {name} - {points} ball - {referrals} ref\n"
        
        text += f"\n⏰ Yangilangan: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        keyboard = [
            [InlineKeyboardButton("📢 Reklama Yuborish", callback_data="admin_broadcast")],
            [InlineKeyboardButton("🔄 Yangilash", callback_data="admin_stats")],
            [InlineKeyboardButton("👑 Admin Panel", callback_data="admin")],
            [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"show_admin_stats da xato: {e}")

async def show_admin_broadcast(query):
    """Reklama yuborish sahifasi"""
    try:
        text = f"""
📢 *REKLAMA YUBORISH*

Barcha {len(data['users'])} ta foydalanuvchilarga xabar yuborish uchun xabar yuboring.

Xabar barcha foydalanuvchilarga yuboriladi.

💡 *Eslatma:* Xabar yuborish biroz vaqt olishi mumkin.
"""
        
        keyboard = [
            [InlineKeyboardButton("👑 Admin Panel", callback_data="admin")],
            [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"show_admin_broadcast da xato: {e}")

# YORDAMCHI FUNKSIYALAR
async def back_to_main(query):
    """Asosiy menyuga qaytish"""
    try:
        user = query.from_user
        user_id = user.id
        
        keyboard = [
            [
                InlineKeyboardButton("🎯 SIGNAL OLISH", callback_data="get_signals"),
                InlineKeyboardButton("📊 MENING BALLIM", callback_data="my_points")
            ],
            [
                InlineKeyboardButton("📤 REFERAL HAVOLA", callback_data="get_referral_link"),
                InlineKeyboardButton("🎁 BONUSLAR", callback_data="bonuses")
            ],
            [
                InlineKeyboardButton("ℹ️ YORDAM", callback_data="help")
            ]
        ]
        
        if is_admin(user_id):
            keyboard.append([InlineKeyboardButton("👑 ADMIN PANEL", callback_data="admin")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🍎 *Apple of Fortune - Asosiy Menyu*\n\n"
            "Ball to'plang, signallar oling va yutuqlarga erishing! 🚀\n\n"
            f"💰 Sizning balansingiz: {get_user_points(user_id)} ball",
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
        
        # Reklama yuborish
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

# ASOSIY DASTUR
def main():
    """Asosiy dastur"""
    try:
        application = Application.builder().token(TOKEN).build()
        
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CallbackQueryHandler(button_handler))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_message))
        application.add_handler(MessageHandler(filters.PHOTO, handle_admin_message))
        
        logger.info("Apple of Fortune Bot ishga tushmoqda...")
        print("✅ Bot muvaffaqiyatli ishga tushdi!")
        print("🍎 Apple of Fortune Signal Boti")
        print(f"👑 Admin ID: {ADMIN_ID}")
        print("🎯 BARCHA FUNKSIYALAR ISHLAYDI:")
        print("   • 🎯 Oddiy signal (20 ball) -> signal7.digital")
        print("   • 💎 VIP signal (50 ball) -> signal7.digital") 
        print("   • 🎁 Yangi foydalanuvchi: 40 ball")
        print("   • 📤 Referal tizimi: 5 ball har bir taklif")
        print("   • 📊 Chiroyli statistika")
        print("   • 📢 Reklama yuborish")
        print("   • 👑 Soddalashtirilgan admin panel")
        
        application.run_polling()
        
    except Exception as e:
        logger.error(f"Main da xato: {e}")
        print(f"❌ Xato: {e}")

if __name__ == "__main__":
    main()
