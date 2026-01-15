from django.apps import AppConfig


class AppApiConfig(AppConfig):
    name = "plane.app"

    def ready(self):
        """
        Register signal handlers when the app is ready.

        This imports the signals module which registers handlers for:
        - Issue assignment notifications
        - Issue status change notifications
        - Comment notifications
        - Mention notifications
        """
        # Import signals to register handlers
        # pylint: disable=import-outside-toplevel,unused-import
        from plane.app import signals  # noqa: F401
