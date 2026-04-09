import os
import sys

from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = 'Core'

    def ready(self):
        if os.getenv("ASF_ENABLE_BACKGROUND_SERVICES", "0") != "1":
            return

        process_role = os.getenv("ASF_PROCESS_ROLE", "all").strip().lower()
        if process_role not in {"all", "worker"}:
            return

        management_commands_to_skip = {
            "migrate",
            "makemigrations",
            "collectstatic",
            "shell",
            "dbshell",
            "createsuperuser",
            "check",
            "test",
        }
        if any(arg in management_commands_to_skip for arg in sys.argv[1:]):
            return

        if "runserver" in sys.argv and os.getenv("RUN_MAIN") == "false":
            return

        from Lib.montior import MainMonitor

        MainMonitor().start()
