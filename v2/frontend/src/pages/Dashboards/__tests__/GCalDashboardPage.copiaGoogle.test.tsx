/**
 * GCalDashboardPage — o que a cópia Google → sistema mudou aparece legível na linha do tempo.
 *
 * O registro `GCAL_COPIA_GOOGLE` (horário ou cancelamento feito na agenda do Google) traz
 * `antes`/`depois` e, no horário, o `choque` (D3: copia mesmo com choque e avisa). A tela mostra
 * o que mudou em português e o aviso de choque, em vez do nome técnico da ação.
 */
import { render, screen, fireEvent } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

const { getEventDetailMock } = vi.hoisted(() => ({
    getEventDetailMock: vi.fn(),
}));

vi.mock("../../../api/gcal", () => ({
    getDashboardMetrics: vi
        .fn()
        .mockResolvedValue({ counts: {}, recent_errors: [] }),
    listDashboardEvents: vi.fn().mockResolvedValue({
        count: 1,
        results: [
            {
                id: 7,
                summary: "Formação em Sobral",
                gcal_status: "PUBLISHED",
                gcal_last_sync_at: null,
                gcal_last_error: null,
            },
        ],
    }),
    getDashboardSuccessRate: vi
        .fn()
        .mockResolvedValue({
            published: 0,
            error: 0,
            pending: 0,
            none: 0,
            rate: 0,
        }),
    getDashboardTopInsights: vi
        .fn()
        .mockResolvedValue({ items: [], metric: "municipios", limit: 5 }),
    getDashboardEventDetail: getEventDetailMock,
    reapplyBatch: vi.fn(),
    resyncBatch: vi.fn(),
    buildDashboardEventsExportUrl: vi.fn(),
}));

import GCalDashboardPage from "../GCalDashboardPage";

vi.setConfig({ testTimeout: 20_000 });

const log = (over: Record<string, unknown>) => ({
    id: 1,
    usuario_nome: "Sistema",
    created_at: "2026-11-03T12:00:00+00:00",
    ...over,
});

beforeEach(() => {
    getEventDetailMock.mockResolvedValue({
        id: 7,
        municipio_nome: "Sobral",
        projeto_nome: "Projeto",
        tipo_evento_nome: "Formação",
        inicio: null,
        fim: null,
        usuario_nome: "Operadora",
        coordenador_nome: null,
        fluxo: "NAO_SUPER",
        gcal_status: "PUBLISHED",
        external_event_id: null,
        gcal_last_sync_at: null,
        meet_link: null,
        gcal_payload_hash: null,
        gcal_last_error: null,
        updated_at: null,
        participations: [],
        timeline: [
            log({
                id: 2,
                action: "GCAL_COPIA_GOOGLE",
                details: {
                    solicitacao_id: 7,
                    origem: "gcal_copia",
                    campo: "horario",
                    antes: {
                        inicio: "2026-11-10T12:00:00+00:00",
                        fim: "2026-11-10T15:00:00+00:00",
                    },
                    depois: {
                        inicio: "2026-11-11T13:00:00+00:00",
                        fim: "2026-11-11T16:00:00+00:00",
                    },
                    choque: [
                        { usuario_id: 11, codigo: "E" },
                        { usuario_id: 11, codigo: "T" },
                        { usuario_id: 12, codigo: "E" },
                    ],
                },
            }),
            log({
                id: 3,
                action: "GCAL_COPIA_GOOGLE",
                details: {
                    solicitacao_id: 7,
                    origem: "gcal_copia",
                    campo: "status",
                    motivo: "cancelado_no_google",
                    antes: { status: "aprovado" },
                    depois: { status: "reprovado" },
                },
            }),
        ],
    });
});

describe("GCalDashboardPage — cópia do Google na linha do tempo", () => {
    test("horário copiado mostra antes e depois no fuso de Fortaleza e o aviso de choque", async () => {
        render(<GCalDashboardPage />);
        fireEvent.click(await screen.findByText("Formação em Sobral"));

        expect(
            await screen.findAllByText("Mudança feita no Google"),
        ).toHaveLength(2);
        expect(
            screen.getByText("Horário: 10/11 09:00–12:00 → 11/11 10:00–13:00"),
        ).toBeInTheDocument();
        expect(
            screen.getByText("Choque de agenda: 2 pessoas (E, T)"),
        ).toBeInTheDocument();
    });

    test("cancelamento no Google mostra que o evento foi reprovado", async () => {
        render(<GCalDashboardPage />);
        fireEvent.click(await screen.findByText("Formação em Sobral"));

        expect(
            await screen.findByText(
                "Cancelado no Google: o evento foi reprovado",
            ),
        ).toBeInTheDocument();
        expect(screen.queryByText("GCAL_COPIA_GOOGLE")).not.toBeInTheDocument();
    });
});
