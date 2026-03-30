import { Spin } from 'antd';

export function FullscreenLoader(): JSX.Element {
  return <Spin size="large" tip="Carregando..." fullscreen />;
}
