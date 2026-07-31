import { Spin } from 'antd';

import type { JSX } from "react";

export function FullscreenLoader(): JSX.Element {
  return <Spin size="large" tip="Carregando..." fullscreen />;
}
