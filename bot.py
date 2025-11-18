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
            "text": "",
            "photo": None,
            "button_text": "🎰 1xBet Ro'yxatdan o'tish",
            "url": "https://1xbet.com"
        },
        "melbet": {
            "text": "",
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
                'points': data['settings']['new_user_points'],
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

        welcome_text = f"""
🍎 *APPLE OF FORTUNE SIGNAL BOTIGA XUSH KELIBSIZ!* 🎰

✨ *Exclusive Signallar - Faqat Bizda!*
• 🎯 Oddiy Signal - 20 ball
• 💎 VIP Signal (100%) - 50 ball
• 📊 Professional tahlillar
• 💰 Yuqori daromad kafolati

🎁 *BONUS: Yangi foydalanuvchilar uchun 40 ball BEPUL!*

⚠️ *DIQQAT: Signallarni olish uchun AIFUT promokodi orqali 1xBet yoki MelBet da ro'yxatdan o'ting!*

🏆 *BALL TIZIMI:*
• 📤 1 do'st taklif = *5 ball*
• 🎁 Har bir yangi do'st = *40 ball* (bepul start)

📊 *SIZNING HOLATINGIZ:*
💰 Balans: *{get_user_points(user_id)} ball*
👥 Referallar: *{get_user_referrals(user_id)} ta*
📝 Ro'yxatdan o'tish: {'✅ Bajarildi' if data['users'][str(user_id)].get('has_registered', False) else '❌ Bajarilmadi'}

🚀 *HOZIRROQ BOSHLANG!*
Ro'yxatdan o'ting, ball to'plang va signallar oling!
"""

        keyboard = [
            [
                InlineKeyboardButton("🎯 SIGNAL OLISH", callback_data="get_signals"),
                InlineKeyboardButton("📊 MENING BALLIM", callback_data="my_points")
            ],
            [
                InlineKeyboardButton("📝 RO'YXATDAN O'TISH", callback_data="registration"),
                InlineKeyboardButton("📤 REFERAL HAVOLA", callback_data="get_referral_link")
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

# RO'YXATDAN O'TISH TIZIMI
async def show_registration_options(query, user_id):
    """Ro'yxatdan o'tish variantlarini ko'rsatish"""
    try:
        user_data = data['users'].get(str(user_id), {})
        has_registered = user_data.get('has_registered', False)
        
        text = """
📝 *RO'YXATDAN O'TISH*

🎯 *DIQQAT: Signallarni olish uchun quyidagi bukmeker kontorlaridan birida AIFUT promokodi orqali ro'yxatdan o'ting!*

✨ *AIFUT promokodini kiriting va maxsus bonuslardan bahramand bo'ling!*

🏆 *Ro'yxatdan o'tish afzalliklari:*
• ✅ Signallarni olish imkoniyati
• 🎁 AIFUT promokodi bilan bonus
• 💰 Birinchi depozit uchun 100% bonus
• 📈 Professional signallar

Quyidagi bukmeker kontorlaridan birini tanlang:
"""

        keyboard = [
            [InlineKeyboardButton("🎰 1xBET RO'YXATDAN O'TISH", callback_data="register_1xbet")],
            [InlineKeyboardButton("🎯 MELBET RO'YXATDAN O'TISH", callback_data="register_melbet")]
        ]
        
        if has_registered:
            keyboard.append([InlineKeyboardButton("✅ RO'YXATDAN O'TGANMAN", callback_data="get_signals")])
        else:
            keyboard.append([InlineKeyboardButton("✅ MEN RO'YXATDAN O'TDIM", callback_data="confirm_registration")])
        
        keyboard.append([InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")])
        
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
        
        if reg_data.get('photo'):
            # Rasm bilan xabar
            await query.message.reply_photo(
                photo=reg_data['photo'],
                caption=reg_data['text'] + f"\n\n👆 *Yuqoridagi tugma orqali ro'yxatdan o'ting va AIFUT promokodini kiriting!*",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(reg_data['button_text'], url=reg_data['url'])
                ], [
                    InlineKeyboardButton("🔙 Orqaga", callback_data="back_to_registration")
                ]]),
                parse_mode='Markdown'
            )
        else:
            # Faqat matn bilan xabar
            text = reg_data['text'] if reg_data['text'] else """
🎰 *1xBET RO'YXATDAN O'TISH*

✅ *1xBet afzalliklari:*
• 🎁 AIFUT promokodi - 100% bonus
• 💰 Birinchi depozit uchun 130% gacha bonus
• 📱 Zamonaviy platforma
• 🌍 Butun dunyo bo'ylab xizmat

🔑 *Ro'yxatdan o'tish:*
1. Quyidagi havolani bosing
2. AIFUT promokodini kiriting
3. Hisobingizni tasdiqlang
4. Birinchi depozitingizni qo'ying
5. Bonuslaringizni oling!

🚀 *Hoziroq ro'yxatdan o'ting va signallardan foydalaning!*
"""
            
            await query.edit_message_text(
                text + f"\n\n🔗 *Havolani bosing va ro'yxatdan o'ting:*",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(reg_data['button_text'], url=reg_data['url'])
                ], [
                    InlineKeyboardButton("✅ Men Ro'yxatdan O'tdim", callback_data="confirm_registration"),
                    InlineKeyboardButton("🔙 Orqaga", callback_data="back_to_registration")
                ]]),
                parse_mode='Markdown'
            )
        
    except Exception as e:
        logger.error(f"show_1xbet_registration da xato: {e}")

