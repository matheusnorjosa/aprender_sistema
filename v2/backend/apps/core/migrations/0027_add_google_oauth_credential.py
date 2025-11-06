# Generated migration for Sprint 1 - OAuth 2.0 Google Calendar
# Issue #1: Core OAuth - Backend + Frontend
# GAP-2: Encryption key dedicada (GCAL_ENCRYPTION_KEY)
# GAP-5: Multi-calendar preparado (allowed_calendars)

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0026_alter_usuario_cpf'),
    ]

    operations = [
        migrations.CreateModel(
            name='GoogleOAuthCredential',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('google_email', models.EmailField(db_index=True, help_text='E-mail da conta Google conectada (ex: operacional1@aprendereditora.com.br)', max_length=255, verbose_name='E-mail Google')),
                ('access_token_encrypted', models.BinaryField(help_text='Access token criptografado com Fernet (GCAL_ENCRYPTION_KEY)', verbose_name='Access Token (criptografado)')),
                ('refresh_token_encrypted', models.BinaryField(help_text='Refresh token criptografado com Fernet (GCAL_ENCRYPTION_KEY)', verbose_name='Refresh Token (criptografado)')),
                ('token_expiry', models.DateTimeField(help_text='Timestamp UTC de expiração do access token (geralmente 1h)', verbose_name='Expiração do Token')),
                ('scope', models.CharField(default='https://www.googleapis.com/auth/calendar', help_text='Permissões concedidas pelo usuário (separadas por espaço)', max_length=500, verbose_name='Scopes OAuth')),
                ('default_calendar_id', models.CharField(blank=True, default='', help_text="ID do calendário padrão (ex: 'primary' ou ID específico)", max_length=255, verbose_name='Calendário Padrão')),
                ('allowed_calendars', models.JSONField(blank=True, default=list, help_text='Lista de IDs de calendários que o usuário pode publicar (GAP-5: multi-calendar futuro)', verbose_name='Calendários Permitidos')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Conectado em')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Atualizado em')),
                ('user', models.OneToOneField(help_text='Usuário Controle que conectou sua conta Google', on_delete=django.db.models.deletion.CASCADE, related_name='google_oauth', to=settings.AUTH_USER_MODEL, verbose_name='Usuário')),
            ],
            options={
                'verbose_name': 'Credencial OAuth Google',
                'verbose_name_plural': 'Credenciais OAuth Google',
                'db_table': 'core_google_oauth_credential',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='googleoauthcredential',
            index=models.Index(fields=['user', 'token_expiry'], name='core_google_user_id_4f8f1e_idx'),
        ),
        migrations.AddIndex(
            model_name='googleoauthcredential',
            index=models.Index(fields=['google_email'], name='core_google_google__62ff5d_idx'),
        ),
        migrations.AddIndex(
            model_name='googleoauthcredential',
            index=models.Index(fields=['token_expiry'], name='core_google_token_e_3b0c3e_idx'),
        ),
    ]
