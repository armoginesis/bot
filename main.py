from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler
import logging
import re
from telegram import BotCommand

# Включение логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Состояния
WAITING_FOR_NORM = 1
WAITING_FOR_DISTANCE_AND_VOZ = 2

# Зависимость расстояний от коэффициента (норма воза)
distance_coeffs = [
    (0.1, 0.2, 68),
    (0.21, 0.3, 61),
    (0.31, 0.4, 56),
    (0.41, 0.5, 53),
    (0.51, 0.6, 50),
    (0.61, 0.7, 47),
    (0.71, 0.8, 45),
    (0.81, 0.9, 43),
    (0.91, 1.0, 42),
    (1.1, 1.2, 40),
    (1.3, 1.4, 37),
    (1.5, 1.6, 35),
    (1.7, 1.8, 33),
    (1.9, 2.0, 32),
    (2.1, 2.3, 30),
    (2.4, 2.6, 28),
    (2.7, 2.9, 27),
    (3.0, 3.2, 26),
    (3.3, 3.5, 25),
    (3.6, 3.8, 24),
    (3.9, 4.2, 23),
    (4.3, 4.6, 21),
    (4.7, 5.0, 20),
    (5.1, 5.4, 19),
    (5.5, 5.8, 18),
    (5.9, 6.2, 17),
    (6.3, 6.6, 16),
    (6.7, 7.0, 15),
    (7.1, 7.8, 14),
    (7.8, 8.6, 13),
    (8.6, 9.0, 12),
    (9.1, 10.0, 11),
    (10.1, 11.0, 9),
    (11.01, 15.0, 8)
]

# Функция для вычисления нормы для расстояния
def get_norm_for_distance(distance):
    for lower, upper, coeff in distance_coeffs:
        if lower <= distance <= upper:
            return coeff
    return 0  # Если не найдено подходящее расстояние

# Клавиатура для команды /start
def start_keyboard():
    return ReplyKeyboardMarkup(
        [['/reset', '/calculate']],
        one_time_keyboard=True, resize_keyboard=True
    )

# Начало работы с бото



async def start(update: Update, context):
    await update.message.reply_text("Ну, привет. =)")

    # Проверяем, введена ли нормовая путёвка
    if 'norm' not in context.user_data:
        await update.message.reply_text('Для установки нормы, введи число:',
                                        reply_markup=start_keyboard())
        return WAITING_FOR_NORM
    else:
        await update.message.reply_text('Ты уже установил нормовую путёвку. Введи расстояние и количество возов.',
                                        reply_markup=start_keyboard())
        return WAITING_FOR_DISTANCE_AND_VOZ

# Ввод нормовой путёвки
async def set_norm(update: Update, context):
    user_input = update.message.text
    try:
        norm = float(user_input)
        context.user_data['norm'] = norm

        await update.message.reply_text(f'Норма установлена: {int(norm)}. Вводи расстояние и воза через пробел'
                                        f'\nПример: 2.2 10'
                                        f'\n\nУ тебя больше чем одно расстояние? Добавь с нового абзаца.',
                                        reply_markup=start_keyboard(), )
        return WAITING_FOR_DISTANCE_AND_VOZ
    except ValueError:
        await update.message.reply_text('Пожалуйста, введи корректное число для нормовой путёвки.',
                                        reply_markup=start_keyboard())
        return WAITING_FOR_NORM


# Ввод расстояний и возов (поддержка ввода абзацем)
async def handle_distance_and_voz(update: Update, context):
    user_input = update.message.text.strip()

    # Регулярное выражение для поиска пар (расстояние, воза)
    matches = re.findall(r'(\d+(\.\d+)?)\s+(\d+)', user_input)

    if not matches:
        await update.message.reply_text(
            'Не удалось определить расстояния и воза. Введи данные в формате:\n2.2 10\n3.5 5',
            reply_markup=start_keyboard()
        )
        return WAITING_FOR_DISTANCE_AND_VOZ

    if 'distances' not in context.user_data:
        context.user_data['distances'] = []

    # Добавляем новые записи в список
    for match in matches:
        distance = float(match[0])  # Первое число - расстояние
        voz = int(match[2])  # Второе число - количество возов
        context.user_data['distances'].append((distance, voz))

    # Формируем сообщение со ВСЕМИ расстояниями и возами
    all_records = "\n".join([f'Расстояние: {d}, Воза: {v}' for d, v in context.user_data['distances']])

    await update.message.reply_text(
        f'Текущий список расстояний и возов:\n{all_records}\n\n'
        f'Ты можешь добавить ещё или ввести /calculate для расчёта.',
        reply_markup=start_keyboard()
    )
    return WAITING_FOR_DISTANCE_AND_VOZ

# Расчёт и вывод результата
async def calculate(update: Update, context):
    total_salary = 0
    norm = context.user_data.get('norm', 0)
    distances = context.user_data.get('distances', [])

    for distance, voz in distances:
        norm_for_distance = get_norm_for_distance(distance)
        if norm_for_distance != 0:
            earned_money = (norm / norm_for_distance) * voz
            total_salary += earned_money

    # Округляем результат до целого числа
    total_salary = round(total_salary)  # или можно использовать int(total_salary)

    await update.message.reply_text(
        f'Твоя общая заработная плата:  {total_salary} рублей  за смену. \n'
        'Счетчик обнулен, можешь посчитать заново.',
        reply_markup=start_keyboard()
    )

    # Сбрасываем данные для следующего расчёта
    context.user_data['distances'] = []

    # Возвращаемся к ожиданию расстояний и возов
    return WAITING_FOR_DISTANCE_AND_VOZ

# Сброс нормовой путёвки
async def reset_norm(update: Update, context):
    if 'norm' in context.user_data:
        del context.user_data['norm']
        await update.message.reply_text('Нормовая путёвка сброшена. Введи новую нормовую путёвку.',
                                        reply_markup=start_keyboard())
        return WAITING_FOR_NORM
    else:
        await update.message.reply_text('Нормовая путёвка ещё не установлена. Введи свою норму:',
                                        reply_markup=start_keyboard())
        return WAITING_FOR_NORM

# Основная функция
def main():
    application = Application.builder().token("7773666339:AAFLJym_g7H13VqEq7g3wCaV8j7co9pWfh4").build()

    conversation_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            WAITING_FOR_NORM: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_norm)],
            WAITING_FOR_DISTANCE_AND_VOZ: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_distance_and_voz),
                CommandHandler('calculate', calculate)
            ],
        },
        fallbacks=[CommandHandler('reset', reset_norm)],
    )


    application.add_handler(conversation_handler)

    async def set_bot_commands(application):
        commands = [
            BotCommand("reset", "🔄 Сброс нормовой путёвки"),
            BotCommand("calculate", "💰 Рассчитать зарплату")
        ]
        await application.bot.set_my_commands(commands)

        # Устанавливаем команды
        application.job_queue.run_once(lambda _: application.create_task(set_bot_commands(application)), when=1)

    application.run_polling()

if __name__ == '__main__':
    main()