async def show_melbet_registration(query, user_id):
    """MelBet ro'yxatdan o'tish sahifasi"""
    try:
        data['stats']['registration_clicks'] += 1
        save_data(data)
        
        reg_data = data['registration_messages']['melbet']
        
        if reg_data.get('photo'):
            # Rasm bilan xabar
            await query.message.reply_photo(
                photo=reg_data['photo'],
                caption=reg_data['text'] + f"\n\n👆 *Yuqoridagi tugma orqali ro'yxatdan o'ting va AIFUT promokodini kiriting!*",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(reg_data['button_text'], url=reg_data['url'])
                ], [
                    InlineKeyboardButton("🔙 Orqaga", callback_data="back_to_registration")
                ]]),
                parse_mode='Markdown'
            )
        else:
            # Faqat matn bilan xabar
            text = reg_data['text'] if reg_data['text'] else """
🎯 *MELBET RO'YXATDAN O'TISH*

✅ *MelBet afzalliklari:*
• 🎁 AIFUT promokodi - maxsus taklif
• 💰 Birinchi depozit uchun 100% bonus
• 📊 Yuqori koeffitsientlar
• 🎮 Ko'p turlidagi o'yinlar

🔑 *Ro'yxatdan o'tish:*
1. Quyidagi havolani bosing
2. AIFUT promokodini kiriting
3. Hisobingizni tasdiqlang
4. Birinchi depozitingizni qo'ying
5. Bonuslaringizni oling!

🚀 *Hoziroq ro'yxatdan o'ting va signallardan foydalaning!*
"""
            
            await query.edit_message_text(
                text + f"\n\n🔗 *Havolani bosing va ro'yxatdan o'ting:*",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(reg_data['button_text'], url=reg_data['url'])
                ], [
                    InlineKeyboardButton("✅ Men Ro'yxatdan O'tdim", callback_data="confirm_registration"),
                    InlineKeyboardButton("🔙 Orqaga", callback_data="back_to_registration")
                ]]),
                parse_mode='Markdown'
            )
        
    except Exception as e:
        logger.error(f"show_melbet_registration da xato: {e}")

async def confirm_registration(query, user_id):
    """Ro'yxatdan o'tishni tasdiqlash"""
    try:
        user_data = data['users'].get(str(user_id), {})
        
        if not user_data.get('has_registered', False):
            user_data['has_registered'] = True
            user_data['registration_date'] = datetime.now().strftime("%Y-%m-%d %H:%M")
            save_data(data)
            
            text = f"""
🎉 *TABRIKLAYMIZ! RO'YXATDAN O'TDINGIZ!*

✅ Siz muvaffaqiyatli ro'yxatdan o'tdingiz!
📅 Ro'yxatdan o'tish sanasi: {datetime.now().strftime("%Y-%m-%d %H:%M")}

🎯 Endi siz:
• Signallarni olishingiz mumkin
• Ball to'plashingiz mumkin
• Do'stlaringizni taklif qilishingiz mumkin

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
            [InlineKeyboardButton("🎯 SIGNAL OLISH", callback_data="get_signals")],
            [InlineKeyboardButton("📤 REFERAL HAVOLA", callback_data="get_referral_link")],
            [InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"confirm_registration da xato: {e}")

# SIGNAL OLISH TIZIMI (oldingi kod bilan bir xil, lekin ro'yxatdan o'tganligini tekshiramiz)
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

# ADMIN RO'YXATDAN O'TISH BOSHQARISH
async def show_admin_manage_registration(query):
    """Ro'yxatdan o'tish xabarlarini boshqarish"""
    try:
        text = """
