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
    "registration_messages": {
        "1xbet": {
            "text": "🎰 *1xBET RO'YXATDAN O'TISH*\n\nAIFUT promokodini kiriting va 100% bonus oling!",
            "photo": None,
            "button_text": "🎰 1xBet Ro'yxatdan o'tish",
            "url": "https://1xbet.com"
        },
        "melbet": {
            "text": "🎯 *MELBET RO'YXATDAN O'TISH*\n\nAIFUT promokodini kiriting va maxsus bonus oling!",
            "photo": None,
            "button_text": "🎯 MelBet Ro'yxatdan o'tish", 
            "url": "https://melbet.com"
        }
    },
    "stats": {
        "total_users": 0,
        "today_users": 0,
        "today_referrals": 0,
        "total_points_given": 0,
        "total_signals_used": 0,
        "total_vip_signals_used": 0,
        "registration_clicks": 0
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
                'points_history': [],
                'has_registered': False
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

        user_data = data['users'].get(str(user_id), {})
        has_registered = user_data.get('has_registered', False)
        
        welcome_text = f"""
🍎 *APPLE OF FORTUNE SIGNAL BOTIGA XUSH KELIBSIZ!* 🎰

💰 *Sizning balansingiz:* {get_user_points(user_id)} ball
👥 *Referallaringiz:* {get_user_referrals(user_id)} ta
📝 *Ro'yxatdan o'tish:* {'✅ Bajarildi' if has_registered else '❌ Bajarilmadi'}

"""

        if not has_registered:
            welcome_text += """
⚠️ *DIQQAT: Signallarni olish uchun avval ro'yxatdan o'ting!*

🎯 *Qanday boshlash kerak:*
1. 📝 Ro'yxatdan o'ting (AIFUT promokodi bilan)
2. 🎯 Signallar olishni boshlang
3. 📤 Do'stlaringizni taklif qiling
4. 💰 Ball to'plang va yutuqqa erishing!

🚀 *HOZIR RO'YXATDAN O'TING!*
"""
        else:
            welcome_text += """
✅ *Siz ro'yxatdan o'tgansiz! Endi signallar olishingiz mumkin.*

🎯 *Nimalar qilishingiz mumkin:*
• 🎯 Signallar olish
• 📤 Do'stlaringizni taklif qilish
• 💰 Ball to'plash
• 🚀 Yutuqqa erishish

🔥 *SIGNALLAR OLISHNI BOSHLANG!*
"""

        # HAR DOIM SHAXSIY TUGMALAR
        keyboard = [
            [
                InlineKeyboardButton("🎯 SIGNAL OLISH", callback_data="get_signals"),
                InlineKeyboardButton("💰 BALLIM", callback_data="my_points")
            ],
            [
                InlineKeyboardButton("📝 RO'YXATDAN O'TISH", callback_data="registration"),
                InlineKeyboardButton("📤 REFERAL", callback_data="get_referral_link")
            ],
            [
                InlineKeyboardButton("🎁 BONUSLAR", callback_data="bonuses"),
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
        elif query.data == "registration":
            await show_registration_options(query, user_id)
        elif query.data == "register_1xbet":
            await show_1xbet_registration(query, user_id)
        elif query.data == "register_melbet":
            await show_melbet_registration(query, user_id)
        elif query.data == "confirm_registration":
            await confirm_registration(query, user_id)
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
        elif query.data == "back_to_registration":
            await show_registration_options(query, user_id)
        
        # ADMIN HANDLERLARI
        elif query.data == "admin":
            if is_admin(user_id):
                await show_admin_panel(query)
        
        elif query.data == "admin_stats":
            await show_admin_stats(query)
        elif query.data == "admin_broadcast":
            await show_admin_broadcast(query)
        elif query.data == "admin_manage_registration":
            await show_admin_manage_registration(query)
        elif query.data == "admin_edit_1xbet":
            await admin_edit_1xbet_message(query)
        elif query.data == "admin_edit_melbet":
            await admin_edit_melbet_message(query)
        
        else:
            await query.message.reply_text("❌ Noma'lum buyruq!")
            
    except Exception as e:
        logger.error(f"Button handlerda xato: {e}")
        await query.message.reply_text("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

# RO'YXATDAN O'TISH TIZIMI
async def show_registration_options(query, user_id):
    """Ro'yxatdan o'tish variantlarini ko'rsatish"""
    try:
        user_data = data['users'].get(str(user_id), {})
        has_registered = user_data.get('has_registered', False)
        
        status_icon = "✅" if has_registered else "❌"
        
        text = f"""
📝 *RO'YXATDAN O'TISH* {status_icon}

🎯 *DIQQAT: Signallarni olish uchun quyidagi bukmeker kontorlaridan birida AIFUT promokodi orqali ro'yxatdan o'ting!*

✨ *AIFUT promokodini kiriting va maxsus bonuslardan bahramand bo'ling!*

Quyidagi bukmeker kontorlaridan birini tanlang:
"""

        keyboard = [
            [
                InlineKeyboardButton("🎰 1xBET", callback_data="register_1xbet"),
                InlineKeyboardButton("🎯 MELBET", callback_data="register_melbet")
            ],
            [InlineKeyboardButton("✅ MEN RO'YXATDAN O'TDIM", callback_data="confirm_registration")],
            [
                InlineKeyboardButton("🎯 SIGNALLAR", callback_data="get_signals"),
                InlineKeyboardButton("🔙 ORQAGA", callback_data="back")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"show_registration_options da xato: {e}")

async def show_1xbet_registration(query, user_id):
    """1xBet ro'yxatdan o'tish sahifasi"""
    try:
        data['stats']['registration_clicks'] += 1
        save_data(data)
        
        reg_data = data['registration_messages']['1xbet']
        
        text = reg_data['text'] + "\n\n🔗 *Havolani bosing va ro'yxatdan o'ting:*"
        
        keyboard = [
            [InlineKeyboardButton(reg_data['button_text'], url=reg_data['url'])],
            [
                InlineKeyboardButton("✅ MEN RO'YXATDAN O'TDIM", callback_data="confirm_registration"),
                InlineKeyboardButton("🔙 ORQAGA", callback_data="back_to_registration")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"show_1xbet_registration da xato: {e}")

async def show_melbet_registration(query, user_id):
    """MelBet ro'yxatdan o'tish sahifasi"""
    try:
        data['stats']['registration_clicks'] += 1
        save_data(data)
        
        reg_data = data['registration_messages']['melbet']
        
        text = reg_data['text'] + "\n\n🔗 *Havolani bosing va ro'yxatdan o'ting:*"
        
        keyboard = [
            [InlineKeyboardButton(reg_data['button_text'], url=reg_data['url'])],
            [
                InlineKeyboardButton("✅ MEN RO'YXATDAN O'TDIM", callback_data="confirm_registration"),
                InlineKeyboardButton("🔙 ORQAGA", callback_data="back_to_registration")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"show_melbet_registration da xato: {e}")

async def confirm_registration(query, user_id):
    """Ro'yxatdan o'tishni tasdiqlash"""
    try:
        user_data = data['users'].get(str(user_id), {})
        
        if not user_data.get('has_registered', False):
            user_data['has_registered'] = True
            user_data['registration_date'] = datetime.now().strftime("%Y-%m-%d %H:%M")
            
            # Ro'yxatdan o'tish bonusini qo'shamiz
            registration_bonus = 10
            add_user_points(user_id, registration_bonus, "Ro'yxatdan o'tish bonusi")
            
            save_data(data)
            
            text = f"""
🎉 *TABRIKLAYMIZ! RO'YXATDAN O'TDINGIZ!*

✅ Siz muvaffaqiyatli ro'yxatdan o'tdingiz!
📅 Ro'yxatdan o'tish sanasi: {datetime.now().strftime("%Y-%m-%d %H:%M")}
🎁 Ro'yxatdan o'tish bonusi: +{registration_bonus} ball

💰 *Sizning balansingiz: {get_user_points(user_id)} ball*

🚀 *Endi signallar olishni boshlang!*
"""
        else:
            text = f"""
✅ *Siz allaqachon ro'yxatdan o'tgansiz!*

📅 Ro'yxatdan o'tgan sana: {user_data.get('registration_date', 'Noma\'lum')}

💰 *Sizning balansingiz: {get_user_points(user_id)} ball*

🎯 Signallar olishda davom eting!
"""
        
        keyboard = [
            [
                InlineKeyboardButton("🎯 SIGNAL OLISH", callback_data="get_signals"),
                InlineKeyboardButton("💰 BALLIM", callback_data="my_points")
            ],
            [
                InlineKeyboardButton("📝 RO'YXATDAN O'TISH", callback_data="registration"),
                InlineKeyboardButton("📤 REFERAL", callback_data="get_referral_link")
            ],
            [InlineKeyboardButton("🔙 BOSH MENYU", callback_data="back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"confirm_registration da xato: {e}")

# SIGNAL OLISH TIZIMI
async def show_signal_selection(query, user_id):
    """Signal olish sahifasi"""
    try:
        user_data = data['users'].get(str(user_id), {})
        
        # Ro'yxatdan o'tganligini tekshirish
        if not user_data.get('has_registered', False):
            await query.answer("❌ Signallarni olish uchun avval ro'yxatdan o'ting!", show_alert=True)
            return await show_registration_options(query, user_id)
        
        user_points = get_user_points(user_id)
        regular_price = data['settings']['regular_signal_price']
        vip_price = data['settings']['vip_signal_price']
        
        text = f"""
🎰 *APPLE OF FORTUNE SIGNALLARI*

💰 **Sizning balansingiz:** {user_points} ball
✅ **Ro'yxatdan o'tish:** Tasdiqlangan

💎 *Signallar:*

🎯 **ODDIY SIGNAL** - {regular_price} ball
• Professional tahlillar
• O'rtacha daromad

💎 **VIP SIGNAL (100%)** - {vip_price} ball  
• Premium tahlillar
• Maximum daromad
• 100% ishonch

🔗 *Signal olish uchun ball to'lang va havolani oling!*
"""

        keyboard = []
        
        # Oddiy signal tugmasi
        if user_points >= regular_price:
            keyboard.append([InlineKeyboardButton(f"🎯 ODDIY SIGNAL ({regular_price} ball)", callback_data="get_regular_signal")])
        else:
            keyboard.append([InlineKeyboardButton(f"❌ ODDIY SIGNAL ({regular_price} ball)", callback_data="get_regular_signal")])
        
        # VIP signal tugmasi
        if user_points >= vip_price:
            keyboard.append([InlineKeyboardButton(f"💎 VIP SIGNAL ({vip_price} ball)", callback_data="get_vip_signal")])
        else:
            keyboard.append([InlineKeyboardButton(f"❌ VIP SIGNAL ({vip_price} ball)", callback_data="get_vip_signal")])
        
        keyboard.extend([
            [
                InlineKeyboardButton("📤 BALL TO'PLASH", callback_data="get_referral_link"),
                InlineKeyboardButton("💰 BALLIM", callback_data="my_points")
            ],
            [
                InlineKeyboardButton("📝 RO'YXATDAN O'TISH", callback_data="registration"),
                InlineKeyboardButton("🔙 ORQAGA", callback_data="back")
            ]
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"show_signal_selection da xato: {e}")

async def get_regular_signal(query, user_id):
    """Oddiy signal olish"""
    try:
        user_data = data['users'].get(str(user_id), {})
        if not user_data.get('has_registered', False):
            await query.answer("❌ Signallarni olish uchun avval ro'yxatdan o'ting!", show_alert=True)
            return await show_registration_options(query, user_id)
            
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

🔗 **Signal havolasi:**
{signal_url}

📝 *Ko'rsatma:*
1. Havolani bosing
2. Signalni oling
3. O'yinda foydalaning

🎉 *Omad tilaymiz!*
"""
        
        keyboard = [
            [InlineKeyboardButton("🔗 SIGNALNI OLISH", url=signal_url)],
            [
                InlineKeyboardButton("🔄 YANA SIGNAL", callback_data="get_signals"),
                InlineKeyboardButton("💰 BALLIM", callback_data="my_points")
            ],
            [
                InlineKeyboardButton("📝 RO'YXATDAN O'TISH", callback_data="registration"),
                InlineKeyboardButton("🔙 MENYU", callback_data="back")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"get_regular_signal da xato: {e}")

async def get_vip_signal(query, user_id):
    """VIP signal olish"""
    try:
        user_data = data['users'].get(str(user_id), {})
        if not user_data.get('has_registered', False):
            await query.answer("❌ Signallarni olish uchun avval ro'yxatdan o'ting!", show_alert=True)
            return await show_registration_options(query, user_id)
            
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

🔗 **Signal havolasi:**
{signal_url}

📝 *Ko'rsatma:*
1. Havolani bosing
2. VIP signalni oling
3. Darhol o'yinda foydalaning

⚡ *VIP signal - Maximum yutuq kafolati!*
"""
        
        keyboard = [
            [InlineKeyboardButton("🔗 VIP SIGNALNI OLISH", url=signal_url)],
            [
                InlineKeyboardButton("🔄 YANA SIGNAL", callback_data="get_signals"),
                InlineKeyboardButton("💰 BALLIM", callback_data="my_points")
            ],
            [
                InlineKeyboardButton("📝 RO'YXATDAN O'TISH", callback_data="registration"),
                InlineKeyboardButton("🔙 MENYU", callback_data="back")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"get_vip_signal da xato: {e}")

# ASOSIY MENYUGA QAYTISH
async def back_to_main(query):
    """Asosiy menyuga qaytish"""
    try:
        user = query.from_user
        user_id = user.id
        
        user_data = data['users'].get(str(user_id), {})
        has_registered = user_data.get('has_registered', False)
        
        welcome_text = f"""
🍎 *Apple of Fortune - Asosiy Menyu*

💰 *Sizning balansingiz:* {get_user_points(user_id)} ball
👥 *Referallaringiz:* {get_user_referrals(user_id)} ta
📝 *Ro'yxatdan o'tish:* {'✅ Bajarildi' if has_registered else '❌ Bajarilmadi'}

"""

        if not has_registered:
            welcome_text += "⚠️ *Signallarni olish uchun ro'yxatdan o'ting!*"
        else:
            welcome_text += "✅ *Siz ro'yxatdan o'tgansiz! Signallar olishingiz mumkin.*"

        # HAR DOIM SHAXSIY TUGMALAR
        keyboard = [
            [
                InlineKeyboardButton("🎯 SIGNAL OLISH", callback_data="get_signals"),
                InlineKeyboardButton("💰 BALLIM", callback_data="my_points")
            ],
            [
                InlineKeyboardButton("📝 RO'YXATDAN O'TISH", callback_data="registration"),
                InlineKeyboardButton("📤 REFERAL", callback_data="get_referral_link")
            ],
            [
                InlineKeyboardButton("🎁 BONUSLAR", callback_data="bonuses"),
                InlineKeyboardButton("ℹ️ YORDAM", callback_data="help")
            ]
        ]
        
        if is_admin(user_id):
            keyboard.append([InlineKeyboardButton("👑 ADMIN PANEL", callback_data="admin")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            welcome_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"back_to_main da xato: {e}")

# QOLGAN FUNKSIYALAR (oldingi kod bilan bir xil)
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
"""

        keyboard = [
            [
                InlineKeyboardButton("🎯 SIGNAL OLISH", callback_data="get_signals"),
                InlineKeyboardButton("📤 REFERAL", callback_data="get_referral_link")
            ],
            [
                InlineKeyboardButton("📝 RO'YXATDAN O'TISH", callback_data="registration"),
                InlineKeyboardButton("🔙 ORQAGA", callback_data="back")
            ]
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
📤 *BALL TO'PLASH USULI*

🔗 **Sizning referal havolangiz:**
`{ref_link}`

💰 **Ball to'plash formulasi:**
• Har bir do'st taklif = *{points_per_ref} ball*
• Yangi foydalanuvchi = *{data['settings']['new_user_points']} ball* (bepul)

📊 **Sizning holatingiz:**
• Do'stlar: {referrals_count} ta
• Balans: {user_points} ball
"""

        keyboard = [
            [InlineKeyboardButton("🔗 TELEGRAMDA ULASHISH", callback_data="share_referral")],
            [
                InlineKeyboardButton("🎯 SIGNALLAR", callback_data="get_signals"),
                InlineKeyboardButton("💰 BALLIM", callback_data="my_points")
            ],
            [
                InlineKeyboardButton("📝 RO'YXATDAN O'TISH", callback_data="registration"),
                InlineKeyboardButton("🔙 ORQAGA", callback_data="back")
            ]
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
💰 Professional tahlillar
🎁 Yangi foydalanuvchilar uchun {data['settings']['new_user_points']} ball BEPUL!

📤 Do'stlaringizni taklif qiling va ball to'plang!

Botga kirib, daromad olishni boshlang:
{ref_link}"""

        keyboard = [
            [InlineKeyboardButton("📤 TELEGRAMDA ULASHISH", url=f"https://t.me/share/url?url={ref_link}&text={share_text}")],
            [
                InlineKeyboardButton("💰 BALLIM", callback_data="my_points"),
                InlineKeyboardButton("🎯 SIGNALLAR", callback_data="get_signals")
            ],
            [
                InlineKeyboardButton("📝 RO'YXATDAN O'TISH", callback_data="registration"),
                InlineKeyboardButton("🔙 ORQAGA", callback_data="back")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🔗 *Havolani quyidagi tugma orqali osongina ulashing:*",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"share_referral_link da xato: {e}")

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

🎯 **Signallar:**
• Oddiy signal = {data['settings']['regular_signal_price']} ball
• VIP signal = {data['settings']['vip_signal_price']} ball
"""

        keyboard = [
            [
                InlineKeyboardButton("📤 REFERAL", callback_data="get_referral_link"),
                InlineKeyboardButton("🎯 SIGNALLAR", callback_data="get_signals")
            ],
            [
                InlineKeyboardButton("📝 RO'YXATDAN O'TISH", callback_data="registration"),
                InlineKeyboardButton("💰 BALLIM", callback_data="my_points")
            ],
            [InlineKeyboardButton("🔙 ORQAGA", callback_data="back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"show_bonuses da xato: {e}")

async def show_help(query):
    """Yordam sahifasi"""
    try:
        text = f"""
ℹ️ *BOTDAN FOYDALANISH QO'LLANMASI*

🍎 *Apple of Fortune Signallari:*
• **Oddiy Signal** - {data['settings']['regular_signal_price']} ball
• **VIP Signal (100%)** - {data['settings']['vip_signal_price']} ball

💰 *Ball Tizimi:*
• **Yangi foydalanuvchi** = {data['settings']['new_user_points']} ball (bepul)
• **1 do'st taklif** = {data['settings']['referral_points']} ball

🎯 *Qanday boshlash kerak:*
1. 📝 Ro'yxatdan o'ting (AIFUT promokodi bilan)
2. 📤 Do'stlaringizni taklif qiling
3. 💰 Ball to'plang
4. 🎯 Signallar oling
"""

        keyboard = [
            [
                InlineKeyboardButton("🎯 SIGNALLAR", callback_data="get_signals"),
                InlineKeyboardButton("📤 REFERAL", callback_data="get_referral_link")
            ],
            [
                InlineKeyboardButton("📝 RO'YXATDAN O'TISH", callback_data="registration"),
                InlineKeyboardButton("💰 BALLIM", callback_data="my_points")
            ],
            [InlineKeyboardButton("🔙 ORQAGA", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"show_help da xato: {e}")

# ADMIN FUNKSIYALARI (qisqartirilgan)
async def show_admin_panel(query):
    """Admin panelini ko'rsatish"""
    try:
        total_users = len(data['users'])
        registered_users = sum(1 for user in data['users'].values() if user.get('has_registered', False))
        total_points = sum(user.get('points', 0) for user in data['users'].values())
        
        text = f"""
👑 *ADMIN PANELI*

📊 **Bot Statistikasi:**
👥 Jami foydalanuvchilar: {total_users} ta
✅ Ro'yxatdan o'tganlar: {registered_users} ta
💰 Jami ballar: {total_points} ball
🎯 Oddiy signallar: {data['stats']['total_signals_used']} ta
💎 VIP signallar: {data['stats']['total_vip_signals_used']} ta
"""

        keyboard = [
            [InlineKeyboardButton("📊 Batafsil Statistika", callback_data="admin_stats")],
            [InlineKeyboardButton("📝 Ro'yxatdan O'tish Xabarlari", callback_data="admin_manage_registration")],
            [InlineKeyboardButton("📢 Reklama Yuborish", callback_data="admin_broadcast")],
            [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"show_admin_panel da xato: {e}")

# QOLGAN ADMIN FUNKSIYALARI (oldingi kod bilan bir xil)
async def show_admin_stats(query):
    """Batafsil statistika"""
    try:
        total_users = len(data['users'])
        registered_users = sum(1 for user in data['users'].values() if user.get('has_registered', False))
        total_points = sum(user.get('points', 0) for user in data['users'].values())
        total_referrals = sum(user.get('referrals', 0) for user in data['users'].values())
        
        text = f"""
📊 *BATAFSIL STATISTIKA*

👥 **Foydalanuvchilar:**
• Jami: {total_users} ta
• Ro'yxatdan o'tgan: {registered_users} ta
• Ro'yxatdan o'tmagan: {total_users - registered_users} ta

💰 **Ball Tizimi:**
• Jami berilgan: {data['stats']['total_points_given']} ball
• Foydalanuvchilarda: {total_points} ball
• Oddiy signallar: {data['stats']['total_signals_used']} ta
• VIP signallar: {data['stats']['total_vip_signals_used']} ta

📈 **Referallar:**
• Jami referallar: {total_referrals} ta
• Ro'yxatdan o'tish bosish: {data['stats']['registration_clicks']} ta
"""

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
"""

        keyboard = [
            [InlineKeyboardButton("👑 Admin Panel", callback_data="admin")],
            [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"show_admin_broadcast da xato: {e}")

async def show_admin_manage_registration(query):
    """Ro'yxatdan o'tish xabarlarini boshqarish"""
    try:
        text = """
👑 *RO'YXATDAN O'TISH XABARLARINI BOSHQARISH*

Bu yerda siz foydalanuvchilar ko'radigan ro'yxatdan o'tish xabarlarini sozlashingiz mumkin.

Quyidagi bukmeker kontorlari uchun xabarlarni sozlang:
"""

        keyboard = [
            [InlineKeyboardButton("🎰 1xBet Xabarini Sozlash", callback_data="admin_edit_1xbet")],
            [InlineKeyboardButton("🎯 MelBet Xabarini Sozlash", callback_data="admin_edit_melbet")],
            [InlineKeyboardButton("👑 Admin Panel", callback_data="admin")],
            [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"show_admin_manage_registration da xato: {e}")

async def admin_edit_1xbet_message(query):
    """1xBet xabarini sozlash"""
    try:
        context = query.message._bot
        context.user_data['admin_action'] = 'edit_1xbet'
        
        text = """
📝 *1xBET XABARINI SOZLASH*

1xBet ro'yxatdan o'tish sahifasi uchun yangi matn yuboring:

Xabar quyidagilarni o'z ichiga olishi tavsiya etiladi:
• AIFUT promokodi haqida ma'lumot
• Ro'yxatdan o'tish bosqichlari
• Bonuslar va afzalliklar
"""

        await query.edit_message_text(text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"admin_edit_1xbet_message da xato: {e}")

async def admin_edit_melbet_message(query):
    """MelBet xabarini sozlash"""
    try:
        context = query.message._bot
        context.user_data['admin_action'] = 'edit_melbet'
        
        text = """
📝 *MELBET XABARINI SOZLASH*

MelBet ro'yxatdan o'tish sahifasi uchun yangi matn yuboring:

Xabar quyidagilarni o'z ichiga olishi tavsiya etiladi:
• AIFUT promokodi haqida ma'lumot
• Ro'yxatdan o'tish bosqichlari
• Bonuslar va afzalliklar
"""

        await query.edit_message_text(text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"admin_edit_melbet_message da xato: {e}")

# ADMIN XABARLARINI QAYTA ISHLASH
async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin xabarlarini qayta ishlash"""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return
    
    try:
        message = update.message
        
        # Ro'yxatdan o'tish xabarlarini sozlash
        admin_action = context.user_data.get('admin_action')
        
        if admin_action == 'edit_1xbet':
            reg_data = data['registration_messages']['1xbet']
            reg_data['text'] = message.text
            save_data(data)
            await message.reply_text("✅ 1xBet ro'yxatdan o'tish xabari yangilandi!")
            context.user_data.pop('admin_action', None)
            return
            
        elif admin_action == 'edit_melbet':
            reg_data = data['registration_messages']['melbet']
            reg_data['text'] = message.text
            save_data(data)
            await message.reply_text("✅ MelBet ro'yxatdan o'tish xabari yangilandi!")
            context.user_data.pop('admin_action', None)
            return
        
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
            f"❌ Xatolik: {total_users - successful} ta",
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
        
        logger.info("Apple of Fortune Bot ishga tushmoqda...")
        print("✅ Bot muvaffaqiyatli ishga tushdi!")
        print("🍎 Apple of Fortune Signal Boti")
        print(f"👑 Admin ID: {ADMIN_ID}")
        print("🎯 BARCHA FUNKSIYALAR ISHLAYDI:")
        print("   • 📝 Ro'yxatdan o'tish tizimi (doimiy ko'rinadi)")
        print("   • 🎯 Signal olish (20 va 50 ball)")
        print("   • 📤 Referal tizimi")
        print("   • 👑 Admin paneli")
        print("   • 🔥 Chiroyli tugma joylashuvi")
        
        application.run_polling()
        
    except Exception as e:
        logger.error(f"Main da xato: {e}")
        print(f"❌ Xato: {e}")

if __name__ == "__main__":
    main()
