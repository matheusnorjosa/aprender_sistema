from django.conf import settings

print("STATIC_URL:", settings.STATIC_URL)
print("STATIC_ROOT:", settings.STATIC_ROOT)
print("STATICFILES_DIRS:", settings.STATICFILES_DIRS)
print("WHITENOISE:", any("whitenoise" in m.lower() for m in settings.MIDDLEWARE))
