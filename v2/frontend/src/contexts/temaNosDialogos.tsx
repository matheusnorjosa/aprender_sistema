/**
 * DEF-33: os métodos estáticos do antd (Modal.confirm/error/warning/info/success, message e
 * notification) renderizam fora da árvore do App, portanto fora do <ConfigProvider theme>. Sem isto,
 * eles usam o tema padrão do antd: o "Sim, excluir" sai com texto branco no vermelho antigo (3,27:1,
 * abaixo do AA), o botão primário no azul padrão e o tema escuro não chega a eles.
 *
 * `holderRender` é o recurso do antd 5 para dar contexto a esses métodos. O App chama esta função
 * com o tema ativo, e de novo a cada troca de tema.
 */
import type { ReactNode } from 'react';
import { ConfigProvider, type ThemeConfig } from 'antd';
import ptBR from 'antd/locale/pt_BR';

export function aplicarTemaNosDialogos(tema: ThemeConfig): void {
  ConfigProvider.config({
    holderRender: (filhos: ReactNode) => (
      <ConfigProvider locale={ptBR} theme={tema}>
        {filhos}
      </ConfigProvider>
    ),
  });
}
