# pid_bot
Телеграм от для игры правда или действие. Присылает случайное задание из базы данных по категориям в инлайн режиме. Так же есть механизм добавления заданий через бота. Задания отправляются на подтверждение администратору в телеграм.

## Установка
- Задать переменные окружения BOT_TOKEN и ADMIN_ID
- По желанию создать виртуальное окружние 
- Установить зависимости (aiogram, sqlalchemy, aioschedule)
- Запустить bot.py