"""
AS v2 — Cópia Google → Sistema

Lê o que mudou na agenda da organização (syncToken) e traz para o sistema o horário novo e o
cancelamento de evento aprovado e publicado. Desligada: só o comando `gcal_copia` chama.

Regras (decisões do dono de 29/10):
- casa só por `Solicitacao.external_event_id == evento["id"]`; id em mais de uma linha não casa;
- entra só linha `aprovado` + `PUBLISHED`, e só no futuro (`s.inicio >= agora` e, no horário, o
  início novo do Google também); evento em andamento fica de fora (perda aceita);
- cancelado no Google vira `reprovado` (D2), sem `autoridade` no AuditLog (não é decisão humana);
- choque de horário copia mesmo assim e fica registrado (D3);
- SUPER aprovada continua aprovada (D4): a cópia não chama a regra de reaprovação;
- linha adotada (hash nulo) segue com hash nulo (D5).

Nada de dado pessoal no AuditLog, no log ou no `resumo`: só s<id>, u<id>, event ids, datas e códigos.
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportOptionalMemberAccess=false, reportArgumentType=false, reportFunctionMemberAccess=false

from __future__ import annotations

import logging
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from datetime import timezone as dt_timezone
from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import DatabaseError, IntegrityError, connection, transaction
from django.utils import timezone

from apps.core.models import AuditLog, GCalCopiaCursor, Solicitacao
from apps.core.services.solicitacao_availability import check_solicitacao_availability
from apps.core.types import JsonDict

from .client import CalendarClientAdapter, SyncTokenExpirado
from .payload import build_event_payload, compute_payload_hash
from .sync import desvincular_do_google

logger = logging.getLogger(__name__)

# Mais que isto de cancelamentos numa rodada: nenhum é aplicado (freio de massa). Mudar exige PR.
FREIO_CANCELAMENTOS = 5
MAX_ADIADOS = 200
MAX_TENTATIVAS_ADIADO = 5
MAX_IDS_POR_MOTIVO = 200
MAX_FALHAS = 200
# Trava de sessão (classid, objid), a mesma no comando e na task. 1452 é a dos participantes.
_TRAVA_COPIA = (1453, 1)
ORIGEM = "gcal_copia"

COPIAR_HORARIO = "copiar_horario"
CANCELADO = "cancelado"
FREIO = "freio"
ECO = "eco"
SEM_VINCULO = "sem_vinculo"
ID_DUPLICADO = "id_duplicado"
NAO_APROVADA = "nao_aprovada"
ERRO_GCAL = "erro_gcal"
PENDENTE_GCAL = "pendente_gcal"
NAO_PUBLICADA = "nao_publicada"
RECORRENTE = "recorrente"
DIA_INTEIRO = "dia_inteiro"
SEM_HORARIO = "sem_horario"
FIM_ANTES_INICIO = "fim_antes_inicio"
PASSADO = "passado"
MOVIDO_PARA_PASSADO = "movido_para_passado"
TRAVA_OCUPADA = "trava_ocupada"
# Pulos que passam: o event id fica em `cursor.adiados` e é relido na rodada seguinte, porque o
# syncToken não devolve a mesma mudança duas vezes. Linha que sumiu cai em TRAVA_OCUPADA também.
_TRANSITORIOS = frozenset({PENDENTE_GCAL, TRAVA_OCUPADA})
# Erro de um item só: vai para `resumo.falhas` e a rodada segue. O resto (banco caído, HttpError,
# token do Google) aborta a rodada sem mexer no token.
_ERROS_DE_DOMINIO = (IntegrityError, Solicitacao.DoesNotExist, ValidationError)


@dataclass(frozen=True)
class Decisao:
    motivo: str
    solicitacao: Solicitacao | None = None
    inicio: datetime | None = None
    fim: datetime | None = None


@dataclass
class Resultado:
    status: str  # OK | SKIPPED | ERROR
    resumo: dict[str, Any] = field(default_factory=dict)
    erro: str = ""
    token_novo: str | None = None


def _instante(horario: Any) -> datetime | None:
    """`dateTime` do Google (com offset ou Z) como instante em UTC; None se faltar ou vier sem fuso."""
    valor = horario.get("dateTime") if isinstance(horario, dict) else None
    if not isinstance(valor, str):
        return None
    try:
        instante = datetime.fromisoformat(valor)
    except ValueError:
        return None
    if instante.tzinfo is None:
        return None
    return instante.astimezone(dt_timezone.utc)


def decidir(evento: JsonDict, linhas: Sequence[Solicitacao], agora: datetime) -> Decisao:
    """O que fazer com um item do Google. Pura: não lê o banco nem o relógio.

    `linhas` são TODAS as linhas com `external_event_id == evento["id"]`, de qualquer status.
    """
    if not linhas:
        return Decisao(SEM_VINCULO)
    if len(linhas) > 1:
        return Decisao(ID_DUPLICADO)
    s = linhas[0]
    if s.status != Solicitacao.Status.APROVADO:
        return Decisao(NAO_APROVADA, s)
    if s.gcal_status == Solicitacao.GCalStatus.PENDING:
        return Decisao(PENDENTE_GCAL, s)
    if s.gcal_status == Solicitacao.GCalStatus.ERROR:
        # Pode ter edição do sistema que ainda não chegou ao Google: o Google não vence aqui.
        return Decisao(ERRO_GCAL, s)
    if s.gcal_status != Solicitacao.GCalStatus.PUBLISHED:
        return Decisao(NAO_PUBLICADA, s)
    if evento.get("recurringEventId") or evento.get("recurrence"):
        return Decisao(RECORRENTE, s)
    if evento.get("status") == "cancelled":
        # A lápide só traz id e status: só dá para olhar o início do sistema.
        return Decisao(CANCELADO if s.inicio >= agora else PASSADO, s)
    if isinstance(evento.get("start"), dict) and evento["start"].get("date"):
        return Decisao(DIA_INTEIRO, s)
    inicio, fim = _instante(evento.get("start")), _instante(evento.get("end"))
    if inicio is None or fim is None:
        return Decisao(SEM_HORARIO, s)
    if fim <= inicio:
        return Decisao(FIM_ANTES_INICIO, s)
    if inicio == s.inicio and fim == s.fim:
        return Decisao(ECO, s)
    if s.inicio < agora:
        return Decisao(PASSADO, s)  # inclui o evento em andamento
    if inicio < agora:
        return Decisao(MOVIDO_PARA_PASSADO, s)
    return Decisao(COPIAR_HORARIO, s, inicio, fim)


class _Resumo:
    """Contagens por motivo, s<id> por motivo (sem repetição), futuro/passado e falhas."""

    def __init__(self, modo: str, agora: datetime) -> None:
        self.modo = modo
        self.agora = agora
        self.contagens: dict[str, int] = {}
        self.ids: dict[str, set[int]] = {}
        self.futuro = 0
        self.passado = 0
        self.falhas: list[dict[str, str]] = []
        self.freio = 0
        self.leitura_completa = False
        self.lidos = 0

    def conta(self, d: Decisao) -> None:
        self.contagens[d.motivo] = self.contagens.get(d.motivo, 0) + 1
        if d.solicitacao is not None:
            self.ids.setdefault(d.motivo, set()).add(d.solicitacao.pk)
            if d.solicitacao.inicio >= self.agora:
                self.futuro += 1
            else:
                self.passado += 1

    def falha(self, event_id: str, motivo: str) -> None:
        self.falhas.append({"event_id": event_id, "motivo": motivo})

    def como_dict(self, anterior: dict[str, Any] | None = None) -> dict[str, Any]:
        """O resumo da rodada; no `observar` ele soma ao da rodada anterior do mesmo modo."""
        contagens = dict(self.contagens)
        ids = {m: set(v) for m, v in self.ids.items()}
        futuro, passado, falhas, rodadas = self.futuro, self.passado, list(self.falhas), 1
        if anterior:
            for m, n in anterior.get("contagens", {}).items():
                contagens[m] = contagens.get(m, 0) + int(n)
            for m, lista in anterior.get("ids", {}).items():
                ids.setdefault(m, set()).update(int(x[1:]) for x in lista)
            futuro += int(anterior.get("futuro", 0))
            passado += int(anterior.get("passado", 0))
            falhas = [*anterior.get("falhas", []), *falhas]
            rodadas += int(anterior.get("rodadas", 1))
        return {
            "modo": self.modo,
            "em": self.agora.isoformat(),
            "rodadas": rodadas,
            "lidos": self.lidos,
            "leitura_completa": self.leitura_completa,
            "contagens": contagens,
            "ids": {m: [f"s{pk}" for pk in sorted(v)[:MAX_IDS_POR_MOTIVO]] for m, v in sorted(ids.items())},
            "futuro": futuro,
            "passado": passado,
            "falhas": falhas[-MAX_FALHAS:],
            "freio": self.freio,
        }


def _erro_curto(e: BaseException) -> str:
    """Tipo do erro e status HTTP, nunca a mensagem (o texto do Google pode trazer e-mail)."""
    status = getattr(getattr(e, "resp", None), "status", None)
    return f"{type(e).__name__} {status}" if status is not None else type(e).__name__


@contextmanager
def _trava_da_copia() -> Iterator[bool]:
    """`pg_try_advisory_lock` de sessão; solta no `finally`. Se o processo morre, a conexão leva a trava."""
    with connection.cursor() as c:
        c.execute("SELECT pg_try_advisory_lock(%s, %s)", list(_TRAVA_COPIA))
        livre = bool(c.fetchone()[0])
    try:
        yield livre
    finally:
        if livre:
            try:
                with connection.cursor() as c:
                    c.execute("SELECT pg_advisory_unlock(%s, %s)", list(_TRAVA_COPIA))
                    if not c.fetchone()[0]:
                        logger.warning("gcal_copia: a trava já não estava com esta sessão")
            except DatabaseError:
                logger.warning("gcal_copia: não deu para soltar a trava (conexão caiu; sai com ela)")


def _travar_linha(pk: int) -> Solicitacao | None:
    """A linha travada para escrita; None se outra transação a segura ou se ela sumiu."""
    return Solicitacao.objects.select_for_update(skip_locked=True).filter(pk=pk).first()


def _linhas_por_event_id(event_ids: Sequence[str]) -> dict[str, list[Solicitacao]]:
    """Todas as linhas com cada event id, de qualquer status (o duplicado conta antes do filtro)."""
    por_id: dict[str, list[Solicitacao]] = {}
    for s in Solicitacao.objects.filter(external_event_id__in=list(event_ids)).select_related("projeto"):
        por_id.setdefault(str(s.external_event_id), []).append(s)
    return por_id


def _copiar_horario(s: Solicitacao, d: Decisao, event_id: str, operador_id: int) -> None:
    assert d.inicio is not None and d.fim is not None
    antes = {"inicio": s.inicio.isoformat(), "fim": s.fim.isoformat()}
    # Já fora de dia com o Google (título, convidados, local): o PATCH só da descrição não acerta
    # isso, então o hash vira nulo e o próximo Reapply manda tudo.
    if s.gcal_payload_hash is not None and s.gcal_payload_hash != compute_payload_hash(s):
        s.gcal_payload_hash = None
    s.inicio, s.fim = d.inicio, d.fim
    s.save(update_fields=["inicio", "fim", "gcal_payload_hash", "updated_at"])
    # D3: copia mesmo com choque; só ids e códigos (nada de nome, título ou e-mail de convidado).
    guarda = check_solicitacao_availability(s, lock=True)
    choque = sorted({(p.usuario_id, c.code) for p in guarda.blocked for c in p.conflicts})
    details: dict[str, Any] = {
        "solicitacao_id": s.pk,
        "origem": ORIGEM,
        "event_id": event_id,
        "campo": "horario",
        "antes": antes,
        "depois": {"inicio": s.inicio.isoformat(), "fim": s.fim.isoformat()},
        "choque": [{"usuario_id": uid, "codigo": codigo} for uid, codigo in choque],
    }
    if getattr(s.projeto, "fluxo", None) == "SUPER":
        # D4: continua aprovada; a regra da reaprovação (PA-04) não vale para a cópia.
        details["aprovada_como_super"] = True
        details["mudou_material_sem_reaprovacao"] = True
    AuditLog.objects.create(
        usuario=None, action=AuditLog.Action.GCAL_COPIA_GOOGLE, model_name="Solicitacao", details=details
    )
    pk = s.pk

    def _enfileirar() -> None:
        from apps.core.tasks import task_gcal_copia_descricao

        task_gcal_copia_descricao.delay(pk, operador_id)

    # Só depois do commit do item: rollback ou dry-run não chegam ao Google.
    transaction.on_commit(_enfileirar)


def _reprovar(s: Solicitacao, event_id: str) -> None:
    """D2, no formato da carga da virada: REJECT sem `autoridade` + o registro da linha do tempo."""
    status_anterior = s.status
    s.status = Solicitacao.Status.REPROVADO
    s.save(update_fields=["status", "updated_at"])
    AuditLog.objects.create(
        usuario=None,
        action=AuditLog.Action.REJECT,
        model_name="Solicitacao",
        details={
            "solicitacao_id": s.pk,
            "origem": ORIGEM,
            "motivo": "cancelado_no_google",
            "status_anterior": status_anterior,
            "event_id_antigo": event_id,
        },
    )
    AuditLog.objects.create(
        usuario=None,
        action=AuditLog.Action.GCAL_COPIA_GOOGLE,
        model_name="Solicitacao",
        details={
            "solicitacao_id": s.pk,
            "origem": ORIGEM,
            "event_id": event_id,
            "campo": "status",
            "motivo": "cancelado_no_google",
            "antes": {"status": status_anterior},
            "depois": {"status": Solicitacao.Status.REPROVADO},
        },
    )
    # O evento já está cancelado no Google: só limpa o vínculo, sem chamar o Google.
    desvincular_do_google(s)


def _aplicar_item(
    pk: int, event_id: str, evento: JsonDict, agora: datetime, operador_id: int, freio: bool, lido_em: datetime
) -> Decisao:
    """Grava um item na própria transação, com a linha travada e a decisão refeita sob a trava."""
    with transaction.atomic():
        s = _travar_linha(pk)
        if s is None:
            return Decisao(TRAVA_OCUPADA)
        if s.gcal_last_sync_at and s.gcal_last_sync_at >= lido_em:
            # O sistema publicou a linha depois da leitura: o item lido já não vale. Relê na próxima.
            return Decisao(PENDENTE_GCAL, s)
        linhas = [s] if s.external_event_id == event_id else []
        if linhas:
            linhas += list(Solicitacao.objects.filter(external_event_id=event_id).exclude(pk=s.pk))
        d = decidir(evento, linhas, agora)
        if d.motivo == COPIAR_HORARIO:
            _copiar_horario(s, d, event_id, operador_id)
        elif d.motivo == CANCELADO and freio:
            d = Decisao(FREIO, s)
        elif d.motivo == CANCELADO:
            _reprovar(s, event_id)
        return d


def sincronizar(
    cursor: GCalCopiaCursor,
    client: CalendarClientAdapter,
    *,
    escrever: bool,
    agora: datetime | None = None,
    operador_id: int | None = None,
    liberar_freio: bool = False,
) -> Resultado:
    """
    Uma rodada da cópia.

    - `escrever=False` (dry-run): lê e decide; não grava nada (nem o cursor) e não chama a fila.
    - `escrever=True` + `observar`: grava só o cursor (token, resumo somado, adiados).
    - `escrever=True` + `copiar`: grava o horário e o cancelamento, item a item.

    `operador_id` (padrão `cursor.operador_id`) é quem faz o PATCH da descrição depois.
    `liberar_freio` é a saída manual do dono para uma rodada que o freio de massa segurou.
    """
    agora = agora or timezone.now()
    pino = str(getattr(settings, "GCAL_OAUTH_CALENDAR_ID", "") or "")
    if not pino or pino == "primary" or cursor.calendar_id != pino:
        return Resultado("ERROR", erro="calendário do cursor não é o pino da organização")
    operador_id = operador_id or cursor.operador_id
    aplicar = escrever and cursor.modo == GCalCopiaCursor.Modo.COPIAR
    if aplicar and operador_id is None:
        return Resultado("ERROR", erro="modo copiar sem operador")
    if not escrever:
        return _rodada(cursor, client, pino, agora, escrever=False, aplicar=False, operador_id=0, liberar_freio=False)
    with _trava_da_copia() as livre:
        if not livre:
            logger.info("gcal_copia: outra rodada em execução; pulada")
            return Resultado("SKIPPED", erro="cópia já em execução")
        # O modo e o token valem como estão sob a trava: a ordem de parar (`observar`) não se perde.
        cursor.refresh_from_db()
        operador_id = operador_id or cursor.operador_id
        aplicar = cursor.modo == GCalCopiaCursor.Modo.COPIAR
        if aplicar and operador_id is None:
            return Resultado("ERROR", erro="modo copiar sem operador")
        return _rodada(
            cursor,
            client,
            pino,
            agora,
            escrever=True,
            aplicar=aplicar,
            operador_id=operador_id or 0,
            liberar_freio=liberar_freio,
        )


def _rodada(
    cursor: GCalCopiaCursor,
    client: CalendarClientAdapter,
    calendario: str,
    agora: datetime,
    *,
    escrever: bool,
    aplicar: bool,
    operador_id: int,
    liberar_freio: bool,
) -> Resultado:
    resumo = _Resumo(cursor.modo, agora)
    token_lido = cursor.sync_token
    tentativas = {
        str(a["event_id"]): int(a.get("tentativas", 0))
        for a in (cursor.adiados or [])
        if isinstance(a, dict) and a.get("event_id")
    }
    adiados: dict[str, int] = {}
    freio = False
    lido_em = timezone.now()
    try:
        # 1) Adiados da rodada anterior: o syncToken não os traz de novo, então relê um a um.
        eventos: dict[str, JsonDict] = {}
        for event_id in tentativas:
            evento = client.get(calendario, event_id)
            if evento is None:
                resumo.falha(event_id, "sumiu_do_google")
            else:
                eventos[event_id] = evento
        # 2) O que mudou desde o token. 410: leitura completa na mesma rodada (decide por valor).
        try:
            itens, token_novo = client.list_changes(calendario, token_lido)
        except SyncTokenExpirado:
            itens, token_novo = client.list_changes(calendario, None)
            resumo.leitura_completa = True
        resumo.leitura_completa = resumo.leitura_completa or token_lido is None
        for item in itens:
            if item.get("id"):
                eventos[str(item["id"])] = item  # o item da leitura é mais novo que o do GET
        resumo.lidos = len(eventos)

        linhas = _linhas_por_event_id(list(eventos))
        decisoes = {eid: decidir(ev, linhas.get(eid, []), agora) for eid, ev in eventos.items()}
        cancelamentos = sum(1 for d in decisoes.values() if d.motivo == CANCELADO)
        # O freio do `copiar` fica puxado: se a rodada anterior segurou o token, segue segurando até o
        # dono liberar ou não sobrar cancelamento (a contagem cai quando um vira passado ou volta).
        # Vale também no dry-run do `copiar`, para a prévia dar o mesmo veredito do --apply.
        segurado = (
            cursor.modo == GCalCopiaCursor.Modo.COPIAR
            and isinstance(cursor.resumo, dict)
            and cursor.resumo.get("modo") == GCalCopiaCursor.Modo.COPIAR
            and int(cursor.resumo.get("freio", 0)) > 0
        )
        # A liberação do dono só cobre os s<id> que ele viu segurados: se entrou algum outro, a rodada
        # segue segurada com a lista nova e ele libera de novo depois de vê-la. Lista cortada em
        # MAX_IDS_POR_MOTIVO: o que ficou de fora não está em `vistos` e o freio segue puxado.
        vistos = set(cursor.resumo.get("ids", {}).get(FREIO, [])) if segurado else set()
        atuais = {
            f"s{d.solicitacao.pk}" for d in decisoes.values() if d.motivo == CANCELADO and d.solicitacao is not None
        }
        liberado = liberar_freio and bool(atuais) and atuais <= vistos
        freio = (cancelamentos > FREIO_CANCELAMENTOS or (segurado and cancelamentos > 0)) and not liberado
        if freio:
            resumo.freio = cancelamentos

        for event_id, d in decisoes.items():
            if aplicar and d.motivo in (COPIAR_HORARIO, CANCELADO) and d.solicitacao is not None:
                try:
                    d = _aplicar_item(d.solicitacao.pk, event_id, eventos[event_id], agora, operador_id, freio, lido_em)
                except _ERROS_DE_DOMINIO as e:
                    resumo.falha(event_id, type(e).__name__)
                    continue
            elif d.motivo == CANCELADO and freio:
                d = Decisao(FREIO, d.solicitacao)
            resumo.conta(d)
            if d.motivo in _TRANSITORIOS:
                n = tentativas.get(event_id, 0) + 1
                if n >= MAX_TENTATIVAS_ADIADO:
                    resumo.falha(event_id, f"adiado_{MAX_TENTATIVAS_ADIADO}x")
                elif len(adiados) >= MAX_ADIADOS:
                    resumo.falha(event_id, "adiados_cheio")
                else:
                    adiados[event_id] = n
    except Exception as e:  # infraestrutura: aborta, token intacto
        erro = _erro_curto(e)
        logger.error("gcal_copia: rodada abortada (%s); token intacto", erro)
        if escrever and cursor.pk:
            GCalCopiaCursor.objects.filter(pk=cursor.pk).update(ultimo_erro=erro, updated_at=timezone.now())
        return Resultado("ERROR", resumo.como_dict(), erro)

    anterior = cursor.resumo if cursor.modo == GCalCopiaCursor.Modo.OBSERVAR else None
    if not (isinstance(anterior, dict) and anterior.get("modo") == GCalCopiaCursor.Modo.OBSERVAR):
        anterior = None
    dados = resumo.como_dict(anterior)
    ultimo_erro = f"freio: {resumo.freio} cancelamentos" if freio else ""
    logger.info(
        "gcal_copia: modo=%s lidos=%s contagens=%s falhas=%s freio=%s",
        cursor.modo,
        resumo.lidos,
        resumo.contagens,
        len(resumo.falhas),
        resumo.freio,
    )
    if not escrever:
        return Resultado("OK", dados, ultimo_erro, token_novo)

    campos: dict[str, Any] = {
        "resumo": dados,
        "adiados": [{"event_id": eid, "tentativas": n} for eid, n in adiados.items()],
        "ultimo_sucesso_em": timezone.now(),
        "ultimo_erro": ultimo_erro,
        "updated_at": timezone.now(),
    }
    # Com o freio no `copiar`, o token NÃO avança: os cancelamentos voltam na próxima rodada até o
    # dono liberar (`liberar_freio`). O horário copiado nesta rodada volta como eco, sem efeito. No
    # `observar` nada é aplicado: o token avança e o freio fica só como aviso.
    if not (freio and aplicar):
        campos["sync_token"] = token_novo
    # Compare-and-set: só grava se ninguém trocou o token nem o modo durante a rodada (`trocar_modo`).
    if not GCalCopiaCursor.objects.filter(pk=cursor.pk, sync_token=token_lido, modo=cursor.modo).update(**campos):
        logger.warning("gcal_copia: o token mudou durante a rodada; resultado descartado")
        return Resultado("ERROR", dados, "o token mudou durante a rodada", token_novo)
    return Resultado("OK", dados, ultimo_erro, token_novo)


def trocar_modo(cursor: GCalCopiaCursor, modo: str) -> None:
    """Troca o modo. Ir para `copiar` zera o token: a 1ª rodada relê tudo e decide por valor, e pega
    toda edição feita no Google enquanto a cópia só observava."""
    cursor.modo = modo
    campos = ["modo", "updated_at"]
    if modo == GCalCopiaCursor.Modo.COPIAR:
        cursor.sync_token = None
        campos.append("sync_token")
    cursor.save(update_fields=campos)


def atualizar_descricao_no_google(
    solicitacao_id: int, operador_id: int, *, client: CalendarClientAdapter | None = None
) -> str:
    """
    Depois da cópia do horário: PATCH só da descrição (a linha "📅 Data"), sem convite por e-mail.

    O hash só é recalculado se não era nulo e só depois do PATCH dar certo; na linha adotada fica
    nulo (D5). Se o PATCH falha, o hash antigo fica e o próximo Reapply manda tudo.
    """
    calendario = str(getattr(settings, "GCAL_OAUTH_CALENDAR_ID", "") or "")
    if not calendario or calendario == "primary":
        return "pulado"
    if client is None:
        # Fora da transação, como no `excluir`: o refresh do token grava (e, no invalid_grant, apaga a
        # credencial e registra o GOOGLE_DISCONNECT) e isso não pode voltar no rollback daqui.
        from apps.core.models import Usuario
        from apps.core.services.gcal_client_factory import get_oauth_client_for_user

        client, _ = get_oauth_client_for_user(Usuario.objects.get(pk=operador_id))
    with transaction.atomic():
        s = Solicitacao.objects.select_for_update().filter(pk=solicitacao_id).first()
        if (
            s is None
            or s.status != Solicitacao.Status.APROVADO
            or s.gcal_status != Solicitacao.GCalStatus.PUBLISHED
            or not s.external_event_id
        ):
            return "pulado"
        client.patch_descricao(calendario, s.external_event_id, build_event_payload(s)["description"])
        if s.gcal_payload_hash is not None:
            s.gcal_payload_hash = compute_payload_hash(s)
            s.save(update_fields=["gcal_payload_hash"])
    return "ok"