👑 *RO'YXATDAN O'TISH XABARLARINI BOSHQARISH*

Bu yerda siz foydalanuvchilar ko'radigan ro'yxatdan o'tish xabarlarini sozlashingiz mumkin.

📊 *Statistika:*
• Ro'yxatdan o'tish bosishlar: {data['stats']['registration_clicks']} ta
• Ro'yxatdan o'tganlar: {sum(1 for user in data['users'].values() if user.get('has_registered', False))} ta

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

1xBet ro'yxatdan o'tish sahifasi uchun xabar yuboring:

🖼️ *Rasm + matn:* Rasm va taglavha yuboring
📄 *Faqat matn:* Oddiy matn xabar yuboring

Xabar quyidagilarni o'z ichiga olishi tavsiya etiladi:
• AIFUT promokodi haqida ma'lumot
• Ro'yxatdan o'tish bosqichlari
• Bonuslar va afzalliklar
• Havola va tugma matni

⚠️ *Eslatma:* Rasm yuborsangiz, taglavha xabar matni bo'ladi.
"""

        keyboard = [
            [InlineKeyboardButton("🔙 Ro'yxatdan O'tish Boshqarish", callback_data="admin_manage_registration")],
            [InlineKeyboardButton("👑 Admin Panel", callback_data="admin")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"admin_edit_1xbet_message da xato: {e}")

async def admin_edit_melbet_message(query):
    """MelBet xabarini sozlash"""
    try:
        context = query.message._bot
        context.user_data['admin_action'] = 'edit_melbet'
        
        text = """
📝 *MELBET XABARINI SOZLASH*

MelBet ro'yxatdan o'tish sahifasi uchun xabar yuboring:

🖼️ *Rasm + matn:* Rasm va taglavha yuboring
📄 *Faqat matn:* Oddiy matn xabar yuboring

Xabar quyidagilarni o'z ichiga olishi tavsiya etiladi:
• AIFUT promokodi haqida ma'lumot
• Ro'yxatdan o'tish bosqichlari
• Bonuslar va afzalliklar
• Havola va tugma matni

