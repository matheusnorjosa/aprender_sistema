from apps.core.models import Municipio, Projeto, TipoEvento

print("=== PROJETOS (primeiros 10) ===")
for p in Projeto.objects.all()[:10]:
    print(f"{p.codigo}: {p.nome} ({p.fluxo})")
print(f"... Total: {Projeto.objects.count()}\n")

print("=== TIPOS EVENTO ===")
for t in TipoEvento.objects.all():
    print(f"{t.id}: {t.nome}")
print(f"\n=== MUNICÍPIOS (primeiros 10) ===")
for m in Municipio.objects.all()[:10]:
    print(f"{m.nome}-{m.uf}")
print(f"... Total: {Municipio.objects.count()}")
