import importlib
import pkgutil

from telegram.ext import Application
from bot.common import TOKEN

def _load_handlers(package_name):
    package = importlib.import_module(package_name)
    handlers = []
    for _, module_name, _ in pkgutil.iter_modules(package.__path__):
        module = importlib.import_module(f"{package_name}.{module_name}")
        if hasattr(module, "handler"):
            handlers.append(module.handler)
            print(f"{module_name} Handler loaded successfully")

    return handlers

async def post_init(app):
    await app.bot.set_my_commands([
        ("attendance_add", "Usage Example - /attendance_add junnie 0745"),
        ("attendance_remove", "Usage Example - /attendance_remove junnie 0745")
    ])

def main():
    app = Application.builder().token(TOKEN).post_init(post_init).build()

    for package in (
        "bot.handlers.commands",
        "bot.handlers.callbacks",
        "bot.handlers.messages",
        "bot.handlers.others",
    ):
        for h in _load_handlers(package):
            app.add_handler(h)

    app.run_polling()


if __name__ == "__main__":
    main()