⚠️ *Eslatma:* Rasm yuborsangiz, taglavha xabar matni bo'ladi.
"""

        keyboard = [
            [InlineKeyboardButton("🔙 Ro'yxatdan O'tish Boshqarish", callback_data="admin_manage_registration")],
            [InlineKeyboardButton("👑 Admin Panel", callback_data="admin")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"admin_edit_melbet_message da xato: {e}")

# QOLGAN FUNKSIYALAR (oldingi kod bilan bir xil)
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

# ADMIN XABARLARINI QAYTA ISHLASH (YANGILANGAN)
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
            
            if message.photo:
                # Rasm bilan xabar
                reg_data['photo'] = message.photo[-1].file_id
                reg_data['text'] = message.caption if message.caption else ""
            else:
                # Faqat matn bilan xabar
                reg_data['text'] = message.text
                reg_data['photo'] = None
            
            save_data(data)
            await message.reply_text("✅ 1xBet ro'yxatdan o'tish xabari yangilandi!")
            context.user_data.pop('admin_action', None)
            return
            
        elif admin_action == 'edit_melbet':
            reg_data = data['registration_messages']['melbet']
            
            if message.photo:
                # Rasm bilan xabar
                reg_data['photo'] = message.photo[-1].file_id
                reg_data['text'] = message.caption if message.caption else ""
            else:
                # Faqat matn bilan xabar
                reg_data['text'] = message.text
                reg_data['photo'] = None
            
            save_data(data)
            await message.reply_text("✅ MelBet ro'yxatdan o'tish xabari yangilandi!")
            context.user_data.pop('admin_action', None)
            return
        
        # Reklama yuborish (oldingi kod bilan bir xil)
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

# ADMIN PANELINI YANGILASH
async def show_admin_panel(query):
    """Admin panelini ko'rsatish"""
    try:
        stats = get_user_statistics()
        total_points = sum(user.get('points', 0) for user in data['users'].values())
        registered_users = sum(1 for user in data['users'].values() if user.get('has_registered', False))
        
        text = f"""
👑 *ADMIN PANELI*

📊 **Bot Statistikasi:**
👥 Jami foydalanuvchilar: {stats['total_users']} ta
✅ Ro'yxatdan o'tganlar: {registered_users} ta
💰 Jami ballar: {total_points} ball
🎯 Oddiy signallar: {data['stats']['total_signals_used']} ta
💎 VIP signallar: {data['stats']['total_vip_signals_used']} ta
📈 Bugungi yangi: {stats['today_users']} ta
📤 Bugungi referallar: {stats['today_referrals']} ta
🔗 Ro'yxatdan o'tish bosish: {data['stats']['registration_clicks']} ta

⚙️ **Sozlamalar:**
• Yangi foydalanuvchi: {data['settings']['new_user_points']} ball
• Referal ball: {data['settings']['referral_points']} ball
• Oddiy signal: {data['settings']['regular_signal_price']} ball  
• VIP signal: {data['settings']['vip_signal_price']} ball
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

# YANGI START XABARINI YANGILASH
async def back_to_main(query):
    """Asosiy menyuga qaytish"""
    try:
        user = query.from_user
        user_id = user.id
        
        user_data = data['users'].get(str(user_id), {})
        
        keyboard = [
            [
                InlineKeyboardButton("🎯 SIGNAL OLISH", callback_data="get_signals"),
                InlineKeyboardButton("📊 MENING BALLIM", callback_data="my_points")
            ],
            [
                InlineKeyboardButton("📝 RO'YXATDAN O'TISH", callback_data="registration"),
                InlineKeyboardButton("📤 REFERAL HAVOLA", callback_data="get_referral_link")
            ],
            [
                InlineKeyboardButton("🎁 BONUSLAR", callback_data="bonuses"),
                InlineKeyboardButton("ℹ️ YORDAM", callback_data="help")
            ]
        ]
        
        if is_admin(user_id):
            keyboard.append([InlineKeyboardButton("👑 ADMIN PANEL", callback_data="admin")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        status_text = "✅ Ro'yxatdan o'tgan" if user_data.get('has_registered', False) else "❌ Ro'yxatdan o'tmagan"
        
        await query.edit_message_text(
            f"🍎 *Apple of Fortune - Asosiy Menyu*\n\n"
            f"Ball to'plang, signallar oling va yutuqlarga erishing! 🚀\n\n"
            f"💰 Sizning balansingiz: {get_user_points(user_id)} ball\n"
            f"📝 Holat: {status_text}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"back_to_main da xato: {e}")

# QOLGAN FUNKSIYALAR (oldingi kod bilan bir xil)
# show_admin_stats, show_admin_broadcast, show_my_points, show_bonuses, show_help, 
# show_referral_link, share_referral_link, get_user_statistics funksiyalari 
# oldingi kod bilan bir xil saqlansin

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
        print("   • 📝 Ro'yxatdan o'tish tizimi (AIFUT promokodi)")
        print("   • 🎰 1xBet ro'yxatdan o'tish (admin sozlashi mumkin)")
        print("   • 🎯 MelBet ro'yxatdan o'tish (admin sozlashi mumkin)") 
        print("   • 🎯 Oddiy signal (20 ball) -> signal7.digital")
        print("   • 💎 VIP signal (50 ball) -> signal7.digital")
        print("   • 🎁 Yangi foydalanuvchi: 40 ball")
        print("   • 📤 Referal tizimi: 5 ball har bir taklif")
        print("   • 📊 Chiroyli statistika")
        print("   • 📢 Reklama yuborish")
        
        application.run_polling()
        
    except Exception as e:
        logger.error(f"Main da xato: {e}")
        print(f"❌ Xato: {e}")

if __name__ == "__main__":
    main()
