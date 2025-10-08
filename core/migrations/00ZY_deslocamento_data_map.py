from django.db import migrations

def forwards(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    Des = apps.get_model('core','Deslocamento')
    # Se ainda existir o modelo legado 'Formador' no apps antigo, tentamos mapear por email/nome.
    try:
        Formador = apps.get_model('core','Formador')
        def find_user_by_formador(f):
            if getattr(f,'email',None):
                u = User.objects.filter(email__iexact=f.email.strip()).first()
                if u: return u
            nome = (getattr(f,'nome',None) or '').strip()
            if nome:
                u = (User.objects.filter(first_name__iexact=nome).first()
                     or User.objects.filter(username__iexact=nome.replace(' ','').lower()).first())
                if u: return u
            return None
        for d in Des.objects.all().iterator():
            # se já estiver apontando pra user, pula
            for field in ('pessoa_1_id','pessoa_2_id'):
                val = getattr(d, field)
                # nada a fazer aqui; schema já aponta para User
            # best effort: se houver atributos sombra p1_legacy/p2_legacy, ignore
            pass
        # Nota: se 'Formador' não existir mais, é porque o backfill já foi feito anteriormente; não há o que migrar.
    except LookupError:
        pass

def backwards(apps, schema_editor):
    pass

class Migration(migrations.Migration):
    dependencies = [
        ('core', '00ZZ_deslocamento_to_auth_user'),
    ]
    operations = [migrations.RunPython(forwards, backwards)]
